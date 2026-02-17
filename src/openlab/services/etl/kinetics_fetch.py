"""Kinetics parameter fetching with trust-hierarchy waterfall — async from DNAView.

Waterfall order:
1. BRENDA/SABIO-RK M. genitalium → measured
2. BRENDA/SABIO-RK Mycoplasma genus → measuredHomolog
3. SABIO-RK broad search → measuredHomolog
4. Datanator → estimated
5. Conservative defaults → assumed
"""

import logging
from datetime import datetime, timezone

from openlab.models import KineticsEntry, Provenance, ProvenancedValue, TrustLevel

from .brenda import AsyncBRENDAClient
from .sabio_rk import AsyncSabioRKClient
from .datanator import AsyncDatanatorClient

logger = logging.getLogger(__name__)

DEFAULT_KCAT = 10.0  # 1/s
DEFAULT_KM = 0.1     # mM

MYCOPLASMA_SPECIES = [
    "Mycoplasma genitalium",
    "Mycoplasma pneumoniae",
    "Mycoplasma mycoides",
    "Mycoplasma gallisepticum",
]


def _make_prov(value: float, trust: TrustLevel, source: str, ec: str = "", cv: float = 0.0) -> ProvenancedValue:
    return ProvenancedValue(
        value=value,
        cv=cv,
        provenance=Provenance(
            trust_level=trust,
            source=source,
            source_id=ec,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        ),
    )


async def waterfall_kcat(
    ec: str,
    brenda: AsyncBRENDAClient | None,
    sabio: AsyncSabioRKClient | None,
    datanator: AsyncDatanatorClient | None,
) -> ProvenancedValue:
    """Waterfall search for kcat."""
    # 1. BRENDA native organism
    if brenda:
        entries = await brenda.get_kcat(ec, "Mycoplasma genitalium")
        if entries:
            val = _extract_numeric(entries[0])
            if val is not None:
                return _make_prov(val, TrustLevel.MEASURED, "BRENDA", ec)

    # 2. SABIO-RK native organism
    if sabio:
        entries = await sabio.search_kinetics(ec, "Mycoplasma genitalium")
        kcat_val = _extract_sabio_kcat(entries)
        if kcat_val is not None:
            return _make_prov(kcat_val, TrustLevel.MEASURED, "SABIO-RK", ec)

    # 3. BRENDA Mycoplasma genus (homolog)
    if brenda:
        for species in MYCOPLASMA_SPECIES[1:]:
            entries = await brenda.get_kcat(ec, species)
            if entries:
                val = _extract_numeric(entries[0])
                if val is not None:
                    return _make_prov(val, TrustLevel.MEASURED_HOMOLOG, "BRENDA", ec, cv=0.30)

    # 4. SABIO-RK broad search
    if sabio:
        entries = await sabio.search_kinetics_broad(ec)
        kcat_val = _extract_sabio_kcat(entries)
        if kcat_val is not None:
            return _make_prov(kcat_val, TrustLevel.MEASURED_HOMOLOG, "SABIO-RK", ec)

    # 5. Datanator
    if datanator:
        entries = await datanator.get_rate_constants(ec)
        if entries:
            val = _extract_datanator_kcat(entries)
            if val is not None:
                return _make_prov(val, TrustLevel.ESTIMATED, "Datanator", ec)

    # 6. Default
    return _make_prov(DEFAULT_KCAT, TrustLevel.ASSUMED, "default", ec, cv=2.0)


async def waterfall_km(
    ec: str,
    substrate: str,
    brenda: AsyncBRENDAClient | None,
    datanator: AsyncDatanatorClient | None,
) -> ProvenancedValue:
    """Waterfall search for Km."""
    if brenda:
        # Native organism
        entries = await brenda.get_km(ec, "Mycoplasma genitalium")
        for entry in entries:
            val = _extract_numeric(entry)
            if val is not None:
                return _make_prov(val, TrustLevel.MEASURED, "BRENDA", ec)

        # Homolog
        for species in MYCOPLASMA_SPECIES[1:]:
            entries = await brenda.get_km(ec, species)
            for entry in entries:
                val = _extract_numeric(entry)
                if val is not None:
                    return _make_prov(val, TrustLevel.MEASURED_HOMOLOG, "BRENDA", ec)

    if datanator:
        entries = await datanator.get_rate_constants(ec)
        if entries:
            for entry in entries:
                if "km" in entry:
                    try:
                        return _make_prov(float(entry["km"]), TrustLevel.ESTIMATED, "Datanator", ec)
                    except (ValueError, TypeError):
                        pass

    return _make_prov(DEFAULT_KM, TrustLevel.ASSUMED, "default", ec, cv=2.0)


async def fetch_kinetics_for_ec(
    ec_number: str,
    reaction_id: str = "",
    substrate_ids: list[str] | None = None,
    brenda: AsyncBRENDAClient | None = None,
    sabio: AsyncSabioRKClient | None = None,
    datanator: AsyncDatanatorClient | None = None,
) -> KineticsEntry:
    """Fetch kinetic parameters for a single EC number using the trust waterfall."""
    kcat = await waterfall_kcat(ec_number, brenda, sabio, datanator)

    km: dict[str, ProvenancedValue] = {}
    if substrate_ids:
        for sub_id in substrate_ids:
            km[sub_id] = await waterfall_km(ec_number, sub_id, brenda, datanator)

    return KineticsEntry(
        reaction_id=reaction_id or f"rxn_{ec_number.replace('.', '_')}",
        ec_number=ec_number,
        kcat=kcat,
        km=km,
        reversible=False,
    )


def _extract_numeric(entry: dict) -> float | None:
    for key in ("turnoverNumber", "kmValue", "kiValue", "value"):
        if key in entry:
            try:
                return float(entry[key])
            except (ValueError, TypeError):
                pass
    return None


def _extract_sabio_kcat(entries: list[dict]) -> float | None:
    for entry in entries:
        params = entry.get("parameters", {})
        for key in ("kcat", "Vmax", "k_cat"):
            if key in params:
                return params[key]
    return None


def _extract_datanator_kcat(entries: list[dict]) -> float | None:
    for entry in entries:
        if "kcat" in entry:
            try:
                return float(entry["kcat"])
            except (ValueError, TypeError):
                pass
        if "parameter" in entry and entry.get("parameter_type") == "kcat":
            try:
                return float(entry["parameter"])
            except (ValueError, TypeError):
                pass
    return None


def compute_coverage(kinetics_entries: list[KineticsEntry]) -> dict:
    """Compute trust-level coverage report."""
    from collections import Counter
    trust_counts: Counter[str] = Counter()
    for k in kinetics_entries:
        trust_counts[k.kcat.provenance.trust_level.value] += 1

    total = sum(trust_counts.values()) or 1
    report = {}
    for level in ["measured", "measuredHomolog", "computed", "estimated", "predicted", "assumed"]:
        count = trust_counts.get(level, 0)
        report[level] = {"count": count, "pct": round(count / total * 100, 1)}

    assumed_pct = report.get("assumed", {}).get("pct", 0)
    report["warning"] = assumed_pct > 15
    return report
