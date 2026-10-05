/* Shared rendering boundary. DOMPurify is vendored; never trust author/model HTML. */
(function (root) {
    'use strict';
    function escape(value) {
        const node = document.createElement('span');
        node.textContent = String(value ?? '');
        return node.innerHTML.replaceAll('"', '&quot;').replaceAll("'", '&#39;');
    }
    function html(value) {
        if (!root.DOMPurify) return escape(value); // Fail closed if the bundle is unavailable.
        return root.DOMPurify.sanitize(String(value ?? ''), {
            ALLOWED_TAGS: ['p', 'br', 'hr', 'strong', 'b', 'em', 'i', 'u', 's', 'del',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote',
                'pre', 'code', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
                'div', 'span', 'sup', 'sub'],
            ALLOWED_ATTR: ['href', 'title', 'colspan', 'rowspan'],
            ALLOW_DATA_ATTR: false,
            ALLOW_ARIA_ATTR: false,
            SANITIZE_NAMED_PROPS: true
        });
    }
    function markdown(value) {
        return root.marked ? html(root.marked.parse(String(value ?? ''), { async: false })) : escape(value);
    }
    function setMarkdown(element, value) {
        if (!element) return;
        element.innerHTML = markdown(value);
        element.querySelectorAll('a[href]').forEach(link => {
            try {
                const url = new URL(link.getAttribute('href'), root.location.href);
                if (!['http:', 'https:', 'mailto:'].includes(url.protocol)) link.removeAttribute('href');
                else if (url.origin !== root.location.origin) link.rel = 'noopener noreferrer';
            } catch { link.removeAttribute('href'); }
        });
    }
    function generationNotice(element, data) {
        if (!element) return;
        element.querySelector('[data-generation-notice]')?.remove();
        const usage = data?.source_selection || data?.generation?.source_usage || data?._source_usage;
        if (!usage || (!data?.source_selection && !usage.source_document_id)) return;
        const message = (key, fallback) => root.SLMClient?.message?.(key, fallback) || fallback;
        const notice = document.createElement('p');
        notice.dataset.generationNotice = '';
        notice.className = 'alert alert-warning';
        notice.setAttribute('role', 'status');
        const ranges = usage.ranges || [];
        const supplied = usage.supplied_characters ?? ranges.reduce((sum, range) => sum + Math.max(0, Number(range.end) - Number(range.start)), 0);
        const total = Number(usage.source_characters);
        const count = Number.isFinite(supplied) && Number.isFinite(total) ? ` ${supplied}/${total}.` : '';
        notice.textContent = message('source_context', 'Source context') + count + ' ' +
            (usage.use_coverage === 'partial' ? message('source_partial', 'Partial source: some material was not included.') + ' ' : '') +
            message('generation_receipt_scope', 'This receipt records text sent to the model; it does not prove that the response is supported by the source.');
        element.prepend(notice);
    }
    function lessonText(data) {
        if (!data || typeof data !== 'object') return typeof data === 'string' ? data : '';
        const message = (key, fallback) => root.SLMClient?.message?.(key, fallback) || fallback;
        const blocks = [];
        const list = (key, title) => {
            const items = Array.isArray(data[key]) ? data[key].filter(item => typeof item === 'string') : [];
            if (items.length) blocks.push(`## ${title}\n\n` + items.map(item => `- ${item}`).join('\n'));
        };
        list('objectives', message('learning_objectives', 'Learning objectives'));
        if (Array.isArray(data.sections) && data.sections.length) {
            data.sections.forEach(section => {
                if (!section || typeof section !== 'object') return;
                const title = typeof section.title === 'string' ? `## ${section.title}\n\n` : '';
                const body = section.content || section.text;
                if (typeof body === 'string') blocks.push(title + body);
            });
        } else {
            const body = data.content || data.body || data.text;
            if (typeof body === 'string') blocks.push(body);
        }
        if (typeof data.summary === 'string') blocks.push(`## ${message('lesson_summary', 'Summary')}\n\n${data.summary}`);
        if (Array.isArray(data.vocabulary)) {
            const terms = data.vocabulary.filter(term => term && typeof term.term === 'string' && typeof term.definition === 'string');
            if (terms.length) blocks.push(`## ${message('lesson_terms', 'Key terms')}\n\n` + terms.map(term => `- **${term.term}**: ${term.definition}`).join('\n'));
        }
        list('key_concepts', message('lesson_concepts', 'Key concepts'));
        list('discussion_questions', message('lesson_questions', 'Discussion questions'));
        for (const [key, label] of [['worked_example','Worked example'],['independent_attempt','Independent attempt'],['feedback','Feedback'],['delayed_review','Later review'],['prerequisite_check','Before you start']]) {
            if (typeof data[key] === 'string') blocks.push(`## ${message('lesson_' + key, label)}\n\n${data[key]}`);
        }
        return blocks.join('\n\n');
    }
    root.SLMRender = Object.freeze({ escape, html, markdown, setMarkdown, generationNotice, lessonText });
})(window);
