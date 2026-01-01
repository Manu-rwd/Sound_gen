/**
 * WebSocket message types for the biosignal dashboard.
 */

// Sensor metadata
export interface ChannelInfo {
    id: string;
    label: string;
    unit?: string;
}

export type SensorKind = 'EEG' | 'ECG' | 'GSR' | 'HR' | 'ACCEL' | 'OTHER';

export interface SensorDescriptor {
    id: string;
    name: string;
    kind: SensorKind;
    channels: ChannelInfo[];
    sampling_rate: number;
    backend: string;
    enabled: boolean;
}

// Sample data
export interface SampleBatch {
    deviceId: string;
    timestamp: number;
    channels: string[];
    samplingRate: number;
    values: number[][];  // [n_samples][n_channels]
}

// Messages from server
export interface DescriptorsMessage {
    type: 'descriptors';
    payload: SensorDescriptor[];
}

export interface SamplesMessage {
    type: 'samples';
    payload: SampleBatch[];
}

export interface StateScores {
    focus: number;
    stress: number;
    relaxation: number;
}

export interface StateEstimate {
    type: 'state';
    timestamp: number;
    scores: StateScores;
    label?: string;
    explanation?: string;
}

export interface AudioEvent {
    timestamp: number;
    event: 'start' | 'stop' | 'tag';
    trackId?: string;
    trackName?: string;
    tags?: string[];
}

export interface AudioMessage {
    type: 'audio';
    payload: AudioEvent;
}

export interface ErrorMessage {
    type: 'error';
    message: string;
    deviceId?: string;
}

export interface PongMessage {
    type: 'pong';
    timestamp: number;
}

export type ServerMessage =
    | DescriptorsMessage
    | SamplesMessage
    | StateEstimate
    | AudioMessage
    | ErrorMessage
    | PongMessage;

// Messages to server
export interface ControlAction {
    type: 'control';
    action: 'enable' | 'disable';
    deviceId: string;
}

export interface AudioEventAction {
    type: 'audio_event';
    event: 'start' | 'stop';
    trackId: string;
    trackName?: string;
    tags?: string[];
}

export interface PingAction {
    type: 'ping';
}

export type ClientMessage = ControlAction | AudioEventAction | PingAction;
