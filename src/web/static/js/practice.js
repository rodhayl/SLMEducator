/* Low-stakes independent practice. No client grades, progress or rewards. */
(function (root) {
    'use strict';
    const text = (key, fallback) => SLMClient.message(key, fallback);
    let current = null;
    function optionsFor(question) {
        let options = question.options?.choices || question.options;
        if (Array.isArray(options)) return options.map((value, index) => ({ key: String.fromCharCode(65 + index), value: String(value) }));
        if (options && typeof options === 'object') return Object.entries(options).map(([key, value]) => ({ key, value: String(value) }));
        if (question.type === 'true_false' || question.question_type === 'true_false') return [{ key: 'true', value: 'True' }, { key: 'false', value: 'False' }];
        return [];
    }
    function render(container, raw) {
        const questions = Array.isArray(raw.questions) ? raw.questions : [raw];
        if (!questions.length || questions.some(q => !q.question && !q.question_text)) {
            container.textContent = text('practice_unavailable', 'This practice item needs teacher review before it can be answered.');
            return;
        }
        container.replaceChildren();
        const note = document.createElement('p'); note.className = 'alert alert-info';
        note.textContent = text('practice_notice', 'Low-stakes practice. Try an independent answer first. Self-checks are not final grades.');
        container.append(note);
        const inputs = [];
        const state = { inputs, hints: [], owner: null, contentId: null, attemptId: null };
        current = state;
        questions.forEach((question, index) => {
            const section = document.createElement('section'); section.className = 'card p-3 mb-3';
            const label = document.createElement('label'); label.className = 'form-label fw-bold';
            label.textContent = question.question || question.question_text;
            label.htmlFor = `practice-answer-${index}`;
            const options = optionsFor(question);
            const input = document.createElement(options.length ? 'select' : 'textarea');
            input.className = options.length ? 'form-select' : 'form-control';
            input.id = label.htmlFor;
            if (options.length) {
                input.append(new Option(text('select_answer', 'Choose an answer'), ''));
                options.forEach(option => input.append(new Option(option.value, option.value)));
            } else { input.rows = 3; }
            const feedback = document.createElement('div'); feedback.className = 'mt-2';
            feedback.setAttribute('role', 'status'); feedback.setAttribute('aria-live', 'polite');
            const buttons = document.createElement('div'); buttons.className = 'd-flex gap-2 mt-2';
            const hint = document.createElement('button'); hint.type = 'button'; hint.className = 'btn btn-outline-secondary';
            hint.textContent = text('show_hint', 'Show a hint');
            const hints = (Array.isArray(question.hints) ? question.hints : [question.hint]).filter(value => typeof value === 'string' && value.trim());
            if (!hints.length) hints.push(text('practice_hint', 'Find the key idea in the lesson and explain it in your own words.'));
            const progress = { count: 0, hint, feedback, hints };
            state.hints.push(progress);
            hint.onclick = () => {
                if (current !== state || (state.owner !== null && state.owner !== SLMClient.account()) || progress.count >= hints.length) return;
                feedback.textContent = hints[progress.count++];
                hint.disabled = progress.count === hints.length;
                state.save?.();
            };
            const check = document.createElement('button'); check.type = 'button'; check.className = 'btn btn-outline-primary';
            check.textContent = text('self_check', 'Self-check');
            check.onclick = () => selfCheck(question, options, input, feedback);
            buttons.append(hint, check); section.append(label, input, buttons, feedback); container.append(section); inputs.push(input);
        });
    }
    function selfCheck(question, options, input, feedback) {
        if (!input.value.trim()) { feedback.textContent = text('attempt_first', 'Write or choose your own answer first.'); input.focus(); return; }
        const answer = question.correct_answer ?? question.answer;
        if (answer === undefined || answer === null) { feedback.textContent = text('ask_teacher', 'No answer key is available. Ask your teacher to review your response.'); return; }
        const solution = options.find(option => option.key.toLowerCase() === String(answer).toLowerCase())?.value || String(answer);
        const matched = options.length && input.value.trim().toLocaleLowerCase() === solution.trim().toLocaleLowerCase();
        const prefix = options.length ? (matched ? text('practice_match', 'Your choice matches the answer key.') : text('practice_compare', 'Compare your choice with the answer key.')) : text('practice_compare', 'Compare your response with the answer key.');
        feedback.textContent = `${prefix} ${text('suggested_answer', 'Suggested answer')}: ${solution}. ${question.explanation || ''} ${text('not_final_grade', 'This is a practice self-check, not a final grade.')}`;
    }
    async function bindAttempt(owner, contentId, attemptId) {
        if (!current) return;
        const state = current;
        Object.assign(state, { owner, contentId, attemptId });
        const saved = SLMClient.drafts.read('practice', contentId, attemptId);
        if (saved?.answers?.some(Boolean) || saved?.hints?.some(count => count > 0)) {
            const choice = await SLMClient.chooseDraft();
            if (current !== state || owner !== SLMClient.account()) return;
            if (choice === 'restore') {
                state.inputs.forEach((input, index) => { input.value = saved.answers?.[index] || ''; });
                state.hints.forEach((progress, index) => {
                    const count = saved.hints?.[index];
                    if (!Number.isInteger(count) || count < 1) return;
                    progress.count = Math.min(count, progress.hints.length);
                    progress.feedback.textContent = progress.hints[progress.count - 1];
                    progress.hint.disabled = progress.count === progress.hints.length;
                });
            }
            else if (choice === 'discard') SLMClient.drafts.remove('practice', contentId, attemptId);
            else { root.location.href = '/dashboard.html'; return; }
        }
        const save = () => {
            if (current !== state || owner !== SLMClient.account()) return;
            SLMClient.drafts.write('practice', contentId, attemptId, { answers: state.inputs.map(input => input.value), hints: state.hints.map(progress => progress.count) });
        };
        state.save = save;
        state.inputs.forEach(input => input.addEventListener('input', save));
        root.addEventListener('pagehide', save);
    }
    root.SLMPractice = Object.freeze({ render, bindAttempt, optionsFor });
})(window);
