type WSEventHandler = (type: string, payload: Record<string, unknown>, ts: number) => void;

export type WSStatus = 'disconnected' | 'connecting' | 'connected';

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const PING_INTERVAL_MS = 25000;

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_BASE = `${WS_PROTOCOL}//${window.location.host}/api/ws`;

let ws: WebSocket | null = null;
let statusListeners: Array<(s: WSStatus) => void> = [];
let eventListeners: Array<WSEventHandler> = [];
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let reconnectAttempt = 0;
let intentionalClose = false;

function notifyStatus(s: WSStatus) {
  for (const l of statusListeners) l(s);
}

function notifyEvent(type: string, payload: Record<string, unknown>, ts: number) {
  for (const l of eventListeners) l(type, payload, ts);
}

function scheduleReconnect() {
  if (intentionalClose) return;
  if (reconnectTimer) return;
  const delay = Math.min(RECONNECT_BASE_MS * 2 ** reconnectAttempt, RECONNECT_MAX_MS);
  reconnectAttempt++;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

function startPing() {
  stopPing();
  pingTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, PING_INTERVAL_MS);
}

function stopPing() {
  if (pingTimer) {
    clearInterval(pingTimer);
    pingTimer = null;
  }
}

function getToken(): string | null {
  try {
    return sessionStorage.getItem('rastro-token');
  } catch {
    return null;
  }
}

export function connect(): void {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  intentionalClose = false;
  notifyStatus('connecting');

  const token = getToken();
  const url = token ? `${WS_BASE}?token=${encodeURIComponent(token)}` : WS_BASE;

  try {
    ws = new WebSocket(url);
  } catch {
    notifyStatus('disconnected');
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    reconnectAttempt = 0;
    notifyStatus('connected');
    startPing();
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'pong') return;
      notifyEvent(data.type, data.payload || {}, data.ts || 0);
    } catch {
      // ignore malformed messages
    }
  };

  ws.onclose = () => {
    stopPing();
    ws = null;
    notifyStatus('disconnected');
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws?.close();
  };
}

export function disconnect(): void {
  intentionalClose = true;
  stopPing();
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  reconnectAttempt = 0;
  if (ws) {
    ws.onclose = null;
    ws.onerror = null;
    ws.onmessage = null;
    ws.onopen = null;
    ws.close();
    ws = null;
  }
  notifyStatus('disconnected');
}

export function onStatus(fn: (s: WSStatus) => void): () => void {
  statusListeners.push(fn);
  return () => {
    statusListeners = statusListeners.filter(l => l !== fn);
  };
}

export function onEvent(fn: WSEventHandler): () => void {
  eventListeners.push(fn);
  return () => {
    eventListeners = eventListeners.filter(l => l !== fn);
  };
}

export function subscribe(pattern: string): void {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'subscribe', pattern }));
  }
}

export function getStatus(): WSStatus {
  if (!ws) return 'disconnected';
  if (ws.readyState === WebSocket.CONNECTING) return 'connecting';
  if (ws.readyState === WebSocket.OPEN) return 'connected';
  return 'disconnected';
}
