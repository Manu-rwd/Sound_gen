/**
 * Zustand store for sensor descriptors and connection state.
 */

import { create } from 'zustand';
import type { SensorDescriptor } from '../api/messageTypes';
import type { ConnectionState } from '../api/wsClient';

interface SensorsState {
    // Connection state
    connectionState: ConnectionState;
    setConnectionState: (state: ConnectionState) => void;

    // Sensor descriptors
    sensors: SensorDescriptor[];
    setSensors: (sensors: SensorDescriptor[]) => void;

    // Helpers
    getSensor: (deviceId: string) => SensorDescriptor | undefined;
    getEnabledSensors: () => SensorDescriptor[];
}

export const useSensorsStore = create<SensorsState>((set, get) => ({
    connectionState: 'disconnected',
    setConnectionState: (connectionState) => set({ connectionState }),

    sensors: [],
    setSensors: (sensors) => set({ sensors }),

    getSensor: (deviceId) => get().sensors.find((s) => s.id === deviceId),

    getEnabledSensors: () => get().sensors.filter((s) => s.enabled),
}));
