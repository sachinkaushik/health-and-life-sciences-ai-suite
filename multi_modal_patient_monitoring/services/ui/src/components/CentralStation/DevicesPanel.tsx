// src/components/CentralStation/DevicesPanel.tsx
import React from 'react';
import type { DeviceKind } from '../../services/api';

const DevicesPanel: React.FC<{
  count: number;
  busy: boolean;
  error: string | null;
  onAdd: (type: DeviceKind) => void;
}> = ({ count, busy, error, onAdd }) => (
  <div className="devices-panel">
    <span className="devices-count">{count} bed{count === 1 ? '' : 's'}</span>
    <button className="start-button" disabled={busy} onClick={() => onAdd('monitor')}>
      + Patient monitor
    </button>
    <button className="start-button" disabled={busy} onClick={() => onAdd('multimodal')}>
      + Multimodal monitor
    </button>
    {error && <span className="devices-error">{error}</span>}
  </div>
);

export default DevicesPanel;
