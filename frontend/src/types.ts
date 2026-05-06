export interface User {
  id: number;
  email: string;
  is_admin: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Camera {
  id: number;
  device_id: string;
  owner_id: number | null;
  name: string;
  location: string | null;
  is_online: boolean;
  created_at: string;
}

export interface MotionEvent {
  id: number;
  camera_id: number;
  event_id_client: string;
  detected_at: string;
  confidence: number;
  video_url: string | null;
  raw_payload: unknown;
}

export interface Alert {
  id: number;
  event_id: number;
  user_id: number;
  ml_score: number;
  ml_label: string;
  channel: string;
  sent_at: string;
  delivered_at: string | null;
  // Embedded summaries returned by GET /alerts/recent so we don't N+1.
  event: {
    id: number;
    detected_at: string;
    confidence: number;
  };
  camera: {
    id: number;
    name: string;
    device_id: string;
    location: string | null;
  };
}
