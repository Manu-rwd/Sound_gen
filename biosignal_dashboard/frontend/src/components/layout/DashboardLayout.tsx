/**
 * Dashboard layout component with draggable/resizable panels using react-grid-layout.
 */

import { useState, useCallback, useEffect } from 'react';
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import { useSensorsStore } from '../../state/sensorsStore';
import { EEGChart } from '../charts/EEGChart';
import { GSRChart } from '../charts/GSRChart';
import { ECGChart } from '../charts/ECGChart';
import './DashboardLayout.css';

const STORAGE_KEY = 'biosignal_dashboard_layout';

// Layout item type
interface LayoutItem {
    i: string;
    x: number;
    y: number;
    w: number;
    h: number;
    minW?: number;
    minH?: number;
}

// Default layouts for each sensor type
const DEFAULT_LAYOUTS: Record<string, LayoutItem> = {
    eeg: { i: 'eeg', x: 0, y: 0, w: 12, h: 6, minW: 4, minH: 4 },
    ecg: { i: 'ecg', x: 0, y: 6, w: 6, h: 5, minW: 3, minH: 3 },
    gsr: { i: 'gsr', x: 6, y: 6, w: 6, h: 5, minW: 3, minH: 3 },
};

interface DashboardLayoutProps {
    rowHeight?: number;
    cols?: number;
}

export function DashboardLayout({ rowHeight = 40, cols = 12 }: DashboardLayoutProps) {
    const sensors = useSensorsStore((state) => state.sensors);
    const [containerWidth, setContainerWidth] = useState<number>(800);
    const containerRef = useCallback((node: HTMLDivElement | null) => {
        if (node) {
            setContainerWidth(node.clientWidth);
            const observer = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    setContainerWidth(entry.contentRect.width);
                }
            });
            observer.observe(node);
        }
    }, []);

    // Find enabled sensors
    const eegSensor = sensors.find((s) => s.kind === 'EEG' && s.enabled);
    const gsrSensor = sensors.find((s) => s.kind === 'GSR' && s.enabled);
    const ecgSensor = sensors.find((s) => s.kind === 'ECG' && s.enabled);

    // Load saved layout from localStorage
    const loadLayout = (): LayoutItem[] => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {
            console.warn('Failed to load layout:', e);
        }
        return [];
    };

    const [savedLayouts, setSavedLayouts] = useState<LayoutItem[]>(loadLayout);

    // Build current layout based on enabled sensors
    const buildLayout = useCallback((): LayoutItem[] => {
        const layouts: LayoutItem[] = [];

        if (eegSensor) {
            const saved = savedLayouts.find((l) => l.i === 'eeg');
            layouts.push(saved || DEFAULT_LAYOUTS.eeg);
        }
        if (ecgSensor) {
            const saved = savedLayouts.find((l) => l.i === 'ecg');
            layouts.push(saved || DEFAULT_LAYOUTS.ecg);
        }
        if (gsrSensor) {
            const saved = savedLayouts.find((l) => l.i === 'gsr');
            layouts.push(saved || DEFAULT_LAYOUTS.gsr);
        }

        return layouts;
    }, [eegSensor, ecgSensor, gsrSensor, savedLayouts]);

    const [layout, setLayout] = useState<LayoutItem[]>(buildLayout);

    // Update layout when sensors change
    useEffect(() => {
        setLayout(buildLayout());
    }, [buildLayout]);

    // Handle layout changes
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleLayoutChange = useCallback((newLayout: any[]) => {
        const items = newLayout as LayoutItem[];
        setLayout(items);
        setSavedLayouts(items);

        // Persist to localStorage
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
        } catch (e) {
            console.warn('Failed to save layout:', e);
        }
    }, []);

    // Calculate chart heights from grid units
    const getChartHeight = (itemId: string): number => {
        const item = layout.find((l) => l.i === itemId);
        if (!item) return 200;
        // Account for panel padding and title
        return (item.h * rowHeight) - 50;
    };

    const hasEnabledSensors = eegSensor || gsrSensor || ecgSensor;

    if (!hasEnabledSensors) {
        return (
            <div className="empty-state">
                <p>Enable a device to start streaming</p>
            </div>
        );
    }

    return (
        <div ref={containerRef} style={{ width: '100%' }}>
            <GridLayout
                className="dashboard-grid"
                layout={layout}
                cols={cols}
                rowHeight={rowHeight}
                width={containerWidth}
                onLayoutChange={handleLayoutChange}
                draggableHandle=".panel-drag-handle"
                isResizable={true}
                isDraggable={true}
                compactType="vertical"
                preventCollision={false}
                margin={[16, 16]}
            >
                {eegSensor && (
                    <div key="eeg" className="grid-panel">
                        <div className="panel-header">
                            <span className="panel-drag-handle">⋮⋮</span>
                            <span className="panel-title">{eegSensor.name}</span>
                        </div>
                        <div className="panel-content">
                            <EEGChart
                                deviceId={eegSensor.id}
                                title=""
                                height={getChartHeight('eeg')}
                            />
                        </div>
                    </div>
                )}

                {ecgSensor && (
                    <div key="ecg" className="grid-panel">
                        <div className="panel-header">
                            <span className="panel-drag-handle">⋮⋮</span>
                            <span className="panel-title">{ecgSensor.name}</span>
                        </div>
                        <div className="panel-content">
                            <ECGChart
                                deviceId={ecgSensor.id}
                                title=""
                                height={getChartHeight('ecg')}
                            />
                        </div>
                    </div>
                )}

                {gsrSensor && (
                    <div key="gsr" className="grid-panel">
                        <div className="panel-header">
                            <span className="panel-drag-handle">⋮⋮</span>
                            <span className="panel-title">{gsrSensor.name}</span>
                        </div>
                        <div className="panel-content">
                            <GSRChart
                                deviceId={gsrSensor.id}
                                title=""
                                height={getChartHeight('gsr')}
                            />
                        </div>
                    </div>
                )}
            </GridLayout>
        </div>
    );
}
