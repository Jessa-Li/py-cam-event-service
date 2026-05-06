import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api';
import { clearAuth, getUser } from '../auth';
import AlertFeed from '../components/AlertFeed';
import CameraList from '../components/CameraList';
import CameraSimulator from '../components/CameraSimulator';
import EventFeed from '../components/EventFeed';
import RegisterCameraForm from '../components/RegisterCameraForm';
import ArchitectureDiagram, { Step } from '../components/ArchitectureDiagram';
import type { Camera, MotionEvent } from '../types';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const navigate = useNavigate();
  const user = getUser();

  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selected, setSelected] = useState<Camera | null>(null);
  const [activeStep, setActiveStep] = useState<Step | null>(null);
  const [loadingCameras, setLoadingCameras] = useState(true);

  // Events state lives here (lifted from the old CameraDetail component) so
  // both the Simulator (left) and the EventFeed (right) can read/write it.
  const [events, setEvents] = useState<MotionEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [lastIngestStatus, setLastIngestStatus] = useState<string | null>(null);
  const [reusedEventId, setReusedEventId] = useState<string | null>(null);

  const flash = useCallback((step: Step) => {
    setActiveStep(step);
    setTimeout(() => setActiveStep((s) => (s === step ? null : s)), 1200);
  }, []);

  // Stable callbacks (see comment in earlier version): inline arrows would
  // change identity every render and trigger re-fetch storms.
  const onIngestStart = useCallback(() => flash('ingest-event'), [flash]);
  const onReadStart = useCallback(() => flash('read-events'), [flash]);
  const onListAlerts = useCallback(() => flash('list-alerts'), [flash]);
  const onAckAlert = useCallback(() => flash('ack-alert'), [flash]);

  const refreshCameras = useCallback(async () => {
    flash('list-cameras');
    const resp = await api.listCameras();
    setCameras(resp.cameras);
    setLoadingCameras(false);
    return resp.cameras;
  }, [flash]);

  useEffect(() => {
    refreshCameras().catch(() => {
      clearAuth();
      navigate('/login');
    });
  }, [refreshCameras, navigate]);

  // Re-fetch events with a diagram flash (the user-visible "Refresh" button).
  const refreshEvents = useCallback(async () => {
    if (!selected) return;
    onReadStart();
    setLoadingEvents(true);
    try {
      const resp = await api.recentEvents(selected.id);
      setEvents(resp.events);
    } finally {
      setLoadingEvents(false);
    }
  }, [selected, onReadStart]);

  // Reset event state and load on camera change.
  useEffect(() => {
    setLastIngestStatus(null);
    setReusedEventId(null);
    if (!selected) {
      setEvents([]);
      return;
    }
    refreshEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id]);

  function logout() {
    clearAuth();
    navigate('/login');
  }

  async function onCameraCreated(camera: Camera) {
    flash('register-camera');
    const list = await refreshCameras();
    const created = list.find((c) => c.id === camera.id) ?? camera;
    setSelected(created);
  }

  // Click the already-selected camera to deselect — useful when the user
  // wants to clear the simulator panel and just look at the diagram /
  // alerts feed without a camera context.
  const toggleSelected = useCallback((camera: Camera) => {
    setSelected((prev) => (prev?.id === camera.id ? null : camera));
  }, []);

  async function simulateEvent(replay: boolean) {
    if (!selected) return;
    onIngestStart();
    const event_id_client =
      replay && reusedEventId ? reusedEventId : crypto.randomUUID();

    const { status, body } = await api.ingestEvent({
      device_id: selected.device_id,
      // Confidence on [0.6, 1.0] — see CameraSimulator hint for distribution.
      confidence: 0.6 + Math.random() * 0.4,
      event_id_client,
      payload: { source: 'web-simulator', t: new Date().toISOString() },
    });

    if (status === 201 && body.event) {
      setLastIngestStatus(`201 Created — new row id=${body.event.id}`);
      setReusedEventId(event_id_client);
    } else if (status === 200 && body.event) {
      setLastIngestStatus(
        `200 OK — replay returned the same row id=${body.event.id} (idempotent ✓)`,
      );
    } else {
      setLastIngestStatus(`${status} ${body.error ?? 'error'}: ${body.message ?? ''}`);
    }

    // Re-fetch events without firing onReadStart — we want the ingest-event
    // flash to play through, not be overwritten by a read-events flash.
    try {
      const resp = await api.recentEvents(selected.id);
      setEvents(resp.events);
    } catch {
      // Non-fatal: next manual refresh will resync.
    }
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1>py-cam-event-service</h1>
        <div className={styles.userInfo}>
          <span>{user?.email}</span>
          {user?.is_admin && <span className={styles.badge}>admin</span>}
          <button onClick={logout} className={styles.logoutBtn}>
            Logout
          </button>
        </div>
      </header>

      <main className={styles.main}>
        {/* INPUT side: pick a camera, register a new one, fire events. */}
        <section className={styles.colInput}>
          {user?.is_admin && <RegisterCameraForm onCreated={onCameraCreated} />}
          <CameraList
            cameras={cameras}
            selectedId={selected?.id}
            loading={loadingCameras}
            onSelect={toggleSelected}
            onRefresh={refreshCameras}
          />
          {selected ? (
            <CameraSimulator
              camera={selected}
              lastIngestStatus={lastIngestStatus}
              canReplay={!!reusedEventId}
              onSimulate={simulateEvent}
              onClose={() => setSelected(null)}
            />
          ) : (
            <div className={styles.empty}>
              <strong>
                {cameras.length === 0
                  ? 'No cameras yet'
                  : 'Pick a camera to get started'}
              </strong>
              <span>
                {cameras.length === 0
                  ? 'Register one above to begin simulating events.'
                  : 'Click one in the list above, then trigger a motion event and watch the request flow.'}
              </span>
            </div>
          )}
        </section>

        {/* VISUALIZATION: the request flow diagram. */}
        <section className={styles.colDiagram}>
          <ArchitectureDiagram active={activeStep} />
        </section>

        {/* OUTPUT side: what the system produced — events ingested, alerts. */}
        <section className={styles.colOutput}>
          {selected && (
            <EventFeed
              events={events}
              loading={loadingEvents}
              camera={selected}
              onRefresh={refreshEvents}
            />
          )}
          <AlertFeed onListStart={onListAlerts} onAckStart={onAckAlert} />
        </section>
      </main>
    </div>
  );
}
