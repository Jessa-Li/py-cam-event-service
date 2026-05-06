import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api, ApiError } from '../api';
import { saveAuth } from '../auth';
import styles from './Login.module.css';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('admin');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp = await api.login(email, password);
      saveAuth(resp.access_token, resp.user);
      navigate('/app');
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError('login failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.shell}>
      <form className={styles.card} onSubmit={onSubmit}>
        <h1 className={styles.title}>py-cam-event-service</h1>
        <p className={styles.subtitle}>Sign in to continue</p>

        <label className={styles.field}>
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className={styles.field}>
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {error && <div className={styles.error}>{error}</div>}

        <button type="submit" className={styles.submit} disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>

        <p className={styles.hint}>
          Default dev creds: <code>admin@example.com</code> / <code>admin</code>
        </p>
      </form>
    </div>
  );
}
