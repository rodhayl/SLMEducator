/* Explicit timezone display; legacy offset-free timestamps are never guessed. */
(function (root) {
    'use strict';
    let timezone = 'UTC';
    let owner = null;
    let pending = null;
    let revision = 0;
    let saving = false;
    let lastStatus = null;
    const text = (key, fallback) => root.SLMClient.message(key, fallback);
    function validTimezone(value) {
        if (typeof value !== 'string' || !value.trim()) return false;
        try { new Intl.DateTimeFormat('en', { timeZone: value }); return true; }
        catch { return false; }
    }
    function epoch(value, provenance) {
        if (provenance === 'legacy_unknown' || typeof value !== 'string' ||
            !/T| /.test(value) || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
        const instant = Date.parse(value);
        return Number.isFinite(instant) ? instant : null;
    }
    function format(value, options = {}) {
        if (value === null || value === undefined || value === '') return '—';
        const instant = epoch(value, options.provenance);
        if (instant === null) return String(value) + ' (' + text('timezone_unknown', 'timezone unknown') + ')';
        const zone = validTimezone(options.timezone) ? options.timezone : timezone;
        return new Intl.DateTimeFormat(options.locale, {
            timeZone: zone, year: 'numeric', month: 'short', day: 'numeric',
            ...(options.dateOnly ? {} : { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        }).format(new Date(instant)) + ` (${zone})`;
    }
    function apply(settings) {
        if (!validTimezone(settings?.timezone)) throw new Error('Invalid timezone settings');
        timezone = settings.timezone;
        const field = document.getElementById('settings-timezone');
        if (field) field.value = timezone;
        return settings;
    }
    async function load(force = false) {
        const account = root.SLMClient.account();
        if (owner !== account) { owner = account; timezone = 'UTC'; pending = null; }
        if (!account) return { timezone: 'UTC', timezone_source: 'default' };
        if (!pending || force) {
            const version = ++revision;
            const requestedOwner = account;
            pending = root.SLMClient.request('/api/settings/timezone').then(settings => {
                if (root.SLMClient.account() === requestedOwner && version === revision) return apply(settings);
                throw new Error('Account changed');
            }).catch(error => { if (version === revision) pending = null; throw error; });
        }
        return pending;
    }
    function status(key, fallback, failed = false) {
        lastStatus = {key, fallback, failed};
        const target = document.getElementById('timezone-status');
        if (target) { target.textContent = text(key, fallback); target.classList.toggle('text-danger', failed); }
    }
    root.loadTimezoneSettings = async function () {
        if (saving) return;
        try {
            const settings = await load(true);
            if (settings.timezone_source === 'default') status('timezone_default', 'UTC is the explicit default. Choose and save your timezone.');
            else status('timezone_loaded', 'Saved timezone loaded.');
        } catch { status('timezone_load_failed', 'Could not load your timezone. Dates use the last confirmed setting, or UTC if none.', true); }
    };
    root.saveTimezoneSettings = async function () {
        if (saving) return;
        const field = document.getElementById('settings-timezone');
        const selected = field.value.trim();
        if (!validTimezone(selected)) { status('timezone_invalid', 'Enter a valid IANA timezone, such as Europe/Madrid.', true); field.focus(); return; }
        saving = true;
        field.disabled = true;
        const button = document.getElementById('save-timezone');
        button.disabled = true;
        const requestedOwner = root.SLMClient.account();
        try {
            const settings = await root.SLMClient.request('/api/settings/timezone', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ timezone: selected }) });
            if (settings?.timezone !== selected || requestedOwner !== root.SLMClient.account()) throw new Error('Timezone save not confirmed');
            revision++;
            apply(settings);
            pending = Promise.resolve(settings);
            status('timezone_saved', 'Timezone saved. Existing timestamps with no offset remain unknown.');
            if (typeof root.loadProfile === 'function') root.loadProfile();
        } catch { status('timezone_save_failed', 'Timezone could not be saved. Your selection is kept; retry.', true); }
        finally { saving = false; button.disabled = false; field.disabled = false; }
    };
    // Translate the existing result, without a new request or changing an unsaved selection.
    for (const event of ['i18n-loaded', 'i18n-language-changed']) {
        document.addEventListener(event, () => {
            if (lastStatus) status(lastStatus.key, lastStatus.fallback, lastStatus.failed);
        });
    }
    root.SLMTime = Object.freeze({ format, epoch, validTimezone, load, getTimezone: () => timezone });
})(window);
