class I18nService {
    constructor() {
        this.currentLang = 'es'; // Default to Spanish
        this.translations = {};
        this.fallbackTranslations = {}; // English fallback
        this.loaded = false;
        this.defaultLang = 'es';
        this.fallbackLang = 'en';

        // Debug mode - enabled on localhost
        this.debugMode = window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1';
        this.missingKeys = new Set();
    }

    async init() {
        try {
            // Load English fallback first (always needed)
            await this.loadFallbackTranslations();

            // Load default language
            const defaultLoaded = await this.loadTranslations(this.defaultLang);
            this.currentLang = defaultLoaded ? this.defaultLang : this.fallbackLang;

            // Try to load user preference if authenticated
            if (window.AuthService && window.AuthService.isAuthenticated()) {
                const token = window.AuthService.getToken();
                const res = await fetch('/api/settings/app', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const config = await res.json();
                    if (config.language && config.language !== this.currentLang) {
                        const preferredLoaded = await this.loadTranslations(config.language);
                        this.currentLang = config.language;
                        if (!preferredLoaded) {
                            console.warn(`[I18n] Language '${config.language}' not found. Falling back to English keys.`);
                        }
                    }
                }
            }

            this.translatePage();
            this.loaded = true;

            // Log debug info
            if (this.debugMode) {
                console.log(`[I18n] Loaded language: ${this.currentLang}`);
                console.log(`[I18n] Debug mode enabled - missing keys will be logged`);
            }

            document.dispatchEvent(new CustomEvent('i18n-loaded'));

        } catch (e) {
            console.error("I18n Init Error:", e);
        }
    }

    async loadFallbackTranslations() {
        try {
            const res = await fetch(`/api/settings/translations/${this.fallbackLang}`);
            if (res.ok) {
                this.fallbackTranslations = await res.json();
            }
        } catch (e) {
            console.warn('Failed to load fallback translations', e);
        }
    }

    async loadTranslations(lang) {
        try {
            const res = await fetch(`/api/settings/translations/${lang}`);
            if (res.ok) {
                const data = await res.json();
                this.translations = data;
                // Cache logic could go here
                return true;
            } else {
                console.error(`Failed to load translations for ${lang}`);
            }
        } catch (e) {
            console.error(`Network error loading translations for ${lang}`, e);
        }

        // Keep current language state, but force key-level fallback (English).
        this.translations = {};
        return false;
    }

    /**
     * Dynamically switch language without page reload.
     * This is the preferred method for changing language from settings.
     * @param {string} lang - Language code ('en' or 'es')
     * @returns {Promise<boolean>} - True if successful
     */
    async setLanguage(lang) {
        if (!lang || lang === this.currentLang) {
            return true; // Already using this language
        }

        try {
            // Load the new language translations
            const loaded = await this.loadTranslations(lang);
            this.currentLang = lang;

            // Re-translate the entire page
            this.translatePage();

            // Dispatch event so other components can react
            document.dispatchEvent(new CustomEvent('i18n-language-changed', {
                detail: { language: lang }
            }));

            if (this.debugMode) {
                if (loaded) {
                    console.log(`[I18n] Language switched to: ${lang}`);
                } else {
                    console.warn(`[I18n] Requested language '${lang}' missing. Using English fallback keys.`);
                }
            }

            return loaded;
        } catch (e) {
            console.error(`[I18n] Failed to switch language to ${lang}:`, e);
            return false;
        }
    }

    translatePage() {
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);
            if (translation) {
                // Check if we should update textContent, placeholder, or title
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    if (el.hasAttribute('placeholder')) {
                        el.placeholder = translation;
                    }
                } else {
                    el.textContent = translation;
                }

                // Also handle tooltips if any (title attribute)
                // If the element has data-i18n-title, we translate that too
            }
        });

        // Handle specific attributes
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });

        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            el.title = this.t(key);
        });
    }

    /**
     * Resolve a dot-notation key from a translations object
     * @param {string} key - Dot notation key like "navigation.dashboard"
     * @param {object} translations - Translation object to search
     * @returns {string|null} - Translation value or null if not found
     */
    resolve(key, translations) {
        if (!key || !translations) return null;

        const parts = key.split('.');
        let value = translations;

        for (const part of parts) {
            if (value && typeof value === 'object' && part in value) {
                value = value[part];
            } else {
                return null;
            }
        }

        return typeof value === 'string' ? value : null;
    }

    /**
     * Translate a key with optional parameters
     * Fallback chain: current language → English → raw key
     * @param {string} key - Translation key
     * @param {object} params - Interpolation parameters
     * @returns {string} - Translated string
     */
    t(key, params = {}) {
        if (!key) return '';

        // Try current language first
        let value = this.resolve(key, this.translations);

        // Fallback to English if not found
        if (!value && this.fallbackTranslations) {
            value = this.resolve(key, this.fallbackTranslations);
            if (value && this.debugMode && this.loaded) {
                console.warn(`[I18n] Using fallback for: ${key}`);
            }
        }

        // If still not found, track as missing and return raw key
        if (!value) {
            this.missingKeys.add(key);
            if (this.debugMode) {
                console.warn(`[I18n] Missing key: ${key}`);
            }
            return key;
        }

        // Apply parameter interpolation
        if (params && Object.keys(params).length > 0) {
            return value.replace(/{(\w+)}/g, (match, p1) => {
                return params[p1] !== undefined ? params[p1] : match;
            });
        }

        return value;
    }

    /**
     * Check if i18n is ready (translations loaded)
     * @returns {boolean}
     */
    get isReady() {
        return this.loaded;
    }

    /**
     * Get list of missing translation keys (for development debugging)
     * @returns {string[]} - Array of missing keys
     */
    getMissing() {
        return Array.from(this.missingKeys);
    }

    /**
     * Print missing keys summary to console
     */
    reportMissing() {
        if (this.missingKeys.size === 0) {
            console.log('[I18n] ✅ No missing translation keys!');
            return;
        }
        console.group(`[I18n] ❌ ${this.missingKeys.size} missing keys:`);
        this.getMissing().sort().forEach(key => console.log(`  • ${key}`));
        console.groupEnd();
    }
}

// Global I18n Instance
window.I18n = new I18nService();
window.I18nService = window.I18n; // Alias for compatibility with dashboard.js and other files

// Auto-init on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.I18n.init();
});
