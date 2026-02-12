import { create } from 'zustand';

interface WebSocketMessage {
  type: string;
  job_id?: string;
  stage?: string;
  status?: string;
  data?: any;
  message?: string;
  error?: string;
}

interface WebSocketState {
  socket: WebSocket | null;
  connected: boolean;
  messages: WebSocketMessage[];
  reconnectDelay: number;
  connect: (url: string) => void;
  disconnect: () => void;
  subscribe: (jobId: string) => void;
  clearMessages: () => void;
  setReconnectDelay: (delay: number) => void;
}

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  socket: null,
  connected: false,
  messages: [],
  reconnectDelay: 3000,

  setReconnectDelay: (delay: number) => {
    set({ reconnectDelay: delay });
  },

  connect: (url: string) => {
    const { socket } = get();
    if (socket?.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected');
      set({ connected: true, socket: ws });
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      set({ connected: false, socket: null });

      // Reconnect after configurable delay
      const { reconnectDelay } = get();
      setTimeout(() => {
        get().connect(url);
      }, reconnectDelay);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        set((state) => ({
          messages: [...state.messages.slice(-100), message],
        }));
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    set({ socket: ws });
  },

  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.close();
      set({ socket: null, connected: false });
    }
  },

  subscribe: (jobId: string) => {
    const { socket } = get();
    if (socket?.readyState === WebSocket.OPEN) {
      // Send JSON-formatted subscription message
      socket.send(JSON.stringify({
        type: 'subscribe',
        job_id: jobId
      }));
    }
  },

  clearMessages: () => {
    set({ messages: [] });
  },
}));
