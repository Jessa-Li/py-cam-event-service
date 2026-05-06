// Token storage. Using localStorage matches the 8h TTL on the backend — we
// re-login when it expires rather than refresh-token rotation, which is the
// right shape for an admin dashboard but NOT what you'd ship for a public
// consumer app (where refresh tokens + httpOnly cookies are safer).
import type { User } from './types';

const TOKEN_KEY = 'auth.token';
const USER_KEY = 'auth.user';

export function saveAuth(token: string, user: User): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// Decode the JWT payload locally just to short-circuit obviously-expired
// tokens. The backend is still the source of truth — never trust this for
// authorization decisions.
export function isTokenValid(token: string | null): boolean {
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}
