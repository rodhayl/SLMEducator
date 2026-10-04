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
    root.SLMRender = Object.freeze({ escape, html, markdown, setMarkdown });
})(window);
