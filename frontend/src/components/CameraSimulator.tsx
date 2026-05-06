import type { Camera } from '../types';
import styles from './CameraSimulator.module.css';

interface Props {
  camera: Camera;
  lastIngestStatus: string | null;
  canReplay: boolean;
  onSimulate: (replay: boolean) => void;
  onClose: () => void;
}

/**
 * The "input" side of the demo: shows which camera is selected and the
 * Simulate / Replay buttons. Lives in the left column under the camera
 * list. Events state lives in Dashboard and is rendered on the right.
 */
export default function CameraSimulator({
  camera,
  lastIngestStatus,
  canReplay,
  onSimulate,
  onClose,
}: Props) {
  return (
    <div className={styles.card}>
      <header className={styles.head}>
        <div className={styles.headText}>
          <h2>{camera.name}</h2>
          <div className={styles.meta}>
            <code>{camera.device_id}</code>
            {camera.location && <span> · {camera.location}</span>}
          </div>
        </div>
        <button
          onClick={onClose}
          className={styles.closeBtn}
          title="Deselect camera"
          aria-label="Deselect camera"
        >
          ×
        </button>
      </header>

      <section className={styles.simulator}>
        <h3>Simulate</h3>
        <p className={styles.simHint}>
          Confidence is randomized across <code>[0.6, 1.0]</code> — most events
          alert, some land below the classifier threshold and are dropped.{' '}
          <em>Replay last</em> sends the same <code>event_id_client</code> a
          second time and the server returns 200 with the same row id —
          idempotency contract.
        </p>
        <div className={styles.simButtons}>
          <button onClick={() => onSimulate(false)} className={styles.btnPrimary}>
            New motion event
          </button>
          <button
            onClick={() => onSimulate(true)}
            disabled={!canReplay}
            className={styles.btnSecondary}
          >
            Replay last
          </button>
        </div>
        {lastIngestStatus && <div className={styles.simStatus}>{lastIngestStatus}</div>}
      </section>
    </div>
  );
}
