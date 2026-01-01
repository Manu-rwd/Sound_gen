/**
 * Dashboard layout component with draggable/resizable panels using react-grid-layout.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
// @ts-ignore - Handle RGL imports defensively for Vite
import * as RGL from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import { useSensorsStore } from '../../state/sensorsStore';
import { EEGChart } from '../charts/EEGChart';
import { GSRChart } from '../charts/GSRChart';
import { ECGChart } from '../charts/ECGChart';
import './DashboardLayout.css';

// Defensive import for Responsive
// @ts-ignore
const Responsive = RGL.Responsive || RGL.default?.Responsive || RGL.default;

// Explicitly use Responsive grid WITHOUT WidthProvider
// We will measure width manually to ensure it's never undefined/0
const ResponsiveGridLayout = Responsive;

const STORAGE_KEY = 'biosignal_dashboard_layout';

// Specific interface for our layout logic
interface DashboardLayoutItem {
    i: string;
    x: number;
    y: number;
    w: number;
    h: number;
    minW?: number;
    minH?: number;
    static?: boolean;
}

// Default layouts for each sensor type
// User requested all panels to be same size as EEG (full width)
const DEFAULT_LAYOUTS: Record<string, DashboardLayoutItem> = {
    eeg: { i: 'eeg', x: 0, y: 0, w: 12, h: 6, minW: 4, minH: 4 },
    gsr: { i: 'gsr', x: 0, y: 6, w: 12, h: 6, minW: 3, minH: 3 },
    ecg: { i: 'ecg', x: 0, y: 12, w: 12, h: 6, minW: 3, minH: 3 },
};

interface DashboardLayoutProps {
    rowHeight?: number;
    cols?: { lg: number; md: number; sm: number; xs: number; xxs: number };
}

export function DashboardLayout({
    rowHeight = 40,
    cols = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }
}: DashboardLayoutProps) {
    const sensors = useSensorsStore((state) => state.sensors);
    const containerRef = useRef<HTMLDivElement>(null);
    const [width, setWidth] = useState(1200); // Default back to non-zero to ensure render
    const [mounted, setMounted] = useState(false);

    // Measure container width robustly
    useEffect(() => {
        setMounted(true);
        if (!containerRef.current) return;

        // Immediate measurement to snap to correct size ASAP
        if (containerRef.current.offsetWidth > 0) {
            setWidth(containerRef.current.offsetWidth);
        }

        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                if (entry.contentRect.width > 0) {
                    setWidth(entry.contentRect.width);
                }
            }
        });

        resizeObserver.observe(containerRef.current);

        return () => resizeObserver.disconnect();
    }, []);

    // Find enabled sensors
    const eegSensor = sensors?.find((s) => s.kind === 'EEG' && s.enabled);
    const gsrSensor = sensors?.find((s) => s.kind === 'GSR' && s.enabled);
    const ecgSensor = sensors?.find((s) => s.kind === 'ECG' && s.enabled);

    // Load saved layouts from localStorage
    // Use 'any' for return type to avoid RGL type import headaches
    const loadLayouts = useCallback((): any => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                // Handle legacy array format migration
                if (Array.isArray(parsed)) {
                    return { lg: parsed, md: parsed, sm: parsed, xs: parsed, xxs: parsed };
                }
                return parsed;
            }
        } catch (e) {
            console.warn('Failed to load layout:', e);
        }
        return {};
    }, []);

    const [savedLayouts, setSavedLayouts] = useState<any>(loadLayouts());

    // Build layouts for all breakpoints
    const buildLayouts = useCallback((): any => {
        // Helper to get fresh default or saved if valid for a specific breakpoint
        const getLayoutForBreakPoint = (bp: string, kind: string, defaultL: DashboardLayoutItem) => {
            const bpLayouts = savedLayouts[bp];
            const saved = Array.isArray(bpLayouts) ? bpLayouts.find((l: any) => l.i === kind) : undefined;
            return saved || { ...defaultL };
        };

        const generateLayout = (bp: string) => {
            const layout: DashboardLayoutItem[] = [];
            if (eegSensor) layout.push(getLayoutForBreakPoint(bp, 'eeg', DEFAULT_LAYOUTS.eeg));
            if (gsrSensor) layout.push(getLayoutForBreakPoint(bp, 'gsr', DEFAULT_LAYOUTS.gsr));
            if (ecgSensor) layout.push(getLayoutForBreakPoint(bp, 'ecg', DEFAULT_LAYOUTS.ecg));
            return layout;
        };

        return {
            lg: generateLayout('lg'),
            md: generateLayout('md'),
            sm: generateLayout('sm'),
            xs: generateLayout('xs'),
            xxs: generateLayout('xxs'),
        };
    }, [eegSensor, ecgSensor, gsrSensor, savedLayouts]);

    const [layouts, setLayouts] = useState<any>(buildLayouts());

    // Update layouts when sensors change
    useEffect(() => {
        setLayouts(buildLayouts());
    }, [buildLayouts]);

    // Handle layout changes
    const handleLayoutChange = useCallback((currentLayout: any[], allLayouts: any) => {
        // Guard against RGL firing initial 'garbage' layout (all 1x1 at 0,0)
        // This often happens if width is 0 or uninitialized during first render pass
        const isGarbage = currentLayout.some((i: any) => i.w === 1 && i.h === 1 && i.x === 0);
        if (isGarbage && currentLayout.length > 0) {
            return;
        }

        setLayouts(allLayouts);
        setSavedLayouts(allLayouts);

        // Persist to localStorage
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(allLayouts));
        } catch (e) {
            console.warn('Failed to save layout:', e);
        }
    }, []);

    // Calculate chart heights from grid units (using LG layout as reference or fallback)
    const getChartHeight = (itemId: string): number => {
        // We can look at the first available layout or specifically 'lg'
        const item = layouts.lg?.find((l: any) => l.i === itemId) ||
            layouts.md?.find((l: any) => l.i === itemId) ||
            (Object.values(layouts)[0] as any[])?.find((l: any) => l.i === itemId);

        if (!item) return 200;
        return (item.h * rowHeight) - 50;
    };

    const hasEnabledSensors = eegSensor || gsrSensor || ecgSensor;

    const resetLayout = () => {
        localStorage.removeItem(STORAGE_KEY);
        // Force reload to clear state cleanly
        window.location.reload();
    };

    const handlePanelReset = (itemId: string) => {
        const defaultItem = DEFAULT_LAYOUTS[itemId];
        if (!defaultItem) return;

        // Reset this item across ALL breakpoints to the default full size
        const newLayouts = { ...layouts };

        Object.keys(newLayouts).forEach(bp => {
            if (Array.isArray(newLayouts[bp])) {
                newLayouts[bp] = newLayouts[bp].map((item: any) => {
                    if (item.i === itemId) {
                        return { ...item, w: defaultItem.w, h: defaultItem.h, x: defaultItem.x };
                    }
                    return item;
                });
            }
        });

        setLayouts(newLayouts);
        handleLayoutChange([], newLayouts);
    };

    if (!hasEnabledSensors) {
        return (
            <div className="empty-state">
                <p>Enable a device to start streaming</p>
            </div>
        );
    }

    // Don't render grid until we have a real width and are mounted
    // preventing the 1x1 collapse issue
    const isReady = mounted && width > 0;

    if (!ResponsiveGridLayout) {
        return <div>Error loading Grid Layout</div>;
    }

    return (
        <div
            ref={containerRef}
            style={{ width: '100%', height: '100%', position: 'relative' }}
        >
            {isReady && (
                <ResponsiveGridLayout
                    className="dashboard-grid"
                    layouts={layouts}
                    breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                    cols={cols}
                    rowHeight={rowHeight}
                    width={width} // CRITICAL: Explicitly pass width
                    style={{ width: '100%' }}
                    onLayoutChange={handleLayoutChange}
                    draggableHandle=".panel-drag-handle"
                    isResizable={true}
                    resizeHandles={['se', 'e', 's', 'w', 'sw', 'nw', 'ne', 'n']}
                    isDraggable={true}
                    margin={[16, 16]}
                    containerPadding={[0, 0]}
                    compactType="vertical"
                    preventCollision={false}
                >
                    {eegSensor && (
                        <div key="eeg" className="grid-panel">
                            <div className="panel-header">
                                <span className="panel-drag-handle">⋮⋮</span>
                                <span
                                    className="panel-title"
                                    onDoubleClick={() => handlePanelReset('eeg')}
                                    title="Double-click to reset size"
                                    style={{ cursor: 'pointer' }}
                                >
                                    {eegSensor.name}
                                </span>
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
                                <span
                                    className="panel-title"
                                    onDoubleClick={() => handlePanelReset('ecg')}
                                    title="Double-click to reset size"
                                    style={{ cursor: 'pointer' }}
                                >
                                    {ecgSensor.name}
                                </span>
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
                                <span
                                    className="panel-title"
                                    onDoubleClick={() => handlePanelReset('gsr')}
                                    title="Double-click to reset size"
                                    style={{ cursor: 'pointer' }}
                                >
                                    {gsrSensor.name}
                                </span>
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
                </ResponsiveGridLayout>
            )}
        </div>
    );
}
