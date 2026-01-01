/**
 * WebSocket client for the biosignal dashboard.
 * Handles connection, reconnection, and message routing.
 */

import type {
    ServerMessage,
    ClientMessage,
    SensorDescriptor,
    SampleBatch,
    StateEstimate,
    AudioEvent,
} from './messageTypes';

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WSClientCallbacks {
    onConnectionChange?: (state: ConnectionState) => void;
    onDescriptors?: (descriptors: SensorDescriptor[]) => void;
    onSamples?: (batches: SampleBatch[]) => void;
    onState?: (state: StateEstimate) => void;
    onAudio?: (event: AudioEvent) => void;
    onError?: (message: string) => void;
}

const DEFAULT_URL = 'ws://localhost:8000/ws';
const RECONNECT_DELAY_MS = 2000;
const PING_INTERVAL_MS = 30000;

class WSClient {
    private ws: WebSocket | null = null;
    private url: string = DEFAULT_URL;
    private callbacks: WSClientCallbacks = {};
    private reconnectTimeout: number | null = null;
    private pingInterval: number | null = null;
    private shouldReconnect: boolean = true;
    private _connectionState: ConnectionState = 'disconnected';

    get connectionState(): ConnectionState {
        return this._connectionState;
    }

    private setConnectionState(state: ConnectionState) {
        this._connectionState = state;
        this.callbacks.onConnectionChange?.(state);
    }

    /**
     * Set callbacks for message handling.
     */
    setCallbacks(callbacks: WSClientCallbacks) {
        this.callbacks = { ...this.callbacks, ...callbacks };
    }

    /**
     * Connect to the WebSocket server.
     */
    connect(url: string = DEFAULT_URL) {
        this.url = url;
        this.shouldReconnect = true;
        this.doConnect();
    }

    /**
     * Disconnect from the WebSocket server.
     */
    disconnect() {
        this.shouldReconnect = false;
        this.cleanup();
        this.setConnectionState('disconnected');
    }

    /**
     * Send a message to the server.
     */
    send(message: ClientMessage): boolean {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.warn('Cannot send: WebSocket not connected');
            return false;
        }

        try {
            this.ws.send(JSON.stringify(message));
            return true;
        } catch (err) {
            console.error('Failed to send message:', err);
            return false;
        }
    }

    /**
     * Enable a sensor device.
     */
    enableDevice(deviceId: string) {
        return this.send({ type: 'control', action: 'enable', deviceId });
    }

    /**
     * Disable a sensor device.
     */
    disableDevice(deviceId: string) {
        return this.send({ type: 'control', action: 'disable', deviceId });
    }

    private doConnect() {
        this.cleanup();
        this.setConnectionState('connecting');

        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.setConnectionState('connected');
                this.startPingInterval();
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.cleanup();

                if (this.shouldReconnect) {
                    this.setConnectionState('disconnected');
                    this.scheduleReconnect();
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.setConnectionState('error');
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };
        } catch (err) {
            console.error('Failed to create WebSocket:', err);
            this.setConnectionState('error');
            this.scheduleReconnect();
        }
    }

    private handleMessage(data: string) {
        try {
            const message = JSON.parse(data) as ServerMessage;

            switch (message.type) {
                case 'descriptors':
                    this.callbacks.onDescriptors?.(message.payload);
                    break;

                case 'samples':
                    this.callbacks.onSamples?.(message.payload);
                    break;

                case 'state':
                    this.callbacks.onState?.(message);
                    break;

                case 'audio':
                    this.callbacks.onAudio?.(message.payload);
                    break;

                case 'error':
                    console.error('Server error:', message.message);
                    this.callbacks.onError?.(message.message);
                    break;

                case 'pong':
                    // Ping successful, connection is healthy
                    break;

                default:
                    console.warn('Unknown message type:', (message as { type: string }).type);
            }
        } catch (err) {
            console.error('Failed to parse message:', err);
        }
    }

    private startPingInterval() {
        this.stopPingInterval();
        this.pingInterval = window.setInterval(() => {
            this.send({ type: 'ping' });
        }, PING_INTERVAL_MS);
    }

    private stopPingInterval() {
        if (this.pingInterval !== null) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    private scheduleReconnect() {
        if (this.reconnectTimeout !== null) return;

        console.log(`Reconnecting in ${RECONNECT_DELAY_MS}ms...`);
        this.reconnectTimeout = window.setTimeout(() => {
            this.reconnectTimeout = null;
            if (this.shouldReconnect) {
                this.doConnect();
            }
        }, RECONNECT_DELAY_MS);
    }

    private cleanup() {
        this.stopPingInterval();

        if (this.reconnectTimeout !== null) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }

        if (this.ws) {
            this.ws.onopen = null;
            this.ws.onclose = null;
            this.ws.onerror = null;
            this.ws.onmessage = null;

            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.close();
            }
            this.ws = null;
        }
    }
}

// Singleton instance
export const wsClient = new WSClient();
