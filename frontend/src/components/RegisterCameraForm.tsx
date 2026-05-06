import { FormEvent, useState } from 'react';

import { api, ApiError } from '../api';
import type { Camera } from '../types';
import styles from './RegisterCameraForm.module.css';

interface Props {
  onCreated: (camera: Camera) => void;
}

export default function RegisterCameraForm({ onCreated }: Props) {
  const [deviceId, setDeviceId] = useState('');
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp = await api.createCamera({
        device_id: deviceId,
        name,
        location: location || undefined,
      });
      onCreated(resp.camera);
      setDeviceId('');
      setName('');
      setLocation('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'failed to register');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className={styles.card} onSubmit={onSubmit}>
      <h2>Register camera</h2>
      <p className={styles.note}>
        Admin-only. Hits <code>POST /cameras</code>.
      </p>
      <input
        placeholder="device_id (e.g. cam-1)"
        value={deviceId}
        onChange={(e) => setDeviceId(e.target.value)}
        required
      />
      <input
        placeholder="name (e.g. Front Door)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <input
        placeholder="location (optional)"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
      />
      {error && <div className={styles.error}>{error}</div>}
      <button type="submit" disabled={busy} className={styles.btn}>
        {busy ? 'Registering…' : 'Register'}
      </button>
    </form>
  );
}
