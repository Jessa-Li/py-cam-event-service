import type { Camera } from '../types';
import styles from './CameraList.module.css';

interface Props {
  cameras: Camera[];
  selectedId?: number;
  loading: boolean;
  onSelect: (camera: Camera) => void;
  onRefresh: () => void;
}

export default function CameraList({ cameras, selectedId, loading, onSelect, onRefresh }: Props) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <h2>Cameras</h2>
        <button onClick={onRefresh} className={styles.refresh} title="GET /cameras">
          ↻
        </button>
      </div>
      {loading ? (
        <div className={styles.empty}>Loading…</div>
      ) : cameras.length === 0 ? (
        <div className={styles.empty}>No cameras registered yet.</div>
      ) : (
        <ul className={styles.list}>
          {cameras.map((c) => (
            <li key={c.id}>
              <button
                className={c.id === selectedId ? styles.itemActive : styles.item}
                onClick={() => onSelect(c)}
              >
                <div className={styles.itemName}>{c.name}</div>
                <div className={styles.itemSub}>
                  <code>{c.device_id}</code>
                  {c.location && <span> · {c.location}</span>}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
