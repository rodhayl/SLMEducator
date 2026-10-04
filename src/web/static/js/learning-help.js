/* Reusable, lesson-scoped help. All provider output remains an unverified suggestion. */
(function (root) {
    'use strict';
    let nextId = 0;
    const mounted = new WeakMap();
    const words = {
        tutor: 'Tutor', teacher: 'Ask my teacher', close: 'Back to lesson',
        title: 'Help with this lesson', context: 'Lesson', loading: 'Checking lesson context and assistance policy…',
        refresh: 'Refresh context and policy', source_version: 'Source version',
        partial: 'Partial source: only a bounded selection of lesson text is included.',
        complete: 'The source preview includes all available lesson text.',
        unverified: 'AI suggestions are unverified. Check them against your lesson or ask your teacher.',
        sections: 'Choose lesson sections', section_help: 'Choose up to 12 sections. With none selected, the tutor chooses relevant sections within its text limit.',
        characters: 'characters', section_limit: 'Choose no more than 12 sections.',
        hint: 'Hint', explanation: 'Explanation', assistance: 'Kind of help',
        hints_only: 'Your teacher allows hints only while an assessment attempt is open.',
        explanations: 'Hints and explanations are available. Start with a hint and try the next step yourself.',
        disabled: 'Your teacher has disabled AI help while an assessment attempt is open. You can still ask your teacher.',
        question: 'What would you like help with?', send: 'Ask tutor', sending: 'Waiting for a tutor suggestion…',
        reply: 'Tutor suggestion', you: 'Your question', references: 'Source sections used',
        unavailable: 'The tutor could not provide a usable suggestion. Your question is kept; retry or ask your teacher.',
        load_failed: 'Context or policy could not be loaded. Refresh to retry. Your question is kept.',
        source_changed: 'The lesson source changed. Refresh the context before asking again. Your question is kept.',
        policy_changed: 'The assistance policy changed. Refresh it before asking again. Your question is kept.',
        failed: 'The request could not be completed. Your text is kept; please retry.',
        owner_changed: 'Your account changed. Reopen the lesson before requesting help.',
        required: 'Write a question before sending.', too_long: 'Keep your question within 4,000 characters.',
        subject: 'Subject', description: 'What have you tried, and where are you stuck?',
        urgency: 'How soon do you need help?', normal: 'Normal', soon: 'Soon', urgent: 'Urgent',
        teacher_context: 'Your teacher will receive this lesson and course context with your request.',
        teacher_send: 'Send help request', teacher_sending: 'Sending your help request…',
        teacher_required: 'Add a subject and describe the help you need.',
        teacher_receipt: 'Help request #{id} was received and is open for your teacher.',
        teacher_receipt_resolved: 'Help request #{id} was already received and resolved by your teacher.',
        teacher_unconfirmed: 'The server did not confirm this help request. Your text is kept. Check your help requests before sending again.',
        teacher_interrupted: 'Delivery of the previous request is unconfirmed. Check your help requests before sending again.',
        teacher_student: 'Teacher help requests are available to learners.',
        new_request: 'Write another request', cancel: 'Cancel tutor request',
        cancelling: 'Requesting cancellation of this answer…',
        cancelled: 'Answer delivery was cancelled. Your question is kept.',
        cancel_finished: 'This request had already finished. Its answer was not added after cancellation.',
        cancel_unconfirmed: 'Cancellation is unconfirmed. The provider may still be working and may charge. Your question is kept.',
        request_pending: 'This request is still unconfirmed. Retry the same question or cancel it before sending a different question.',
        request_active: 'A tutor request is already active. Wait for it or cancel its delivery before sending another.',
        request_limit: 'The daily tutor request limit has been reached.', usage_unavailable: 'Tutor request usage is unavailable.',
        usage: 'Tutor requests today', receipt: 'Tutor request details', request_id: 'Request ID',
        receipt_status: 'Status', completed: 'Completed', failed_status: 'Failed', cancelled_status: 'Cancelled', timed_out: 'Timed out',
        provider: 'Provider', model: 'Model', elapsed: 'Elapsed seconds', tokens: 'Tokens used',
        max_output: 'Maximum output tokens', unknown: 'Unavailable',
        cost_unknown: 'Provider cost is unknown; this app does not calculate charges.',
        provider_continue: 'Provider work may continue and may still incur charges.',
        receipt_unconfirmed: 'The server did not confirm this tutor request. Your question is kept; retry or cancel the pending request.',
        receipt_missing: 'The server did not report a request receipt or token usage.',
        new_tutor_request: 'Prepare a new request',
        new_tutor_confirm: 'Start a new request for this question? The previous outcome is unknown and its provider work may still finish or incur charges. The new request uses a new request ID and counts separately.'
    };
    function t(key, values = {}) {
        const translated = root.I18n?.t?.(`help_panel.${key}`);
        let text = translated && translated !== `help_panel.${key}` ? translated : words[key];
        Object.entries(values).forEach(([name, value]) => { text = text.replaceAll(`{${name}}`, String(value)); });
        return text;
    }
    function node(tag, className = '', key) {
        const element = document.createElement(tag);
        element.className = className;
        if (key) { element.dataset.i18n = `help_panel.${key}`; element.textContent = t(key); }
        return element;
    }
    function button(key, className = 'btn btn-outline-secondary') {
        const element = node('button', className, key); element.type = 'button'; return element;
    }
    function validId(value) { return Number.isInteger(Number(value)) && Number(value) > 0 ? Number(value) : null; }
    function requestId() {
        if (root.crypto.randomUUID) return root.crypto.randomUUID();
        const bytes = root.crypto.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
        const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('');
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    }
    function context(options) {
        const revision = options.contextRevision && typeof options.contextRevision === 'object' ?
            JSON.stringify(Object.fromEntries(Object.entries(options.contextRevision).sort(([a], [b]) => a.localeCompare(b)))) : String(options.contextRevision || '');
        return { contentId: validId(options.contentId), studyPlanId: validId(options.studyPlanId), sessionId: validId(options.sessionId),
            contentTitle: String(options.contentTitle || ''), contextRevision: revision };
    }
    class HelpPanel {
        constructor(host, options) {
            this.host = host; this.options = options; this.context = context(options);
            this.owner = root.SLMClient.account(); this.id = `lesson-help-${++nextId}`;
            this.epoch = 0; this.mode = null; this.source = null; this.policy = null;
            this.controllers = new Set(); this.history = []; this.receipt = null; this.pendingTeacher = null;
            this.build(); this.bind(); this.translate();
        }
        build() {
            const controls = node('div', 'd-flex flex-wrap gap-2');
            this.tutorButton = button('tutor', 'btn btn-outline-primary');
            this.teacherButton = button('teacher');
            controls.append(this.tutorButton, this.teacherButton);
            this.panel = node('section', 'card mt-3'); this.panel.id = this.id;
            this.panel.hidden = true; this.panel.setAttribute('aria-labelledby', `${this.id}-title`);
            const header = node('div', 'card-header d-flex flex-wrap align-items-center justify-content-between gap-2');
            const title = node('h2', 'h5 mb-0', 'title'); title.id = `${this.id}-title`;
            this.closeButton = button('close', 'btn btn-sm btn-outline-secondary'); header.append(title, this.closeButton);
            const body = node('div', 'card-body'); this.contextLabel = node('p', 'fw-semibold');
            this.tutor = node('div'); this.teacher = node('div');
            this.buildTutor(); this.buildTeacher(); body.append(this.contextLabel, this.tutor, this.teacher);
            this.panel.append(header, body); this.host.replaceChildren(controls, this.panel);
            [this.tutorButton, this.teacherButton].forEach(control => control.setAttribute('aria-controls', this.id));
        }
        field(parent, tag, name, key) {
            const wrapper = node('div', 'mb-3');
            const label = node('label', 'form-label', key); label.htmlFor = `${this.id}-${name}`;
            const input = node(tag, tag === 'select' ? 'form-select' : 'form-control');
            input.id = label.htmlFor; input.name = name;
            wrapper.append(label, input); parent.append(wrapper); return input;
        }
        status(parent) {
            const element = node('p', 'small my-2'); element.setAttribute('role', 'status');
            element.setAttribute('aria-live', 'polite'); element.setAttribute('aria-atomic', 'true');
            parent.append(element); return element;
        }
        buildTutor() {
            this.policyStatus = this.status(this.tutor); this.refreshButton = button('refresh', 'btn btn-sm btn-outline-secondary mb-3');
            this.sourceBox = node('div', 'border rounded p-3 mb-3');
            this.sourceVersion = node('p', 'small text-break'); this.sourcePartial = node('p', 'small');
            this.sourceBox.append(this.sourceVersion, this.sourcePartial, node('p', 'small', 'unverified'));
            this.sections = node('fieldset'); this.sections.append(node('legend', 'h6', 'sections'));
            const help = node('p', 'small text-muted', 'section_help'); help.id = `${this.id}-section-help`;
            this.sectionChoices = node('div', 'd-grid gap-2 overflow-auto'); this.sectionChoices.style.maxHeight = '16rem';
            this.sections.setAttribute('aria-describedby', help.id);
            this.sections.append(help, this.sectionChoices); this.sourceBox.append(this.sections);
            this.transcript = node('div', 'd-grid gap-3 mb-3'); this.transcript.setAttribute('role', 'log');
            this.transcript.setAttribute('aria-live', 'polite');
            this.tutorForm = node('form'); this.assistance = this.field(this.tutorForm, 'select', 'assistance', 'assistance');
            ['hint', 'explanation'].forEach(mode => { const option = node('option', '', mode); option.value = mode; this.assistance.append(option); });
            this.question = this.field(this.tutorForm, 'textarea', 'question', 'question');
            this.question.rows = 3; this.question.maxLength = 4000; this.question.required = true;
            this.tutorSend = button('send', 'btn btn-primary'); this.tutorSend.type = 'submit';
            this.cancelButton = button('cancel'); this.cancelButton.hidden = true;
            this.newTutorButton = button('new_tutor_request'); this.newTutorButton.hidden = true;
            this.tutorStatus = this.status(this.tutorForm); const actions = node('div', 'd-flex flex-wrap gap-2');
            actions.append(this.tutorSend, this.cancelButton, this.newTutorButton); this.tutorForm.append(actions);
            this.usageStatus = this.status(this.tutor); this.cancelStatus = this.status(this.tutor);
            this.receiptBox = node('div', 'border rounded p-3 mt-3'); this.receiptBox.hidden = true;
            this.receiptBox.setAttribute('aria-live', 'polite');
            this.tutor.append(this.refreshButton, this.sourceBox, this.transcript, this.tutorForm, this.receiptBox);
        }
        buildTeacher() {
            this.teacher.append(node('p', 'small', 'teacher_context')); this.teacherForm = node('form');
            this.subject = this.field(this.teacherForm, 'input', 'subject', 'subject');
            this.subject.required = true; this.subject.maxLength = 200;
            this.description = this.field(this.teacherForm, 'textarea', 'description', 'description');
            this.description.rows = 4; this.description.required = true; this.description.maxLength = 4000;
            this.urgency = this.field(this.teacherForm, 'select', 'urgency', 'urgency');
            ['normal', 'soon', 'urgent'].forEach((key, index) => {
                const option = node('option', '', key); option.value = String(index + 1); this.urgency.append(option);
            });
            this.teacherSend = button('teacher_send', 'btn btn-primary'); this.teacherSend.type = 'submit';
            this.teacherStatus = this.status(this.teacher); this.teacherForm.append(this.teacherSend);
            this.newRequest = button('new_request'); this.newRequest.hidden = true;
            this.teacher.append(this.teacherForm, this.newRequest);
        }
        bind() {
            this.tutorButton.onclick = () => this.open('tutor', this.tutorButton);
            this.teacherButton.onclick = () => this.open('teacher', this.teacherButton);
            this.closeButton.onclick = () => this.close();
            this.refreshButton.onclick = () => this.load();
            this.cancelButton.onclick = () => this.cancelTutor();
            this.newTutorButton.onclick = () => this.prepareNewRequest();
            this.tutorForm.onsubmit = event => { event.preventDefault(); this.sendTutor(); };
            this.teacherForm.onsubmit = event => { event.preventDefault(); this.sendTeacher(); };
            this.sectionChoices.onchange = event => this.changeSections(event);
            this.newRequest.onclick = () => {
                this.receipt = null; this.pendingTeacher = null; this.teacherError = null; this.subject.value = ''; this.description.value = '';
                this.urgency.value = '1'; this.translate(); this.subject.focus();
            };
            this.onKey = event => { if (event.key === 'Escape' && this.mode) { event.preventDefault(); this.close(); } };
            this.onLanguage = () => this.translate();
            this.onStorage = event => { if (['user', 'token'].includes(event.key)) this.checkOwner(); };
            this.host.addEventListener('keydown', this.onKey);
            document.addEventListener('i18n-loaded', this.onLanguage);
            document.addEventListener('i18n-language-changed', this.onLanguage);
            root.addEventListener('storage', this.onStorage);
        }
        invalidate() {
            this.epoch++; this.controllers.forEach(controller => controller.abort()); this.controllers.clear();
            if (this.pendingTutor) this.requestCancellation(this.pendingTutor);
            if (this.teacherBusy) this.teacherError = { key: 'teacher_interrupted' };
            this.loading = false; this.tutorBusy = false; this.teacherBusy = false;
        }
        checkOwner() {
            if (!this.destroyed && this.owner && root.SLMClient.account() === this.owner) return true;
            this.invalidate(); this.owner = null; this.source = null; this.policy = null; this.history = [];
            this.receipt = null; this.question.value = ''; this.subject.value = ''; this.description.value = '';
            this.pendingTutor = null; this.pendingTeacher = null; this.lastReceipt = null; this.receiptMissing = false; this.cancelState = null; this.usage = null;
            this.transcript.replaceChildren(); this.sectionChoices.replaceChildren();
            this.loadError = { key: 'owner_changed' }; this.teacherError = { key: 'owner_changed' };
            this.translate(); return false;
        }
        current(epoch) { return !this.destroyed && epoch === this.epoch && this.mode && this.checkOwner(); }
        async request(url, options = {}) {
            const controller = new AbortController(); this.controllers.add(controller);
            try { return await root.SLMClient.request(url, { ...options, signal: controller.signal }); }
            finally { this.controllers.delete(controller); }
        }
        async open(mode = 'tutor', trigger) {
            if (!['tutor', 'teacher'].includes(mode) || !this.checkOwner()) return;
            const changed = this.mode !== mode;
            if (changed) this.invalidate();
            this.mode = mode; this.trigger = trigger || document.activeElement;
            this.panel.hidden = false; this.translate();
            (mode === 'tutor' ? this.question : this.receipt ? this.newRequest : this.subject).focus();
            if (mode === 'tutor' && !this.loading && (changed || !this.source || !this.policy)) await this.load();
        }
        close() {
            if (this.destroyed) return;
            this.invalidate(); this.mode = null; this.panel.hidden = true; this.source = null; this.policy = null;
            this.translate();
            const target = typeof this.options.returnFocus === 'function' ? this.options.returnFocus() : this.options.returnFocus;
            (target || this.trigger || this.tutorButton)?.focus?.();
        }
        setContext(options) {
            const next = context(options);
            if (JSON.stringify(next) === JSON.stringify(this.context)) return;
            this.invalidate(); this.options = { ...this.options, ...options }; this.context = next;
            this.source = null; this.policy = null; this.history = []; this.receipt = null; this.loadedVersion = null;
            this.pendingTutor = null; this.pendingTeacher = null; this.lastReceipt = null; this.receiptMissing = false; this.cancelState = null; this.usage = null;
            this.loadError = null; this.tutorError = null; this.teacherError = null;
            this.question.value = ''; this.subject.value = ''; this.description.value = ''; this.urgency.value = '1';
            this.transcript.replaceChildren(); this.sectionChoices.replaceChildren(); this.translate();
            if (this.mode === 'tutor') return this.load();
        }
        async load() {
            if (this.mode !== 'tutor' || !this.checkOwner()) return;
            const oldVersion = this.loadedVersion;
            this.invalidate(); const epoch = this.epoch; this.loading = true;
            this.source = null; this.policy = null; this.loadError = null; this.tutorError = null;
            this.translate();
            const params = new URLSearchParams();
            if (this.context.contentId) params.set('content_id', this.context.contentId);
            if (this.context.studyPlanId) params.set('study_plan_id', this.context.studyPlanId);
            if (this.context.sessionId) params.set('session_id', this.context.sessionId);
            try {
                if (!this.context.contentId) throw new Error(t('load_failed'));
                const [policy, preview, usage] = await Promise.all([
                    this.request('/api/ai/assistance-policy'), this.request(`/api/ai/context?${params}`),
                    this.request('/api/ai/usage').catch(() => null)
                ]);
                if (!this.current(epoch)) return;
                this.usage = this.validUsage(usage) ? usage : null;
                if (!this.validPolicy(policy) || !this.validSource(preview?.source)) throw new Error(t('load_failed'));
                this.policy = policy; this.source = preview.source;
                if (oldVersion !== this.source.source_version) { this.history = []; this.transcript.replaceChildren(); }
                this.loadedVersion = this.source.source_version;
                this.renderSections();
            } catch (error) { if (this.current(epoch)) this.loadError = { key: 'load_failed', detail: error.message }; }
            finally { if (this.current(epoch)) { this.loading = false; this.translate(); } }
        }
        validPolicy(policy) { return ['hints_only', 'explanations', 'disabled'].includes(policy?.mode); }
        validUsage(usage) {
            return usage && (usage.active_request_id === null || typeof usage.active_request_id === 'string') &&
                Number.isInteger(usage.requests_used_today) && usage.requests_used_today >= 0 &&
                Number.isInteger(usage.requests_limit_daily) && usage.requests_limit_daily > 0;
        }
        validReceipt(receipt, id) {
            return receipt && receipt.request_id === id && ['completed', 'failed', 'cancelled', 'timed_out'].includes(receipt.status) &&
                Number.isFinite(receipt.elapsed_seconds) && receipt.elapsed_seconds >= 0 &&
                (receipt.tokens_used === null || Number.isInteger(receipt.tokens_used) && receipt.tokens_used >= 0) &&
                Number.isInteger(receipt.max_output_tokens) && receipt.max_output_tokens > 0 &&
                Number.isInteger(receipt.requests_used_today) && receipt.requests_used_today >= 0 &&
                Number.isInteger(receipt.requests_limit_daily) && receipt.requests_limit_daily > 0 &&
                typeof receipt.provider_may_continue === 'boolean' && receipt.cost_known === false;
        }
        rememberReceipt(receipt) {
            this.lastReceipt = receipt;
            this.usage = { ...(this.usage || {}), active_request_id: null,
                requests_used_today: receipt.requests_used_today, requests_limit_daily: receipt.requests_limit_daily };
        }
        cancelTutor() {
            if (!this.checkOwner()) return;
            if (!this.pendingTutor && this.usage?.active_request_id) this.pendingTutor = { id: this.usage.active_request_id };
            this.invalidate(); this.translate();
        }
        async requestCancellation(pending) {
            if (pending.cancelling || pending.terminal || this.destroyed || !this.owner || this.owner !== root.SLMClient.account()) return;
            pending.cancelling = true;
            const owner = this.owner, state = { requestId: pending.id, key: 'cancelling' }; this.cancelState = state;
            try {
                const result = await root.SLMClient.request(`/api/ai/requests/${encodeURIComponent(pending.id)}/cancel`, { method: 'POST' });
                if (this.destroyed || this.owner !== owner || root.SLMClient.account() !== owner || this.cancelState !== state) return;
                const receipt = result;
                if (!this.validReceipt(receipt, pending.id)) throw new Error(t('cancel_unconfirmed'));
                this.rememberReceipt(receipt); state.key = receipt.status === 'cancelled' ? 'cancelled' : 'cancel_finished';
                pending.terminal = true;
                if (this.pendingTutor === pending && receipt.status !== 'completed') this.pendingTutor = null;
            } catch {
                if (this.cancelState === state) state.key = 'cancel_unconfirmed';
            } finally {
                pending.cancelling = false;
                if (!this.destroyed && this.owner === owner && this.cancelState === state) this.translate();
            }
        }
        async prepareNewRequest() {
            if (!this.checkOwner() || !this.pendingTutor || this.tutorBusy || this.pendingTutor.cancelling || !root.showConfirm) return;
            const pending = this.pendingTutor, epoch = this.epoch;
            this.newTutorButton.disabled = true;
            try {
                if (!await root.showConfirm(t('new_tutor_confirm'), t('new_tutor_request'))) return;
                if (!this.current(epoch) || this.pendingTutor !== pending) return;
                this.pendingTutor = null; this.cancelState = null; this.tutorError = null;
                await this.load(); this.question.focus();
            } finally { if (this.current(epoch)) this.translate(); }
        }
        validSource(source) {
            return source && source.id === this.context.contentId && typeof source.source_version === 'string' &&
                source.source_version.length > 0 && Array.isArray(source.available_sections) &&
                source.available_sections.length > 0 && source.available_sections.every(section =>
                    typeof section.id === 'string' && typeof section.title === 'string' && Number.isFinite(section.characters)) &&
                typeof source.truncated === 'boolean' && Array.isArray(source.references) &&
                source.references.every(reference => typeof reference === 'string' && source.available_sections.some(section => section.id === reference)) &&
                new Set(source.available_sections.map(section => section.id)).size === source.available_sections.length;
        }
        renderSections() {
            const selected = new Set(this.selectedSections()); this.sectionChoices.replaceChildren();
            this.source.available_sections.forEach((section, index) => {
                const wrapper = node('div', 'form-check'); const input = node('input', 'form-check-input');
                input.type = 'checkbox'; input.id = `${this.id}-section-${index}`; input.value = section.id;
                input.checked = selected.has(section.id);
                const label = node('label', 'form-check-label'); label.htmlFor = input.id;
                label.dataset.sectionTitle = section.title || section.id; label.dataset.characters = section.characters;
                label.textContent = `${label.dataset.sectionTitle} (${section.characters} ${t('characters')})`;
                wrapper.append(input, label); this.sectionChoices.append(wrapper);
            });
        }
        selectedSections() { return [...this.sectionChoices.querySelectorAll('input:checked')].map(input => input.value); }
        changeSections(event) {
            if (!this.checkOwner()) return;
            this.invalidate(); this.history = []; this.transcript.replaceChildren(); this.tutorError = null;
            if (this.selectedSections().length > 12) { event.target.checked = false; this.tutorError = { key: 'section_limit' }; }
            this.translate();
        }
        async sendTutor() {
            if (!this.checkOwner() || this.mode !== 'tutor' || this.loading || this.tutorBusy || !this.source ||
                !this.policy || this.policy.mode === 'disabled' || this.pendingTutor?.cancelling || this.usageBlocksSend()) return;
            const message = this.question.value.trim();
            if (!message || message.length > 4000) { this.tutorError = { key: message ? 'too_long' : 'required' }; this.translate(); return; }
            const payload = { message, content_id: this.context.contentId, study_plan_id: this.context.studyPlanId,
                assistance: this.policy.mode === 'hints_only' ? 'hint' : this.assistance.value,
                section_ids: this.selectedSections(), source_version: this.source.source_version,
                conversation_history: this.history.slice(-10) };
            if (this.context.sessionId) payload.session_id = this.context.sessionId;
            if (payload.section_ids.length > 12) return;
            const fingerprint = JSON.stringify(payload);
            if (this.pendingTutor?.terminal && this.pendingTutor.fingerprint !== fingerprint) this.pendingTutor = null;
            if (this.usageBlocksSend()) { this.tutorError = { key: 'request_limit' }; this.translate(); return; }
            if (this.pendingTutor && this.pendingTutor.fingerprint !== fingerprint) {
                this.tutorError = { key: 'request_pending' }; this.translate(); return;
            }
            if (!this.pendingTutor) { this.pendingTutor = { id: requestId(), fingerprint }; this.lastReceipt = null; this.receiptMissing = false; }
            const pending = this.pendingTutor; payload.client_request_id = pending.id; this.cancelState = null;
            const epoch = this.epoch; this.tutorBusy = true; this.tutorError = null; this.translate();
            try {
                const data = await this.request('/api/ai/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (!this.current(epoch)) return;
                if (!this.acceptTutorResponse(data, payload)) return;
                this.appendExchange(message, data); this.history.push({ role: 'user', content: message }, { role: 'assistant', content: data.response.slice(0, 4000) });
                this.history = this.history.slice(-10);
                if (this.question.value.trim() === message) this.question.value = '';
            } catch (error) {
                if (!this.current(epoch)) return;
                const changedSource = error.status === 409 && /source revision|source changed|selected sections|does not belong/i.test(error.message);
                if (changedSource) this.source = null;
                if (error.status === 403) this.policy = null;
                if ([401, 403, 429].includes(error.status) || changedSource) this.pendingTutor = null;
                this.tutorError = { key: changedSource ? 'source_changed' : error.status === 409 ? 'request_pending' : error.status === 429 ? 'request_limit' : 'failed', detail: error.message };
            } finally { if (this.current(epoch)) { this.tutorBusy = false; this.translate(); } }
        }
        acceptTutorResponse(data, payload) {
            if (data?.receipt !== undefined && !this.validReceipt(data.receipt, payload.client_request_id)) {
                this.tutorError = { key: 'receipt_unconfirmed' }; return false;
            }
            this.receiptMissing = data?.receipt === undefined;
            if (data?.receipt) this.rememberReceipt(data.receipt);
            this.pendingTutor = null;
            if (!this.validPolicy(data.assistance_policy)) { this.policy = null; this.tutorError = { key: 'policy_changed' }; return false; }
            this.policy = data.assistance_policy;
            if (this.policy.mode === 'disabled' || (this.policy.mode === 'hints_only' && data.effective_assistance !== 'hint')) {
                this.policy = null; this.tutorError = { key: 'policy_changed' }; return false;
            }
            if (!this.validSource(data.source) || data.source.source_version !== payload.source_version) {
                this.source = null; this.tutorError = { key: 'source_changed' }; return false;
            }
            if ((data.receipt && data.receipt.status !== 'completed') || data.status !== 'suggestion' || typeof data.response !== 'string' || !data.response.trim()) {
                this.tutorError = { key: 'unavailable' }; return false;
            }
            return true;
        }
        usageBlocksSend() {
            return Boolean(this.usage && (this.usage.requests_used_today >= this.usage.requests_limit_daily && !this.pendingTutor ||
                this.usage.active_request_id && this.usage.active_request_id !== this.pendingTutor?.id));
        }
        renderReceipt() {
            this.receiptBox.replaceChildren(); this.receiptBox.hidden = !this.lastReceipt && !this.receiptMissing;
            if (this.receiptBox.hidden) return;
            this.receiptBox.append(node('h3', 'h6', 'receipt'));
            const receipt = this.lastReceipt;
            if (!receipt) this.receiptBox.append(node('p', 'small', 'receipt_missing'));
            else {
                const statusKey = { completed: 'completed', failed: 'failed_status', cancelled: 'cancelled_status', timed_out: 'timed_out' }[receipt.status];
                const values = { request_id: receipt.request_id, receipt_status: t(statusKey), provider: receipt.provider,
                    model: receipt.model, elapsed: receipt.elapsed_seconds, tokens: receipt.tokens_used, max_output: receipt.max_output_tokens,
                    usage: `${receipt.requests_used_today} / ${receipt.requests_limit_daily}` };
                Object.entries(values).forEach(([key, value]) => {
                    const line = node('p', 'small mb-1 text-break');
                    line.textContent = `${t(key)}: ${value === null || value === undefined || value === '' ? t('unknown') : String(value)}`;
                    this.receiptBox.append(line);
                });
                if (receipt.provider_may_continue) this.receiptBox.append(node('p', 'small mt-2', 'provider_continue'));
            }
            this.receiptBox.append(node('p', 'small mt-2 mb-0', 'cost_unknown'));
        }
        appendExchange(message, data) {
            const exchange = node('article', 'border rounded p-3');
            const questionLabel = node('h3', 'h6', 'you'); const question = node('p'); question.textContent = message;
            const answerLabel = node('h3', 'h6', 'reply'); const answer = node('div');
            if (root.SLMRender) root.SLMRender.setMarkdown(answer, data.response); else answer.textContent = data.response;
            const meta = node('p', 'small text-muted mt-2'); meta.dataset.sourceVersion = data.source.source_version;
            const refs = node('p', 'small text-break'); refs.dataset.references = JSON.stringify(data.source.references || []);
            exchange.append(questionLabel, question, answerLabel, answer, node('p', 'small', 'unverified'), meta, refs);
            if (data.source.truncated) exchange.append(node('p', 'small', 'partial'));
            this.transcript.append(exchange);
        }
        async sendTeacher() {
            if (!this.checkOwner() || this.mode !== 'teacher' || this.teacherBusy || this.receipt || !this.context.contentId) return;
            if (root.AuthService?.getRole?.() !== 'student') { this.teacherError = { key: 'teacher_student' }; this.translate(); return; }
            const subject = this.subject.value.trim(), description = this.description.value.trim();
            if (!subject || !description || subject.length > 200 || description.length > 4000) {
                this.teacherError = { key: 'teacher_required' }; this.translate(); return;
            }
            const payload = { subject, description, urgency: Number(this.urgency.value),
                content_id: this.context.contentId, study_plan_id: this.context.studyPlanId };
            if (![1, 2, 3].includes(payload.urgency)) return;
            if (this.context.sessionId) payload.session_id = this.context.sessionId;
            const fingerprint = JSON.stringify(payload);
            if (!this.pendingTeacher || this.pendingTeacher.fingerprint !== fingerprint) this.pendingTeacher = {id:requestId(),fingerprint};
            payload.client_request_id = this.pendingTeacher.id;
            const epoch = this.epoch; this.teacherBusy = true; this.teacherError = null; this.translate();
            try {
                const data = await this.request('/api/classroom/help', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (!this.current(epoch)) return;
                if (!validId(data?.id) || String(data.student_id) !== this.owner || !['open','resolved'].includes(data.status) || data.client_request_id !== payload.client_request_id ||
                    data.content_id !== payload.content_id || (data.study_plan_id ?? null) !== payload.study_plan_id ||
                    data.request_text !== `${subject}: ${description}` || (this.context.contextRevision && context({contextRevision:data.context_revision}).contextRevision !== this.context.contextRevision)) {
                    this.teacherError = { key: 'teacher_unconfirmed' }; return;
                }
                this.receipt = data;
            } catch (error) { if (this.current(epoch)) this.teacherError = { key: 'failed', detail: error.message }; }
            finally { if (this.current(epoch)) { this.teacherBusy = false; this.translate(); if (this.receipt) this.newRequest.focus(); } }
        }
        errorText(error) { return error ? t(error.key) + (error.detail && error.detail !== t(error.key) ? ` ${error.detail}` : '') : ''; }
        translate() {
            this.host.querySelectorAll('[data-i18n^="help_panel."]').forEach(element => {
                element.textContent = t(element.dataset.i18n.slice('help_panel.'.length));
            });
            this.contextLabel.textContent = `${t('context')}: ${this.context.contentTitle || this.context.contentId || ''}`;
            this.tutor.hidden = this.mode !== 'tutor'; this.teacher.hidden = this.mode !== 'teacher';
            [['tutor', this.tutorButton], ['teacher', this.teacherButton]].forEach(([mode, control]) => {
                control.setAttribute('aria-expanded', String(this.mode === mode)); control.disabled = !this.owner;
                control.classList.toggle('active', this.mode === mode);
            });
            this.policyStatus.textContent = this.loading ? t('loading') : this.errorText(this.loadError) || (this.policy ? t(this.policy.mode) : '');
            this.sourceBox.hidden = !this.source;
            this.sourceVersion.textContent = this.source ? `${t('source_version')}: ${this.source.source_version}` : '';
            this.sourcePartial.textContent = this.source ? t(this.source.truncated ? 'partial' : 'complete') : '';
            this.refreshButton.disabled = this.loading || !this.owner;
            this.assistance.querySelector('[value="explanation"]').disabled = this.policy?.mode !== 'explanations';
            if (this.policy?.mode !== 'explanations') this.assistance.value = 'hint';
            this.assistance.disabled = !this.policy || this.policy.mode === 'disabled' || this.tutorBusy;
            this.tutorSend.disabled = !this.owner || !this.source || !this.policy || this.policy.mode === 'disabled' || this.tutorBusy || this.loading || this.pendingTutor?.cancelling || this.usageBlocksSend();
            this.cancelButton.hidden = (!this.pendingTutor || this.pendingTutor.terminal) && !this.usage?.active_request_id;
            this.cancelButton.disabled = !this.owner || Boolean(this.pendingTutor?.cancelling);
            this.newTutorButton.hidden = !this.pendingTutor || this.pendingTutor.terminal || this.tutorBusy || !(this.tutorError || this.cancelState?.key === 'cancel_unconfirmed');
            this.newTutorButton.disabled = !this.owner || Boolean(this.pendingTutor?.cancelling);
            this.cancelStatus.textContent = this.cancelState ? t(this.cancelState.key) : '';
            this.usageStatus.textContent = this.usage ? `${t('usage')}: ${this.usage.requests_used_today} / ${this.usage.requests_limit_daily}. ` +
                (this.usage.requests_used_today >= this.usage.requests_limit_daily ? t('request_limit') :
                    this.usage.active_request_id ? t('request_active') : '') : t('usage_unavailable');
            this.tutorStatus.textContent = this.tutorBusy ? t('sending') : this.errorText(this.tutorError);
            this.teacherSend.disabled = !this.owner || !this.context.contentId || this.teacherBusy || Boolean(this.receipt);
            [this.subject, this.description, this.urgency].forEach(input => { input.disabled = !this.owner || this.teacherBusy || Boolean(this.receipt); });
            this.teacherForm.hidden = Boolean(this.receipt); this.newRequest.hidden = !this.receipt;
            this.teacherStatus.textContent = this.teacherBusy ? t('teacher_sending') : this.receipt ? t(this.receipt.status === 'resolved' ? 'teacher_receipt_resolved' : 'teacher_receipt', { id: this.receipt.id }) : this.errorText(this.teacherError);
            this.transcript.querySelectorAll('[data-source-version]').forEach(element => { element.textContent = `${t('source_version')}: ${element.dataset.sourceVersion}`; });
            this.transcript.querySelectorAll('[data-references]').forEach(element => { element.textContent = `${t('references')}: ${JSON.parse(element.dataset.references).join(', ')}`; });
            this.sectionChoices.querySelectorAll('[data-section-title]').forEach(element => {
                element.textContent = `${element.dataset.sectionTitle} (${element.dataset.characters} ${t('characters')})`;
            });
            this.renderReceipt();
        }
        destroy() {
            if (this.destroyed) return;
            this.invalidate(); this.destroyed = true; this.history = []; this.owner = null;
            this.host.removeEventListener('keydown', this.onKey);
            document.removeEventListener('i18n-loaded', this.onLanguage);
            document.removeEventListener('i18n-language-changed', this.onLanguage);
            root.removeEventListener('storage', this.onStorage); this.host.replaceChildren(); mounted.delete(this.host);
        }
    }
    /** Mount inline lesson help; close preserves input, setContext clears the previous lesson's conversation. */
    function mount(host, options = {}) {
        if (!host || !root.SLMClient) throw new Error('SLMHelp needs a host element and SLMClient.');
        mounted.get(host)?.destroy(); const panel = new HelpPanel(host, options); mounted.set(host, panel);
        return Object.freeze({ open: (mode, trigger) => panel.open(mode, trigger), close: () => panel.close(),
            setContext: next => panel.setContext(next), destroy: () => panel.destroy() });
    }
    root.SLMHelp = Object.freeze({ mount });
})(window);
