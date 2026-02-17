"""Sparse stoichiometric matrix (metabolites x reactions).

Uses scipy.sparse COO format for storage efficiency.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from openlab.models import CellSpecReaction, CellSpecMetabolite


@dataclass
class MassBalanceResult:
    """Result of mass balance check for a single reaction."""
    reaction_id: str
    sum_coefficients: float
    num_participants: int
    balanced: bool


class StoichiometricMatrix:
    """Sparse stoichiometric matrix S where S[i,j] is the coefficient of
    metabolite i in reaction j. Negative = consumed, positive = produced.
    """

    def __init__(
        self,
        metabolite_ids: list[str],
        reaction_ids: list[str],
        matrix: sparse.coo_matrix | None = None,
    ):
        self.metabolite_ids = metabolite_ids
        self.reaction_ids = reaction_ids
        self._met_index = {mid: i for i, mid in enumerate(metabolite_ids)}
        self._rxn_index = {rid: i for i, rid in enumerate(reaction_ids)}

        if matrix is not None:
            self.matrix = matrix.tocsr()
        else:
            self.matrix = sparse.csr_matrix(
                (len(metabolite_ids), len(reaction_ids))
            )

    @property
    def num_metabolites(self) -> int:
        return len(self.metabolite_ids)

    @property
    def num_reactions(self) -> int:
        return len(self.reaction_ids)

    @property
    def num_nonzero(self) -> int:
        return self.matrix.nnz

    @classmethod
    def from_reactions(
        cls,
        reactions: list[CellSpecReaction],
        metabolites: list[CellSpecMetabolite],
    ) -> StoichiometricMatrix:
        """Build from lists of Reaction and Metabolite models."""
        met_ids = [m.id for m in metabolites]
        rxn_ids = [r.id for r in reactions]
        met_index = {mid: i for i, mid in enumerate(met_ids)}

        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []

        for j, rxn in enumerate(reactions):
            for sub in rxn.substrates:
                mi = met_index.get(sub.metabolite_id)
                if mi is not None:
                    rows.append(mi)
                    cols.append(j)
                    vals.append(-abs(sub.coefficient))

            for prod in rxn.products:
                mi = met_index.get(prod.metabolite_id)
                if mi is not None:
                    rows.append(mi)
                    cols.append(j)
                    vals.append(abs(prod.coefficient))

        coo = sparse.coo_matrix(
            (vals, (rows, cols)),
            shape=(len(met_ids), len(rxn_ids)),
        )

        return cls(met_ids, rxn_ids, coo)

    def get(self, metabolite_idx: int, reaction_idx: int) -> float:
        return float(self.matrix[metabolite_idx, reaction_idx])

    def get_reaction_column(self, reaction_idx: int) -> np.ndarray:
        return np.asarray(self.matrix[:, reaction_idx].todense()).flatten()

    def get_metabolite_row(self, metabolite_idx: int) -> np.ndarray:
        return np.asarray(self.matrix[metabolite_idx, :].todense()).flatten()

    def compute_flux(self, rates: np.ndarray) -> np.ndarray:
        """dC/dt = S @ v"""
        return np.asarray(self.matrix @ rates).flatten()

    def check_mass_balance(self) -> list[MassBalanceResult]:
        results = []
        dense = self.matrix.toarray()

        for j in range(self.num_reactions):
            col = dense[:, j]
            nonzero_mask = col != 0
            sum_coeff = float(col.sum())
            n_participants = int(nonzero_mask.sum())
            balanced = abs(sum_coeff) < 1e-6 or n_participants <= 2

            results.append(MassBalanceResult(
                reaction_id=self.reaction_ids[j],
                sum_coefficients=sum_coeff,
                num_participants=n_participants,
                balanced=balanced,
            ))

        return results

    def to_coo_list(self) -> list[list[float]]:
        coo = self.matrix.tocoo()
        return [
            [float(r), float(c), float(v)]
            for r, c, v in zip(coo.row, coo.col, coo.data)
        ]

    @classmethod
    def from_coo_list(
        cls,
        coo_list: list[list[float]],
        metabolite_ids: list[str],
        reaction_ids: list[str],
    ) -> StoichiometricMatrix:
        if not coo_list:
            return cls(metabolite_ids, reaction_ids)

        rows = [int(entry[0]) for entry in coo_list]
        cols = [int(entry[1]) for entry in coo_list]
        vals = [entry[2] for entry in coo_list]

        coo = sparse.coo_matrix(
            (vals, (rows, cols)),
            shape=(len(metabolite_ids), len(reaction_ids)),
        )
        return cls(metabolite_ids, reaction_ids, coo)

    def to_dense(self) -> np.ndarray:
        return self.matrix.toarray()
