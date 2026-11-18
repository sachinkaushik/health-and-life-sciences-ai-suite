// src/components/CentralStation/CentralStation.tsx
import React, { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { setBeds, setBedsUnavailable } from '../../redux/slices/bedsSlice';
import { api } from '../../services/api';
import type { DeviceKind } from '../../services/api';
import BedTile from './BedTile';
import DevicesPanel from './DevicesPanel';
import '../../assets/css/CentralStation.css';

const POLL_MS = 3000;

const CentralStation: React.FC = () => {
  const dispatch = useAppDispatch();
  const { list, live, available } = useAppSelector((state) => state.beds);
  const isProcessing = useAppSelector((state) => state.app.isProcessing);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [, setTick] = useState(0);

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
      setTick((t) => t + 1); // re-evaluate stale tiles
    }, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      // The bridge picks up new or removed providers on its next discovery round.
      setTimeout(refresh, 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const onAdd = (type: DeviceKind) => run(() => api.addDevice(type));
  const onRemove = (bedId: string) => run(() => api.removeDevice(bedId));

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
      <DevicesPanel count={list.length} busy={busy} error={error} onAdd={onAdd} />
      {!isProcessing && <div className="central-hint">Press Start to stream vitals from the beds.</div>}
      <div className="bed-grid">
        {list.map((bed) => (
          <BedTile key={bed.bed_id} bed={bed} live={live[bed.bed_id]} onRemove={onRemove} removing={busy} />
        ))}
        {list.length === 0 && <div className="central-empty">Waiting for SDC devices to be discovered…</div>}
      </div>
    </div>
  );
};

export default CentralStation;
