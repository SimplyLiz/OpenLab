import { useState, useEffect, useRef } from "react";
import { useGeneStore } from "../../store";

export function PlaybackBar() {
  const simulationSnapshots = useGeneStore((s) => s.simulationSnapshots);
  const simulationProgress = useGeneStore((s) => s.simulationProgress);

  const [playbackIndex, setPlaybackIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(30);
  const timerRef = useRef<number>(0);

  const isComplete = simulationProgress === 1;
  const total = simulationSnapshots.length;

  // Start at last frame when simulation completes
  useEffect(() => {
    if (isComplete && total > 0 && playbackIndex === -1) {
      setPlaybackIndex(total - 1);
    }
  }, [isComplete, total, playbackIndex]);

  // Playback timer
  useEffect(() => {
    if (!isComplete || !isPlaying || total === 0) return;

    timerRef.current = window.setInterval(() => {
      setPlaybackIndex((prev) => {
        const next = prev + 1;
        if (next >= total) {
          setIsPlaying(false);
          return total - 1;
        }
        return next;
      });
    }, 1000 / speed);

    return () => clearInterval(timerRef.current);
  }, [isComplete, isPlaying, speed, total]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === " ") {
        e.preventDefault();
        if (isComplete && total > 0) {
          setIsPlaying((p) => !p);
        }
      }
      if (e.key === "ArrowLeft" && isComplete) {
        e.preventDefault();
        setIsPlaying(false);
        setPlaybackIndex((p) => Math.max(0, p - 1));
      }
      if (e.key === "ArrowRight" && isComplete) {
        e.preventDefault();
        setIsPlaying(false);
        setPlaybackIndex((p) => Math.min(total - 1, p + 1));
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isComplete, total]);

  if (!isComplete || total < 2) return null;

  const currentFrame = playbackIndex >= 0 ? playbackIndex : total - 1;

  return (
    <div className="glass-panel playback-bar">
      <button
        className="playback-btn"
        onClick={() => {
          if (!isPlaying && playbackIndex >= total - 1) {
            setPlaybackIndex(0);
          }
          setIsPlaying(!isPlaying);
        }}
      >
        {isPlaying ? "\u23F8" : "\u25B6"}
      </button>

      <input
        type="range"
        className="playback-slider"
        min={0}
        max={total - 1}
        value={currentFrame}
        onChange={(e) => {
          setIsPlaying(false);
          setPlaybackIndex(Number(e.target.value));
        }}
      />

      <span className="playback-frame">
        {currentFrame + 1} / {total}
      </span>

      <select
        className="playback-speed"
        value={speed}
        onChange={(e) => setSpeed(Number(e.target.value))}
      >
        <option value={10}>10fps</option>
        <option value={30}>30fps</option>
        <option value={60}>60fps</option>
        <option value={120}>120fps</option>
      </select>
    </div>
  );
}
