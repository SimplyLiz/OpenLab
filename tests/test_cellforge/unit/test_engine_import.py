"""Tests for the Rust engine bridge import."""

from __future__ import annotations


def test_engine_import() -> None:
    from openlab.cellforge._engine import __version__

    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_cellforge_package_import() -> None:
    import openlab.cellforge as cellforge

    assert hasattr(cellforge, "Simulation")
    assert hasattr(cellforge, "SimulationConfig")
    assert hasattr(cellforge, "KnowledgeBase")
    assert hasattr(cellforge, "CellForgeProcess")
