(() => {
    const THEME_STORAGE_KEY = "slm_theme_preference";

    function applyTheme(theme) {
        const body = document.body;
        if (!body) return;

        body.classList.remove("theme-dark", "theme-light");

        if (theme === "dark") {
            body.classList.add("theme-dark");
        } else if (theme === "light") {
            body.classList.add("theme-light");
        } else {
            const prefersDark =
                window.matchMedia &&
                window.matchMedia("(prefers-color-scheme: dark)").matches;
            body.classList.add(prefersDark ? "theme-dark" : "theme-light");
        }
    }

    async function loadThemeFromServer() {
        const token = localStorage.getItem("token");
        if (!token) return null;

        try {
            const res = await fetch("/api/settings/app", {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.status === 401) {
                // Token is invalid/expired - clear it to fix the issue
                console.warn("Theme: Invalid token detected, clearing session");
                localStorage.removeItem("token");
                localStorage.removeItem("user");
                return null;
            }
            if (!res.ok) return null;
            const data = await res.json();
            return data?.theme || null;
        } catch {
            return null;
        }
    }

    async function initTheme() {
        const cached = localStorage.getItem(THEME_STORAGE_KEY);
        if (cached) applyTheme(cached);

        const serverTheme = await loadThemeFromServer();
        if (serverTheme) {
            localStorage.setItem(THEME_STORAGE_KEY, serverTheme);
            applyTheme(serverTheme);
            return;
        }

        if (!cached) applyTheme("auto");
    }

    window.ThemeService = {
        apply: applyTheme,
        init: initTheme,
        storageKey: THEME_STORAGE_KEY,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initTheme);
    } else {
        void initTheme();
    }
})();

