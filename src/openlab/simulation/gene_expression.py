"""Gene expression simulation module.

First-order transcription and translation with degradation, coupled to
metabolic resource availability. Runs interleaved with metabolism.
"""
from __future__ import annotations

from openlab.models import CellSpecGene
from openlab.simulation.state import CellState

# Base rate constants (M. genitalium literature values)
BASE_TRANSCRIPTION_RATE = 0.0001   # mRNA/gene/s
BASE_TRANSLATION_RATE = 0.34       # protein/mRNA/s (polysome model)
MRNA_DEGRADATION_RATE = 0.005      # 1/s (t half ~ 2.3 min)
PROTEIN_DEGRADATION_RATE = 0.00001  # 1/s (~19 hr half-life)

# Resource costs per macromolecule
NTP_PER_NUCLEOTIDE = 1.0
ATP_PER_AMINO_ACID = 2.0
GTP_PER_AMINO_ACID = 2.0
AA_PER_AMINO_ACID = 1.0

# Average gene/protein sizes for M. genitalium
AVG_MRNA_LENGTH = 1000.0   # nucleotides
AVG_PROTEIN_LENGTH = 330.0  # amino acids

# Km values for resource limitation (mM)
KM_ATP = 0.5
KM_GTP = 0.3
KM_AA = 0.2


class GeneExpressionModule:
    """Gene expression module with resource-coupled transcription/translation."""

    def __init__(self, genes: list[CellSpecGene], stochastic: bool = False):
        self._genes = genes
        self._stochastic = stochastic

    def step(self, state: CellState, dt: float) -> None:
        """Execute one gene expression timestep."""
        atp_conc = state.get_metabolite("atp")
        aa_conc = state.get_metabolite("aa_pool")

        atp_factor = atp_conc / (KM_ATP + atp_conc) if (KM_ATP + atp_conc) > 0 else 0.0
        aa_factor = aa_conc / (KM_AA + aa_conc) if (KM_AA + aa_conc) > 0 else 0.0

        has_metabolites = "atp" in state.metabolite_index

        txn_resource = atp_factor if has_metabolites else 1.0
        tln_resource = (atp_factor * aa_factor) if has_metabolites else 1.0

        total_atp_consumed = 0.0
        total_gtp_consumed = 0.0
        total_ntp_consumed = 0.0
        total_aa_consumed = 0.0

        for i, gene in enumerate(self._genes):
            if state.is_knocked_out(gene.locus_tag):
                state.mrna_counts[i] = max(
                    0.0, state.mrna_counts[i] - MRNA_DEGRADATION_RATE * state.mrna_counts[i] * dt
                )
                state.protein_counts[i] = max(
                    0.0, state.protein_counts[i] - PROTEIN_DEGRADATION_RATE * state.protein_counts[i] * dt
                )
                continue

            gene_rate = gene.expression_rate if gene.expression_rate is not None else 1.0

            # Apply expression modifier and methylation penalty
            modifier = state.gene_expression_modifiers[i]
            methylation_penalty = 1.0 - state.methylation[i] * 0.8
            effective_modifier = modifier * methylation_penalty

            eff_txn_rate = BASE_TRANSCRIPTION_RATE * txn_resource * gene_rate * effective_modifier
            eff_tln_rate = BASE_TRANSLATION_RATE * tln_resource * gene_rate * effective_modifier

            # Transcription
            mrna = state.mrna_counts[i]
            if self._stochastic:
                new_mrna = float(state.rng.poisson(max(0.0, eff_txn_rate * dt)))
            else:
                new_mrna = eff_txn_rate * dt
            degraded_mrna = MRNA_DEGRADATION_RATE * mrna * dt
            state.mrna_counts[i] = max(0.0, mrna + new_mrna - degraded_mrna)

            if new_mrna > 0 and has_metabolites:
                ntp_cost = new_mrna * AVG_MRNA_LENGTH * NTP_PER_NUCLEOTIDE
                total_atp_consumed += ntp_cost * 0.25
                total_gtp_consumed += ntp_cost * 0.25
                total_ntp_consumed += ntp_cost * 0.50

            # Translation
            protein = state.protein_counts[i]
            if self._stochastic:
                new_protein = float(state.rng.poisson(max(0.0, eff_tln_rate * state.mrna_counts[i] * dt)))
            else:
                new_protein = eff_tln_rate * state.mrna_counts[i] * dt
            degraded_protein = PROTEIN_DEGRADATION_RATE * protein * dt
            state.protein_counts[i] = max(0.0, protein + new_protein - degraded_protein)

            if new_protein > 0 and has_metabolites:
                total_atp_consumed += new_protein * AVG_PROTEIN_LENGTH * ATP_PER_AMINO_ACID
                total_gtp_consumed += new_protein * AVG_PROTEIN_LENGTH * GTP_PER_AMINO_ACID
                total_aa_consumed += new_protein * AVG_PROTEIN_LENGTH * AA_PER_AMINO_ACID

            # Essential unknown genes: maintain minimum protein level
            if gene.classification == "unknown" and not gene.predicted_function:
                state.protein_counts[i] = max(state.protein_counts[i], 20.0)

        # Convert molecule counts to concentration changes (mM)
        if has_metabolites:
            volume_l = state.volume * 1e-15
            mol_to_mm = 1.0 / (6.022e23 * volume_l) * 1e3

            total_energy_cost = total_atp_consumed + total_gtp_consumed
            _consume_metabolite(state, "atp", total_energy_cost * mol_to_mm)
            _consume_metabolite(state, "aa_pool", total_aa_consumed * mol_to_mm)
            _consume_metabolite(state, "ctp", total_ntp_consumed * 0.5 * mol_to_mm)
            _consume_metabolite(state, "utp", total_ntp_consumed * 0.5 * mol_to_mm)


def _consume_metabolite(state: CellState, met_id: str, amount: float) -> None:
    """Reduce a metabolite concentration, clamping at zero."""
    idx = state.metabolite_index.get(met_id)
    if idx is not None:
        state.metabolite_concentrations[idx] = max(
            0.0, state.metabolite_concentrations[idx] - amount
        )
