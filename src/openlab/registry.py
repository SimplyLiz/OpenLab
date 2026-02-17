"""Evidence source registry — plugin interface for contrib modules.

Core BioLab defines the registry. Contrib modules (like dnasyn) call
register_source() to add their evidence producers. The evidence_runner,
persistence layer, and CLI all consume from this registry.

Usage from a contrib module:

    from openlab.registry import register_source
    from openlab.db.models.evidence import EvidenceType

    register_source(
        name="esmfold",
        evidence_type=EvidenceType.STRUCTURE,
        module_path="openlab.contrib.dnasyn.sources.esmfold",
        runner_func="run_esmfold",
        async_func="search_esmfold",
    )
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class SourceRegistration:
    """A registered evidence source."""
    name: str
    evidence_type: Any  # EvidenceType enum value
    module_path: str
    runner_func: str  # sync batch runner: run_xxx(db, genes, http) -> int
    async_func: str | None = None  # async searcher: search_xxx(http, ...) -> dict
    description: str = ""
    group: str = ""  # e.g. "dnasyn", "custom"


# Global registries — populated by contrib modules at import time
_source_registry: dict[str, SourceRegistration] = {}
_evidence_type_map: dict[str, Any] = {}
_convergence_weights: dict[str, float] = {}


def register_source(
    name: str,
    evidence_type: Any,
    module_path: str,
    runner_func: str,
    async_func: str | None = None,
    description: str = "",
    group: str = "",
    convergence_weight: float = 0.5,
) -> None:
    """Register an evidence source. Called by contrib modules."""
    reg = SourceRegistration(
        name=name,
        evidence_type=evidence_type,
        module_path=module_path,
        runner_func=runner_func,
        async_func=async_func,
        description=description,
        group=group,
    )
    _source_registry[name] = reg
    _evidence_type_map[name] = evidence_type
    _convergence_weights[name] = convergence_weight
    logger.debug("Registered evidence source: %s (%s)", name, group)


def get_source(name: str) -> SourceRegistration | None:
    """Look up a registered source by name."""
    return _source_registry.get(name)


def list_registered_sources() -> dict[str, SourceRegistration]:
    """Return all registered sources."""
    return dict(_source_registry)


def get_evidence_type_map() -> dict[str, Any]:
    """Return the current source -> EvidenceType mapping."""
    return dict(_evidence_type_map)


def get_convergence_weights() -> dict[str, float]:
    """Return source -> convergence weight mapping."""
    return dict(_convergence_weights)


def evidence_type_for(name: str) -> Any:
    """Get evidence type for a source. Falls back to COMPUTATIONAL."""
    ev_type = _evidence_type_map.get(name)
    if ev_type is not None:
        return ev_type
    from openlab.db.models.evidence import EvidenceType
    return EvidenceType.COMPUTATIONAL


def load_runner(name: str) -> Callable:
    """Import and return the batch runner function for a source."""
    reg = _source_registry.get(name)
    if not reg:
        raise ValueError(f"Unknown source: {name}. Registered: {sorted(_source_registry)}")
    mod = importlib.import_module(reg.module_path)
    return getattr(mod, reg.runner_func)


def load_async_func(name: str) -> Callable | None:
    """Import and return the async search function for a source (if any)."""
    reg = _source_registry.get(name)
    if not reg or not reg.async_func:
        return None
    mod = importlib.import_module(reg.module_path)
    return getattr(mod, reg.async_func)


def check_source_availability(name: str) -> str:
    """Check if a source's dependencies are importable. Returns status string."""
    reg = _source_registry.get(name)
    if not reg:
        return "not_registered"
    try:
        importlib.import_module(reg.module_path)
        return "available"
    except ImportError:
        return "missing_deps"


# ── Built-in core sources (always present) ────────────────────────

def _register_core_sources():
    """Register the built-in evidence sources that ship with BioLab core."""
    from openlab.db.models.evidence import EvidenceType

    core_sources = {
        "protein_features": (EvidenceType.COMPUTATIONAL, 0.3),
        "cdd": (EvidenceType.STRUCTURE, 1.8),
        "ncbi_blast": (EvidenceType.HOMOLOGY, 2.0),
        "interpro": (EvidenceType.COMPUTATIONAL, 2.0),
        "string": (EvidenceType.COMPUTATIONAL, 1.0),
        "uniprot": (EvidenceType.LITERATURE, 1.8),
        "literature": (EvidenceType.LITERATURE, 0.2),
    }
    for name, (ev_type, weight) in core_sources.items():
        _evidence_type_map[name] = ev_type
        _convergence_weights[name] = weight


try:
    _register_core_sources()
except Exception:
    pass  # DB models not yet available (e.g. during initial import)
