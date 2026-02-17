"""Tests for KnowledgeBase construction and methods."""

from __future__ import annotations

import pytest

from openlab.cellforge.core.knowledge_base import Gene, KnowledgeBase, Metabolite, Reaction


def test_empty_kb() -> None:
    kb = KnowledgeBase()
    assert kb.organism == "unknown"
    assert len(kb.genes) == 0
    assert len(kb.reactions) == 0


def test_kb_summary(m_genitalium_kb: KnowledgeBase) -> None:
    summary = m_genitalium_kb.summary()
    assert summary["organism"] == "Mycoplasma genitalium"
    assert summary["num_genes"] == 2
    assert summary["num_metabolites"] == 3
    assert summary["num_reactions"] == 1
    assert summary["genome_length"] == 580076


def test_kb_to_cobra_not_implemented(m_genitalium_kb: KnowledgeBase) -> None:
    with pytest.raises(NotImplementedError):
        m_genitalium_kb.to_cobra_model()


def test_kb_serialization() -> None:
    kb = KnowledgeBase(
        organism="test",
        genes=[Gene(id="g1", name="gene1")],
        metabolites=[Metabolite(id="m1", name="met1")],
        reactions=[Reaction(id="r1", name="rxn1")],
    )
    data = kb.model_dump()
    restored = KnowledgeBase.model_validate(data)
    assert restored.organism == "test"
    assert len(restored.genes) == 1
    assert len(restored.metabolites) == 1
    assert len(restored.reactions) == 1
