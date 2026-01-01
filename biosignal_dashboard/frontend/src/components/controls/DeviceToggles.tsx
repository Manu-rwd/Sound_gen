/**
 * Device toggle controls for enabling/disabling sensors.
 */

import { useSensorsStore } from '../../state/sensorsStore';
import { wsClient } from '../../api/wsClient';
import './DeviceToggles.css';

export function DeviceToggles() {
    const sensors = useSensorsStore((state) => state.sensors);

    const handleToggle = (deviceId: string, currentlyEnabled: boolean) => {
        if (currentlyEnabled) {
            wsClient.disableDevice(deviceId);
        } else {
            wsClient.enableDevice(deviceId);
        }
    };

    const getKindIcon = (kind: string) => {
        switch (kind) {
            case 'EEG':
                return '🧠';
            case 'ECG':
                return '❤️';
            case 'GSR':
                return '💧';
            default:
                return '📊';
        }
    };

    return (
        <div className="device-toggles">
            <h3>Devices</h3>
            <div className="toggle-list">
                {sensors.map((sensor) => (
                    <div key={sensor.id} className="toggle-item">
                        <span className="toggle-icon">{getKindIcon(sensor.kind)}</span>
                        <span className="toggle-name">{sensor.name}</span>
                        <button
                            className={`toggle-button ${sensor.enabled ? 'active' : ''}`}
                            onClick={() => handleToggle(sensor.id, sensor.enabled)}
                            title={sensor.enabled ? 'Click to disable' : 'Click to enable'}
                        >
                            {sensor.enabled ? 'ON' : 'OFF'}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
