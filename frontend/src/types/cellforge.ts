export interface SimulationConfig {
  organismName: string;
  genomeFasta?: string;
  totalTime: number;
  dt: number;
  seed: number;
  temperature: number;
  ph: number;
}

export interface SimulationStatus {
  simulationId: string;
  status: 'created' | 'running' | 'paused' | 'completed' | 'error';
  time: number;
  totalTime: number;
  progress: number;
}

export interface SimulationState {
  simulationId: string;
  time: number;
  metaboliteConcentrations: Record<string, number>;
  mrnaCounts: Record<string, number>;
  proteinCounts: Record<string, number>;
  fluxDistribution: Record<string, number>;
  growthRate: number;
  cellMass: number;
  replicationProgress: number;
}

export interface Perturbation {
  perturbationType: string;
  target: string;
  value: number | string | boolean;
}

export interface Gene {
  id: string;
  name: string;
  locusTag: string;
  start: number;
  end: number;
  strand: number;
  product: string;
}

export interface Metabolite {
  id: string;
  name: string;
  compartment: string;
  concentration: number;
}

export interface Reaction {
  id: string;
  name: string;
  equation: string;
  flux: number;
  subsystem: string;
}

export interface StreamingDataPoint {
  time: number;
  variable: string;
  value: number;
}

export interface HistorySnapshot {
  time: number;
  metaboliteConcentrations: Record<string, number>;
  mrnaCounts: Record<string, number>;
  proteinCounts: Record<string, number>;
  growthRate: number;
  cellMass: number;
}
