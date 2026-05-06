import type { Camera, MotionEvent } from '../types';
import styles from './EventFeed.module.css';

interface Props {
  events: MotionEvent[];
  loading: boolean;
  camera: Camera;
  onRefresh: () => void;
}

export default function EventFeed({ events, loading, camera, onRefresh }: Props) {
  return (
    <div className={styles.feed}>
      <div className={styles.head}>
        <h3>Recent events</h3>
        <button
          onClick={onRefresh}
          className={styles.refresh}
          title="GET /events/by-camera/.../recent"
        >
          ↻ Refresh
        </button>
      </div>
      <p className={styles.note}>
        Last hour, max 100. Cached server-side for 15s; an ingest invalidates
        the cache, so a simulated event shows up immediately on refresh.
      </p>
      {loading && events.length === 0 ? (
        <div className={styles.empty}>Loading…</div>
      ) : events.length === 0 ? (
        <div className={styles.empty}>No events in the last hour.</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>camera</th>
              <th>detected_at</th>
              <th>confidence</th>
              <th>event_id_client</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{camera.name}</td>
                <td>{new Date(e.detected_at).toLocaleTimeString()}</td>
                <td>{e.confidence.toFixed(2)}</td>
                <td>
                  <code title={e.event_id_client}>{e.event_id_client}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
