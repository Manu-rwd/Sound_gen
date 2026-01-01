/**
 * GSR Chart component using uPlot.
 */

import { useEffect, useRef, useCallback } from 'react';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import { signalBuffers } from '../../state/signalBuffers';

interface GSRChartProps {
    deviceId: string;
    title?: string;
    height?: number;
}

export function GSRChart({ deviceId, title = 'GSR', height = 150 }: GSRChartProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const plotRef = useRef<uPlot | null>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        const opts: uPlot.Options = {
            width: containerRef.current.clientWidth,
            height,
            title,
            cursor: {
                show: true,
                drag: { x: false, y: false },
            },
            scales: {
                x: { time: false },
                y: { auto: true },
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
                    label: 'µS',
                    labelFont: '10px system-ui',
                },
            ],
            series: [
                { label: 'Time' },
                {
                    label: 'GSR',
                    stroke: '#f97316',  // Orange
                    fill: 'rgba(249, 115, 22, 0.1)',
                    width: 2,
                },
            ],
        };

        const initialData: uPlot.AlignedData = [
            new Float64Array(0),
            new Float64Array(0),
        ];

        plotRef.current = new uPlot(opts, initialData, containerRef.current);

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

    const updateChart = useCallback(() => {
        if (!plotRef.current) return;

        const buffer = signalBuffers.getBuffer(deviceId);
        if (!buffer || buffer.timestamps.length === 0) return;

        const data: uPlot.AlignedData = [
            new Float64Array(buffer.timestamps),
            new Float64Array(buffer.data[0] ?? []),
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
