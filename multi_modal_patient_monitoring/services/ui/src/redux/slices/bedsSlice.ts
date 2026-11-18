// src/redux/slices/bedsSlice.ts
// Live per-bed data for the central station (SDC device source only).
import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { BedInfo } from '../../services/api';
import { stopProcessing } from './appSlice';

export type BedNumerics = {
  HR?: number;
  RR?: number;
  SpO2?: number;
  TEMP?: number;
  CO2_ET?: number;
  BP_SYS?: number;
  BP_DIA?: number;
  BP_MAP?: number;
};

export type BedWaveKind = 'ECG' | 'PLETH' | 'CO2' | 'BP';

export type BedLive = {
  numerics: BedNumerics;
  waves: Partial<Record<BedWaveKind, number[]>>;
  lastUpdate: number;
};

interface BedsState {
  list: BedInfo[];
  live: Record<string, BedLive>;
  available: boolean; // false when the device source is not SDC (no /beds endpoint)
}

const initialState: BedsState = { list: [], live: {}, available: false };

const bedsSlice = createSlice({
  name: 'beds',
  initialState,
  reducers: {
    setBeds: (state, action: PayloadAction<BedInfo[]>) => {
      state.list = action.payload;
      state.available = true;
      const ids = new Set(action.payload.map((b) => b.bed_id));
      for (const id of Object.keys(state.live)) {
        if (!ids.has(id)) delete state.live[id];
      }
    },
    setBedsUnavailable: (state) => {
      state.available = false;
    },
    bedVital: (
      state,
      action: PayloadAction<{ bedId: string; numerics?: BedNumerics; wave?: { kind: BedWaveKind; samples: number[] }; ts: number }>,
    ) => {
      const { bedId, numerics, wave, ts } = action.payload;
      const live = (state.live[bedId] ??= { numerics: {}, waves: {}, lastUpdate: 0 });
      if (numerics) Object.assign(live.numerics, numerics);
      if (wave) live.waves[wave.kind] = wave.samples;
      live.lastUpdate = ts;
    },
    clearBedLive: (state) => {
      state.live = {};
    },
  },
  extraReducers: (builder) => {
    builder.addCase(stopProcessing, (state) => {
      state.live = {};
    });
  },
});

export const { setBeds, setBedsUnavailable, bedVital, clearBedLive } = bedsSlice.actions;
export default bedsSlice.reducer;
