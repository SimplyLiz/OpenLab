"""Simulation orchestrator (PRD §4.2)."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

from openlab.cellforge.core.config import SimulationConfig
from openlab.cellforge.core.knowledge_base import KnowledgeBase
from openlab.cellforge.core.process import CellForgeProcess

logger = logging.getLogger(__name__)

# Standard amino acids (single-letter codes)
_AMINO_ACIDS = [
    "ala", "arg", "asn", "asp", "cys", "gln", "glu", "gly",
    "his", "ile", "leu", "lys", "met", "phe", "pro", "ser",
    "thr", "trp", "tyr", "val",
]

# Demo genes for when no knowledge base is provided
_DEMO_GENES = [
    ("dnaA", "Chromosomal replication initiator"),
    ("rpoB", "RNA polymerase beta subunit"),
    ("rpsA", "30S ribosomal protein S1"),
    ("gyrA", "DNA gyrase subunit A"),
    ("ftsZ", "Cell division protein"),
    ("pgi", "Glucose-6-phosphate isomerase"),
    ("pfkA", "6-phosphofructokinase"),
    ("gapA", "Glyceraldehyde-3-phosphate dehydrogenase"),
    ("eno", "Enolase"),
    ("pykF", "Pyruvate kinase"),
    ("aceE", "Pyruvate dehydrogenase"),
    ("gltA", "Citrate synthase"),
    ("icd", "Isocitrate dehydrogenase"),
    ("sucA", "2-oxoglutarate dehydrogenase"),
    ("sdhA", "Succinate dehydrogenase"),
    ("atpA", "ATP synthase subunit alpha"),
]


class Simulation:
    """Top-level simulation interface (PRD §4.2).

    Manages the knowledge base, registered processes, state, and
    time-stepping loop.
    """

    def __init__(
        self,
        config: SimulationConfig,
        knowledge_base: KnowledgeBase | None = None,
    ) -> None:
        self.config = config
        self.knowledge_base = knowledge_base
        self._processes: dict[str, CellForgeProcess] = {}
        self._state: dict[str, Any] = {}
        self._time: float = 0.0
        self._initialized: bool = False
        self._running: bool = False
        self._history: list[dict[str, Any]] = []
        self._step_count: int = 0
        self._callbacks: list = []

    @classmethod
    def from_fasta(cls, fasta_path: str | Path, config: SimulationConfig | None = None) -> Simulation:
        """Create a simulation from a genome FASTA file."""
        path = Path(fasta_path)
        if not path.exists():
            raise FileNotFoundError(f"FASTA file not found: {path}")

        # Read FASTA and create minimal KB
        sequence = ""
        organism = path.stem
        with open(path) as f:
            for line in f:
                if not line.startswith(">"):
                    sequence += line.strip()

        kb = KnowledgeBase(
            organism=organism,
            genome_length=len(sequence),
            gc_content=_gc_content(sequence) if sequence else 0.0,
        )

        if config is None:
            config = SimulationConfig(organism_name=organism)
        return cls(config=config, knowledge_base=kb)

    @classmethod
    def from_knowledge_base(
        cls,
        kb: KnowledgeBase,
        config: SimulationConfig | None = None,
    ) -> Simulation:
        """Create a simulation from an existing knowledge base."""
        if config is None:
            config = SimulationConfig(organism_name=kb.organism)
        return cls(config=config, knowledge_base=kb)

    def register_process(self, process: CellForgeProcess) -> None:
        """Register a biological process with the simulation."""
        self._processes[process.name] = process

    def on_step(self, callback: Any) -> None:
        """Register a callback invoked after each step with (time, state)."""
        self._callbacks.append(callback)

    def initialize(self) -> None:
        """Initialize all processes and set up the initial state."""
        random.seed(self.config.seed)

        # Register default processes if none registered
        if not self._processes:
            self._register_default_processes()

        # Build initial state
        self._state = self._build_initial_state()
        self._time = 0.0
        self._state["time"] = 0.0
        self._history = []
        self._step_count = 0

        # Let each process initialize
        for proc in self._processes.values():
            proc_config = self.config.processes.get(proc.name)
            if proc_config and not proc_config.enabled:
                continue
            proc.initialize(self._state)

        self._initialized = True
        self._running = False
        logger.info("Simulation initialized with %d processes", len(self._processes))

    def step(self, dt: float | None = None) -> dict[str, Any]:
        """Advance the simulation by one time step."""
        if not self._initialized:
            self.initialize()

        dt = dt or self.config.dt
        all_updates: list[dict[str, Any]] = []

        # Run each enabled process
        for proc_name, proc in self._processes.items():
            proc_config = self.config.processes.get(proc_name)
            if proc_config and not proc_config.enabled:
                continue
            try:
                updates = proc.step(self._state, dt)
                all_updates.append(updates)
            except Exception:
                logger.exception("Process %s failed at t=%.1f", proc_name, self._time)

        # Merge all updates into state
        self._apply_updates(all_updates)

        # Advance time
        self._time += dt
        self._state["time"] = self._time
        self._step_count += 1

        # Handle division
        if self._state.get("division_event"):
            self._handle_division()

        # Record history at output intervals
        if self._step_count % max(1, int(self.config.output_interval / dt)) == 0:
            self._record_snapshot()

        # Fire callbacks
        for cb in self._callbacks:
            try:
                cb(self._time, self._state)
            except Exception:
                logger.exception("Callback failed")

        return dict(self._state)

    def run(self) -> dict[str, Any]:
        """Run the simulation for the configured total_time."""
        if not self._initialized:
            self.initialize()

        self._running = True
        dt = self.config.dt
        steps = int(self.config.total_time / dt)

        logger.info(
            "Starting simulation: %.0fs, dt=%.2fs, %d steps",
            self.config.total_time, dt, steps,
        )

        for i in range(steps):
            if not self._running:
                logger.info("Simulation stopped at step %d (t=%.1f)", i, self._time)
                break
            self.step(dt)

        self._running = False
        logger.info("Simulation complete at t=%.1f", self._time)
        return dict(self._state)

    def stop(self) -> None:
        """Stop a running simulation."""
        self._running = False

    def inject_perturbation(
        self,
        perturbation_type: str,
        target: str,
        value: Any,
    ) -> None:
        """Inject a perturbation into the running simulation."""
        if not self._initialized:
            raise RuntimeError("Simulation not initialized")

        if perturbation_type == "knockout":
            # Set gene state to 0 (inactive)
            if target in self._state.get("gene_states", {}):
                self._state["gene_states"][target] = 0
                self._state["promoter_activities"][target] = 0.0
                logger.info("Gene knockout: %s", target)

        elif perturbation_type == "overexpress":
            # Increase mRNA count
            factor = float(value) if value else 10.0
            if target in self._state.get("mrna_counts", {}):
                self._state["mrna_counts"][target] = int(
                    self._state["mrna_counts"][target] * factor
                )
                logger.info("Overexpression: %s x%.1f", target, factor)

        elif perturbation_type == "media_shift":
            # Change external metabolite concentration
            self._state["external_metabolites"][target] = float(value)
            logger.info("Media shift: %s = %.2f mM", target, float(value))

        elif perturbation_type == "temperature":
            # This would affect rate constants; simplified here
            self.config.temperature = float(value)
            logger.info("Temperature shift: %.1f K", float(value))

        elif perturbation_type == "metabolite":
            self._state["metabolite_concentrations"][target] = float(value)
            logger.info("Metabolite set: %s = %.2f mM", target, float(value))

        else:
            raise ValueError(f"Unknown perturbation type: {perturbation_type}")

    def get_state(self) -> dict[str, Any]:
        """Return the current simulation state."""
        return dict(self._state)

    def get_history(self) -> list[dict[str, Any]]:
        """Return recorded state history."""
        return list(self._history)

    def save_checkpoint(self, path: str | Path) -> None:
        """Save a simulation checkpoint to disk."""
        checkpoint = {
            "config": self.config.model_dump(),
            "state": _serialize_state(self._state),
            "time": self._time,
            "step_count": self._step_count,
            "history": self._history,
        }
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(checkpoint, f, indent=2, default=str)
        logger.info("Checkpoint saved to %s", out)

    @classmethod
    def from_checkpoint(cls, path: str | Path) -> Simulation:
        """Restore a simulation from a checkpoint."""
        with open(path) as f:
            data = json.load(f)

        config = SimulationConfig(**data["config"])
        sim = cls(config=config)
        sim._state = data["state"]
        sim._time = data["time"]
        sim._step_count = data["step_count"]
        sim._history = data.get("history", [])
        sim._initialized = True
        sim._register_default_processes()
        return sim

    # --- Private methods ---

    def _register_default_processes(self) -> None:
        """Register all 9 biological processes with default params."""
        from openlab.cellforge.processes.metabolism import Metabolism
        from openlab.cellforge.processes.transcription import Transcription
        from openlab.cellforge.processes.translation import Translation
        from openlab.cellforge.processes.degradation import Degradation
        from openlab.cellforge.processes.replication import Replication
        from openlab.cellforge.processes.division import Division
        from openlab.cellforge.processes.regulation import Regulation
        from openlab.cellforge.processes.maintenance import Maintenance
        from openlab.cellforge.processes.transport import Transport

        kb = self.knowledge_base
        genome_len = kb.genome_length if kb else 4_600_000

        defaults = [
            Metabolism(knowledge_base=kb),
            Transcription(),
            Translation(),
            Degradation(),
            Replication(genome_length=genome_len),
            Division(),
            Regulation(knowledge_base=kb),
            Maintenance(),
            Transport(),
        ]

        for proc in defaults:
            if proc.name not in self._processes:
                self._processes[proc.name] = proc

    def _build_initial_state(self) -> dict[str, Any]:
        """Build initial state from knowledge base."""
        kb = self.knowledge_base

        state: dict[str, Any] = {
            "time": 0.0,

            # Metabolite pools
            "metabolite_concentrations": {
                "glucose": 10.0, "atp": 5.0, "adp": 1.0, "amp": 0.5,
                "nadh": 2.0, "nad": 5.0, "nadph": 1.5, "nadp": 2.5,
                "pyruvate": 0.5, "acetyl_coa": 0.3, "oxaloacetate": 0.2,
                "succinate": 0.3, "fumarate": 0.1, "malate": 0.2,
                "glutamate": 2.0, "glutamine": 1.0, "aspartate": 1.0,
            },
            "external_metabolites": dict(self.config.media) if self.config.media else {
                "glucose": 20.0, "amino_acids": 10.0, "oxygen": 8.0,
            },

            # Gene expression
            "gene_states": {},
            "promoter_activities": {},
            "mrna_counts": {},
            "protein_counts": {},

            # Machinery
            "rnap_count": 2000,
            "ribosome_count": 15000,
            "enzyme_concentrations": {},
            "tf_concentrations": {},
            "transporter_counts": {"glucose": 200, "amino_acids": 100, "oxygen": 500},

            # Nucleotide pools (mM)
            "ntp_concentrations": {"atp": 5.0, "gtp": 2.0, "ctp": 1.0, "utp": 1.0},
            "aa_concentrations": {aa: 1.0 for aa in _AMINO_ACIDS},
            "dntp_concentrations": {"datp": 0.5, "dgtp": 0.5, "dctp": 0.5, "dttp": 0.5},

            # Replication
            "replisome_state": 0.0,
            "replication_progress": 0.0,
            "chromosome_count": 1,

            # Cell properties
            "cell_mass": 1000.0,  # femtograms
            "growth_rate": 0.0,

            # Outputs
            "flux_distribution": {},
            "metabolite_flux": {},
            "division_event": False,
            "daughter_state": None,
        }

        # Populate from KB
        if kb:
            genes = kb.genes if kb.genes else [
                type("G", (), {"id": name, "name": name, "product": prod})()
                for name, prod in _DEMO_GENES
            ]
            for gene in genes:
                state["gene_states"][gene.id] = 1
                state["promoter_activities"][gene.id] = 1.0
                state["mrna_counts"][gene.id] = random.randint(5, 20)
                state["protein_counts"][gene.id] = random.randint(50, 200)

            for met in kb.metabolites:
                state["metabolite_concentrations"][met.id] = met.concentration or 1.0
                if met.compartment == "extracellular":
                    state["external_metabolites"][met.id] = met.concentration or 10.0

            for protein in kb.proteins:
                if protein.is_enzyme:
                    state["enzyme_concentrations"][protein.id] = 1.0
        else:
            # Demo mode: use built-in gene set
            for name, _ in _DEMO_GENES:
                state["gene_states"][name] = 1
                state["promoter_activities"][name] = 1.0
                state["mrna_counts"][name] = random.randint(5, 20)
                state["protein_counts"][name] = random.randint(50, 200)

        return state

    def _apply_updates(self, all_updates: list[dict[str, Any]]) -> None:
        """Merge process outputs into simulation state."""
        met_deltas: dict[str, float] = {}
        mrna_deltas: dict[str, int] = {}
        protein_deltas: dict[str, int] = {}
        ntp_deltas: dict[str, float] = {}
        aa_deltas: dict[str, float] = {}
        dntp_deltas: dict[str, float] = {}

        for updates in all_updates:
            # --- Accumulate deltas ---
            for k, v in updates.get("metabolite_updates", {}).items():
                met_deltas[k] = met_deltas.get(k, 0.0) + v

            for k, v in updates.get("mrna_counts", {}).items():
                mrna_deltas[k] = mrna_deltas.get(k, 0) + v

            for k, v in updates.get("mrna_updates", {}).items():
                mrna_deltas[k] = mrna_deltas.get(k, 0) + v

            for k, v in updates.get("protein_counts", {}).items():
                protein_deltas[k] = protein_deltas.get(k, 0) + v

            for k, v in updates.get("protein_updates", {}).items():
                protein_deltas[k] = protein_deltas.get(k, 0) + v

            for k, v in updates.get("ntp_updates", {}).items():
                ntp_deltas[k] = ntp_deltas.get(k, 0.0) + v

            for k, v in updates.get("aa_updates", {}).items():
                aa_deltas[k] = aa_deltas.get(k, 0.0) + v

            for k, v in updates.get("dntp_updates", {}).items():
                dntp_deltas[k] = dntp_deltas.get(k, 0.0) + v

            # ATP consumption (from maintenance)
            if "atp_consumption" in updates:
                met_deltas["atp"] = met_deltas.get("atp", 0.0) - updates["atp_consumption"]

            # --- Direct replacements ---
            for key in ("growth_rate", "cell_mass", "division_event", "daughter_state",
                        "replication_progress", "replisome_state", "chromosome_count"):
                if key in updates:
                    self._state[key] = updates[key]

            for key in ("flux_distribution", "gene_states", "promoter_activities", "metabolite_flux"):
                if key in updates:
                    self._state[key] = updates[key]

        # Apply accumulated deltas (clamped to non-negative)
        for k, v in met_deltas.items():
            cur = self._state["metabolite_concentrations"].get(k, 0.0)
            self._state["metabolite_concentrations"][k] = max(0.0, cur + v)

        for k, v in mrna_deltas.items():
            cur = self._state["mrna_counts"].get(k, 0)
            self._state["mrna_counts"][k] = max(0, cur + v)

        for k, v in protein_deltas.items():
            cur = self._state["protein_counts"].get(k, 0)
            self._state["protein_counts"][k] = max(0, cur + v)

        for k, v in ntp_deltas.items():
            cur = self._state["ntp_concentrations"].get(k, 0.0)
            self._state["ntp_concentrations"][k] = max(0.0, cur + v)

        for k, v in aa_deltas.items():
            cur = self._state["aa_concentrations"].get(k, 0.0)
            self._state["aa_concentrations"][k] = max(0.0, cur + v)

        for k, v in dntp_deltas.items():
            cur = self._state["dntp_concentrations"].get(k, 0.0)
            self._state["dntp_concentrations"][k] = max(0.0, cur + v)

        # Keep NTP pool in sync with metabolite concentrations for ATP
        if "atp" in self._state["metabolite_concentrations"]:
            self._state["ntp_concentrations"]["atp"] = self._state["metabolite_concentrations"]["atp"]

    def _handle_division(self) -> None:
        """Handle cell division event."""
        logger.info("Cell division at t=%.1f!", self._time)

        # Halve all mRNA and protein counts
        for gene_id in self._state["mrna_counts"]:
            self._state["mrna_counts"][gene_id] = max(
                1, self._state["mrna_counts"][gene_id] // 2
            )
        for gene_id in self._state["protein_counts"]:
            self._state["protein_counts"][gene_id] = max(
                1, self._state["protein_counts"][gene_id] // 2
            )

        # Halve machinery
        self._state["rnap_count"] = max(100, self._state["rnap_count"] // 2)
        self._state["ribosome_count"] = max(1000, self._state["ribosome_count"] // 2)

        # Reset division flag
        self._state["division_event"] = False

    def _record_snapshot(self) -> None:
        """Record a state snapshot for history."""
        snapshot = {
            "time": self._time,
            "growth_rate": self._state.get("growth_rate", 0.0),
            "cell_mass": self._state.get("cell_mass", 0.0),
            "replication_progress": self._state.get("replication_progress", 0.0),
            "metabolite_concentrations": dict(self._state.get("metabolite_concentrations", {})),
            "mrna_counts": dict(self._state.get("mrna_counts", {})),
            "protein_counts": dict(self._state.get("protein_counts", {})),
            "flux_distribution": dict(self._state.get("flux_distribution", {})),
        }
        self._history.append(snapshot)


def _gc_content(sequence: str) -> float:
    """Calculate GC content of a DNA sequence."""
    if not sequence:
        return 0.0
    gc = sum(1 for c in sequence.upper() if c in "GC")
    return gc / len(sequence)


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Make state JSON-serializable."""
    result = {}
    for k, v in state.items():
        if isinstance(v, dict):
            result[k] = {str(kk): vv for kk, vv in v.items()}
        else:
            result[k] = v
    return result
