import { useEffect, useState } from 'react';
import styles from './ArchitectureDiagram.module.css';

export type Step =
  | 'login'
  | 'list-cameras'
  | 'register-camera'
  | 'ingest-event'
  | 'read-events'
  | 'list-alerts'
  | 'ack-alert';

interface StepInfo {
  title: string;
  method: string;
  path: string;
  flow: string[];
}

// What each user action actually does on the server, expanded for the side
// panel. Keep these in sync with the backend handlers.
const stepInfo: Record<Step, StepInfo> = {
  login: {
    title: 'Login',
    method: 'POST',
    path: '/auth/login',
    flow: [
      'Flask: rate-limit check (5/min/ip)',
      'Postgres: SELECT user WHERE email=$1',
      'werkzeug: check_password_hash',
      'JWT: mint token (8h ttl, is_admin claim)',
    ],
  },
  'list-cameras': {
    title: 'List cameras',
    method: 'GET',
    path: '/cameras',
    flow: [
      'Flask: @jwt_required',
      'Postgres: SELECT * FROM cameras ORDER BY created_at DESC',
    ],
  },
  'register-camera': {
    title: 'Register camera',
    method: 'POST',
    path: '/cameras',
    flow: [
      'Flask: @admin_required (is_admin claim must be true)',
      'Postgres: SELECT WHERE device_id=$1 (uniqueness check)',
      'Postgres: INSERT INTO cameras',
    ],
  },
  'ingest-event': {
    title: 'Ingest motion event',
    method: 'POST',
    path: '/events',
    flow: [
      'Flask: @jwt_required + 60/min/camera limit',
      'Postgres: SELECT WHERE (camera_id, event_id_client) — idempotency',
      'Postgres: INSERT INTO motion_events  (or 200 with existing row)',
      'Redis: DEL recent_events:<camera_id>',
      'Classifier: classify(payload, confidence) — inline stub',
      'Postgres: INSERT INTO alerts (if score >= threshold)',
      'Redis: DEL recent_alerts:<owner_id>',
    ],
  },
  'read-events': {
    title: 'Read recent events',
    method: 'GET',
    path: '/events/by-camera/:id/recent',
    flow: [
      'Flask: cache.memoize(15s) — Redis GET first',
      'Postgres (on miss): SELECT motion_events WHERE detected_at >= now() - 1h',
      'Redis: SET recent_events:<id> with 15s ttl',
    ],
  },
  'list-alerts': {
    title: 'List recent alerts',
    method: 'GET',
    path: '/alerts/recent',
    flow: [
      'Flask: @jwt_required, scope to current user',
      'Postgres: JOIN alerts × motion_events × cameras — last 24h',
      'Frontend: poll every 60s (real notify uses push)',
    ],
  },
  'ack-alert': {
    title: 'Acknowledge alert',
    method: 'POST',
    path: '/alerts/:id/ack',
    flow: [
      'Flask: @jwt_required + ownership check',
      'Postgres: UPDATE alerts SET delivered_at = now() (idempotent)',
    ],
  },
};

// Which edges in the diagram light up for each step.
const stepEdges: Record<Step, Set<string>> = {
  login: new Set(['client-api', 'api-pg']),
  'list-cameras': new Set(['client-api', 'api-pg']),
  'register-camera': new Set(['client-api', 'api-pg']),
  'ingest-event': new Set(['client-api', 'api-pg', 'api-redis', 'api-ml', 'ml-pg']),
  'read-events': new Set(['client-api', 'api-redis', 'api-pg']),
  'list-alerts': new Set(['client-api', 'api-pg']),
  'ack-alert': new Set(['client-api', 'api-pg']),
};

interface Props {
  active: Step | null;
}

export default function ArchitectureDiagram({ active }: Props) {
  // Keep the side panel showing the LAST action even after the diagram dims,
  // so the user can still read what just happened.
  const [lastSeen, setLastSeen] = useState<Step | null>(null);
  useEffect(() => {
    if (active) setLastSeen(active);
  }, [active]);

  const lit = active ? stepEdges[active] : new Set<string>();
  const detail = lastSeen ? stepInfo[lastSeen] : null;

  const edgeClass = (id: string) => (lit.has(id) ? styles.edgeActive : styles.edge);
  const arrowMarker = (id: string) =>
    lit.has(id) ? 'url(#arrow-active)' : 'url(#arrow)';

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Request flow</h2>

      <div className={styles.svgWrap}>
      <svg
        viewBox="0 0 320 360"
        className={styles.svg}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M0,0 L10,5 L0,10 z" fill="#94a3b8" />
          </marker>
          <marker
            id="arrow-active"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M0,0 L10,5 L0,10 z" fill="#38bdf8" />
          </marker>
        </defs>

        {/* Browser node */}
        <g>
          <rect x="20" y="20" width="100" height="50" rx="6" className={styles.node} />
          <text x="70" y="42" textAnchor="middle" className={styles.nodeLabel}>
            Browser
          </text>
          <text x="70" y="58" textAnchor="middle" className={styles.nodeSub}>
            JWT in localStorage
          </text>
        </g>

        {/* Flask API node */}
        <g>
          <rect x="200" y="20" width="100" height="50" rx="6" className={styles.node} />
          <text x="250" y="42" textAnchor="middle" className={styles.nodeLabel}>
            Flask API
          </text>
          <text x="250" y="58" textAnchor="middle" className={styles.nodeSub}>
            gunicorn
          </text>
        </g>

        {/* ML Classifier node — inline module today, future: separate worker */}
        <g>
          <rect
            x="200"
            y="140"
            width="100"
            height="50"
            rx="6"
            className={styles.nodeDashed}
          />
          <text x="250" y="162" textAnchor="middle" className={styles.nodeLabel}>
            Classifier
          </text>
          <text x="250" y="178" textAnchor="middle" className={styles.nodeSub}>
            inline (→ queue at scale)
          </text>
        </g>

        {/* Postgres node */}
        <g>
          <rect x="20" y="260" width="130" height="60" rx="6" className={styles.node} />
          <text x="85" y="282" textAnchor="middle" className={styles.nodeLabel}>
            Postgres
          </text>
          <text x="85" y="298" textAnchor="middle" className={styles.nodeSub}>
            cameras · events
          </text>
          <text x="85" y="312" textAnchor="middle" className={styles.nodeSub}>
            users · alerts
          </text>
        </g>

        {/* Redis node */}
        <g>
          <rect x="200" y="260" width="100" height="50" rx="6" className={styles.node} />
          <text x="250" y="282" textAnchor="middle" className={styles.nodeLabel}>
            Redis
          </text>
          <text x="250" y="298" textAnchor="middle" className={styles.nodeSub}>
            cache · rate limit
          </text>
        </g>

        {/* Edge: Browser → API */}
        <line
          x1="120"
          y1="45"
          x2="200"
          y2="45"
          className={edgeClass('client-api')}
          markerEnd={arrowMarker('client-api')}
        />
        <text x="160" y="38" textAnchor="middle" className={styles.edgeLabel}>
          HTTP + JWT
        </text>

        {/* Edge: API → Classifier (vertical) */}
        <line
          x1="250"
          y1="72"
          x2="250"
          y2="138"
          className={edgeClass('api-ml')}
          markerEnd={arrowMarker('api-ml')}
        />
        <text x="258" y="108" className={styles.edgeLabel}>
          classify
        </text>

        {/* Edge: API → Postgres (diagonal, primary write/read path) */}
        <line
          x1="215"
          y1="72"
          x2="120"
          y2="258"
          className={edgeClass('api-pg')}
          markerEnd={arrowMarker('api-pg')}
        />
        <text x="155" y="155" className={styles.edgeLabel}>
          SQL
        </text>

        {/* Edge: Classifier → Postgres (writes alerts) */}
        <line
          x1="225"
          y1="192"
          x2="135"
          y2="258"
          className={edgeClass('ml-pg')}
          markerEnd={arrowMarker('ml-pg')}
        />
        <text x="170" y="230" className={styles.edgeLabel}>
          INSERT alert
        </text>

        {/* Edge: API → Redis */}
        <line
          x1="250"
          y1="72"
          x2="250"
          y2="138"
          className={styles.edgeGhost}
        />
        <line
          x1="240"
          y1="192"
          x2="240"
          y2="258"
          className={edgeClass('api-redis')}
          markerEnd={arrowMarker('api-redis')}
        />
      </svg>
      </div>

      <div className={styles.detail}>
        {detail ? (
          <>
            <div className={styles.detailHead}>
              <span className={styles.method}>{detail.method}</span>
              <code>{detail.path}</code>
            </div>
            <ol className={styles.flowList}>
              {detail.flow.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </>
        ) : (
          <div className={styles.detailEmpty}>
            Click around — the diagram highlights which services each call
            touches and this panel breaks down the server-side flow.
          </div>
        )}
      </div>
    </div>
  );
}
