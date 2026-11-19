// src/components/CentralStation/DevicesPanel.tsx
import React from 'react';

export type PendingBed = { bedId: string; since: number };

const DevicesPanel: React.FC<{
  count: number;
  requesting: boolean;
  adding: PendingBed[];
  error: string | null;
  running: boolean;
  onAdd: () => void;
}> = ({ count, requesting, adding, error, running, onAdd }) => (
  <div className="devices-panel">
    <span className="devices-count">{count} room{count === 1 ? '' : 's'}</span>
    <button
      className="start-button"
      disabled={!running || requesting}
      title={running ? undefined : 'Press Start to add or remove rooms'}
      onClick={onAdd}
    >
      {requesting ? <><span className="cs-spinner" /> Adding…</> : 'Add patient room'}
    </button>
    {adding.map((p) => (
      <span key={p.bedId} className="devices-pending" title="Waiting for the SDC bridge to discover the new room">
        <span className="cs-spinner" /> Adding {p.bedId}…
      </span>
    ))}
    {error && <span className="devices-error">{error}</span>}
  </div>
);

export default DevicesPanel;
