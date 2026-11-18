// src/components/CentralStation/DevicesPanel.tsx
import React from 'react';
import type { DeviceKind } from '../../services/api';

export type PendingBed = { bedId: string; type: DeviceKind; since: number };

const LABELS: Record<DeviceKind, string> = { monitor: 'Patient monitor', multimodal: 'Multimodal monitor' };

const DevicesPanel: React.FC<{
  count: number;
  requesting: DeviceKind | null;
  adding: PendingBed[];
  error: string | null;
  running: boolean;
  onAdd: (type: DeviceKind) => void;
}> = ({ count, requesting, adding, error, running, onAdd }) => (
  <div className="devices-panel">
    <span className="devices-count">{count} bed{count === 1 ? '' : 's'}</span>
    {(['monitor', 'multimodal'] as const).map((type) => (
      <button
        key={type}
        className="start-button"
        disabled={!running || requesting !== null}
        title={running ? undefined : 'Press Start to add or remove beds'}
        onClick={() => onAdd(type)}
      >
        {requesting === type ? <><span className="cs-spinner" /> Adding…</> : `+ ${LABELS[type]}`}
      </button>
    ))}
    {adding.map((p) => (
      <span key={p.bedId} className="devices-pending" title="Waiting for the SDC bridge to discover the new device">
        <span className="cs-spinner" /> Adding {p.bedId} ({LABELS[p.type]})…
      </span>
    ))}
    {error && <span className="devices-error">{error}</span>}
  </div>
);

export default DevicesPanel;
