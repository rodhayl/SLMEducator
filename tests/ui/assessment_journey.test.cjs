/* Synthetic DOM journeys; these are not live-browser or live-provider acceptance. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const root = path.resolve(__dirname, '../../src/web');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const reply = (status, data) => ({ ok: status >= 200 && status < 300, status, json: async () => data });
const settle = async () => { await new Promise(resolve => setImmediate(resolve)); await new Promise(resolve => setImmediate(resolve)); };
async function fixture(t, page, query = '', role = 'student') {
    const dom = new JSDOM(read(page), { url: `http://localhost/${page}${query}`, runScripts: 'outside-only', pretendToBeVisual: true });
    t.after(() => dom.window.close());
    const w = dom.window;
    await settle();
    w.owner = 7;
    w.AuthService = { getUser: () => ({ id: w.owner }), getToken: () => 'synthetic-token', isAuthenticated: () => true, getRole: () => role };
    w.I18n = { t: key => key, init: async () => {}, translatePage: () => {} };
    w.toasts = [];
    w.showToast = (...args) => w.toasts.push(args);
    w.showConfirm = async () => true;
    w.modals = [];
    w.showInfoModal = (title, html) => {
        const modal = w.document.createElement('div');
        modal.dataset.modalTitle = title;
        modal.innerHTML = w.SLMRender.html(html);
        w.document.body.append(modal); w.modals.push(modal);
    };
    for (const file of ['static/vendor/dompurify@3.4.16/purify.min.js', 'static/vendor/marked@15.0.12/marked.min.js', 'static/js/safe-render.js', 'static/js/learning-client.js', 'static/js/time-display.js']) w.eval(read(file));
    w.requests = [];
    w.respond = async () => reply(200, {});
    w.fetch = async (url, options = {}) => {
        w.requests.push({ url, options });
        if (url === '/api/settings/timezone') return reply(200, { timezone: 'UTC' });
        return w.respond(url, options);
    };
    w.loadScript = name => w.eval(read(`static/js/${name}`).replace(/^import .*;$/gm, '').replace(/export (?=async function|function)/g, ''));
    return w;
}
const assessment = { id: 4, title: 'Synthetic assessment', description: 'Practice', question_count: 2, is_published: true, time_limit_minutes: null, questions: [
    { id: 10, question_text: '<img src=x onerror=unsafe()> Choose', question_type: 'multiple_choice', points: 10, options: { choices: ['A', 'B'] } },
    { id: 11, question_text: 'Explain', question_type: 'short_answer', points: 20 }
] };
const submission = (overrides = {}) => ({ id: 21, assessment_id: 4, assessment_title: '<img src=x onerror=unsafe()> Assessment', student_id: 7, student_name: 'Synthetic Learner', status: 'graded', score: 0, total_points: 30, feedback: '<script>unsafe()</script> Review your reasoning.', submitted_at: '2026-10-04T12:00:00Z', graded_at: '2026-10-04T13:00:00Z', answers: [
    { response_id: 30, question_id: 11, question_text: 'Explain <svg/onload=unsafe()>', given_answer: '<img src=x onerror=unsafe()> My answer', correct_answer: 'HIDDEN ANSWER KEY', points: 0, max_points: 30, feedback: 'Teacher says: justify the first step.', ai_suggested_score: 7, ai_suggested_feedback: 'Provisional advice' }
], ...overrides });

for (const role of ['teacher', 'admin']) test(`${role} gets working statistics and GET-only preview instead of Start`, async t => {
    const w = await fixture(t, 'dashboard.html', '', role);
    w.respond = async url => reply(200, url === '/api/assessments/' ? [assessment] : url.endsWith('/stats') ? { total_submissions: 1, average_score: 0, highest_score: 0, lowest_score: 0, pass_rate: 0 } : assessment);
    w.loadScript('assessment.js');
    await w.loadAssessments();
    const list = w.document.getElementById('assessment-list');
    assert.equal(list.querySelector('a[href*="assessment_taker"]'), null);
    assert.equal(list.querySelector('[onclick*="viewAssessmentStats"]'), null);
    list.querySelector('[data-assessment-action="stats"]').click(); await settle();
    assert.match(w.modals[0].textContent, /0\.0%/);
    list.querySelector('[data-assessment-action="preview"]').click(); await settle();
    assert.match(w.modals[1].textContent, /does not start or use an attempt/);
    assert.match(w.modals[1].textContent, /Choose/);
    assert.equal(w.modals[1].querySelector('img,script,svg'), null);
    assert.equal(w.requests.some(request => request.options.method === 'POST' || request.url.endsWith('/start')), false);
});

test('student assessment cards link separately to taking and read-only feedback', async t => {
    const w = await fixture(t, 'dashboard.html');
    w.respond = async () => reply(200, [assessment]);
    w.loadScript('assessment.js'); await w.loadAssessments();
    const list = w.document.getElementById('assessment-list');
    assert.equal(list.querySelector('a[href="assessment_taker.html?id=4"]').textContent, 'Start or resume quiz');
    assert.ok(list.querySelector('a[href="assessment_history.html?assessment_id=4"]'));
    assert.equal(list.querySelector('[data-assessment-action]'), null);
});

test('grading opens a submission deep link and returns to its dashboard filter', async t => {
    const w = await fixture(t, 'grading.html', '?submission_id=21&filter=pending', 'teacher');
    w.respond = async url => reply(200, url.includes('submissions?') ? [submission({status:'submitted'})] : submission({status:'submitted',score:null}));
    w.loadScript('grading.js'); await w.initializeGrading();
    assert.match(w.document.getElementById('submission-title').textContent, /Synthetic Learner/);
    assert.equal(w.document.querySelector('#grading-filter-tabs [data-filter="pending"]').getAttribute('aria-pressed'), 'true');
    assert.equal(w.document.getElementById('grading-dashboard-link').getAttribute('href'), 'dashboard.html?view=grading&grading_filter=pending');
    assert.equal(w.document.querySelector('#answers-container img, #answers-container svg'), null);
    assert.equal(w.document.getElementById('grade-score').disabled, false);
    w.filterSubmissions('graded');
    assert.match(w.document.getElementById('grading-dashboard-link').href, /grading_filter=graded$/);
    assert.match(w.location.search, /filter=graded/);
});

test('grading saves integer zero and refreshes current status and feedback', async t => {
    const w = await fixture(t, 'grading.html', '?submission_id=21&filter=pending', 'teacher');
    let saved = false;
    w.respond = async (url, options) => {
        if (options.method === 'POST') { assert.deepEqual(JSON.parse(options.body), {score:0,feedback:'Revise the opening step.'}); saved = true; return reply(200, {status:'ok'}); }
        const sub = submission({ status: saved ? 'graded' : 'submitted', feedback: saved ? 'Revise the opening step.' : '', score: saved ? 0 : null });
        return reply(200, url.includes('submissions?') ? [sub] : sub);
    };
    w.loadScript('grading.js'); await w.initializeGrading();
    w.document.getElementById('grade-score').value = '0';
    w.document.getElementById('grade-feedback').value = 'Revise the opening step.';
    await w.submitGrade();
    assert.equal(saved, true);
    assert.match(w.document.getElementById('submission-status').textContent, /Final grade/);
    assert.equal(w.document.getElementById('grade-score').value, '0');
    assert.equal(w.document.getElementById('grade-feedback').value, 'Revise the opening step.');
    assert.match(w.document.getElementById('submission-list').textContent, /No submissions match/);
    assert.equal(w.document.getElementById('grading-dashboard-link').getAttribute('href'), 'dashboard.html?view=grading&grading_filter=pending');
});

test('grading rejects fractional scores before sending and keeps failed selection uneditable', async t => {
    const w = await fixture(t, 'grading.html', '?submission_id=21', 'teacher');
    w.respond = async url => url.endsWith('/22') ? reply(403,{detail:'Not yours'}) : reply(200,url.includes('submissions?') ? [submission()] : submission());
    w.loadScript('grading.js'); await w.initializeGrading();
    w.document.getElementById('grade-score').value = '2.5'; await w.submitGrade();
    assert.equal(w.requests.some(request => request.options.method === 'POST'), false);
    await w.selectSubmission({id:22});
    assert.match(w.document.getElementById('answers-container').textContent, /permission/);
    assert.equal(w.document.getElementById('grade-score').disabled,true);
    assert.equal(w.document.getElementById('grade-score').value,'');
});

test('grading ignores late details after another submission is selected', async t => {
    const w = await fixture(t, 'grading.html', '', 'teacher');
    let resolveFirst;
    w.respond = async url => url.endsWith('/21') ? new Promise(resolve => { resolveFirst = resolve; }) : reply(200, submission({id:22,assessment_title:'Current selection'}));
    w.loadScript('grading.js');
    const first = w.selectSubmission({id:21}); await settle();
    await w.selectSubmission({id:22});
    resolveFirst(reply(200,submission())); await first;
    assert.match(w.document.getElementById('submission-title').textContent,/Current selection/);
    assert.match(w.location.search,/submission_id=22/);
});

test('learner history deep link shows final zero and teacher feedback without grading keys or new attempt', async t => {
    const w = await fixture(t, 'assessment_history.html', '?submission_id=21&assessment_id=4');
    w.respond = async url => reply(200,url.endsWith('/submissions') ? [submission(),submission({id:22,assessment_id:5})] : submission({rubric:{name:'Reasoning',criteria:[{name:'Evidence',description:'Explain why',max_points:30}]}}));
    w.loadScript('assessment_history.js'); await w.initializeSubmissionHistory();
    const detail = w.document.getElementById('learner-submission-detail');
    assert.match(detail.textContent,/Final score: 0 \/ 30/);
    assert.match(detail.textContent,/Question score: 0 \/ 30/);
    assert.match(detail.textContent,/Teacher says: justify/);
    assert.match(detail.textContent,/Review your reasoning/);
    assert.doesNotMatch(detail.textContent,/Assessment rubric|Evidence/);
    assert.doesNotMatch(detail.textContent,/HIDDEN ANSWER KEY|Provisional advice/);
    assert.equal(detail.querySelector('script,img,svg'),null);
    assert.equal(w.document.querySelectorAll('#learner-submission-list a').length,1);
    assert.equal(w.requests.every(request => !request.options.method || request.options.method === 'GET'),true);
    assert.equal(w.requests.some(request => request.url.endsWith('/start')),false);
});

test('learner pending score is a labelled AI suggestion and is never presented as final', async t => {
    const w = await fixture(t,'assessment_history.html','?submission_id=21');
    w.respond = async url => reply(200,url.endsWith('/submissions') ? [submission({status:'ai_graded',score:7})] : submission({status:'ai_graded',score:7}));
    w.loadScript('assessment_history.js'); await w.initializeSubmissionHistory();
    const detail = w.document.getElementById('learner-submission-detail').textContent;
    assert.match(detail,/Pending teacher review/);
    assert.match(detail,/AI suggestion, awaiting teacher review: 7 \/ 30/);
    assert.doesNotMatch(detail,/Final score:|Question score:/);
});

for (const status of [401,403,500]) test(`learner HTTP ${status} detail error can retry without any POST`, async t => {
    const w = await fixture(t,'assessment_history.html','?submission_id=21');
    let fail = true;
    w.respond = async url => reply(url.endsWith('/submissions') ? 200 : fail ? status : 200,url.endsWith('/submissions') ? [submission()] : fail ? {detail:'Synthetic failure'} : submission());
    w.loadScript('assessment_history.js'); await w.initializeSubmissionHistory();
    const detail = w.document.getElementById('learner-submission-detail');
    assert.equal(detail.querySelector('button').textContent,'Retry');
    fail = false; detail.querySelector('button').click(); await settle();
    assert.match(detail.textContent,/Final score: 0/);
    assert.equal(w.requests.some(request => request.options.method === 'POST'),false);
});

test('learner history ignores late submission details and account changes', async t => {
    const w = await fixture(t,'assessment_history.html');
    w.respond = async () => reply(200,[]);
    w.loadScript('assessment_history.js'); await w.initializeSubmissionHistory();
    let resolveFirst;
    w.respond = async url => url.endsWith('/21') ? new Promise(resolve => {resolveFirst = resolve;}) : reply(200,submission({id:22,assessment_title:'Current assessment'}));
    const first = w.loadLearnerSubmission(21); await settle();
    await w.loadLearnerSubmission(22); resolveFirst(reply(200,submission())); await first;
    assert.equal(w.document.getElementById('submission-detail-heading').textContent,'Current assessment');
    const next = w.loadLearnerSubmission(21); await settle();
    w.owner = 99; resolveFirst(reply(200,submission())); await next;
    assert.doesNotMatch(w.document.getElementById('learner-submission-detail').textContent,/Review your reasoning/);
});

async function takerFixture(t) {
    const w = await fixture(t,'assessment_taker.html','?id=4');
    w.respond = async url => reply(200,url.endsWith('/start') ? {submission_id:21} : assessment);
    w.loadScript('assessment_taker.js'); await w.loadAssessment();
    w.document.querySelector('textarea').value = 'Keep this unfinished reasoning';
    return w;
}

test('closing an attempt requires confirmation, preserves local answers and links history on success', async t => {
    const w = await takerFixture(t);
    let confirmation;
    w.showConfirm = async message => { confirmation = message; return true; };
    w.respond = async (url,options) => {
        assert.equal(url,'/api/assessments/submissions/21/close');
        assert.deepEqual(JSON.parse(options.body),{reason:'abandoned',answers:[{question_id:10,response_text:''},{question_id:11,response_text:'Keep this unfinished reasoning'}]});
        assert.equal(w.SLMClient.drafts.read('assessment',4,21).answers[1].response_text,'Keep this unfinished reasoning');
        return reply(200,{submission_id:21,status:'abandoned'});
    };
    await w.closeAssessmentAttempt();
    assert.match(confirmation,/still count toward your attempt limit and cannot be resumed/);
    assert.match(w.document.getElementById('results').textContent,/Attempt closed/);
    assert.equal(w.document.querySelector('#results a').getAttribute('href'),'/assessment_history.html?submission_id=21');
    assert.equal(w.document.querySelector('textarea').disabled,true);
    assert.equal(w.SLMClient.drafts.read('assessment',4,21).answers[1].response_text,'Keep this unfinished reasoning');
    const requests = w.requests.length; await w.submitAssessment(); await w.closeAssessmentAttempt();
    assert.equal(w.requests.length,requests);
});

test('cancelling attempt closure leaves the active form and makes no close request', async t => {
    const w = await takerFixture(t);
    w.showConfirm = async () => false;
    await w.closeAssessmentAttempt();
    assert.equal(w.requests.some(request => request.url.endsWith('/close')),false);
    assert.equal(w.document.querySelector('textarea').disabled,false);
    assert.equal(w.document.getElementById('close-attempt-btn').disabled,false);
});

for (const status of [401,403,500]) test(`attempt closure HTTP ${status} retains answers and permits retry`, async t => {
    const w = await takerFixture(t);
    w.respond = async () => reply(status,{detail:'Closing failed'});
    await w.closeAssessmentAttempt();
    assert.equal(w.document.querySelector('textarea').value,'Keep this unfinished reasoning');
    assert.equal(w.document.getElementById('results').classList.contains('d-none'),true);
    assert.equal(w.document.getElementById('close-attempt-btn').disabled,false);
    assert.equal(w.SLMClient.drafts.read('assessment',4,21).answers[1].response_text,'Keep this unfinished reasoning');
    w.respond = async () => reply(200,{submission_id:21,status:'abandoned'});
    await w.closeAssessmentAttempt();
    assert.equal(w.document.getElementById('results').classList.contains('d-none'),false);
});

test('closed history restores only the current owner device draft without starting an attempt', async t => {
    const w = await fixture(t,'assessment_history.html','?submission_id=21');
    w.SLMClient.drafts.write('assessment',4,21,{answers:[{question_id:11,response_text:'Local unfinished answer'}]});
    w.respond = async url => reply(200,url.endsWith('/submissions') ? [submission({status:'abandoned'})] : submission({status:'abandoned',answers:[],score:null}));
    w.loadScript('assessment_history.js'); await w.initializeSubmissionHistory();
    assert.match(w.document.getElementById('learner-submission-detail').textContent,/Unsubmitted answers saved on this device/);
    assert.match(w.document.getElementById('learner-submission-detail').textContent,/Local unfinished answer/);
    assert.equal(w.requests.some(request => request.options.method === 'POST'),false);
});

test('assessment actions follow language readiness without refetching or losing role restrictions', async t => {
    const w = await fixture(t,'dashboard.html','','teacher');
    w.respond = async () => reply(200,[assessment]);
    w.loadScript('assessment.js'); await w.loadAssessments();
    const count = w.requests.length;
    w.I18n.t = key => ({'recovery.assessment_preview':'Vista previa','recovery.assessment_stats':'Estadísticas'}[key] || key);
    w.document.dispatchEvent(new w.CustomEvent('i18n-loaded'));
    assert.equal(w.document.querySelector('[data-assessment-action="preview"]').textContent,'Vista previa');
    assert.equal(w.document.querySelector('[data-assessment-action="stats"]').textContent,'Estadísticas');
    assert.equal(w.requests.length,count);
    assert.equal(w.document.querySelector('#assessment-list a[href*="assessment_taker"]'),null);
});

test('staff cannot load the learner-owned history page', async t => {
    const w = await fixture(t,'assessment_history.html','?submission_id=21','teacher');
    w.loadScript('assessment_history.js'); await w.initializeSubmissionHistory();
    assert.match(w.document.getElementById('submission-history-status').textContent,/learners their own submissions/);
    assert.equal(w.requests.length,0);
});

test('failed grade save retains reviewed score and feedback for retry', async t => {
    const w = await fixture(t,'grading.html','?submission_id=21','teacher');
    w.respond = async url => reply(200,url.includes('submissions?') ? [submission()] : submission());
    w.loadScript('grading.js'); await w.initializeGrading();
    w.document.getElementById('grade-score').value = '12';
    w.document.getElementById('grade-feedback').value = 'Keep this teacher feedback';
    w.respond = async () => reply(500,{detail:'Grade was not saved'});
    await w.submitGrade();
    assert.equal(w.document.getElementById('grade-score').value,'12');
    assert.equal(w.document.getElementById('grade-feedback').value,'Keep this teacher feedback');
    assert.equal(w.document.getElementById('grade-score').disabled,false);
    assert.equal(w.toasts.some(toast => toast[1] === 'success'),false);
});

test('ambiguous successful close response never claims closure or discards the draft', async t => {
    const w = await takerFixture(t);
    w.respond = async () => reply(200,{submission_id:22,status:'abandoned'});
    await w.closeAssessmentAttempt();
    assert.equal(w.document.getElementById('results').classList.contains('d-none'),true);
    assert.equal(w.document.getElementById('close-attempt-btn').disabled,false);
    assert.equal(w.SLMClient.drafts.read('assessment',4,21).answers[1].response_text,'Keep this unfinished reasoning');
});

test('attempt closure saves answers durably even when device draft storage is unavailable', async t => {
    const w = await takerFixture(t);
    w.Storage.prototype.setItem = () => {throw new Error('Unavailable storage');};
    w.respond = async (url,options) => {
        assert.equal(JSON.parse(options.body).answers[1].response_text,'Keep this unfinished reasoning');
        return reply(200,{id:21,submission_id:21,status:'abandoned',score:null,needs_review:false});
    };
    await w.closeAssessmentAttempt();
    assert.equal(w.requests.some(request => request.url.endsWith('/close')),true);
    assert.match(w.document.getElementById('results').textContent,/unsubmitted answers are saved/);
    assert.equal(w.document.querySelector('textarea').value,'Keep this unfinished reasoning');
});

test('learner direct grading refresh cannot display grading controls or load data', async t => {
    const w = await fixture(t,'grading.html','?submission_id=21');
    w.loadScript('grading.js'); await w.initializeGrading(); await w.loadSubmissions(); await w.loadSubmissionDetails(21);
    assert.equal(w.requests.length,0);
    assert.equal(w.document.getElementById('grading-area').classList.contains('hidden'),true);
});

test('grade save requires explicit server confirmation and retains inputs on ambiguity', async t => {
    const w = await fixture(t,'grading.html','?submission_id=21','teacher');
    w.respond = async url => reply(200,url.includes('submissions?') ? [submission()] : submission());
    w.loadScript('grading.js'); await w.initializeGrading();
    w.document.getElementById('grade-score').value = '12';
    w.respond = async () => reply(200,{});
    await w.submitGrade();
    assert.equal(w.toasts.some(toast => toast[1] === 'success'),false);
    assert.equal(w.document.getElementById('grade-score').value,'12');
    assert.match(w.toasts[0][0],/could not confirm/);
});
