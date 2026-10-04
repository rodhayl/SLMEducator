export class AuthService {
    static _normalizeRole(role) {
        // Accept legacy shapes: { value: "teacher" } or objects with .value
        const v = role?.value ?? role ?? '';
        const s = String(v).trim();
        if (!s) return '';
        const lower = s.toLowerCase();
        if (lower === 'student' || lower === 'teacher' || lower === 'admin') return lower;
        // Tolerate enum-ish strings like "UserRole.ADMIN"
        if (s.includes('.')) {
            const tail = s.split('.').pop().trim().toLowerCase();
            if (tail === 'student' || tail === 'teacher' || tail === 'admin') return tail;
        }
        return lower;
    }

    static _normalizeUser(user) {
        if (!user || typeof user !== 'object') return user;
        const role = this._normalizeRole(user.role);
        // Always write canonical string shape
        return { ...user, role };
    }

    static async login(username, password) {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);

        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: params
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        const user = AuthService._normalizeUser(data.user);
        localStorage.setItem('user', JSON.stringify(user));
        return user;
    }

    static loginUrl() {
        return '/login.html?redirect=' + encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
    }

    static loginDestination(value) {
        try {
            const target = new URL(value || '/dashboard.html', window.location.origin);
            const allowed = ['/dashboard.html', '/session_player.html', '/assessment_taker.html', '/assessment_history.html', '/grading.html', '/study_plan_builder.html', '/course_designer.html', '/assessment_builder.html', '/portability.html', '/register.html'];
            return target.origin === window.location.origin && allowed.includes(target.pathname)
                ? target.pathname + target.search + target.hash : '/dashboard.html';
        } catch { return '/dashboard.html'; }
    }

    static logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
    }

    static getToken() {
        return localStorage.getItem('token');
    }

    static getUser() {
        const stored = localStorage.getItem('user');
        let user = null;
        if (stored) {
            try {
                user = JSON.parse(stored);
            } catch {
                // Corrupt storage; clear and treat as logged out-ish
                localStorage.removeItem('user');
                user = null;
            }
        }
        const normalized = AuthService._normalizeUser(user);
        if (normalized && JSON.stringify(normalized) !== JSON.stringify(user)) {
            localStorage.setItem('user', JSON.stringify(normalized));
        }
        return normalized;
    }

    static setUser(user) {
        localStorage.setItem('user', JSON.stringify(AuthService._normalizeUser(user)));
    }

    static getRole() {
        const user = AuthService.getUser();
        const fromUser = AuthService._normalizeRole(user?.role);
        if (fromUser) return fromUser;

        // Fallback: derive role from JWT payload to avoid UI regressions when
        // localStorage user is missing/outdated.
        const token = AuthService.getToken();
        if (!token) return '';
        try {
            const payload = AuthService.decodeJwtPayload(token);
            const fromToken = AuthService._normalizeRole(payload?.role);
            if (fromToken && user) {
                AuthService.setUser({ ...user, role: fromToken });
            }
            return fromToken;
        } catch {
            return '';
        }
    }

    static async refreshUser() {
        const token = AuthService.getToken();
        if (!token) return null;

        try {
            const resp = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!resp.ok) {
                // Treat auth failures as logged out.
                if (resp.status === 401 || resp.status === 403) {
                    AuthService.logout();
                }
                return null;
            }
            const profile = await resp.json();
            AuthService.setUser(profile);
            return profile;
        } catch {
            return null;
        }
    }

    static isAuthenticated() {
        const token = this.getToken();
        if (!token) return false;
        return !this.isTokenExpired(token);
    }

    static isTokenExpired(token, skewSeconds = 30) {
        try {
            const payload = this.decodeJwtPayload(token);
            const exp = payload?.exp;
            // Treat missing/invalid exp as expired (invalid token).
            if (!exp || typeof exp !== 'number') return true;
            const nowSeconds = Math.floor(Date.now() / 1000);
            return exp <= (nowSeconds + skewSeconds);
        } catch {
            // If we can't parse the token, treat it as expired (invalid).
            return true;
        }
    }

    static decodeJwtPayload(token) {
        const parts = String(token).split('.');
        if (parts.length < 2) return null;
        const base64Url = parts[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
        const json = atob(padded);
        return JSON.parse(json);
    }
    static async register(userData) {
        const token = AuthService.getToken();
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers,
            body: JSON.stringify(userData)
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Registration failed');
        }
        return await res.json();
    }
}

// Attach to global window for easier debugging/access if needed
window.AuthService = AuthService;

// Handle Login Form if present
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = loginForm.username.value;
        const password = loginForm.password.value;
        const errorDiv = document.getElementById('error-msg');

        try {
            errorDiv.classList.add('d-none');
            errorDiv.style.display = 'none';
            await AuthService.login(username, password);
            const redirect = new URLSearchParams(window.location.search).get('redirect');
            window.location.href = AuthService.loginDestination(redirect);
        } catch (err) {
            errorDiv.textContent = err.message;
            errorDiv.classList.remove('d-none');
            errorDiv.style.display = 'block';
        }
    });
}

// Handle Register Form
const registerForm = document.getElementById('register-form');
if (registerForm) {
    const errorDiv = document.getElementById('error-msg');
    const message = (key, fallback) => SLMClient.message(key, fallback);
    const control = name => registerForm.elements.namedItem(name);
    const allowedRoles = () => AuthService.getRole() === 'admin' ? ['student', 'teacher', 'admin'] : AuthService.getRole() === 'teacher' ? ['student'] : [];
    let creatingAccount = false;
    let accountCreated = false;

    const showRegisterError = (message) => {
        if (!errorDiv) return;
        errorDiv.classList.remove('alert', 'alert-success');
        errorDiv.classList.add('error-message');
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
        errorDiv.style.display = 'block';
    };

    const buildRoleOptions = (roleSelect, allowedRoles) => {
        roleSelect.innerHTML = '';
        allowedRoles.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r;
            opt.dataset.i18n = 'recovery.role_' + r;
            opt.textContent = message('role_' + r, r.charAt(0).toUpperCase() + r.slice(1));
            roleSelect.appendChild(opt);
        });
    };

    const configureRegisterForm = () => {
        if (!AuthService.isAuthenticated()) {
            window.location.href = AuthService.loginUrl();
            return false;
        }

        const currentRole = AuthService.getRole();
        const roleSelect = control('role');
        if (!roleSelect) return true;

        const permittedRoles = allowedRoles();

        if (permittedRoles.length === 0) {
            showRegisterError(message('create_user_denied', 'Only teachers and administrators can create accounts.'));
            registerForm.querySelectorAll('input, select, button').forEach(el => { el.disabled = true; });
            setTimeout(() => { window.location.href = '/dashboard.html'; }, 800);
            return false;
        }

        buildRoleOptions(roleSelect, permittedRoles);

        const params = new URLSearchParams(window.location.search);
        const requestedRole = AuthService._normalizeRole(params.get('role'));
        if (requestedRole && permittedRoles.includes(requestedRole)) {
            roleSelect.value = requestedRole;
        } else {
            roleSelect.value = permittedRoles[0];
        }

        if (currentRole === 'teacher') {
            roleSelect.value = 'student';
            roleSelect.disabled = true;
        }
        return true;
    };

    configureRegisterForm();
    const updateRoleSummary = () => {
        const selected = control('role');
        document.getElementById('register-role-summary').textContent = message('selected_role', 'Account role:') + ' ' + (selected.selectedOptions[0]?.textContent || '');
    };
    control('role').addEventListener('change', updateRoleSummary);
    document.addEventListener('i18n-loaded', updateRoleSummary);
    updateRoleSummary();
    document.getElementById('create-another-account').onclick = () => {
        accountCreated = false;
        const selectedRole = control('role').value;
        registerForm.reset();
        control('role').value = selectedRole;
        errorDiv.classList.add('d-none');
        document.getElementById('register-success-actions').classList.add('d-none');
        registerForm.querySelector('[type=submit]').disabled = false;
        control('first_name').focus();
    };

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (creatingAccount || accountCreated) return;
        if (!AuthService.isAuthenticated()) { window.location.href = AuthService.loginUrl(); return; }
        if (!allowedRoles().includes(control('role').value)) {
            showRegisterError(message('create_user_denied', 'Only teachers and administrators can create accounts.'));
            return;
        }
        const data = {
            role: control('role').value,
            first_name: control('first_name').value,
            last_name: control('last_name').value,
            email: control('email').value,
            username: control('username').value,
            password: control('password').value
        };

        creatingAccount = true;
        const submitButton = registerForm.querySelector('[type=submit]');
        submitButton.disabled = true;
        try {
            errorDiv.classList.add('d-none');
            errorDiv.style.display = 'none';
            await AuthService.register(data);
            accountCreated = true;
            errorDiv.textContent = message('account_created', 'Account created. You are still signed in to your own account.');
            errorDiv.classList.remove('d-none');
            errorDiv.style.display = 'block';
            errorDiv.classList.remove('error-message');
            errorDiv.classList.add('alert', 'alert-success');

            control('password').value = '';
            const destination = data.role === 'student' ? 'students' : data.role === 'teacher' ? 'teachers' : 'admins';
            document.getElementById('register-return').href = '/dashboard.html?tab=' + destination;
            document.getElementById('register-success-actions').classList.remove('d-none');
            document.getElementById('register-return').focus();
        } catch (err) {
            errorDiv.classList.remove('alert', 'alert-success');
            errorDiv.classList.add('error-message');
            errorDiv.textContent = err.message;
            errorDiv.classList.remove('d-none');
            errorDiv.style.display = 'block';
        } finally {
            creatingAccount = false;
            submitButton.disabled = accountCreated;
        }
    });
}
