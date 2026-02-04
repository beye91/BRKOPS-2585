import { create } from 'zustand';

export interface Operation {
  id: string;
  use_case_name: string;
  input_text: string;
  input_audio_url?: string;
  current_stage: string;
  status: string;
  stages: Record<string, StageData>;
  result?: any;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface StageData {
  status: string;
  data?: any;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

interface OperationsState {
  currentOperation: Operation | null;
  recentOperations: Operation[];
  isLoading: boolean;
  error: string | null;

  setCurrentOperation: (operation: Operation | null) => void;
  updateStage: (stage: string, data: StageData) => void;
  addOperation: (operation: Operation) => void;
  updateOperation: (id: string, updates: Partial<Operation>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useOperationsStore = create<OperationsState>((set, get) => ({
  currentOperation: null,
  recentOperations: [],
  isLoading: false,
  error: null,

  setCurrentOperation: (operation) => {
    set({ currentOperation: operation });
    if (operation) {
      // Add to recent operations
      set((state) => ({
        recentOperations: [
          operation,
          ...state.recentOperations.filter((op) => op.id !== operation.id),
        ].slice(0, 10),
      }));
    }
  },

  updateStage: (stage, data) => {
    set((state) => {
      if (!state.currentOperation) return state;

      return {
        currentOperation: {
          ...state.currentOperation,
          current_stage: stage,
          stages: {
            ...state.currentOperation.stages,
            [stage]: data,
          },
        },
      };
    });
  },

  addOperation: (operation) => {
    set((state) => ({
      recentOperations: [
        operation,
        ...state.recentOperations.filter((op) => op.id !== operation.id),
      ].slice(0, 10),
    }));
  },

  updateOperation: (id, updates) => {
    set((state) => ({
      currentOperation:
        state.currentOperation?.id === id
          ? { ...state.currentOperation, ...updates }
          : state.currentOperation,
      recentOperations: state.recentOperations.map((op) =>
        op.id === id ? { ...op, ...updates } : op
      ),
    }));
  },

  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
}));
