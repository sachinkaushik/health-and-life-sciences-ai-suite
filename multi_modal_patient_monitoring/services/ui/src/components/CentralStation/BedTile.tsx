// src/components/CentralStation/BedTile.tsx
import React from 'react';
import type { BedInfo } from '../../services/api';
import { toBrowserVideoUrl } from '../../services/api';
import type { BedLive } from '../../redux/slices/bedsSlice';
import SharedVideo from './SharedVideo';

const STALE_MS = 5000;

const Wave: React.FC<{ samples?: number[]; color: string; label: string }> = ({ samples, color, label }) => {
  const w = 300;
  const h = 48;
  let points = '';
  if (samples && samples.length > 1) {
    let min = Infinity;
    let max = -Infinity;
    for (const s of samples) {
      if (s < min) min = s;
      if (s > max) max = s;
    }
    const span = max - min || 1;
    points = samples
      .map((s, i) => `${((i / (samples.length - 1)) * w).toFixed(1)},${(h - 2 - ((s - min) / span) * (h - 4)).toFixed(1)}`)
      .join(' ');
  }
  return (
    <div className="bed-wave">
      <span className="bed-wave-label" style={{ color }}>{label}</span>
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        {points && <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} />}
      </svg>
    </div>
  );
};

const fmt = (v: number | undefined, digits = 0) => (v === undefined ? '--' : v.toFixed(digits));

const BedTile: React.FC<{
  bed: BedInfo;
  live?: BedLive;
  onRemove?: (bedId: string) => void;
  removing?: boolean;
}> = ({ bed, live, onRemove, removing }) => {
  const n = live?.numerics ?? {};
  const waves = live?.waves ?? {};
  const stale = !live || Date.now() - live.lastUpdate > STALE_MS;
  const videoUrl = bed.type === 'multimodal' ? toBrowserVideoUrl(bed.video_url) : null;

  return (
    <div className={`bed-tile${stale ? ' stale' : ''}`}>
      <div className="bed-tile-header">
        <span className={`bed-status-dot${bed.connected ? ' on' : ''}`} title={bed.connected ? 'Connected' : 'Disconnected'} />
        <span className="bed-id">{bed.bed_id}</span>
        <span className="bed-badge">{bed.type === 'multimodal' ? 'Multimodal' : 'Monitor'}</span>
        {bed.ai && <span className="bed-badge ai">AI</span>}
        {bed.primary && <span className="bed-badge primary" title="Feeds the workload view">Primary</span>}
        <span className="bed-spacer" />
        {onRemove && !bed.primary && (
          <button className="bed-remove" onClick={() => onRemove(bed.bed_id)} disabled={removing} title="Remove device">
            ✕
          </button>
        )}
      </div>

      <div className="bed-numerics">
        <div className="bed-num hr"><label>HR</label><b>{fmt(n.HR)}</b><small>/min</small></div>
        <div className="bed-num spo2"><label>SpO₂</label><b>{fmt(n.SpO2)}</b><small>%</small></div>
        <div className="bed-num rr"><label>RR</label><b>{fmt(n.RR)}</b><small>/min</small></div>
        <div className="bed-num bp">
          <label>ABP</label>
          <b>{fmt(n.BP_SYS)}/{fmt(n.BP_DIA)}</b>
          <small>({fmt(n.BP_MAP)}) mmHg</small>
        </div>
        <div className="bed-num temp"><label>Temp</label><b>{fmt(n.TEMP, 1)}</b><small>°C</small></div>
        <div className="bed-num co2"><label>EtCO₂</label><b>{fmt(n.CO2_ET)}</b><small>mmHg</small></div>
      </div>

      <Wave samples={waves.ECG} color="#2e9e44" label="ECG II" />
      {videoUrl ? (
        <div className="bed-video">
          <SharedVideo url={videoUrl} label={`${bed.bed_id} camera`} />
        </div>
      ) : (
        <Wave samples={waves.PLETH} color="#1f8fd6" label="Pleth" />
      )}
      <Wave samples={waves.CO2} color="#c9a400" label="CO₂" />
    </div>
  );
};

export default BedTile;
