"""Protein function prediction using language models."""

from __future__ import annotations


class ProteinFunctionPredictor:
    """Predicts protein function from sequence using ESM/ProtTrans."""

    def __init__(self, model_name: str = "esm2_t33_650M_UR50D") -> None:
        self.model_name = model_name

    def predict(self, sequence: str) -> dict[str, float]:
        """Predict functional annotations for a protein sequence."""
        raise NotImplementedError("ProteinFunctionPredictor.predict not yet implemented")
