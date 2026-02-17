"""Thermodynamic data — eQuilibrator with heuristic fallback, from DNAView."""

import asyncio
import logging

from openlab.models import Provenance, ProvenancedValue, TrustLevel

logger = logging.getLogger(__name__)


def _init_equilibrator(ph: float = 7.5, ionic_strength: float = 0.25, temperature: float = 310.15):
    """Try to initialize eQuilibrator. Returns None if not available."""
    try:
        from equilibrator_api import ComponentContribution, Q_
        eq = ComponentContribution()
        eq.p_h = Q_(ph)
        eq.ionic_strength = Q_(f"{ionic_strength} M")
        eq.temperature = Q_(f"{temperature} K")
        return eq
    except ImportError:
        logger.info("equilibrator-api not installed; using heuristic estimates")
        return None
    except Exception as e:
        logger.warning(f"eQuilibrator init failed: {e}")
        return None


# Rough dG estimates by subsystem type (kJ/mol)
_SUBSYSTEM_DG = {
    "glycolysis": -20.0,
    "pentose_phosphate": -5.0,
    "nucleotide": -15.0,
    "amino_acid": -10.0,
    "lipid": -25.0,
    "atp_synthase": -30.0,
    "transport": -5.0,
}


def estimate_dg_heuristic(subsystem: str = "") -> ProvenancedValue:
    """Estimate dG from reaction subsystem type."""
    subsystem_lower = subsystem.lower()
    dg_est = -10.0
    for key, val in _SUBSYSTEM_DG.items():
        if key in subsystem_lower:
            dg_est = val
            break
    return ProvenancedValue(
        value=dg_est,
        cv=0.50,
        provenance=Provenance(
            trust_level=TrustLevel.ESTIMATED,
            source="heuristic_estimate",
        ),
    )


async def compute_dg(
    kegg_compound_ids: list[str] | None = None,
    subsystem: str = "",
) -> ProvenancedValue:
    """Compute dG via eQuilibrator if possible, otherwise heuristic."""
    # For now use heuristic — eQuilibrator integration via to_thread if available
    return estimate_dg_heuristic(subsystem)
