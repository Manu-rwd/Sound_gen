/**
 * Zustand store for state estimation (focus/stress/relaxation).
 */

import { create } from 'zustand';
import type { StateScores } from '../api/messageTypes';

interface StateStoreState {
    scores: StateScores;
    label: string;
    lastUpdate: number;
    history: { timestamp: number; scores: StateScores }[];

    // Actions
    updateState: (scores: StateScores, label?: string) => void;
    reset: () => void;
}

const DEFAULT_SCORES: StateScores = {
    focus: 0.5,
    stress: 0.5,
    relaxation: 0.5,
};

const MAX_HISTORY = 60; // Keep 60 seconds of history at 1 Hz

export const useStateStore = create<StateStoreState>((set) => ({
    scores: DEFAULT_SCORES,
    label: 'Neutral',
    lastUpdate: 0,
    history: [],

    updateState: (scores, label) => set((state) => {
        const now = Date.now();
        const newHistory = [
            ...state.history,
            { timestamp: now, scores },
        ].slice(-MAX_HISTORY);

        return {
            scores,
            label: label || state.label,
            lastUpdate: now,
            history: newHistory,
        };
    }),

    reset: () => set({
        scores: DEFAULT_SCORES,
        label: 'Neutral',
        lastUpdate: 0,
        history: [],
    }),
}));
