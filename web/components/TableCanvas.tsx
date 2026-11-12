"use client";

import { useEffect, useRef } from "react";
import { mediaUrl } from "../lib/api";
import type { FogShape, GameMap, Token } from "../lib/types";

interface Camera {
  panX: number;
  panY: number;
  scale: number;
}

interface Props {
  map: GameMap | null;
  tokens: Token[];
  isDM: boolean;
  /** When true (DM only), dragging draws a fog-reveal rectangle instead of panning. */
  fogMode?: boolean;
  tokenImage?: (t: Token) => string | null;
  canMoveToken?: (t: Token) => boolean;
  onTokenMove?: (id: string, x: number, y: number) => void;
  onTokenClick?: (t: Token) => void;
  onFogRect?: (x: number, y: number, w: number, h: number) => void;
}

const DRAG_THRESHOLD = 4;

export default function TableCanvas({
  map,
  tokens,
  isDM,
  fogMode = false,
  tokenImage,
  canMoveToken,
  onTokenMove,
  onTokenClick,
  onFogRect,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const camRef = useRef<Camera>({ panX: 40, panY: 40, scale: 0.6 });
  const mapImgRef = useRef<HTMLImageElement | null>(null);
  const imgCache = useRef<Map<string, HTMLImageElement>>(new Map());
  const tokensRef = useRef<Token[]>(tokens);
  tokensRef.current = tokens;

  // Interaction state (kept in refs to avoid re-renders during drag).
  const drag = useRef<null | {
    mode: "pan" | "token" | "fog";
    startSX: number;
    startSY: number;
    moved: boolean;
    token?: Token;
    grabDX?: number;
    grabDY?: number;
    fogCur?: { x: number; y: number };
  }>(null);

  // --- Image loading --------------------------------------------------------
  useEffect(() => {
    if (!map) {
      mapImgRef.current = null;
      draw();
      return;
    }
    const url = mediaUrl(map.image_path);
    if (!url) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      mapImgRef.current = img;
      draw();
    };
    img.src = url;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map?.id, map?.image_path]);

  function loadToken(url: string): HTMLImageElement {
    const cache = imgCache.current;
    let img = cache.get(url);
    if (!img) {
      img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => draw();
      img.src = url;
      cache.set(url, img);
    }
    return img;
  }

  // --- Coordinate transforms ------------------------------------------------
  const toWorld = (sx: number, sy: number) => {
    const c = camRef.current;
    return { x: (sx - c.panX) / c.scale, y: (sy - c.panY) / c.scale };
  };

  function tokenRadius(t: Token): number {
    const cell = map?.grid_size ?? 70;
    return (Math.max(1, t.size) * cell) / 2;
  }

  function hitToken(sx: number, sy: number): Token | undefined {
    const w = toWorld(sx, sy);
    // Topmost first.
    const sorted = [...tokensRef.current].sort((a, b) => b.z_index - a.z_index);
    return sorted.find((t) => {
      const r = tokenRadius(t);
      return (w.x - t.x) ** 2 + (w.y - t.y) ** 2 <= r * r;
    });
  }

  // --- Drawing --------------------------------------------------------------
  function draw() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const c = camRef.current;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#0c0e14";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.setTransform(c.scale, 0, 0, c.scale, c.panX, c.panY);

    const img = mapImgRef.current;
    const mapW = map?.width || img?.naturalWidth || 0;
    const mapH = map?.height || img?.naturalHeight || 0;
    if (img) ctx.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight);

    // Grid
    if (map && map.grid_type === "square" && map.grid_size > 0 && mapW && mapH) {
      ctx.strokeStyle = map.grid_color || "#000000";
      ctx.globalAlpha = 0.25;
      ctx.lineWidth = 1 / c.scale;
      ctx.beginPath();
      for (let x = map.grid_offset_x; x <= mapW; x += map.grid_size) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, mapH);
      }
      for (let y = map.grid_offset_y; y <= mapH; y += map.grid_size) {
        ctx.moveTo(0, y);
        ctx.lineTo(mapW, y);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Tokens
    for (const t of [...tokensRef.current].sort((a, b) => a.z_index - b.z_index)) {
      const r = tokenRadius(t);
      ctx.save();
      ctx.beginPath();
      ctx.arc(t.x, t.y, r, 0, Math.PI * 2);
      ctx.closePath();
      if (isDM && t.hidden_from_players) ctx.globalAlpha = 0.5;

      const imgPath = tokenImage?.(t) ?? null;
      const imgUrl = imgPath ? mediaUrl(imgPath) : null;
      if (imgUrl) {
        ctx.clip();
        const ti = loadToken(imgUrl);
        if (ti.complete && ti.naturalWidth) {
          ctx.drawImage(ti, t.x - r, t.y - r, r * 2, r * 2);
        } else {
          ctx.fillStyle = t.color;
          ctx.fill();
        }
      } else {
        ctx.fillStyle = t.color;
        ctx.fill();
        if (t.label) {
          ctx.fillStyle = "#fff";
          ctx.font = `${r}px system-ui`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(t.label.slice(0, 2), t.x, t.y);
        }
      }
      ctx.restore();

      // Border
      ctx.beginPath();
      ctx.arc(t.x, t.y, r, 0, Math.PI * 2);
      ctx.lineWidth = 3 / c.scale;
      ctx.strokeStyle = t.border_color || (isDM && t.hidden_from_players ? "#e05050" : "#000000");
      ctx.setLineDash(isDM && t.hidden_from_players ? [8 / c.scale, 6 / c.scale] : []);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Fog (drawn last, in screen space)
    drawFog(ctx, canvas, mapW, mapH);
  }

  function drawFog(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, mapW: number, mapH: number) {
    if (!map || !mapW || !mapH) return;
    const revealed: FogShape[] = map.fog?.revealed ?? [];
    const c = camRef.current;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.save();
    ctx.fillStyle = isDM ? "rgba(10,12,20,0.45)" : "rgba(5,6,10,1)";

    // Cover the map area (screen coords).
    const sx = mapW * 0 * c.scale + c.panX;
    const sy = mapH * 0 * c.scale + c.panY;
    ctx.fillRect(sx, sy, mapW * c.scale, mapH * c.scale);

    // Punch holes for revealed rects.
    ctx.globalCompositeOperation = "destination-out";
    for (const s of revealed) {
      if (s.type !== "rect") continue;
      ctx.fillRect(s.x * c.scale + c.panX, s.y * c.scale + c.panY, s.w * c.scale, s.h * c.scale);
    }
    ctx.restore();

    // In-progress fog rectangle preview.
    const d = drag.current;
    if (d?.mode === "fog" && d.fogCur) {
      const w0 = toWorld(d.startSX, d.startSY);
      const x = Math.min(w0.x, d.fogCur.x);
      const y = Math.min(w0.y, d.fogCur.y);
      const w = Math.abs(d.fogCur.x - w0.x);
      const h = Math.abs(d.fogCur.y - w0.y);
      ctx.save();
      ctx.strokeStyle = "#5fd0ff";
      ctx.lineWidth = 2;
      ctx.strokeRect(x * c.scale + c.panX, y * c.scale + c.panY, w * c.scale, h * c.scale);
      ctx.restore();
    }
  }

  // Redraw when inputs change.
  useEffect(() => {
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokens, map, isDM, fogMode]);

  // Resize to container.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    const resize = () => {
      if (!parent) return;
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
      draw();
    };
    resize();
    const ro = new ResizeObserver(resize);
    if (parent) ro.observe(parent);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Pointer / wheel handlers --------------------------------------------
  const localCoords = (e: React.PointerEvent | React.WheelEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { sx: e.clientX - rect.left, sy: e.clientY - rect.top };
  };

  function onPointerDown(e: React.PointerEvent) {
    canvasRef.current?.setPointerCapture(e.pointerId);
    const { sx, sy } = localCoords(e);
    const hit = hitToken(sx, sy);

    if (fogMode && isDM) {
      drag.current = { mode: "fog", startSX: sx, startSY: sy, moved: false };
    } else if (hit && canMoveToken?.(hit)) {
      const w = toWorld(sx, sy);
      drag.current = { mode: "token", startSX: sx, startSY: sy, moved: false, token: hit, grabDX: w.x - hit.x, grabDY: w.y - hit.y };
    } else if (hit) {
      drag.current = { mode: "token", startSX: sx, startSY: sy, moved: false, token: hit }; // click-only
    } else {
      drag.current = { mode: "pan", startSX: sx, startSY: sy, moved: false };
    }
  }

  function onPointerMove(e: React.PointerEvent) {
    const d = drag.current;
    if (!d) return;
    const { sx, sy } = localCoords(e);
    if (Math.abs(sx - d.startSX) > DRAG_THRESHOLD || Math.abs(sy - d.startSY) > DRAG_THRESHOLD) d.moved = true;

    if (d.mode === "pan") {
      const c = camRef.current;
      c.panX += sx - d.startSX;
      c.panY += sy - d.startSY;
      d.startSX = sx;
      d.startSY = sy;
      draw();
    } else if (d.mode === "token" && d.token && d.grabDX !== undefined && d.moved) {
      const w = toWorld(sx, sy);
      d.token.x = w.x - d.grabDX;
      d.token.y = w.y - (d.grabDY ?? 0);
      draw();
    } else if (d.mode === "fog") {
      d.fogCur = toWorld(sx, sy);
      draw();
    }
  }

  function onPointerUp(e: React.PointerEvent) {
    const d = drag.current;
    drag.current = null;
    if (!d) return;
    const { sx, sy } = localCoords(e);

    if (d.mode === "token" && d.token) {
      if (!d.moved) {
        onTokenClick?.(d.token);
      } else if (d.grabDX !== undefined) {
        onTokenMove?.(d.token.id, d.token.x, d.token.y);
      }
    } else if (d.mode === "fog" && d.moved) {
      const w0 = toWorld(d.startSX, d.startSY);
      const w1 = toWorld(sx, sy);
      onFogRect?.(Math.min(w0.x, w1.x), Math.min(w0.y, w1.y), Math.abs(w1.x - w0.x), Math.abs(w1.y - w0.y));
    }
    draw();
  }

  function onWheel(e: React.WheelEvent) {
    e.preventDefault();
    const { sx, sy } = localCoords(e);
    const c = camRef.current;
    const before = toWorld(sx, sy);
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    c.scale = Math.min(4, Math.max(0.1, c.scale * factor));
    // Keep the point under the cursor fixed.
    c.panX = sx - before.x * c.scale;
    c.panY = sy - before.y * c.scale;
    draw();
  }

  return (
    <canvas
      ref={canvasRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onWheel={onWheel}
      style={{ width: "100%", height: "100%", display: "block", touchAction: "none", cursor: fogMode ? "crosshair" : "grab" }}
    />
  );
}
