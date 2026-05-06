import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '../api';
import type { Alert } from '../types';
import styles from './AlertFeed.module.css';

interface Props {
  // Notify the parent so the architecture diagram can highlight the right
  // edges. These are wired up in Dashboard.tsx.
  onListStart: () => void;
  onAckStart: () => void;
}

const POLL_MS = 60_000;

export default function AlertFeed({ onListStart, onAckStart }: Props) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track previously-seen ids so we can flash new ones in the UI without
  // animating every existing alert on every poll.
  const seenIds = useRef<Set<number>>(new Set());
  const [flashIds, setFlashIds] = useState<Set<number>>(new Set());

  const refresh = useCallback(
    async (silent = false) => {
      if (!silent) onListStart();
      try {
        const resp = await api.recentAlerts();
        const fresh = new Set<number>();
        for (const a of resp.alerts) {
          if (!seenIds.current.has(a.id)) fresh.add(a.id);
          seenIds.current.add(a.id);
        }
        setAlerts(resp.alerts);
        setError(null);
        if (fresh.size > 0) {
          setFlashIds(fresh);
          setTimeout(() => setFlashIds(new Set()), 2500);
        }
      } catch {
        setError('failed to load alerts');
      } finally {
        setLoading(false);
      }
    },
    [onListStart],
  );

  useEffect(() => {
    refresh();
    // Polling stand-in for a real WebSocket / SSE push. 60s is a reasonable
    // cadence for an admin dashboard; an end-user app would want push so
    // the phone can wake from background without a long-poll burning battery.
    const t = setInterval(() => refresh(true), POLL_MS);
    return () => clearInterval(t);
  }, [refresh]);

  async function ack(id: number) {
    onAckStart();
    try {
      const resp = await api.ackAlert(id);
      // The ack endpoint returns the bare alert (no joined event/camera),
      // so merge — don't replace — to preserve the embedded objects we
      // need for rendering.
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, ...resp.alert } : a)),
      );
    } catch {
      setError('failed to ack');
    }
  }

  const undelivered = alerts.filter((a) => a.delivered_at === null).length;

  return (
    <div className={styles.feed}>
      <div className={styles.head}>
        <h3>
          Alerts
          {undelivered > 0 && <span className={styles.badge}>{undelivered}</span>}
        </h3>
        <button onClick={() => refresh()} className={styles.refresh}>
          ↻ Refresh
        </button>
      </div>
      <p className={styles.note}>
        Last 24h. Polled every 60s — in production these arrive via WebSocket
        / push so the user app doesn't burn battery polling. Hit Refresh for
        an immediate fetch.
      </p>
      {error && <div className={styles.error}>{error}</div>}
      {loading && alerts.length === 0 ? (
        <div className={styles.empty}>Loading…</div>
      ) : alerts.length === 0 ? (
        <div className={styles.empty}>
          No alerts yet. Simulate a high-confidence motion event on a camera
          you own — the classifier will fire and one will appear here.
        </div>
      ) : (
        <ul className={styles.list}>
          {alerts.map((a) => {
            const isNew = flashIds.has(a.id);
            const undeliveredCls = a.delivered_at === null ? styles.undelivered : '';
            return (
              <li
                key={a.id}
                className={`${styles.item} ${undeliveredCls} ${isNew ? styles.flash : ''}`}
              >
                <div className={styles.row1}>
                  <span className={styles.label}>{a.ml_label}</span>
                  <span className={styles.score}>
                    score {a.ml_score.toFixed(2)}
                  </span>
                  <span className={styles.channel}>via {a.channel}</span>
                </div>
                <div className={styles.row2}>
                  <strong>{a.camera.name}</strong>
                  <span className={styles.muted}>
                    · {new Date(a.event.detected_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className={styles.row3}>
                  {a.delivered_at ? (
                    <span className={styles.delivered}>
                      ✓ acked {new Date(a.delivered_at).toLocaleTimeString()}
                    </span>
                  ) : (
                    <button onClick={() => ack(a.id)} className={styles.ackBtn}>
                      Acknowledge
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
