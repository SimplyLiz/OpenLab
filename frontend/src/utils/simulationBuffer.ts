/**
 * Mutable ring buffer for streaming simulation snapshots.
 * Lives outside React to prevent re-render storms during streaming.
 * Charts read from this via requestAnimationFrame.
 */
import type { SimulationSnapshot } from "../types";

class SimulationBuffer {
  private _data: SimulationSnapshot[] = [];
  private _version = 0;

  get version(): number {
    return this._version;
  }

  get data(): SimulationSnapshot[] {
    return this._data;
  }

  get length(): number {
    return this._data.length;
  }

  push(snapshot: SimulationSnapshot): void {
    this._data.push(snapshot);
    this._version++;
  }

  clear(): void {
    this._data = [];
    this._version = 0;
  }
}

export const simulationBuffer = new SimulationBuffer();
