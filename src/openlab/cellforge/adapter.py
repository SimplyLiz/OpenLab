"""Adapter bridging BioLab CellSpec <-> CellForge KnowledgeBase."""

from __future__ import annotations

from openlab.models import CellSpec, CellSpecGene, CellSpecMetabolite, CellSpecReaction
from openlab.cellforge.core.knowledge_base import (
    Gene,
    KnowledgeBase,
    Metabolite,
    Reaction,
)


def cellspec_to_knowledge_base(spec: CellSpec) -> KnowledgeBase:
    """Convert a BioLab CellSpec into a CellForge KnowledgeBase.

    Args:
        spec: BioLab CellSpec model.

    Returns:
        Populated KnowledgeBase instance.
    """
    genes = [
        Gene(
            id=g.locus_tag,
            name=g.gene_name,
            locus_tag=g.locus_tag,
            start=g.start,
            end=g.end,
            strand=g.strand,
            product=g.product,
            sequence=g.dna_sequence,
            function=g.predicted_function,
            ec_numbers=[g.ec_number] if g.ec_number else [],
            essential=g.is_essential,
        )
        for g in spec.genes
    ]

    metabolites = [
        Metabolite(
            id=m.id,
            name=m.name,
            formula=m.formula,
            charge=m.charge,
            compartment=m.compartment,
            concentration=m.initial_concentration,
            kegg_id=m.kegg_id,
        )
        for m in spec.metabolites
    ]

    reactions = [
        Reaction(
            id=r.id,
            name=r.name,
            equation="",
            reactants={s.metabolite_id: s.coefficient for s in r.substrates},
            products={p.metabolite_id: p.coefficient for p in r.products},
            gene_reaction_rule=" and ".join(r.gene_locus_tags),
            ec_number=r.ec_number,
            subsystem=r.subsystem,
        )
        for r in spec.reactions
    ]

    return KnowledgeBase(
        organism=spec.organism,
        genes=genes,
        metabolites=metabolites,
        reactions=reactions,
    )


def knowledge_base_to_cellspec(kb: KnowledgeBase) -> CellSpec:
    """Convert a CellForge KnowledgeBase into a BioLab CellSpec.

    Args:
        kb: CellForge KnowledgeBase model.

    Returns:
        Populated CellSpec instance.
    """
    genes = [
        CellSpecGene(
            locus_tag=g.locus_tag or g.id,
            gene_name=g.name,
            start=g.start,
            end=g.end,
            strand=g.strand,
            dna_sequence=g.sequence,
            product=g.product,
            ec_number=g.ec_numbers[0] if g.ec_numbers else "",
            is_essential=g.essential if g.essential is not None else True,
            predicted_function=g.function,
        )
        for g in kb.genes
    ]

    metabolites = [
        CellSpecMetabolite(
            id=m.id,
            name=m.name,
            kegg_id=m.kegg_id,
            formula=m.formula,
            charge=m.charge,
            compartment=m.compartment,
            initial_concentration=m.concentration,
        )
        for m in kb.metabolites
    ]

    from openlab.models import ReactionParticipant

    reactions = [
        CellSpecReaction(
            id=r.id,
            name=r.name,
            ec_number=r.ec_number,
            gene_locus_tags=r.gene_reaction_rule.split(" and ") if r.gene_reaction_rule else [],
            substrates=[
                ReactionParticipant(metabolite_id=mid, coefficient=coeff)
                for mid, coeff in r.reactants.items()
            ],
            products=[
                ReactionParticipant(metabolite_id=mid, coefficient=coeff)
                for mid, coeff in r.products.items()
            ],
            subsystem=r.subsystem,
        )
        for r in kb.reactions
    ]

    return CellSpec(
        organism=kb.organism,
        genes=genes,
        metabolites=metabolites,
        reactions=reactions,
    )
