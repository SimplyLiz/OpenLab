import { create } from 'zustand';
import type { SimulationState, HistorySnapshot } from '@/types/cellforge';

// Demo genes
const DEMO_GENES = [
  'dnaA', 'rpoB', 'rpsA', 'gyrA', 'ftsZ', 'pgi', 'pfkA', 'gapA',
  'eno', 'pykF', 'aceE', 'gltA', 'icd', 'sucA', 'sdhA', 'atpA',
];

function initState(): SimulationState {
  const mrna: Record<string, number> = {};
  const protein: Record<string, number> = {};
  for (const g of DEMO_GENES) {
    mrna[g] = 5 + Math.floor(Math.random() * 15);
    protein[g] = 50 + Math.floor(Math.random() * 150);
  }
  return {
    simulationId: 'local',
    time: 0,
    metaboliteConcentrations: {
      glucose: 10, atp: 5, adp: 1, nadh: 2, nad: 5, pyruvate: 0.5,
    },
    mrnaCounts: mrna,
    proteinCounts: protein,
    fluxDistribution: { glucose_uptake: 0, atp_synthase: 0 },
    growthRate: 0,
    cellMass: 1000,
    replicationProgress: 0,
  };
}

/** Simple Michaelis-Menten */
function mm(s: number, vmax: number, km: number): number {
  if (s <= 0) return 0;
  return vmax * s / (km + s);
}

/** Poisson sample (small lambda) */
function poisson(lam: number): number {
  if (lam <= 0) return 0;
  if (lam > 30) return Math.max(0, Math.round(lam + Math.sqrt(lam) * (Math.random() * 2 - 1)));
  let L = Math.exp(-lam), k = 0, p = 1;
  do { k++; p *= Math.random(); } while (p > L);
  return k - 1;
}

/** Advance simulation by dt seconds */
function stepSimulation(s: SimulationState, dt: number): SimulationState {
  const met = { ...s.metaboliteConcentrations };
  const mrna = { ...s.mrnaCounts };
  const protein = { ...s.proteinCounts };

  // --- Metabolism ---
  const glc = met.glucose ?? 0;
  const glcUptake = mm(glc, 10, 0.05);
  const glcConsumed = glcUptake * dt / 3600;
  met.glucose = Math.max(0, glc - glcConsumed);
  const atpProduced = glcConsumed * 18;
  const atpMaint = 0.001 * (s.cellMass / 1000) * dt;
  met.atp = Math.max(0, (met.atp ?? 5) + atpProduced - atpMaint);
  met.adp = Math.max(0, (met.adp ?? 1) - atpProduced + atpMaint);
  met.pyruvate = Math.max(0, (met.pyruvate ?? 0.5) + glcConsumed * 0.2);
  met.nadh = Math.max(0, (met.nadh ?? 2) + glcConsumed * 4);
  met.nad = Math.max(0, (met.nad ?? 5) - glcConsumed * 4);

  const growthRate = mm(met.atp, 0.0005, 1.0);
  const cellMass = s.cellMass + growthRate * s.cellMass * dt;

  // --- Transcription ---
  for (const g of DEMO_GENES) {
    const newMrna = poisson(0.008 * dt);
    mrna[g] = (mrna[g] ?? 10) + newMrna;
  }

  // --- Translation ---
  for (const g of DEMO_GENES) {
    const newProt = poisson(0.004 * (mrna[g] ?? 0) * dt);
    protein[g] = (protein[g] ?? 100) + newProt;
  }

  // --- Degradation ---
  for (const g of DEMO_GENES) {
    const mDeg = poisson((mrna[g] ?? 0) * 0.0023 * dt);
    mrna[g] = Math.max(0, (mrna[g] ?? 0) - mDeg);
    const pDeg = poisson((protein[g] ?? 0) * 0.000019 * dt);
    protein[g] = Math.max(0, (protein[g] ?? 0) - pDeg);
  }

  // --- Replication ---
  let repl = s.replicationProgress;
  if (cellMass > 1800) {
    repl = Math.min(1, repl + dt / 2300);
  }

  // --- Division ---
  if (repl >= 1.0 && cellMass > 1800) {
    // halve everything
    for (const g of DEMO_GENES) {
      mrna[g] = Math.max(1, Math.floor((mrna[g] ?? 0) / 2));
      protein[g] = Math.max(1, Math.floor((protein[g] ?? 0) / 2));
    }
    return {
      ...s,
      time: s.time + dt,
      metaboliteConcentrations: met,
      mrnaCounts: mrna,
      proteinCounts: protein,
      fluxDistribution: { glucose_uptake: glcUptake, atp_synthase: atpProduced / dt * 3600 },
      growthRate,
      cellMass: cellMass / 2,
      replicationProgress: 0,
    };
  }

  // --- Transport (replenish glucose from media) ---
  met.glucose = Math.max(0, met.glucose + mm(20, 0.01, 0.1) * dt);

  return {
    ...s,
    time: s.time + dt,
    metaboliteConcentrations: met,
    mrnaCounts: mrna,
    proteinCounts: protein,
    fluxDistribution: { glucose_uptake: glcUptake, atp_synthase: atpProduced / dt * 3600 },
    growthRate,
    cellMass,
    replicationProgress: repl,
  };
}

interface CellForgeStore {
  state: SimulationState;
  history: HistorySnapshot[];
  isRunning: boolean;
  speed: number;
  knockedOut: Set<string>;

  play: () => void;
  pause: () => void;
  stepOnce: () => void;
  reset: () => void;
  setSpeed: (s: number) => void;
  knockout: (geneId: string) => void;
  restoreGene: (geneId: string) => void;
  setMediaGlucose: (value: number) => void;
  setState: (state: SimulationState) => void;
}

let _interval: ReturnType<typeof setInterval> | null = null;

export const useCellForgeStore = create<CellForgeStore>((set, get) => ({
  state: initState(),
  history: [],
  isRunning: false,
  speed: 1,
  knockedOut: new Set<string>(),

  play: () => {
    if (_interval) clearInterval(_interval);
    set({ isRunning: true });
    _interval = setInterval(() => {
      const { state: s, history, speed, knockedOut } = get();
      const dt = speed;
      let next = stepSimulation(s, dt);
      // Apply knockouts
      for (const g of knockedOut) {
        next.mrnaCounts[g] = 0;
      }
      const snap: HistorySnapshot = {
        time: next.time,
        metaboliteConcentrations: { ...next.metaboliteConcentrations },
        mrnaCounts: { ...next.mrnaCounts },
        proteinCounts: { ...next.proteinCounts },
        growthRate: next.growthRate,
        cellMass: next.cellMass,
      };
      set({ state: next, history: [...history.slice(-200), snap] });
    }, 100);
  },

  pause: () => {
    if (_interval) { clearInterval(_interval); _interval = null; }
    set({ isRunning: false });
  },

  stepOnce: () => {
    const { state: s, history, speed, knockedOut } = get();
    let next = stepSimulation(s, speed);
    for (const g of knockedOut) { next.mrnaCounts[g] = 0; }
    const snap: HistorySnapshot = {
      time: next.time,
      metaboliteConcentrations: { ...next.metaboliteConcentrations },
      mrnaCounts: { ...next.mrnaCounts },
      proteinCounts: { ...next.proteinCounts },
      growthRate: next.growthRate,
      cellMass: next.cellMass,
    };
    set({ state: next, history: [...history.slice(-200), snap] });
  },

  reset: () => {
    if (_interval) { clearInterval(_interval); _interval = null; }
    set({ state: initState(), history: [], isRunning: false, knockedOut: new Set() });
  },

  setSpeed: (s: number) => set({ speed: s }),

  knockout: (geneId: string) => {
    const ko = new Set(get().knockedOut);
    ko.add(geneId);
    const s = { ...get().state };
    s.mrnaCounts = { ...s.mrnaCounts, [geneId]: 0 };
    set({ knockedOut: ko, state: s });
  },

  restoreGene: (geneId: string) => {
    const ko = new Set(get().knockedOut);
    ko.delete(geneId);
    set({ knockedOut: ko });
  },

  setMediaGlucose: (value: number) => {
    const s = { ...get().state };
    s.metaboliteConcentrations = { ...s.metaboliteConcentrations, glucose: value };
    set({ state: s });
  },

  setState: (state: SimulationState) => set({ state }),
}));
