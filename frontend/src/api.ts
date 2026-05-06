import { clearAuth, getToken } from './auth';
import type { Alert, Camera, LoginResponse, MotionEvent } from './types';

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const resp = await fetch(`/api${path}`, { ...options, headers });

  // Best-effort body parse — some endpoints return empty 204, not relevant
  // for this app but worth being defensive about.
  const body = await resp.json().catch(() => ({} as Record<string, unknown>));

  if (resp.status === 401) {
    // Token rejected (expired or revoked). Wipe it; the router boots the
    // user back to /login on the next render via RequireAuth.
    clearAuth();
  }

  if (!resp.ok) {
    const code = (body as { error?: string }).error ?? 'unknown';
    const message = (body as { message?: string }).message ?? resp.statusText;
    throw new ApiError(resp.status, code, message);
  }

  return body as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  listCameras: () => request<{ cameras: Camera[] }>('/cameras'),
  createCamera: (data: { device_id: string; name: string; location?: string }) =>
    request<{ camera: Camera }>('/cameras', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  recentEvents: (cameraId: number) =>
    request<{ events: MotionEvent[] }>(`/events/by-camera/${cameraId}/recent`),
  ingestEvent: (data: {
    device_id: string;
    event_id_client: string;
    confidence?: number;
    payload?: unknown;
  }) =>
    // Custom return shape: we want the HTTP status (200 = idempotent replay,
    // 201 = first write) so the UI can tell the user which one happened.
    fetch('/api/events', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken() ?? ''}`,
      },
      body: JSON.stringify(data),
    }).then(async (resp) => {
      const body = await resp.json().catch(() => ({}));
      return { status: resp.status, body } as {
        status: number;
        body: { event?: MotionEvent; error?: string; message?: string };
      };
    }),
  recentAlerts: () => request<{ alerts: Alert[] }>('/alerts/recent'),
  ackAlert: (alertId: number) =>
    request<{ alert: Alert }>(`/alerts/${alertId}/ack`, { method: 'POST' }),
};
