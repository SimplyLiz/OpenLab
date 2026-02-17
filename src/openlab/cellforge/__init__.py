"""CellForge: Genome-agnostic whole-cell simulation engine."""

from openlab.cellforge.core.config import SimulationConfig
from openlab.cellforge.core.knowledge_base import KnowledgeBase
from openlab.cellforge.core.process import CellForgeProcess
from openlab.cellforge.core.simulation import Simulation

__all__ = [
    "CellForgeProcess",
    "KnowledgeBase",
    "Simulation",
    "SimulationConfig",
]

try:
    from openlab.cellforge._engine import __version__ as _engine_version
except ImportError:
    _engine_version = None
