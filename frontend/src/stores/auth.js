import { computed, reactive } from 'vue';
import { dispatchGateway } from '@/api/gateway';

/**
 * Global authentication state.
 *
 * Deliberately a module-level reactive object rather than a Pinia store:
 * the router guard and the app shell both need it before the app is mounted,
 * and the rest of the application only reads a handful of fields.
 */
const TOKEN_KEY = 'opchub_session_token';
const USER_KEY = 'opchub_user_session';
const ROLE_KEY = 'opchub_current_role';
const TAB_KEY = 'opchub_active_tab';

function readJSON(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
}

function readRole() {
  const saved = localStorage.getItem(ROLE_KEY);
  return saved === 'ADMIN' || saved === 'MAKER' ? saved : 'MAKER';
}

export const authState = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: readJSON(USER_KEY),
  role: readRole(),
  verified: false,
  checking: false,
  lastError: '',
});

export const isAuthenticated = computed(() => Boolean(authState.token));

export const isPlatformAdmin = computed(
  () => authState.user?.role === 'ADMIN' || authState.user?.user?.role === 'ADMIN'
);

export const mustChangePassword = computed(() => {
  const user = authState.user;
  if (!user) return false;
  return Boolean(user.must_change_password || user.session?.must_change_password);
});

export const displayName = computed(
  () => authState.user?.nickname || authState.user?.email || authState.user?.user?.nickname || '创客'
);

let sessionPromise = null;

function persistRole(role) {
  authState.role = role === 'ADMIN' ? 'ADMIN' : 'MAKER';
  localStorage.setItem(ROLE_KEY, authState.role);
}

/**
 * Write a successful auth payload (login / register / session refresh).
 * `payload` may be the AuthSessionResponse itself or `{ user, token }`.
 */
export function setSession(payload, { preferAdmin = false } = {}) {
  if (!payload) return null;
  const token = payload.token || authState.token;
  if (token) {
    authState.token = token;
    localStorage.setItem(TOKEN_KEY, token);
  }

  const user = payload.user || payload;
  authState.user = user;
  localStorage.setItem(USER_KEY, JSON.stringify(user));

  if (isPlatformAdmin.value) {
    const saved = localStorage.getItem(ROLE_KEY);
    if (saved === 'ADMIN' || saved === 'MAKER') {
      persistRole(saved);
    } else {
      persistRole(preferAdmin ? 'ADMIN' : 'MAKER');
    }
  } else {
    persistRole('MAKER');
  }

  authState.verified = true;
  authState.lastError = '';
  return user;
}

export function updateSessionUser(partial) {
  if (!partial) return;
  if (partial.token) {
    authState.token = partial.token;
    localStorage.setItem(TOKEN_KEY, partial.token);
  }
  const merged = { ...(authState.user || {}), ...partial };
  authState.user = merged;
  localStorage.setItem(USER_KEY, JSON.stringify(merged));
  if (isPlatformAdmin.value) {
    const saved = localStorage.getItem(ROLE_KEY);
    if (saved === 'ADMIN' || saved === 'MAKER') persistRole(saved);
  }
}

export function setRole(role) {
  if (role === 'ADMIN' && !isPlatformAdmin.value) return false;
  persistRole(role);
  return true;
}

export function toggleRole() {
  if (!isAuthenticated.value) return null;
  if (!isPlatformAdmin.value) {
    setRole('MAKER');
    return 'MAKER';
  }
  const next = authState.role === 'ADMIN' ? 'MAKER' : 'ADMIN';
  setRole(next);
  return next;
}

export function clearSession({ keepRole = false } = {}) {
  authState.token = '';
  authState.user = null;
  authState.verified = true;
  authState.lastError = '';
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(TAB_KEY);
  if (!keepRole) {
    authState.role = 'MAKER';
    localStorage.setItem(ROLE_KEY, 'MAKER');
  }
}

export function rememberTab(tab) {
  if (tab) localStorage.setItem(TAB_KEY, tab);
}

export function lastTab() {
  return localStorage.getItem(TAB_KEY) || '';
}

/**
 * Verify the stored token once per application boot.
 * Returns the current user, or null when the token is missing/expired.
 */
export async function ensureSession(force = false) {
  if (!authState.token) {
    authState.verified = true;
    return null;
  }
  if (authState.verified && !force) return authState.user;
  if (sessionPromise && !force) return sessionPromise;

  authState.checking = true;
  sessionPromise = (async () => {
    const res = await dispatchGateway('auth.session', {}, { silent: true });
    if (res.ok && res.data && (res.data.authenticated || res.data.valid)) {
      const user = res.data.user || res.data;
      authState.user = user;
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      if (isPlatformAdmin.value) {
        const saved = localStorage.getItem(ROLE_KEY);
        if (saved === 'ADMIN' || saved === 'MAKER') persistRole(saved);
        else persistRole('ADMIN');
      } else {
        persistRole('MAKER');
      }
      authState.verified = true;
      authState.lastError = '';
      return user;
    }

    authState.lastError = res.error || '会话已失效';
    clearSession({ keepRole: true });
    return null;
  })();

  try {
    return await sessionPromise;
  } finally {
    authState.checking = false;
    sessionPromise = null;
  }
}
