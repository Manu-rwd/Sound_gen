/**
 * Connection status indicator.
 */

import { useSensorsStore } from '../../state/sensorsStore';
import './ConnectionStatus.css';

export function ConnectionStatus() {
    const connectionState = useSensorsStore((state) => state.connectionState);

    const getStatusInfo = () => {
        switch (connectionState) {
            case 'connected':
                return { label: 'Connected', className: 'connected' };
            case 'connecting':
                return { label: 'Connecting...', className: 'connecting' };
            case 'disconnected':
                return { label: 'Disconnected', className: 'disconnected' };
            case 'error':
                return { label: 'Error', className: 'error' };
            default:
                return { label: 'Unknown', className: '' };
        }
    };

    const { label, className } = getStatusInfo();

    return (
        <div className={`connection-status ${className}`}>
            <span className="status-dot" />
            <span className="status-label">{label}</span>
        </div>
    );
}
