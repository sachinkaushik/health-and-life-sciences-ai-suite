// src/components/CentralStation/CentralStation.tsx
import React, { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { setBeds, setBedsUnavailable } from '../../redux/slices/bedsSlice';
import { api } from '../../services/api';
import BedTile from './BedTile';
import DevicesPanel from './DevicesPanel';
import type { PendingBed } from './DevicesPanel';
import '../../assets/css/CentralStation.css';

const POLL_MS = 3000;
// Poll faster while waiting for sdc-bridge to discover or drop a room.
const PENDING_POLL_MS = 1000;
const PENDING_TIMEOUT_MS = 30000;

const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

const CentralStation: React.FC = () => {
  const dispatch = useAppDispatch();
  const { list, live, available } = useAppSelector((state) => state.beds);
  const isProcessing = useAppSelector((state) => state.app.isProcessing);
  const [requesting, setRequesting] = useState(false);
  const [adding, setAdding] = useState<PendingBed[]>([]);
  const [removing, setRemoving] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const pending = adding.length > 0 || Object.keys(removing).length > 0;

  const refresh = useCallback(async () => {
    try {
      const res = await api.getBeds();
      dispatch(setBeds(res.beds));
    } catch {
      dispatch(setBedsUnavailable());
    }
  }, [dispatch]);

  useEffect(() => {
    refresh();
    const id = setInterval(() => {
      refresh();
      setTick((t) => t + 1); // re-evaluate stale tiles and pending timeouts
    }, pending ? PENDING_POLL_MS : POLL_MS);
    return () => clearInterval(id);
  }, [refresh, pending]);

  // A pending add is done once the bridge lists the room; a pending removal once it no longer does.
  useEffect(() => {
    const ids = new Set(list.map((b) => b.bed_id));
    setAdding((prev) => (prev.some((p) => ids.has(p.bedId)) ? prev.filter((p) => !ids.has(p.bedId)) : prev));
    setRemoving((prev) => {
      const gone = Object.keys(prev).filter((id) => !ids.has(id));
      if (gone.length === 0) return prev;
      const next = { ...prev };
      gone.forEach((id) => delete next[id]);
      return next;
    });
  }, [list]);

  useEffect(() => {
    const now = Date.now();
    const expired = adding.filter((p) => now - p.since > PENDING_TIMEOUT_MS);
    if (expired.length > 0) {
      setAdding((prev) => prev.filter((p) => now - p.since <= PENDING_TIMEOUT_MS));
      setError(`${expired.map((p) => p.bedId).join(', ')} not discovered yet. Check the sdc-bridge logs.`);
    }
    const stuck = Object.keys(removing).filter((id) => now - removing[id] > PENDING_TIMEOUT_MS);
    if (stuck.length > 0) {
      setRemoving((prev) => {
        const next = { ...prev };
        stuck.forEach((id) => delete next[id]);
        return next;
      });
    }
  }, [tick, adding, removing]);

  const onAdd = async () => {
    setRequesting(true);
    setError(null);
    try {
      const bed = await api.addRoom();
      setAdding((prev) => [...prev, { bedId: bed.bed_id, since: Date.now() }]);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setRequesting(false);
    }
  };

  const onRemove = async (bedId: string) => {
    setError(null);
    setRemoving((prev) => ({ ...prev, [bedId]: Date.now() }));
    try {
      await api.removeDevice(bedId);
    } catch (e) {
      setRemoving((prev) => {
        const next = { ...prev };
        delete next[bedId];
        return next;
      });
      setError(errorText(e));
    }
  };

  if (!available) {
    return (
      <div className="central-station">
        <div className="central-empty">
          The central station needs the SDC device source. Start the application with <code>DEVICE_SOURCE=sdc</code>.
        </div>
      </div>
    );
  }

  return (
    <div className="central-station">
      <DevicesPanel
        count={list.length}
        requesting={requesting}
        adding={adding}
        error={error}
        running={isProcessing}
        onAdd={onAdd}
      />
      {isProcessing ? (
        <div className="bed-grid">
          {list.map((bed) => (
            <BedTile
              key={bed.bed_id}
              bed={bed}
              live={live[bed.bed_id]}
              onRemove={onRemove}
              removing={bed.bed_id in removing}
            />
          ))}
          {adding.map((p) => (
            <div key={p.bedId} className="bed-tile pending">
              <span className="cs-spinner" />
              <b>Adding {p.bedId}</b>
              <small>Waiting for the SDC bridge to discover the new room…</small>
            </div>
          ))}
          {list.length === 0 && adding.length === 0 && (
            <div className="central-empty">Waiting for rooms to be discovered…</div>
          )}
        </div>
      ) : (
        <div className="central-hint">Press Start to stream vitals from the rooms and to add or remove rooms.</div>
      )}
    </div>
  );
};

export default CentralStation;
