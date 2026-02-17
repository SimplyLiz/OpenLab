import { useRef, useEffect, useCallback, useState } from "react";
import { useGeneStore } from "../store";
import { simulationBuffer } from "../utils/simulationBuffer";
import type { SimulationSnapshot } from "../types";

// ---- Seeded PRNG (mulberry32) ----
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---- Particle type configs ----
interface ParticleConfig {
  field: keyof SimulationSnapshot;
  label: string;
  color: string;
  divisor: number;
  maxDots: number;
}

const PARTICLE_CONFIGS: ParticleConfig[] = [
  { field: "total_protein", label: "Ribosomes", color: "#4fc3f7", divisor: 2000, maxDots: 80 },
  { field: "total_mrna", label: "mRNA", color: "#ef5350", divisor: 2, maxDots: 8 },
  { field: "atp", label: "ATP", color: "#fdd835", divisor: 20, maxDots: 60 },
  { field: "gtp", label: "GTP", color: "#ab47bc", divisor: 5, maxDots: 30 },
  { field: "glucose", label: "Glucose", color: "#66bb6a", divisor: 2, maxDots: 15 },
  { field: "aa_pool", label: "Amino acids", color: "#ff8a65", divisor: 3, maxDots: 20 },
];

// ---- Idle-mode particle (original decorative animation) ----
interface IdleParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  type: "ribosome" | "protein";
  life: number;
}

// ---- Live-mode particle ----
interface LiveParticle {
  x: number;
  y: number;
  jx: number;
  jy: number;
  color: string;
  radius: number;
}

function generateLiveParticles(
  snapshot: SimulationSnapshot,
  rx: number,
  ry: number,
): LiveParticle[] {
  const seed = Math.floor(snapshot.time * 100);
  const rng = mulberry32(seed);
  const particles: LiveParticle[] = [];

  for (const cfg of PARTICLE_CONFIGS) {
    const value = snapshot[cfg.field] as number;
    const count = Math.min(Math.round(value / cfg.divisor), cfg.maxDots);
    const dotRadius = cfg.field === "total_protein" ? 3 : cfg.field === "total_mrna" ? 4 : 2.5;
    for (let i = 0; i < count; i++) {
      const angle = rng() * Math.PI * 2;
      const r = Math.sqrt(rng()) * 0.9;
      particles.push({
        x: r * rx * Math.cos(angle),
        y: r * ry * Math.sin(angle),
        jx: 0,
        jy: 0,
        color: cfg.color,
        radius: dotRadius,
      });
    }
  }
  return particles;
}

export function CellSimulation({ compact = false }: { compact?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const frameRef = useRef(0);

  // Idle mode refs
  const idleParticlesRef = useRef<IdleParticle[]>([]);

  // Live mode refs
  const liveParticlesRef = useRef<LiveParticle[]>([]);
  const lastVersionRef = useRef(-1);
  const lastPlaybackIdxRef = useRef(-1);
  const lastDivCountRef = useRef(0);
  const flashCountdownRef = useRef(0);

  // Playback state (React state for UI, mirrored to refs for rAF)
  const [playbackIndex, setPlaybackIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(30);
  const playbackTimerRef = useRef<number>(0);

  // Refs that mirror React state for the rAF loop to read
  const playbackIndexRef = useRef(-1);
  const simSnapshotsRef = useRef<SimulationSnapshot[]>([]);
  const simProgressRef = useRef(0);

  // Store reads
  const { genome, simulationSnapshots, simulationProgress } = useGeneStore();

  const isComplete = simulationProgress === 1;

  // Keep refs in sync with React state
  playbackIndexRef.current = playbackIndex;
  simSnapshotsRef.current = simulationSnapshots;
  simProgressRef.current = simulationProgress;

  // Playback advance timer
  useEffect(() => {
    if (!isComplete || !isPlaying) return;
    const snapshots = simulationSnapshots;
    if (snapshots.length === 0) return;

    const interval = 1000 / playbackSpeed;
    playbackTimerRef.current = window.setInterval(() => {
      setPlaybackIndex((prev) => {
        const next = prev + 1;
        if (next >= snapshots.length) {
          setIsPlaying(false);
          return snapshots.length - 1;
        }
        return next;
      });
    }, interval);

    return () => clearInterval(playbackTimerRef.current);
  }, [isComplete, isPlaying, playbackSpeed, simulationSnapshots]);

  // Reset playback when new simulation starts
  useEffect(() => {
    if (simulationProgress === 0) {
      setPlaybackIndex(-1);
      setIsPlaying(false);
      lastVersionRef.current = -1;
      lastPlaybackIdxRef.current = -1;
      lastDivCountRef.current = 0;
      flashCountdownRef.current = 0;
      liveParticlesRef.current = [];
    }
  }, [simulationProgress]);

  // ---- Drawing (rAF loop) ----
  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const cx = w / 2;
    const cy = h / 2 - 20;
    const frame = frameRef.current++;
    const t = frame / 60;

    ctx.fillStyle = "#0a0e17";
    ctx.fillRect(0, 0, w, h);

    if (simulationBuffer.length === 0) {
      drawIdleMode(ctx, cx, cy, w, h, t, frame);
    } else {
      drawLiveMode(ctx, cx, cy, w, h, t);
    }

    animRef.current = requestAnimationFrame(animate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [genome]);

  // ---- IDLE MODE (original decorative animation) ----
  function drawIdleMode(
    ctx: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    _w: number,
    h: number,
    t: number,
    frame: number,
  ) {
    const cellRadius = Math.min(cx, cy) - 30;
    const dnaRadius = cellRadius * 0.35;

    // Cell membrane (double circle with wobble)
    ctx.save();
    for (let layer = 0; layer < 2; layer++) {
      const r = cellRadius - layer * 6;
      ctx.beginPath();
      for (let a = 0; a < Math.PI * 2; a += 0.02) {
        const wobble =
          Math.sin(a * 8 + t * 0.5) * 2 + Math.sin(a * 3 - t * 0.3) * 1.5;
        const px = cx + Math.cos(a) * (r + wobble);
        const py = cy + Math.sin(a) * (r + wobble);
        if (a === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.strokeStyle = layer === 0 ? "#a78bfa55" : "#a78bfa33";
      ctx.lineWidth = 3;
      ctx.stroke();
    }
    ctx.restore();

    // DNA circle (being replicated)
    const replicationFork = (t * 0.3) % 1;
    const forkAngle = replicationFork * Math.PI * 2;

    ctx.beginPath();
    ctx.arc(cx, cy, dnaRadius, forkAngle - Math.PI / 2, forkAngle + Math.PI * 1.5 - Math.PI / 2);
    ctx.strokeStyle = "#60a5fa";
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, dnaRadius - 4, -Math.PI / 2, forkAngle - Math.PI / 2);
    ctx.strokeStyle = "#22d3ee";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, dnaRadius + 4, -Math.PI / 2, forkAngle - Math.PI / 2);
    ctx.strokeStyle = "#22d3ee";
    ctx.lineWidth = 2;
    ctx.stroke();

    const forkX = cx + Math.cos(forkAngle - Math.PI / 2) * dnaRadius;
    const forkY = cy + Math.sin(forkAngle - Math.PI / 2) * dnaRadius;
    ctx.beginPath();
    ctx.arc(forkX, forkY, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#fbbf24";
    ctx.fill();

    // Gene activity flashes
    if (genome) {
      const activeGeneIdx = Math.floor(t * 2) % genome.genes.length;
      const activeGene = genome.genes[activeGeneIdx];
      if (activeGene) {
        const geneAngle = (activeGene.start / genome.genome_length) * Math.PI * 2 - Math.PI / 2;
        const gx = cx + Math.cos(geneAngle) * dnaRadius;
        const gy = cy + Math.sin(geneAngle) * dnaRadius;
        const pulse = Math.sin(t * 8) * 0.5 + 0.5;
        ctx.beginPath();
        ctx.arc(gx, gy, 4 + pulse * 6, 0, Math.PI * 2);
        ctx.fillStyle = activeGene.color + "88";
        ctx.fill();

        const mrnaDist = dnaRadius + 15 + ((t * 20) % 40);
        const mx = cx + Math.cos(geneAngle) * mrnaDist;
        const my = cy + Math.sin(geneAngle) * mrnaDist;
        ctx.beginPath();
        ctx.arc(mx, my, 3, 0, Math.PI * 2);
        ctx.fillStyle = "#34d399";
        ctx.fill();
      }
    }

    // Idle particles
    const particles = idleParticlesRef.current;

    if (frame % 30 === 0) {
      const angle = Math.random() * Math.PI * 2;
      const dist = dnaRadius + 30 + Math.random() * (cellRadius - dnaRadius - 60);
      particles.push({
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: 4 + Math.random() * 3,
        color: ["#22d3ee", "#34d399", "#a78bfa", "#fb923c"][Math.floor(Math.random() * 4)],
        type: Math.random() > 0.5 ? "ribosome" : "protein",
        life: 200 + Math.random() * 200,
      });
    }

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.life--;

      const dx = p.x - cx;
      const dy = p.y - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist > cellRadius - 15) {
        const nx = dx / dist;
        const ny = dy / dist;
        p.vx -= nx * 0.3;
        p.vy -= ny * 0.3;
      }

      if (p.life <= 0) {
        particles.splice(i, 1);
        continue;
      }

      const alpha = Math.min(1, p.life / 50);
      ctx.globalAlpha = alpha * 0.7;

      if (p.type === "ribosome") {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
      } else {
        ctx.fillStyle = p.color;
        const s = p.size;
        ctx.beginPath();
        ctx.roundRect(p.x - s, p.y - s / 2, s * 2, s, s / 2);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1.0;

    // Labels
    ctx.fillStyle = "#64748b";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Minimal Synthetic Cell", cx, h - 12);

    if (genome) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px JetBrains Mono, monospace";
      ctx.fillText(`${genome.total_genes} genes active`, cx, h - 28);
    }
  }

  // ---- LIVE MODE (data-driven from simulation) ----
  function drawLiveMode(
    ctx: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    _w: number,
    h: number,
    t: number,
  ) {
    // Read current values from refs (always fresh, no stale closures)
    const pIdx = playbackIndexRef.current;
    const sSnaps = simSnapshotsRef.current;
    const sProgress = simProgressRef.current;

    // Determine which snapshot to show
    let snapshot: SimulationSnapshot | null = null;
    const bufVersion = simulationBuffer.version;
    const bufData = simulationBuffer.data;

    if (sProgress === 1 && pIdx >= 0 && pIdx < sSnaps.length) {
      // Playback mode (complete, slider active)
      snapshot = sSnaps[pIdx];
    } else if (bufData.length > 0) {
      // Streaming mode — latest from buffer
      snapshot = bufData[bufData.length - 1];
    }

    if (!snapshot) return;

    // Decide if we need to regenerate particles
    let needRegen = false;
    if (sProgress === 1 && pIdx >= 0) {
      // In playback: regen only when playback index changed
      if (pIdx !== lastPlaybackIdxRef.current) {
        lastPlaybackIdxRef.current = pIdx;
        needRegen = true;
      }
    } else {
      // Streaming: regen when buffer version changed
      if (bufVersion !== lastVersionRef.current) {
        lastVersionRef.current = bufVersion;
        needRegen = true;
      }
    }

    // Compute cell ellipse from volume
    const baseRadius = Math.min(cx, cy + 20) - 30;
    const scale = Math.pow(snapshot.volume / 0.05, 1 / 3);
    let rx = baseRadius * scale * 0.7;
    let ry = rx / 1.4;
    rx = Math.min(rx, cx - 20);
    ry = Math.min(ry, cy - 10);

    if (needRegen) {
      // Detect division flash
      if (snapshot.division_count > lastDivCountRef.current && lastDivCountRef.current >= 0) {
        flashCountdownRef.current = 15;
      }
      lastDivCountRef.current = snapshot.division_count;

      // Generate deterministic particles
      liveParticlesRef.current = generateLiveParticles(snapshot, rx, ry);
    } else {
      // Apply Brownian jitter
      for (const p of liveParticlesRef.current) {
        p.jx += (Math.random() - 0.5) * 0.6;
        p.jy += (Math.random() - 0.5) * 0.6;
        p.jx *= 0.9;
        p.jy *= 0.9;
      }
    }

    // Flash countdown
    const flashing = flashCountdownRef.current > 0;
    if (flashing) flashCountdownRef.current--;
    const flashAlpha = flashing ? flashCountdownRef.current / 15 : 0;

    // ---- Draw layers back to front ----

    // 1. Membrane glow
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx + 6, ry + 6, 0, 0, Math.PI * 2);
    ctx.strokeStyle = flashing
      ? `rgba(255,255,255,${0.3 * flashAlpha + 0.12})`
      : "rgba(100,255,218,0.12)";
    ctx.lineWidth = 12;
    ctx.stroke();
    ctx.restore();

    // 2. Membrane line with subtle wobble
    ctx.save();
    ctx.beginPath();
    for (let a = 0; a <= Math.PI * 2; a += 0.02) {
      const wobble = Math.sin(a * 6 + t * 0.8) * 1.2 + Math.sin(a * 10 - t * 0.4) * 0.8;
      const px = cx + Math.cos(a) * (rx + wobble);
      const py = cy + Math.sin(a) * (ry + wobble * (ry / rx));
      if (a === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.strokeStyle = flashing
      ? `rgba(255,255,255,${0.6 + 0.4 * flashAlpha})`
      : "rgba(100,255,218,0.6)";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();

    // 3. Chromosome ring (dotted ellipse at 0.3x radius)
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx * 0.3, ry * 0.3, 0, 0, Math.PI * 2);
    ctx.setLineDash([4, 6]);
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    // 4. Particles
    for (const p of liveParticlesRef.current) {
      ctx.beginPath();
      ctx.arc(cx + p.x + p.jx, cy + p.y + p.jy, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = 0.85;
      ctx.fill();
    }
    ctx.globalAlpha = 1.0;

    // ---- Info overlay ----
    const infoY = h - 50;
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "center";

    const timeHours = (snapshot.time / 3600).toFixed(1);
    const volStr = snapshot.volume.toFixed(4);
    const divStr = snapshot.division_count.toString();
    ctx.fillText(
      `t = ${timeHours}h    vol = ${volStr} fL    divisions = ${divStr}`,
      cx,
      infoY,
    );

    // ---- Legend (horizontal, bottom) ----
    const legendY = h - 18;
    const legendStartX = cx - (PARTICLE_CONFIGS.length * 70) / 2;
    ctx.font = "9px Inter, sans-serif";
    ctx.textAlign = "left";

    for (let i = 0; i < PARTICLE_CONFIGS.length; i++) {
      const cfg = PARTICLE_CONFIGS[i];
      const lx = legendStartX + i * 70;

      ctx.beginPath();
      ctx.arc(lx, legendY, 3, 0, Math.PI * 2);
      ctx.fillStyle = cfg.color;
      ctx.fill();

      ctx.fillStyle = "#64748b";
      ctx.fillText(cfg.label, lx + 6, legendY + 3);
    }
  }

  useEffect(() => {
    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [animate]);

  // When simulation completes, start playback at last frame
  useEffect(() => {
    if (isComplete && simulationSnapshots.length > 0 && playbackIndex === -1) {
      setPlaybackIndex(simulationSnapshots.length - 1);
    }
  }, [isComplete, simulationSnapshots.length, playbackIndex]);

  return (
    <div className="cell-sim-wrapper">
      <canvas
        ref={canvasRef}
        className="cell-sim-canvas"
        style={{ width: "100%", height: compact ? "150px" : "400px" }}
      />
      {isComplete && simulationSnapshots.length > 1 && (
        <div className="cell-sim-controls">
          <input
            type="range"
            className="cell-sim-slider"
            min={0}
            max={simulationSnapshots.length - 1}
            value={playbackIndex >= 0 ? playbackIndex : simulationSnapshots.length - 1}
            onChange={(e) => {
              setIsPlaying(false);
              setPlaybackIndex(Number(e.target.value));
            }}
          />
          <div className="cell-sim-controls-row">
            <button
              className="cell-sim-btn"
              onClick={() => {
                if (!isPlaying && playbackIndex >= simulationSnapshots.length - 1) {
                  setPlaybackIndex(0);
                }
                setIsPlaying(!isPlaying);
              }}
            >
              {isPlaying ? "Pause" : "Play"}
            </button>
            <label className="cell-sim-speed">
              Speed
              <select
                value={playbackSpeed}
                onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
              >
                <option value={10}>10 fps</option>
                <option value={30}>30 fps</option>
                <option value={60}>60 fps</option>
                <option value={120}>120 fps</option>
              </select>
            </label>
            <span className="cell-sim-frame-info">
              {playbackIndex >= 0 ? playbackIndex + 1 : simulationSnapshots.length} / {simulationSnapshots.length}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
