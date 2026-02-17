"""Simulation configuration (PRD §4.3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProcessConfig(BaseModel):
    """Configuration for an individual biological process."""

    enabled: bool = True
    dt: float | None = None
    algorithm: str | None = None
    parameters: dict[str, float] = Field(default_factory=dict)


class SimulationConfig(BaseModel):
    """Top-level simulation configuration matching PRD §4.3."""

    # Organism
    organism_name: str = "unknown"
    genome_fasta: str | None = None
    knowledge_base_path: str | None = None

    # Time
    total_time: float = 3600.0
    dt: float = 1.0
    output_interval: float = 10.0

    # Solver settings
    ssa_algorithm: str = "gillespie"
    ode_solver: str = "rk45"
    fba_solver: str = "glpk"
    fba_objective: str = "maximize_growth"

    # Stochastic
    seed: int = 42
    num_realizations: int = 1

    # Process toggles
    processes: dict[str, ProcessConfig] = Field(default_factory=dict)

    # Environment
    temperature: float = 310.15  # K (37°C)
    ph: float = 7.4
    media: dict[str, float] = Field(default_factory=dict)

    # Resource limits
    max_workers: int = 4
    gpu_enabled: bool = False

    # Output
    output_dir: str = "output"
    checkpoint_interval: float = 300.0
    storage_backend: str = "zarr"

    # Logging
    log_level: str = "INFO"
    progress_bar: bool = True
