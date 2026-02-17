"""Stage: CellSpec Assembly — build simulation-ready cell specification."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import httpx

from openlab.config import config
from openlab.models import (
    CellSpec, CellSpecGene, CellSpecMetabolite, CellSpecReaction,
    GenomeRecord, KineticsEntry, PipelineEvent, Provenance,
    ProvenancedValue, ReactionParticipant, SimulationParameters,
    StageStatus, TrustLevel,
)

logger = logging.getLogger(__name__)

STAGE = "cellspec_assembly"

# Base metabolite set for a minimal cell
BASE_METABOLITES = [
    ("atp", "ATP", "C00002", "C10H16N5O13P3", -4, 2.5),
    ("adp", "ADP", "C00008", "C10H15N5O10P2", -3, 0.5),
    ("amp", "AMP", "C00020", "C10H14N5O7P", -2, 0.1),
    ("gtp", "GTP", "C00044", "C10H16N5O14P3", -4, 0.8),
    ("gdp", "GDP", "C00035", "C10H15N5O11P2", -3, 0.1),
    ("nad", "NAD+", "C00003", "C21H28N7O14P2", -1, 0.5),
    ("nadh", "NADH", "C00004", "C21H29N7O14P2", -2, 0.1),
    ("nadp", "NADP+", "C00006", "C21H29N7O17P3", -3, 0.1),
    ("nadph", "NADPH", "C00005", "C21H30N7O17P3", -4, 0.05),
    ("coa", "CoA", "C00010", "C21H36N7O16P3S", -4, 0.05),
    ("acyl_coa", "Acetyl-CoA", "C00024", "C23H38N7O17P3S", -4, 0.02),
    ("pi", "Phosphate", "C00009", "HO4P", -2, 5.0),
    ("ppi", "Diphosphate", "C00013", "H4O7P2", -3, 0.1),
    ("h2o", "Water", "C00001", "H2O", 0, 55000.0),
    ("h", "H+", "C00080", "H", 1, 0.03),  # pH 7.5 ≈ 0.03 mM
    ("co2", "CO2", "C00011", "CO2", 0, 1.0),
    ("glucose", "D-Glucose", "C00031", "C6H12O6", 0, 5.0),
    ("g6p", "Glucose-6-P", "C00092", "C6H13O9P", -2, 0.5),
    ("f6p", "Fructose-6-P", "C00085", "C6H13O9P", -2, 0.3),
    ("pyruvate", "Pyruvate", "C00022", "C3H4O3", -1, 0.5),
    ("glycerol3p", "Glycerol-3-P", "C00093", "C3H9O6P", -2, 0.2),
    ("aa_pool", "Amino acid pool", "", "", 0, 3.0),
]


async def run(
    genome: GenomeRecord,
    kinetics_data: list[dict],
    http: httpx.AsyncClient,
) -> AsyncGenerator[PipelineEvent, None]:
    """Assemble CellSpec from genome + kinetics data."""
    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.0,
        data={"message": "Assembling cell specification..."},
    )

    # Build kinetics lookup by locus_tag (from reaction_id pattern)
    kinetics_by_tag: dict[str, KineticsEntry] = {}
    for kd in kinetics_data:
        entry = KineticsEntry.model_validate(kd)
        # reaction_id is "rxn_LOCUS_TAG"
        tag = entry.reaction_id.replace("rxn_", "", 1)
        kinetics_by_tag[tag] = entry

    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.2,
        data={"message": f"Building genes ({len(genome.genes)})..."},
    )

    # Build CellSpec genes
    cs_genes: list[CellSpecGene] = []
    for gene in genome.genes:
        cs_genes.append(CellSpecGene(
            locus_tag=gene.locus_tag,
            gene_name=gene.gene_name,
            start=gene.start,
            end=gene.end,
            strand=gene.strand,
            dna_sequence=gene.dna_sequence,
            aa_sequence=gene.protein_sequence,
            classification="known" if gene.functional_category not in ("unknown", "predicted") else "unknown",
            product=gene.product,
            is_essential=gene.is_essential,
            predicted_function=gene.product if gene.prediction_source else "",
        ))

    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.4,
        data={"message": "Building metabolite pool..."},
    )

    # Build metabolites
    cs_metabolites: list[CellSpecMetabolite] = []
    for mid, name, kegg, formula, charge, init_conc in BASE_METABOLITES:
        cs_metabolites.append(CellSpecMetabolite(
            id=mid,
            name=name,
            kegg_id=kegg,
            formula=formula,
            charge=charge,
            initial_concentration=init_conc,
        ))

    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.6,
        data={"message": "Building reactions..."},
    )

    # Build reactions from kinetics entries
    cs_reactions: list[CellSpecReaction] = []
    for tag, kin in kinetics_by_tag.items():
        # Find the gene
        gene = next((g for g in genome.genes if g.locus_tag == tag), None)
        if not gene:
            continue

        # Build a basic reaction consuming ATP → ADP
        rxn = CellSpecReaction(
            id=kin.reaction_id,
            name=f"{gene.product or tag} reaction",
            ec_number=kin.ec_number,
            gene_locus_tags=[tag],
            substrates=[ReactionParticipant(metabolite_id="atp", coefficient=1.0)],
            products=[ReactionParticipant(metabolite_id="adp", coefficient=1.0)],
            kinetics=kin,
            provenance=Provenance(
                trust_level=kin.kcat.provenance.trust_level,
                source=kin.kcat.provenance.source,
            ),
        )
        cs_reactions.append(rxn)

    # Add glucose uptake reaction (maintenance)
    cs_reactions.append(CellSpecReaction(
        id="rxn_glucose_uptake",
        name="Glucose uptake",
        substrates=[ReactionParticipant(metabolite_id="glucose", coefficient=1.0)],
        products=[
            ReactionParticipant(metabolite_id="atp", coefficient=2.0),
            ReactionParticipant(metabolite_id="pyruvate", coefficient=2.0),
        ],
        kinetics=KineticsEntry(
            reaction_id="rxn_glucose_uptake",
            kcat=ProvenancedValue(
                value=5.0,
                provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="glycolysis_lumped"),
            ),
            km={"glucose": ProvenancedValue(
                value=0.5,
                provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="glycolysis_lumped"),
            )},
        ),
        provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="glycolysis_lumped"),
    ))

    # Add amino acid synthesis (lumped)
    cs_reactions.append(CellSpecReaction(
        id="rxn_aa_synthesis",
        name="Amino acid synthesis (lumped)",
        substrates=[
            ReactionParticipant(metabolite_id="pyruvate", coefficient=1.0),
            ReactionParticipant(metabolite_id="atp", coefficient=2.0),
        ],
        products=[
            ReactionParticipant(metabolite_id="aa_pool", coefficient=1.0),
            ReactionParticipant(metabolite_id="adp", coefficient=2.0),
        ],
        kinetics=KineticsEntry(
            reaction_id="rxn_aa_synthesis",
            kcat=ProvenancedValue(
                value=3.0,
                provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="amino_acid_lumped"),
            ),
            km={
                "pyruvate": ProvenancedValue(value=0.3, provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="lumped")),
                "atp": ProvenancedValue(value=0.5, provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="lumped")),
            },
        ),
        provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="amino_acid_lumped"),
    ))

    # Add ADP recycling (maintenance ATP regeneration)
    cs_reactions.append(CellSpecReaction(
        id="rxn_atp_regen",
        name="ATP regeneration (maintenance)",
        substrates=[ReactionParticipant(metabolite_id="adp", coefficient=1.0)],
        products=[ReactionParticipant(metabolite_id="atp", coefficient=1.0)],
        kinetics=KineticsEntry(
            reaction_id="rxn_atp_regen",
            kcat=ProvenancedValue(
                value=8.0,
                provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="atp_maintenance"),
            ),
            km={"adp": ProvenancedValue(value=0.3, provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="maintenance"))},
        ),
        provenance=Provenance(trust_level=TrustLevel.ESTIMATED, source="atp_maintenance"),
    ))

    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.8,
        data={"message": "Computing provenance summary..."},
    )

    # Provenance summary
    prov_summary: dict[str, int] = {}
    for rxn in cs_reactions:
        tl = rxn.provenance.trust_level.value
        prov_summary[tl] = prov_summary.get(tl, 0) + 1

    cellspec = CellSpec(
        organism=genome.organism,
        version="1.0",
        created_at=datetime.now(timezone.utc).isoformat(),
        genes=cs_genes,
        reactions=cs_reactions,
        metabolites=cs_metabolites,
        simulation_parameters=SimulationParameters(
            total_duration=config.simulation.total_duration,
            metabolism_dt=config.simulation.metabolism_dt,
            expression_dt=config.simulation.expression_dt,
            temperature=config.simulation.temperature,
            ph=config.simulation.ph,
            initial_volume=config.simulation.initial_volume,
        ),
        provenance_summary=prov_summary,
    )

    logger.info(
        f"CellSpec assembled: {len(cs_genes)} genes, {len(cs_reactions)} reactions, "
        f"{len(cs_metabolites)} metabolites"
    )

    yield PipelineEvent(
        stage=STAGE,
        status=StageStatus.COMPLETED,
        progress=1.0,
        data=cellspec.model_dump(),
    )
