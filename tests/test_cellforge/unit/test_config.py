"""Tests for SimulationConfig defaults and validation."""

from __future__ import annotations

from openlab.cellforge.core.config import SimulationConfig


def test_default_config() -> None:
    config = SimulationConfig()
    assert config.total_time == 3600.0
    assert config.dt == 1.0
    assert config.seed == 42
    assert config.temperature == 310.15
    assert config.ph == 7.4
    assert config.log_level == "INFO"


def test_config_custom_values() -> None:
    config = SimulationConfig(
        organism_name="E. coli",
        total_time=7200.0,
        dt=0.5,
        seed=123,
    )
    assert config.organism_name == "E. coli"
    assert config.total_time == 7200.0
    assert config.dt == 0.5
    assert config.seed == 123


def test_config_serialization() -> None:
    config = SimulationConfig(organism_name="test")
    data = config.model_dump()
    assert data["organism_name"] == "test"
    restored = SimulationConfig.model_validate(data)
    assert restored == config
