"""Shared test fixtures for CellForge tests."""

from __future__ import annotations

import pytest

from openlab.cellforge.core.config import SimulationConfig
from openlab.cellforge.core.knowledge_base import Gene, KnowledgeBase, Metabolite, Reaction
from openlab.cellforge.core.simulation import Simulation


@pytest.fixture
def default_config() -> SimulationConfig:
    """A default simulation configuration."""
    return SimulationConfig()


@pytest.fixture
def m_genitalium_kb() -> KnowledgeBase:
    """A minimal M. genitalium knowledge base stub."""
    return KnowledgeBase(
        organism="Mycoplasma genitalium",
        genome_length=580076,
        gc_content=0.315,
        genes=[
            Gene(id="MG_001", name="dnaN", locus_tag="MG_001", start=1, end=1500, strand=1),
            Gene(id="MG_002", name="dnaA", locus_tag="MG_002", start=1501, end=3000, strand=1),
        ],
        metabolites=[
            Metabolite(id="atp_c", name="ATP", compartment="cytoplasm"),
            Metabolite(id="adp_c", name="ADP", compartment="cytoplasm"),
            Metabolite(id="glc_D_e", name="D-Glucose", compartment="extracellular"),
        ],
        reactions=[
            Reaction(
                id="PFK",
                name="Phosphofructokinase",
                reactants={"atp_c": 1.0, "f6p_c": 1.0},
                products={"adp_c": 1.0, "fdp_c": 1.0},
            ),
        ],
    )


@pytest.fixture
def m_genitalium_sim(default_config: SimulationConfig, m_genitalium_kb: KnowledgeBase) -> Simulation:
    """A minimal M. genitalium simulation stub."""
    return Simulation.from_knowledge_base(m_genitalium_kb, default_config)
