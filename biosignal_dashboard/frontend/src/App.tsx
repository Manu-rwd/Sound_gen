/**
 * Main App component for the biosignal dashboard.
 */

import { useEffect } from 'react';
import { wsClient } from './api/wsClient';
import { useSensorsStore } from './state/sensorsStore';
import { signalBuffers } from './state/signalBuffers';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { DeviceToggles } from './components/controls/DeviceToggles';
import { ConnectionStatus } from './components/controls/ConnectionStatus';
import './App.css';

function App() {
  const setConnectionState = useSensorsStore((state) => state.setConnectionState);
  const setSensors = useSensorsStore((state) => state.setSensors);

  // Initialize WebSocket connection
  useEffect(() => {
    // Set up callbacks
    wsClient.setCallbacks({
      onConnectionChange: (state) => {
        setConnectionState(state);
      },
      onDescriptors: (descriptors) => {
        setSensors(descriptors);
      },
      onSamples: (batches) => {
        // Append samples to buffers
        for (const batch of batches) {
          signalBuffers.appendSamples(batch);
        }
      },
      onError: (message) => {
        console.error('Server error:', message);
      },
    });

    // Connect
    wsClient.connect();

    // Cleanup on unmount
    return () => {
      wsClient.disconnect();
    };
  }, [setConnectionState, setSensors]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Biosignal Dashboard</h1>
        <ConnectionStatus />
      </header>

      <div className="app-content">
        <aside className="sidebar">
          <DeviceToggles />
        </aside>

        <main className="main-area">
          <DashboardLayout />
        </main>
      </div>
    </div>
  );
}

export default App;
