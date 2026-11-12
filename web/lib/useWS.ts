// WebSocket hook for live table sync. Reconnects automatically.
import { useEffect, useRef } from "react";
import { API_URL } from "./api";

export interface WSMessage {
  type: string;
  [k: string]: unknown;
}

function wsBase(): string {
  return API_URL.replace(/^http/, "ws");
}

/** DM channel: ws/dm?campaign_id=..&token=<jwt> */
export function dmSocketUrl(campaignId: string, jwt: string): string {
  return `${wsBase()}/ws/dm?campaign_id=${campaignId}&token=${encodeURIComponent(jwt)}`;
}

/** Player channel: ws/player?share_token=.. */
export function playerSocketUrl(shareToken: string): string {
  return `${wsBase()}/ws/player?share_token=${encodeURIComponent(shareToken)}`;
}

export function useWS(url: string | null, onMessage: (msg: WSMessage) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    if (!url) return;
    let closed = false;
    let retry: ReturnType<typeof setTimeout>;

    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          handlerRef.current(JSON.parse(ev.data));
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        if (!closed) retry = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws.close();
    };
    connect();

    return () => {
      closed = true;
      clearTimeout(retry);
      wsRef.current?.close();
    };
  }, [url]);

  const send = (msg: WSMessage) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
  };

  return { send };
}
