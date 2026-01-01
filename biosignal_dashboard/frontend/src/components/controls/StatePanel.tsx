/**
 * StatePanel - Displays focus/stress/relaxation gauges.
 */

import React, { useState, useEffect } from 'react';
import { useStateStore } from '../../state/stateStore';
import './StatePanel.css';

interface GaugeProps {
    label: string;
    value: number;
    color: string;
}

const Gauge: React.FC<GaugeProps> = ({ label, value, color }) => {
    const percentage = Math.round(value * 100);

    return (
        <div className="gauge">
            <div className="gauge-label">{label}</div>
            <div className="gauge-bar-container">
                <div
                    className="gauge-bar-fill"
                    style={{
                        width: `${percentage}%`,
                        backgroundColor: color,
                    }}
                />
            </div>
            <div className="gauge-value">{percentage}%</div>
        </div>
    );
};

export const StatePanel: React.FC = () => {
    const { scores, label, lastUpdate } = useStateStore();

    // Force re-render every second to update timestamp
    const [, setTick] = useState(0);
    useEffect(() => {
        const interval = setInterval(() => setTick(t => t + 1), 1000);
        return () => clearInterval(interval);
    }, []);

    const timeSinceUpdate = lastUpdate > 0
        ? Math.round((Date.now() - lastUpdate) / 1000)
        : null;

    // Debug: log state updates
    useEffect(() => {
        if (lastUpdate > 0) {
            console.log('[StatePanel] State update:', { scores, label, lastUpdate });
        }
    }, [lastUpdate, scores, label]);

    return (
        <div className="state-panel">
            <div className="state-header">
                <h3>Mental State</h3>
                {timeSinceUpdate !== null ? (
                    <span className="state-updated">
                        Updated {timeSinceUpdate}s ago
                    </span>
                ) : (
                    <span className="state-updated state-waiting">
                        Waiting for data...
                    </span>
                )}
            </div>

            <div className="state-label-container">
                <span className="state-label">{label}</span>
            </div>

            <div className="gauges-container">
                <Gauge
                    label="Focus"
                    value={scores.focus}
                    color="#4CAF50"
                />
                <Gauge
                    label="Stress"
                    value={scores.stress}
                    color="#f44336"
                />
                <Gauge
                    label="Relaxation"
                    value={scores.relaxation}
                    color="#2196F3"
                />
            </div>
        </div>
    );
};
