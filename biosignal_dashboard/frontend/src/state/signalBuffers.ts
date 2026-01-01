/**
 * Signal buffers for storing chart data.
 * 
 * Uses plain arrays outside React state to avoid re-render storms.
 * Charts access this directly via refs.
 */

import type { SampleBatch } from '../api/messageTypes';

export interface SignalBuffer {
    deviceId: string;
    timestamps: number[];    // X-axis data (relative time in seconds)
    channels: string[];      // Channel IDs
    data: number[][];       // One array per channel
    sampleRate: number;
    lastUpdate: number;
}

// Window duration for each sensor type (seconds)
const WINDOW_DURATIONS: Record<string, number> = {
    EEG: 10,
    ECG: 10,
    GSR: 60,
    default: 30,
};

class SignalBufferManager {
    private buffers: Map<string, SignalBuffer> = new Map();
    private listeners: Map<string, Set<() => void>> = new Map();

    /**
     * Get or create a buffer for a device.
     */
    getBuffer(deviceId: string): SignalBuffer | undefined {
        return this.buffers.get(deviceId);
    }

    /**
     * Initialize a buffer for a device.
     */
    initBuffer(deviceId: string, channels: string[], sampleRate: number) {
        if (this.buffers.has(deviceId)) return;

        const buffer: SignalBuffer = {
            deviceId,
            timestamps: [],
            channels,
            data: channels.map(() => []),
            sampleRate,
            lastUpdate: 0,
        };

        this.buffers.set(deviceId, buffer);
    }

    /**
     * Append samples to a buffer.
     */
    appendSamples(batch: SampleBatch) {
        let buffer = this.buffers.get(batch.deviceId);

        if (!buffer) {
            // Auto-create buffer
            buffer = {
                deviceId: batch.deviceId,
                timestamps: [],
                channels: batch.channels,
                data: batch.channels.map(() => []),
                sampleRate: batch.samplingRate,
                lastUpdate: 0,
            };
            this.buffers.set(batch.deviceId, buffer);
        }

        const nSamples = batch.values.length;
        if (nSamples === 0) return;

        const dt = 1 / batch.samplingRate;
        const baseTime = buffer.timestamps.length > 0
            ? buffer.timestamps[buffer.timestamps.length - 1] + dt
            : 0;

        // Append new timestamps
        for (let i = 0; i < nSamples; i++) {
            buffer.timestamps.push(baseTime + i * dt);
        }

        // Append new data for each channel
        const nChannels = batch.channels.length;
        for (let ch = 0; ch < nChannels; ch++) {
            for (let i = 0; i < nSamples; i++) {
                const value = batch.values[i]?.[ch] ?? 0;
                buffer.data[ch].push(value);
            }
        }

        // Trim to window duration
        this.trimBuffer(buffer);

        buffer.lastUpdate = Date.now();

        // Notify listeners
        this.notifyListeners(batch.deviceId);
    }

    /**
     * Trim buffer to keep only the most recent window of data.
     */
    private trimBuffer(buffer: SignalBuffer) {
        const windowDuration = WINDOW_DURATIONS[buffer.deviceId.includes('eeg') ? 'EEG' :
            buffer.deviceId.includes('ecg') ? 'ECG' :
                buffer.deviceId.includes('gsr') ? 'GSR' : 'default'];

        const maxSamples = Math.ceil(windowDuration * buffer.sampleRate);

        if (buffer.timestamps.length > maxSamples) {
            const excess = buffer.timestamps.length - maxSamples;
            buffer.timestamps = buffer.timestamps.slice(excess);
            for (let ch = 0; ch < buffer.data.length; ch++) {
                buffer.data[ch] = buffer.data[ch].slice(excess);
            }
        }
    }

    /**
     * Clear all buffers.
     */
    clear() {
        this.buffers.clear();
    }

    /**
     * Clear a specific buffer.
     */
    clearBuffer(deviceId: string) {
        const buffer = this.buffers.get(deviceId);
        if (buffer) {
            buffer.timestamps = [];
            buffer.data = buffer.channels.map(() => []);
            buffer.lastUpdate = Date.now();
            this.notifyListeners(deviceId);
        }
    }

    /**
     * Subscribe to buffer updates for a device.
     */
    subscribe(deviceId: string, callback: () => void): () => void {
        if (!this.listeners.has(deviceId)) {
            this.listeners.set(deviceId, new Set());
        }
        this.listeners.get(deviceId)!.add(callback);

        return () => {
            this.listeners.get(deviceId)?.delete(callback);
        };
    }

    private notifyListeners(deviceId: string) {
        this.listeners.get(deviceId)?.forEach((cb) => cb());
    }
}

// Singleton instance
export const signalBuffers = new SignalBufferManager();
