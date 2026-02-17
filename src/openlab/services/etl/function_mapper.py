"""Function mapper — map predicted functions to simulation reactions, from DNAView."""

import logging
import re

from openlab.models import (
    CellSpecReaction, KineticsEntry, Provenance, ProvenancedValue,
    ReactionParticipant, TrustLevel,
)

from .kegg import AsyncKEGGClient

logger = logging.getLogger(__name__)

DEFAULT_KCAT = 10.0
DEFAULT_KM = 0.5

# Metabolite name → CellSpec metabolite ID
KEGG_METABOLITE_MAP = {
    "ATP": "atp", "ADP": "adp", "AMP": "amp",
    "GTP": "gtp", "GDP": "gdp", "GMP": "gmp",
    "NAD+": "nad", "NADH": "nadh", "NADP+": "nadp", "NADPH": "nadph",
    "H2O": "h2o", "H+": "h",
    "Orthophosphate": "pi", "Diphosphate": "ppi",
    "CO2": "co2", "CoA": "coa", "Acetyl-CoA": "acyl_coa",
    "L-Glutamate": "aa_pool", "L-Glutamine": "aa_pool",
    "Pyruvate": "pyruvate", "D-Glucose": "glucose",
    "D-Fructose 6-phosphate": "f6p",
    "D-Glucose 6-phosphate": "g6p",
    "Glycerol 3-phosphate": "glycerol3p",
}

# Template reactions by category
REACTION_TEMPLATES: dict[str, dict] = {
    "enzyme": {
        "substrates": [("atp", 1.0)],
        "products": [("adp", 1.0)],
        "kcat": DEFAULT_KCAT,
    },
    "transporter": {
        "substrates": [("atp", 1.0), ("glucose", 1.0)],
        "products": [("adp", 1.0)],
        "kcat": 0.1,
    },
    "membrane_biogenesis": {
        "substrates": [("atp", 1.0), ("acyl_coa", 1.0)],
        "products": [("adp", 1.0)],
        "kcat": DEFAULT_KCAT * 0.5,
    },
    "dna_repair": {
        "substrates": [("atp", 2.0)],
        "products": [("adp", 2.0)],
        "kcat": DEFAULT_KCAT * 0.3,
    },
}


def _make_km_prov(value: float) -> ProvenancedValue:
    return ProvenancedValue(
        value=value,
        provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="template"),
    )


def make_template_reaction(
    locus_tag: str,
    category: str,
    confidence: float = 0.5,
) -> CellSpecReaction | None:
    """Create a template reaction from function category."""
    template = REACTION_TEMPLATES.get(category)
    if not template:
        return None

    scaled_kcat = template["kcat"] * confidence
    substrates = [ReactionParticipant(metabolite_id=m, coefficient=c)
                  for m, c in template["substrates"]]
    products = [ReactionParticipant(metabolite_id=m, coefficient=c)
                for m, c in template["products"]]
    km = {m: _make_km_prov(DEFAULT_KM) for m, _ in template["substrates"]}

    return CellSpecReaction(
        id=f"rxn_predicted_{locus_tag}",
        name=f"Predicted {category} reaction ({locus_tag})",
        gene_locus_tags=[locus_tag],
        substrates=substrates,
        products=products,
        kinetics=KineticsEntry(
            reaction_id=f"rxn_predicted_{locus_tag}",
            kcat=ProvenancedValue(
                value=round(scaled_kcat, 4),
                provenance=Provenance(trust_level=TrustLevel.PREDICTED, source="template"),
            ),
            km=km,
        ),
        provenance=Provenance(trust_level=TrustLevel.PREDICTED, source="DNASyn-template"),
    )


async def resolve_ec_reaction(
    ec_number: str,
    gene_locus_tag: str,
    confidence: float = 0.5,
    kegg: AsyncKEGGClient | None = None,
) -> CellSpecReaction | None:
    """Resolve an EC number to a concrete reaction via KEGG."""
    if kegg is None:
        return None

    try:
        enzyme_text = await kegg.get_enzyme(ec_number)
        if not enzyme_text:
            return None

        rxn_ids = re.findall(r"(R\d{5})", enzyme_text)
        if not rxn_ids:
            return None

        name_match = re.search(r"NAME\s+(.+?)(?:\n[A-Z]|\nCLASS)", enzyme_text, re.DOTALL)
        enzyme_name = name_match.group(1).strip().split("\n")[0] if name_match else ec_number

        for rxn_id in rxn_ids[:3]:
            rxn_text = await kegg.get_reaction(rxn_id)
            if not rxn_text:
                continue

            eq_match = re.search(r"EQUATION\s+(.+)", rxn_text)
            if not eq_match:
                continue

            subs_raw, prods_raw = _parse_kegg_equation(eq_match.group(1).strip())
            subs = _kegg_names_to_ids(subs_raw)
            prods = _kegg_names_to_ids(prods_raw)

            if not subs or not prods:
                continue

            scaled_kcat = DEFAULT_KCAT * confidence
            substrates = [ReactionParticipant(metabolite_id=m, coefficient=c)
                          for m, c in subs.items()]
            products = [ReactionParticipant(metabolite_id=m, coefficient=c)
                        for m, c in prods.items()]
            km = {m: _make_km_prov(DEFAULT_KM) for m in subs}

            return CellSpecReaction(
                id=f"rxn_ec_{ec_number.replace('.', '_')}_{gene_locus_tag}",
                name=f"{enzyme_name} ({ec_number}, {gene_locus_tag})",
                ec_number=ec_number,
                kegg_id=rxn_id,
                gene_locus_tags=[gene_locus_tag],
                substrates=substrates,
                products=products,
                kinetics=KineticsEntry(
                    reaction_id=f"rxn_ec_{ec_number.replace('.', '_')}_{gene_locus_tag}",
                    ec_number=ec_number,
                    kcat=ProvenancedValue(
                        value=round(scaled_kcat, 4),
                        provenance=Provenance(trust_level=TrustLevel.PREDICTED, source=f"KEGG:{rxn_id}"),
                    ),
                    km=km,
                ),
                provenance=Provenance(trust_level=TrustLevel.PREDICTED, source=f"KEGG:{rxn_id}"),
            )

        return None
    except Exception as e:
        logger.warning(f"EC resolution failed for {ec_number}: {e}")
        return None


def _parse_kegg_equation(equation: str) -> tuple[dict[str, float], dict[str, float]]:
    sides = re.split(r"\s*<=>\s*", equation, maxsplit=1)
    if len(sides) != 2:
        return {}, {}

    def parse_side(side: str) -> dict[str, float]:
        result = {}
        for term in re.split(r"\s*\+\s*", side.strip()):
            term = term.strip()
            if not term:
                continue
            m = re.match(r"^(\d+)\s+(.+)$", term)
            if m:
                coeff, name = float(m.group(1)), m.group(2).strip()
            else:
                coeff, name = 1.0, term
            result[name] = coeff
        return result

    return parse_side(sides[0]), parse_side(sides[1])


def _kegg_names_to_ids(metabolites: dict[str, float]) -> dict[str, float]:
    mapped: dict[str, float] = {}
    for name, coeff in metabolites.items():
        mid = KEGG_METABOLITE_MAP.get(name)
        if mid:
            mapped[mid] = mapped.get(mid, 0) + coeff
    return mapped
