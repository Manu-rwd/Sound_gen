/**
 * EEG Chart component using uPlot.
 */

import { useEffect, useRef, useCallback } from 'react';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import { signalBuffers } from '../../state/signalBuffers';

interface EEGChartProps {
    deviceId: string;
    title?: string;
    height?: number;
}

// Color palette for EEG channels
const CHANNEL_COLORS = [
    '#22c55e', // green
    '#3b82f6', // blue
    '#f59e0b', // amber
    '#ef4444', // red
];

export function EEGChart({ deviceId, title = 'EEG', height = 200 }: EEGChartProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const plotRef = useRef<uPlot | null>(null);

    // Initialize uPlot
    useEffect(() => {
        if (!containerRef.current) return;

        const buffer = signalBuffers.getBuffer(deviceId);
        const channelCount = buffer?.channels.length ?? 4;
        const channelLabels = buffer?.channels ?? ['TP9', 'AF7', 'AF8', 'TP10'];

        const series: uPlot.Series[] = [
            { label: 'Time' },
            ...channelLabels.map((label, i) => ({
                label,
                stroke: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
                width: 1.5,
            })),
        ];

        const opts: uPlot.Options = {
            width: containerRef.current.clientWidth,
            height,
            title,
            cursor: {
                show: true,
                drag: { x: false, y: false },
            },
            scales: {
                x: {
                    time: false,
                },
                y: {
                    auto: true,
                },
            },
            axes: [
                {
                    stroke: '#888',
                    grid: { stroke: '#333', width: 1 },
                    ticks: { stroke: '#555' },
                    font: '10px system-ui',
                },
                {
                    stroke: '#888',
                    grid: { stroke: '#333', width: 1 },
                    ticks: { stroke: '#555' },
                    font: '10px system-ui',
                    label: 'µV',
                    labelFont: '10px system-ui',
                },
            ],
            series,
        };

        // Initialize with empty data
        const initialData: uPlot.AlignedData = [
            new Float64Array(0),
            ...Array(channelCount).fill(null).map(() => new Float64Array(0)),
        ];

        plotRef.current = new uPlot(opts, initialData, containerRef.current);

        // Handle resize
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                if (plotRef.current && entry.contentRect.width > 0) {
                    plotRef.current.setSize({
                        width: entry.contentRect.width,
                        height: entry.contentRect.height || height,
                    });
                }
            }
        });
        resizeObserver.observe(containerRef.current);

        return () => {
            resizeObserver.disconnect();
            plotRef.current?.destroy();
            plotRef.current = null;
        };
    }, [deviceId, height, title]);

    // Subscribe to buffer updates and refresh chart
    const updateChart = useCallback(() => {
        if (!plotRef.current) return;

        const buffer = signalBuffers.getBuffer(deviceId);
        if (!buffer || buffer.timestamps.length === 0) return;

        // Build uPlot data format: [timestamps, ch1, ch2, ...]
        const data: uPlot.AlignedData = [
            new Float64Array(buffer.timestamps),
            ...buffer.data.map((ch) => new Float64Array(ch)),
        ];

        plotRef.current.setData(data);
    }, [deviceId]);

    useEffect(() => {
        const unsubscribe = signalBuffers.subscribe(deviceId, updateChart);
        return unsubscribe;
    }, [deviceId, updateChart]);

    return (
        <div className="chart-container" style={{ width: '100%', height: '100%' }}>
            <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
        </div>
    );
}
