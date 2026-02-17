/**
 * Shared canvas drawing helpers for simulation charts.
 * Handles axes, grid, lines, labels, division markers, DPR.
 */

const COLORS = {
  bg: "#0a0e17",
  grid: "#1e293b",
  axis: "#334155",
  text: "#94a3b8",
  textDim: "#64748b",
};

export interface ChartPoint {
  x: number;
  y: number;
}

export interface ChartLine {
  points: ChartPoint[];
  color: string;
  label: string;
  width?: number;
}

export interface ChartConfig {
  title: string;
  xLabel: string;
  yLabel: string;
  yLabelRight?: string;
  lines: ChartLine[];
  linesRight?: ChartLine[];
  divisionTimes?: number[];
  xMax?: number;
  yMin?: number;
  yMax?: number;
  yMinRight?: number;
  yMaxRight?: number;
}

export function setupCanvas(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null {
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);

  // Clear
  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, w, h);

  return ctx;
}

export function drawChart(canvas: HTMLCanvasElement, config: ChartConfig): void {
  const ctx = setupCanvas(canvas);
  if (!ctx) return;

  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  const pad = { top: 30, right: config.linesRight ? 60 : 20, bottom: 40, left: 55 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  if (plotW <= 0 || plotH <= 0) return;

  // Compute ranges
  const allPoints = config.lines.flatMap((l) => l.points);
  const allRightPoints = (config.linesRight ?? []).flatMap((l) => l.points);

  const xMax = config.xMax ?? Math.max(...allPoints.map((p) => p.x), ...allRightPoints.map((p) => p.x), 1);
  const yMin = config.yMin ?? Math.min(...allPoints.map((p) => p.y), 0);
  const yMax = config.yMax ?? Math.max(...allPoints.map((p) => p.y), 1);
  const yRange = yMax - yMin || 1;

  const yMinR = config.yMinRight ?? Math.min(...allRightPoints.map((p) => p.y), 0);
  const yMaxR = config.yMaxRight ?? Math.max(...allRightPoints.map((p) => p.y), 1);
  const yRangeR = yMaxR - yMinR || 1;

  const toX = (v: number) => pad.left + (v / xMax) * plotW;
  const toY = (v: number) => pad.top + plotH - ((v - yMin) / yRange) * plotH;
  const toYR = (v: number) => pad.top + plotH - ((v - yMinR) / yRangeR) * plotH;

  // Grid lines
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (plotH / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
  }

  // Axes
  ctx.strokeStyle = COLORS.axis;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + plotH);
  ctx.lineTo(pad.left + plotW, pad.top + plotH);
  ctx.stroke();

  // Division markers
  if (config.divisionTimes) {
    for (const dt of config.divisionTimes) {
      const x = toX(dt);
      ctx.strokeStyle = "#f8717133";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(x, pad.top);
      ctx.lineTo(x, pad.top + plotH);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  // Draw lines
  const drawLines = (lines: ChartLine[], mapY: (v: number) => number) => {
    for (const line of lines) {
      if (line.points.length < 2) continue;
      ctx.strokeStyle = line.color;
      ctx.lineWidth = line.width ?? 1.5;
      ctx.beginPath();
      const first = line.points[0];
      ctx.moveTo(toX(first.x), mapY(first.y));
      for (let i = 1; i < line.points.length; i++) {
        ctx.lineTo(toX(line.points[i].x), mapY(line.points[i].y));
      }
      ctx.stroke();
    }
  };

  drawLines(config.lines, toY);
  if (config.linesRight) {
    drawLines(config.linesRight, toYR);
  }

  // Title
  ctx.fillStyle = "#e2e8f0";
  ctx.font = "bold 12px Inter, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(config.title, w / 2, 16);

  // X label
  ctx.fillStyle = COLORS.text;
  ctx.font = "10px Inter, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(config.xLabel, pad.left + plotW / 2, h - 5);

  // Y label
  ctx.save();
  ctx.translate(12, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.fillText(config.yLabel, 0, 0);
  ctx.restore();

  // Right Y label
  if (config.yLabelRight) {
    ctx.save();
    ctx.translate(w - 8, pad.top + plotH / 2);
    ctx.rotate(Math.PI / 2);
    ctx.textAlign = "center";
    ctx.fillText(config.yLabelRight, 0, 0);
    ctx.restore();
  }

  // Y tick labels
  ctx.fillStyle = COLORS.textDim;
  ctx.font = "9px JetBrains Mono, monospace";
  ctx.textAlign = "right";
  for (let i = 0; i <= 4; i++) {
    const val = yMin + (yRange / 4) * (4 - i);
    const y = pad.top + (plotH / 4) * i;
    ctx.fillText(formatTickValue(val), pad.left - 4, y + 3);
  }

  // X tick labels
  ctx.textAlign = "center";
  for (let i = 0; i <= 4; i++) {
    const val = (xMax / 4) * i;
    const x = toX(val);
    ctx.fillText(`${((val / 3600)).toFixed(1)}h`, x, pad.top + plotH + 14);
  }

  // Legend
  const allLines = [...config.lines, ...(config.linesRight ?? [])];
  ctx.font = "9px Inter, sans-serif";
  ctx.textAlign = "left";
  let lx = pad.left + 4;
  for (const line of allLines) {
    ctx.fillStyle = line.color;
    ctx.fillRect(lx, pad.top + 4, 12, 3);
    ctx.fillStyle = COLORS.text;
    ctx.fillText(line.label, lx + 16, pad.top + 9);
    lx += ctx.measureText(line.label).width + 28;
  }
}

function formatTickValue(v: number): string {
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`;
  if (Math.abs(v) >= 1) return v.toFixed(1);
  if (Math.abs(v) >= 0.01) return v.toFixed(2);
  return v.toExponential(1);
}
