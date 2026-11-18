import type { Middleware } from '@reduxjs/toolkit';
import { addEvent } from '../slices/eventsSlice';
import { updateWorkloadData, setAggregatorStatus } from '../slices/servicesSlice';
import { bedVital } from '../slices/bedsSlice';
import type { BedNumerics, BedWaveKind } from '../slices/bedsSlice';

// Device-source metric names (OpenICE / SDC bridge) -> central-station fields.
const BED_NUMERICS: Record<string, keyof BedNumerics> = {
  MDC_ECG_HEART_RATE: 'HR',
  MDC_TTHOR_RESP_RATE: 'RR',
  MDC_PULS_OXIM_SAT_O2: 'SpO2',
  MDC_TEMP_BODY: 'TEMP',
  MDC_AWAY_CO2_ET: 'CO2_ET',
  MDC_PRESS_BLD_ART_ABP_SYS: 'BP_SYS',
  MDC_PRESS_BLD_ART_ABP_DIA: 'BP_DIA',
  MDC_PRESS_BLD_ART_ABP_MEAN: 'BP_MAP',
};
const BED_WAVES: Record<string, BedWaveKind> = {
  MDC_ECG_LEAD_II: 'ECG',
  MDC_PULS_OXIM_PLETH: 'PLETH',
  MDC_AWAY_CO2: 'CO2',
  MDC_PRESS_BLD: 'BP',
};

export const sseMiddleware: Middleware = (store) => {
  let eventSource: EventSource | null = null;
  let poseMessageCount = 0;

  return (next) => (action) => {
    if (typeof action !== 'object' || action === null || !('type' in action)) {
      return next(action);
    }

    // Handle SSE connect
    if (action.type === 'sse/connect') {
      const url = (action as any).payload?.url;
      
      if (!url) {
        return next(action);
      }

      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }

      store.dispatch(setAggregatorStatus('connecting'));

      eventSource = new EventSource(url);

      eventSource.onopen = () => {
        store.dispatch(setAggregatorStatus('connected'));
      };

      eventSource.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          
          const workloadType = rawData.workload_type || rawData.workload;
          const eventType = rawData.event_type || 'data';
          const payload = rawData.payload || rawData;
          const timestamp = rawData.timestamp || Date.now();

          // Parse workload-specific data
          let parsedData: any = {};

          if (workloadType === 'rppg') {
            // rPPG can send both waveform and numeric vitals
            if (eventType === 'numeric') {
              const metric = payload.metric;

              if (metric === 'HEART_RATE_AVG' || metric === 'HEART_RATE') {
                parsedData.HR = payload.value;
              } else if (metric === 'RESP_RATE_AVG' || metric === 'RESP_RATE') {
                parsedData.RR = payload.value;
              } else if (metric === 'SPO2' || metric === 'SPO2_AVG' || metric === 'OXYGEN_SATURATION') {
                parsedData.SpO2 = payload.value;
              }
            } else {
              // Waveform / aggregated payload
              parsedData = {
                HR: payload.HR ?? payload.heart_rate,
                RR: payload.RR ?? payload.respiratory_rate ?? payload.value,
                SpO2: payload.SpO2 ?? payload.spo2,
              };
              
              // Extract waveform if present
              if (payload.waveform && Array.isArray(payload.waveform)) {
                parsedData.waveform = payload.waveform;
              }
            }

          } else if (workloadType === 'ai-ecg') {
            // AI-ECG sends: inference object + waveform
            parsedData.prediction = payload.inference ?? 'Unknown';
            parsedData.filename = payload.file ?? 'Unknown';

            // Waveform
            if (Array.isArray(payload.waveform)) {
              parsedData.waveform = payload.waveform;
            }

            // Waveform frequency (very useful for ECG chart scaling)
            if (payload.waveform_frequency_hz) {
              parsedData.waveformFrequency = payload.waveform_frequency_hz;
            }
            
          } else if (workloadType === 'mdpnp') {
            // MDPNP sends: device_type + metric + value/waveform
            const eventType = rawData.event_type;
            const deviceType = rawData.device_type || payload.device_type;
            
            if (eventType === 'numeric') {
              // Map device metrics to unified vitals
              const metric = payload.metric;
              
              if (metric === 'MDC_ECG_HEART_RATE') {
                parsedData.HR = payload.value;
              } 
              else if (metric === 'MDC_AWAY_CO2_ET') {
                parsedData.CO2_ET = payload.value;
              } 
              else if (metric === 'MDC_PRESS_BLD_ART_ABP_DIA') {
                parsedData.BP_DIA = payload.value;
              }
              else if (metric === 'MDC_PRESS_BLD_ART_ABP_SYS') {
                parsedData.BP_SYS = payload.value;
              }
            } 
            else if (eventType === 'waveform') {
              // Extract waveform based on device type
              if (payload.waveform && Array.isArray(payload.waveform)) {
                // Store waveform with device identifier
                if (payload.metric === 'MDC_ECG_LEAD_II') {
                  parsedData.waveform = payload.waveform;
                  parsedData.waveformType = 'ECG';
                } 
                else if (payload.metric === 'MDC_AWAY_CO2') {
                  parsedData.waveform = payload.waveform;
                  parsedData.waveformType = 'CO2';
                } 
                else if (payload.metric === 'MDC_PRESS_BLD') {
                  parsedData.waveform = payload.waveform;
                  parsedData.waveformType = 'BP';
                }
              }
            }
            
          } else if (workloadType === '3d-pose') {
            poseMessageCount++;
            
            let allPeopleJoints: any[] = [];
            
            if (payload.people && Array.isArray(payload.people) && payload.people.length > 0) {
              // Extract joints from ALL people, not just the first one
              allPeopleJoints = payload.people.map((person: any) => {
                return {
                  person_id: person.person_id,
                  joints_3d: person.joints_3d || [],
                  confidence: person.confidence || [],
                };
              });
            }
            
            parsedData = {
              activity: payload.activity || 'Unknown',
              people: allPeopleJoints,
              num_persons: payload.people?.length || 0,
              frame_number: payload.frame_number || 0,
            };

            // Always include frame data immediately (no throttling)
            if (payload.frame_base64) {
              parsedData.frameData = `data:image/jpeg;base64,${payload.frame_base64}`;
            }
            
          }

          const state: any = store.getState();
          const isProcessing = state.app?.isProcessing;
          if (!isProcessing) {
            return;
          }

          // SDC device source: every bed feeds the central station; only the primary
          // bed also feeds the single-patient MDPNP card below.
          if (workloadType === 'mdpnp' && rawData.bed_id) {
            const metric = payload.metric;
            if (eventType === 'numeric' && metric in BED_NUMERICS) {
              store.dispatch(bedVital({
                bedId: rawData.bed_id,
                numerics: { [BED_NUMERICS[metric]]: payload.value },
                ts: timestamp,
              }));
            } else if (eventType === 'waveform' && metric in BED_WAVES && Array.isArray(payload.waveform)) {
              store.dispatch(bedVital({
                bedId: rawData.bed_id,
                wave: { kind: BED_WAVES[metric], samples: payload.waveform },
                ts: timestamp,
              }));
            }
            if (!rawData.primary) {
              return;
            }
          }

          // Dispatch to Redux
          store.dispatch(updateWorkloadData({
            workloadId: workloadType,
            data: parsedData,
            timestamp: timestamp
          }));

          // Also add to events log
          store.dispatch(addEvent({
            workload: workloadType,
            data: parsedData,
            timestamp: timestamp,
            id: ''
          }));

        } catch (error) {
          // Silent error handling
        }
      };

      eventSource.onerror = (error) => {
        store.dispatch(setAggregatorStatus('error'));
        
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }

        // Auto-reconnect after 5 seconds
        setTimeout(() => {
          const state = store.getState();
          if (state.app?.isProcessing) {
            store.dispatch({ type: 'sse/connect', payload: { url } });
          }
        }, 5000);
      };
    }

    // Handle SSE disconnect
    if (action.type === 'sse/disconnect') {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      
      store.dispatch(setAggregatorStatus('stopped'));
    }

    return next(action);
  };
};