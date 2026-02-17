"""Stage 2: Sequence Analysis — deep analysis of the gene's nucleotide and protein sequences.

Computes: ORFs, codon usage, CAI, GC content, CpG islands, splice sites.
All computation is local (Biopython + custom), no external API calls needed.
"""

from __future__ import annotations

from collections import Counter

from openlab.models import (
    CodonUsage, CpGIsland, GCProfile, GeneRecord, ORF,
    SequenceAnalysisResult, SpliceSite,
)

# Standard codon table
CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

# Human codon frequency reference (per thousand) for CAI calculation
HUMAN_CODON_FREQ: dict[str, float] = {
    "TTT": 17.6, "TTC": 20.3, "TTA": 7.7, "TTG": 12.9,
    "CTT": 13.2, "CTC": 19.6, "CTA": 7.2, "CTG": 39.6,
    "ATT": 16.0, "ATC": 20.8, "ATA": 7.5, "ATG": 22.0,
    "GTT": 11.0, "GTC": 14.5, "GTA": 7.1, "GTG": 28.1,
    "TCT": 15.2, "TCC": 17.7, "TCA": 12.2, "TCG": 4.4,
    "CCT": 17.5, "CCC": 19.8, "CCA": 16.9, "CCG": 6.9,
    "ACT": 13.1, "ACC": 18.9, "ACA": 15.1, "ACG": 6.1,
    "GCT": 18.4, "GCC": 27.7, "GCA": 15.8, "GCG": 7.4,
    "TAT": 12.2, "TAC": 15.3, "CAT": 10.9, "CAC": 15.1,
    "CAA": 12.3, "CAG": 34.2, "AAT": 17.0, "AAC": 19.1,
    "AAA": 24.4, "AAG": 31.9, "GAT": 21.8, "GAC": 25.1,
    "GAA": 29.0, "GAG": 39.6, "TGT": 10.6, "TGC": 12.6,
    "TGG": 13.2, "CGT": 4.5, "CGC": 10.4, "CGA": 6.2,
    "CGG": 11.4, "AGT": 12.1, "AGC": 19.5, "AGA": 12.2,
    "AGG": 12.0, "GGT": 10.8, "GGC": 22.2, "GGA": 16.5,
    "GGG": 16.5,
}


def _get_mrna(record: GeneRecord) -> str:
    """Get the mRNA or CDS sequence from the gene record."""
    for s in record.sequences:
        if s.seq_type == "mrna" and s.sequence:
            return s.sequence
    for s in record.sequences:
        if s.seq_type == "cds" and s.sequence:
            return s.sequence
    return ""


def _get_cds(record: GeneRecord) -> str:
    """Get the CDS sequence (prefers CDS over mRNA)."""
    for s in record.sequences:
        if s.seq_type == "cds" and s.sequence:
            return s.sequence
    # Fall back to mRNA — try to find CDS within it
    mrna = _get_mrna(record)
    if mrna:
        # Find first ATG
        atg_pos = mrna.find("ATG")
        if atg_pos >= 0:
            return mrna[atg_pos:]
    return mrna


# ---------------------------------------------------------------------------
# ORF detection
# ---------------------------------------------------------------------------

def find_orfs(sequence: str, min_length_aa: int = 30) -> list[ORF]:
    """Find all open reading frames in all 3 forward frames."""
    seq = sequence.upper().replace("U", "T")
    orfs: list[ORF] = []
    stop_codons = {"TAA", "TAG", "TGA"}

    for frame in range(3):
        i = frame
        start = None
        while i + 3 <= len(seq):
            codon = seq[i:i + 3]
            if codon == "ATG" and start is None:
                start = i
            elif codon in stop_codons and start is not None:
                length_aa = (i - start) // 3
                if length_aa >= min_length_aa:
                    orfs.append(ORF(
                        start=start, end=i + 3, frame=frame,
                        length_aa=length_aa,
                    ))
                start = None
            i += 3

    orfs.sort(key=lambda o: o.length_aa, reverse=True)
    return orfs


# ---------------------------------------------------------------------------
# Codon usage & CAI
# ---------------------------------------------------------------------------

def analyze_codon_usage(cds: str) -> tuple[list[CodonUsage], float]:
    """Analyze codon usage and compute Codon Adaptation Index (CAI)."""
    seq = cds.upper().replace("U", "T")
    codons_raw = [seq[i:i + 3] for i in range(0, len(seq) - 2, 3) if len(seq[i:i + 3]) == 3]
    counts = Counter(codons_raw)
    total = sum(counts.values())

    # Group synonymous codons
    aa_groups: dict[str, list[str]] = {}
    for codon, aa in CODON_TABLE.items():
        if aa == "*":
            continue
        aa_groups.setdefault(aa, []).append(codon)

    # RSCU = (count / expected) where expected = total_for_aa / num_synonymous
    usage: list[CodonUsage] = []
    for codon in sorted(CODON_TABLE.keys()):
        aa = CODON_TABLE[codon]
        if aa == "*":
            continue
        count = counts.get(codon, 0)
        freq = (count / total * 1000) if total > 0 else 0
        # RSCU
        synonyms = aa_groups[aa]
        total_for_aa = sum(counts.get(c, 0) for c in synonyms)
        expected = total_for_aa / len(synonyms) if total_for_aa > 0 else 1
        rscu = count / expected if expected > 0 else 0

        usage.append(CodonUsage(
            codon=codon, amino_acid=aa,
            count=count, frequency=round(freq, 2), rscu=round(rscu, 3),
        ))

    # CAI — geometric mean of w_i values for each codon in the sequence
    # w_i = freq(codon) / max_freq(synonymous codons) using human reference
    import math
    log_sum = 0.0
    n = 0
    for codon_str in codons_raw:
        aa = CODON_TABLE.get(codon_str)
        if not aa or aa == "*":
            continue
        synonyms = aa_groups.get(aa, [codon_str])
        max_freq = max(HUMAN_CODON_FREQ.get(s, 1.0) for s in synonyms)
        codon_freq = HUMAN_CODON_FREQ.get(codon_str, 1.0)
        w_i = codon_freq / max_freq if max_freq > 0 else 0
        if w_i > 0:
            log_sum += math.log(w_i)
            n += 1

    cai = math.exp(log_sum / n) if n > 0 else 0.0

    return usage, round(cai, 4)


# ---------------------------------------------------------------------------
# GC content
# ---------------------------------------------------------------------------

def compute_gc_profile(sequence: str, window: int = 100) -> GCProfile:
    """Compute overall and windowed GC content."""
    seq = sequence.upper()
    gc_count = seq.count("G") + seq.count("C")
    overall = gc_count / len(seq) * 100 if seq else 0

    profile = []
    for i in range(0, len(seq) - window + 1, window):
        w = seq[i:i + window]
        wgc = (w.count("G") + w.count("C")) / len(w) * 100
        profile.append(round(wgc, 1))

    return GCProfile(overall=round(overall, 2), window_size=window, profile=profile)


# ---------------------------------------------------------------------------
# CpG islands
# ---------------------------------------------------------------------------

def find_cpg_islands(
    sequence: str, window: int = 200, min_length: int = 200,
    min_gc: float = 50.0, min_obs_exp: float = 0.6,
) -> list[CpGIsland]:
    """Detect CpG islands using Gardiner-Garden & Frommer criteria."""
    seq = sequence.upper()
    islands: list[CpGIsland] = []
    i = 0

    while i + window <= len(seq):
        w = seq[i:i + window]
        gc = (w.count("G") + w.count("C")) / len(w) * 100
        cpg = w.count("CG")
        c_count = w.count("C")
        g_count = w.count("G")
        expected = (c_count * g_count) / len(w) if len(w) > 0 else 0
        obs_exp = cpg / expected if expected > 0 else 0

        if gc >= min_gc and obs_exp >= min_obs_exp:
            # Extend island
            end = i + window
            while end + window <= len(seq):
                ext = seq[end:end + window]
                ext_gc = (ext.count("G") + ext.count("C")) / len(ext) * 100
                ext_cpg = ext.count("CG")
                ext_c = ext.count("C")
                ext_g = ext.count("G")
                ext_exp = (ext_c * ext_g) / len(ext) if len(ext) > 0 else 0
                ext_obs_exp = ext_cpg / ext_exp if ext_exp > 0 else 0
                if ext_gc >= min_gc and ext_obs_exp >= min_obs_exp:
                    end += window
                else:
                    break

            island_seq = seq[i:end]
            island_gc = (island_seq.count("G") + island_seq.count("C")) / len(island_seq) * 100
            island_cpg = island_seq.count("CG")
            island_c = island_seq.count("C")
            island_g = island_seq.count("G")
            island_exp = (island_c * island_g) / len(island_seq) if len(island_seq) > 0 else 0
            island_oe = island_cpg / island_exp if island_exp > 0 else 0

            if end - i >= min_length:
                islands.append(CpGIsland(
                    start=i, end=end, length=end - i,
                    gc_percent=round(island_gc, 1),
                    obs_exp_ratio=round(island_oe, 3),
                ))
            i = end
        else:
            i += window // 2  # slide by half window

    return islands


# ---------------------------------------------------------------------------
# Splice sites
# ---------------------------------------------------------------------------

def find_splice_sites(sequence: str) -> list[SpliceSite]:
    """Detect canonical splice donor (GT) and acceptor (AG) sites with flanking context."""
    seq = sequence.upper()
    sites: list[SpliceSite] = []

    for i in range(len(seq) - 1):
        dinuc = seq[i:i + 2]
        if dinuc == "GT":
            # Donor site — score based on extended consensus (MAG|GTRAGT)
            context = seq[max(0, i - 3):i + 8]
            score = 0.0
            if i + 5 < len(seq) and seq[i + 2:i + 4] in ("AA", "AG"):
                score = 0.8
            sites.append(SpliceSite(
                position=i, site_type="donor", sequence=context, score=round(score, 2),
            ))
        elif dinuc == "AG":
            # Acceptor site
            context = seq[max(0, i - 10):i + 4]
            score = 0.0
            # Check for polypyrimidine tract upstream
            upstream = seq[max(0, i - 20):i]
            py_count = sum(1 for c in upstream if c in "CT")
            if len(upstream) > 0 and py_count / len(upstream) > 0.6:
                score = 0.7
            sites.append(SpliceSite(
                position=i, site_type="acceptor", sequence=context, score=round(score, 2),
            ))

    # Keep only high-scoring sites to avoid noise
    sites = [s for s in sites if s.score > 0]
    sites.sort(key=lambda s: s.score, reverse=True)
    return sites[:100]  # cap at 100 most likely


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run(record: GeneRecord) -> SequenceAnalysisResult:
    """Run full sequence analysis on the gene record."""
    mrna = _get_mrna(record)
    cds = _get_cds(record)

    if not mrna and not cds:
        return SequenceAnalysisResult()

    seq = mrna or cds
    result = SequenceAnalysisResult(seq_length=len(seq))

    # ORFs
    result.orfs = find_orfs(seq)
    if result.orfs:
        result.primary_orf = result.orfs[0]

    # Codon usage on CDS
    if cds:
        result.codon_usage, result.cai = analyze_codon_usage(cds)

    # GC content
    result.gc_profile = compute_gc_profile(seq)

    # CpG islands
    result.cpg_islands = find_cpg_islands(seq)

    # Splice sites
    result.splice_sites = find_splice_sites(seq)

    return result
