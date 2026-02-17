"""Active learning for iterative model refinement."""

from __future__ import annotations

from typing import Any


class ActiveLearner:
    """Active learning loop for simulation-guided model improvement."""

    def __init__(self) -> None:
        pass

    def suggest_experiments(self, model_state: dict[str, Any]) -> list[dict[str, Any]]:
        """Suggest informative experiments to reduce model uncertainty."""
        raise NotImplementedError("ActiveLearner.suggest_experiments not yet implemented")
