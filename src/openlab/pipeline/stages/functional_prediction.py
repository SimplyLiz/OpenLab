"""Stage: Functional Prediction — uncover what mystery genes do.

Upgraded with DNASyn's evidence pipeline:
  Phase 1: Local protein analysis (instant) + CDD domain search
  Phase 2: Multi-source evidence collection (InterPro, STRING, UniProt, literature)
  Phase 3: Evidence normalization + convergence scoring
  Phase 4: LLM synthesis for top mystery genes (Anthropic/OpenAI/Ollama)

This is the "fully decipher genes by all means" engine.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from openlab.config import config
from openlab.models import (
    BlastHit, ConvergenceResult, DomainHit, EvidenceRecord,
    FunctionalCategory, FunctionalPrediction, GenomeFunctionalAnalysis,
    GenomeGene, GenomeRecord, Hypothesis, PipelineEvent, ProteinFeatures,
    StageStatus,
)
from openlab.pipeline.stages.evidence_collection import collect_evidence_for_gene
from openlab.services.convergence import classify_confidence_tier, compute_convergence
from openlab.services.evidence_normalizer import NormalizedEvidence, normalize_evidence
from openlab.services import llm_synthesis
from openlab.services.prior_knowledge import get_prior_knowledge

logger = logging.getLogger(__name__)

# Amino acid properties
AA_MW: dict[str, float] = {
    "A": 89.1, "R": 174.2, "N": 132.1, "D": 133.1, "C": 121.2,
    "E": 147.1, "Q": 146.2, "G": 75.0, "H": 155.2, "I": 131.2,
    "L": 131.2, "K": 146.2, "M": 149.2, "F": 165.2, "P": 115.1,
    "S": 105.1, "T": 119.1, "W": 204.2, "Y": 181.2, "V": 117.1,
}

# Kyte-Doolittle hydrophobicity
KD_HYDRO: dict[str, float] = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "E": -3.5, "Q": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

CHARGED = set("DEKRH")


def analyze_protein_features(seq: str) -> ProteinFeatures:
    """Compute physical/chemical properties of a protein sequence."""
    if not seq:
        return ProteinFeatures()

    seq = seq.upper()
    n = len(seq)

    mw = sum(AA_MW.get(aa, 0) for aa in seq) - (n - 1) * 18.015
    mw = round(mw, 1)

    pos_charge = seq.count("K") + seq.count("R") + seq.count("H")
    neg_charge = seq.count("D") + seq.count("E")
    if pos_charge > neg_charge:
        pi = 8.0 + (pos_charge - neg_charge) / n * 5
    elif neg_charge > pos_charge:
        pi = 6.0 - (neg_charge - pos_charge) / n * 5
    else:
        pi = 7.0
    pi = round(max(3.0, min(12.0, pi)), 2)

    gravy = sum(KD_HYDRO.get(aa, 0) for aa in seq) / n
    gravy = round(gravy, 3)

    tm_count = 0
    window = 20
    for i in range(len(seq) - window + 1):
        segment = seq[i:i + window]
        avg_hydro = sum(KD_HYDRO.get(aa, 0) for aa in segment) / window
        if avg_hydro > 1.6:
            tm_count += 1
    tm_helices = min(tm_count // 15 + (1 if tm_count % 15 > 5 else 0), 20) if tm_count > 0 else 0

    has_signal = False
    if n > 30:
        n_term = seq[:25]
        n_hydro = sum(KD_HYDRO.get(aa, 0) for aa in n_term) / 25
        has_signal = n_hydro > 0.5 and seq[0] == "M"

    charged_pct = round(sum(1 for aa in seq if aa in CHARGED) / n * 100, 1)

    disorder_count = 0
    for i in range(0, n - 30, 10):
        segment = seq[i:i + 30]
        seg_hydro = sum(KD_HYDRO.get(aa, 0) for aa in segment) / 30
        seg_charged = sum(1 for aa in segment if aa in CHARGED) / 30
        if seg_hydro < -0.5 and seg_charged > 0.3:
            disorder_count += 1
    disorder_pct = round(disorder_count / max(1, (n - 30) // 10) * 100, 1)

    return ProteinFeatures(
        molecular_weight=mw,
        isoelectric_point=pi,
        hydrophobicity=gravy,
        has_signal_peptide=has_signal,
        has_transmembrane=tm_helices > 0,
        transmembrane_count=tm_helices,
        is_secreted=has_signal and tm_helices <= 1,
        charged_residues_pct=charged_pct,
        disorder_pct=disorder_pct,
    )


async def search_cdd(http: httpx.AsyncClient, protein_seq: str) -> list[DomainHit]:
    """Search NCBI Conserved Domain Database."""
    if not protein_seq or len(protein_seq) < 20:
        return []

    try:
        resp = await http.post(
            "https://www.ncbi.nlm.nih.gov/Structure/bwrpsb/bwrpsb.cgi",
            data={
                "queries": f">query\n{protein_seq}",
                "db": "cdd",
                "smode": "auto",
                "useid1": "true",
                "compbasedadj": "1",
                "filter": "true",
                "evalue": "0.01",
                "maxhit": "10",
                "tdata": "hits",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        text = resp.text

        cdsid_match = re.search(r"#cdsid\s+(\S+)", text)
        if not cdsid_match:
            return []
        cdsid = cdsid_match.group(1)

        for _ in range(10):
            await asyncio.sleep(2)
            result_resp = await http.get(
                "https://www.ncbi.nlm.nih.gov/Structure/bwrpsb/bwrpsb.cgi",
                params={"cdsid": cdsid, "tdata": "hits"},
                timeout=20.0,
            )
            result_text = result_resp.text

            if "#status\t0" in result_text:
                domains = []
                for line in result_text.split("\n"):
                    if line.startswith("Q#"):
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) >= 8 and not line.startswith("#"):
                        try:
                            domains.append(DomainHit(
                                domain_id=parts[7] if len(parts) > 7 else parts[1],
                                name=parts[8] if len(parts) > 8 else parts[7],
                                description=parts[8] if len(parts) > 8 else "",
                                evalue=float(parts[5]) if parts[5] else 0,
                                score=float(parts[4]) if parts[4] else 0,
                                start=int(parts[3]) if parts[3] else 0,
                                end=int(parts[4]) if parts[4] else 0,
                            ))
                        except (ValueError, IndexError):
                            continue
                return domains

            if "#status\t3" in result_text:
                continue
            break

    except Exception:
        pass

    return []


async def blast_search(
    http: httpx.AsyncClient, protein_seq: str, max_hits: int = 5
) -> list[BlastHit]:
    """Quick BLAST search against NCBI nr database."""
    if not protein_seq or len(protein_seq) < 20:
        return []

    try:
        resp = await http.post(
            "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi",
            data={
                "CMD": "Put",
                "PROGRAM": "blastp",
                "DATABASE": "nr",
                "QUERY": protein_seq,
                "EXPECT": "1e-5",
                "HITLIST_SIZE": str(max_hits),
                "FORMAT_TYPE": "JSON2",
            },
            timeout=30.0,
        )
        resp.raise_for_status()

        rid_match = re.search(r"RID = (\S+)", resp.text)
        if not rid_match:
            return []
        rid = rid_match.group(1)

        for _ in range(30):
            await asyncio.sleep(5)
            check = await http.get(
                "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi",
                params={"CMD": "Get", "RID": rid, "FORMAT_TYPE": "JSON2"},
                timeout=20.0,
            )

            if "WAITING" in check.text[:500]:
                continue

            if "BlastOutput2" in check.text:
                try:
                    import json
                    data = json.loads(check.text)
                    results = data.get("BlastOutput2", [{}])
                    if not results:
                        return []
                    search = results[0].get("report", {}).get("results", {}).get("search", {})
                    hit_list = search.get("hits", [])

                    hits = []
                    for h in hit_list[:max_hits]:
                        desc_list = h.get("description", [{}])
                        desc = desc_list[0] if desc_list else {}
                        hsps = h.get("hsps", [{}])
                        hsp = hsps[0] if hsps else {}

                        hits.append(BlastHit(
                            accession=desc.get("accession", ""),
                            description=desc.get("title", ""),
                            organism=desc.get("sciname", ""),
                            identity=round(hsp.get("identity", 0) / max(hsp.get("align_len", 1), 1) * 100, 1),
                            coverage=round(hsp.get("align_len", 0) / max(len(protein_seq), 1) * 100, 1),
                            evalue=hsp.get("evalue", 0),
                            score=hsp.get("bit_score", 0),
                        ))
                    return hits
                except Exception:
                    return []
            break

    except Exception:
        pass

    return []


def _build_evidence_records(
    gene: GenomeGene,
    features: ProteinFeatures,
    domains: list[DomainHit],
    blast_hits: list[BlastHit],
    external_evidence: list[dict[str, Any]],
) -> list[EvidenceRecord]:
    """Build normalized evidence records from all sources."""
    records: list[EvidenceRecord] = []

    # Protein features as evidence
    if features.molecular_weight > 0:
        feat_payload = {
            "source": "protein_features",
            "molecular_weight": features.molecular_weight,
            "isoelectric_point": features.isoelectric_point,
            "hydrophobicity": features.hydrophobicity,
            "transmembrane_count": features.transmembrane_count,
            "has_signal_peptide": features.has_signal_peptide,
            "charged_residues_pct": features.charged_residues_pct,
            "disorder_pct": features.disorder_pct,
        }
        if features.has_transmembrane:
            feat_payload["description"] = f"Membrane protein with {features.transmembrane_count} TM helix(es)"
        if features.is_secreted:
            feat_payload["description"] = "Secreted protein with signal peptide"
        norm = normalize_evidence(feat_payload)
        records.append(EvidenceRecord(
            source="protein_features",
            payload=feat_payload,
            go_terms=sorted(norm.go_terms),
            ec_numbers=sorted(norm.ec_numbers),
            categories=sorted(norm.categories),
            keywords=sorted(list(norm.keywords)[:20]),
        ))

    # CDD domains as evidence
    if domains:
        domain_payload: dict[str, Any] = {
            "source": "cdd",
            "domains": [
                {"name": d.name, "description": d.description,
                 "evalue": d.evalue, "domain_id": d.domain_id}
                for d in domains
            ],
        }
        norm = normalize_evidence(domain_payload)
        records.append(EvidenceRecord(
            source="cdd",
            payload=domain_payload,
            confidence=0.8,
            go_terms=sorted(norm.go_terms),
            ec_numbers=sorted(norm.ec_numbers),
            categories=sorted(norm.categories),
            keywords=sorted(list(norm.keywords)[:20]),
        ))

    # BLAST hits as evidence
    if blast_hits:
        blast_payload: dict[str, Any] = {
            "source": "ncbi_blast",
            "hits": [
                {"description": h.description, "organism": h.organism,
                 "identity": h.identity, "evalue": h.evalue}
                for h in blast_hits
            ],
        }
        norm = normalize_evidence(blast_payload)
        records.append(EvidenceRecord(
            source="ncbi_blast",
            payload=blast_payload,
            confidence=blast_hits[0].identity / 100 if blast_hits else 0,
            go_terms=sorted(norm.go_terms),
            ec_numbers=sorted(norm.ec_numbers),
            categories=sorted(norm.categories),
            keywords=sorted(list(norm.keywords)[:20]),
        ))

    # External evidence (InterPro, STRING, UniProt, literature)
    for ev in external_evidence:
        source = ev.get("source", "unknown")
        norm = normalize_evidence(ev)
        records.append(EvidenceRecord(
            source=source,
            payload=ev,
            go_terms=sorted(norm.go_terms),
            ec_numbers=sorted(norm.ec_numbers),
            categories=sorted(norm.categories),
            keywords=sorted(list(norm.keywords)[:20]),
        ))

    return records


def synthesize_prediction(
    gene: GenomeGene,
    features: ProteinFeatures,
    domains: list[DomainHit],
    blast_hits: list[BlastHit],
    evidence_records: list[EvidenceRecord],
    convergence_score: float,
    hypothesis: Hypothesis | None = None,
) -> FunctionalPrediction:
    """Synthesize all evidence into a functional prediction."""
    evidence_summary: list[str] = []
    confidence = "none"
    predicted_function = ""
    category = FunctionalCategory.UNKNOWN

    # Use LLM hypothesis if available (highest priority)
    if hypothesis and hypothesis.predicted_function:
        predicted_function = hypothesis.predicted_function
        if hypothesis.confidence_score >= 0.7:
            confidence = "high"
        elif hypothesis.confidence_score >= 0.4:
            confidence = "medium"
        else:
            confidence = "low"
        evidence_summary.append(f"AI synthesis: {hypothesis.predicted_function}")
        if hypothesis.suggested_category:
            cat_map = {
                "gene_expression": FunctionalCategory.GENE_EXPRESSION,
                "cell_membrane": FunctionalCategory.CELL_MEMBRANE,
                "metabolism": FunctionalCategory.METABOLISM,
                "genome_preservation": FunctionalCategory.GENOME_PRESERVATION,
            }
            category = cat_map.get(hypothesis.suggested_category, FunctionalCategory.PREDICTED)

    # Evidence from domains
    if domains:
        domain_names = [d.name for d in domains]
        evidence_summary.append(f"Conserved domains: {', '.join(domain_names)}")
        if not predicted_function:
            predicted_function = f"Contains domain(s): {domain_names[0]}"
            confidence = "medium"

    # Evidence from BLAST
    if blast_hits:
        best = blast_hits[0]
        if best.identity > 50:
            evidence_summary.append(
                f"Strong homolog: {best.description} ({best.organism}, "
                f"{best.identity}% identity, E={best.evalue:.1e})"
            )
            if "hypothetical" not in best.description.lower() and not predicted_function:
                predicted_function = best.description
                confidence = "high" if best.identity > 70 else "medium"
        elif best.identity > 30:
            evidence_summary.append(
                f"Distant homolog: {best.description} ({best.organism}, "
                f"{best.identity}% identity)"
            )
            if "hypothetical" not in best.description.lower() and not predicted_function:
                predicted_function = f"Possible: {best.description}"
                confidence = "low"

    # Evidence from protein properties
    if features.has_transmembrane:
        evidence_summary.append(f"Predicted {features.transmembrane_count} TM helix(es) — membrane protein")
        if not predicted_function:
            predicted_function = "Putative membrane protein"
            category = FunctionalCategory.CELL_MEMBRANE
            confidence = confidence or "low"

    if features.is_secreted:
        evidence_summary.append("Signal peptide detected — secreted/membrane-associated")
        if not predicted_function:
            predicted_function = "Putative secreted protein"
            category = FunctionalCategory.CELL_MEMBRANE
            confidence = confidence or "low"

    if features.molecular_weight < 10000:
        evidence_summary.append(f"Small protein ({features.molecular_weight/1000:.1f} kDa)")

    if features.disorder_pct > 50:
        evidence_summary.append(f"High disorder ({features.disorder_pct}%) — possible regulatory")

    if features.charged_residues_pct > 35:
        evidence_summary.append(f"Highly charged ({features.charged_residues_pct}%) — nucleic acid binding?")
        if not predicted_function:
            predicted_function = "Putative nucleic acid-binding protein"
            category = FunctionalCategory.GENE_EXPRESSION
            confidence = confidence or "low"

    # Count evidence sources with meaningful content
    sources_with_data = len([r for r in evidence_records if r.go_terms or r.categories or r.keywords])
    if sources_with_data > 0:
        evidence_summary.append(f"Evidence from {sources_with_data} independent source(s), convergence: {convergence_score:.3f}")

    # Convergence-based confidence override
    if convergence_score >= 0.5 and confidence in ("none", "low"):
        confidence = "medium"
    elif convergence_score >= 0.3 and confidence == "none":
        confidence = "low"

    # Infer category from text
    if predicted_function and category == FunctionalCategory.UNKNOWN:
        func_lower = predicted_function.lower()
        for cat, keywords in {
            FunctionalCategory.GENE_EXPRESSION: ["ribosom", "trna", "translation", "transcription", "polymerase"],
            FunctionalCategory.CELL_MEMBRANE: ["membrane", "transport", "permease", "lipid", "lipoprotein"],
            FunctionalCategory.METABOLISM: ["kinase", "synthas", "transferas", "hydrolase", "oxidoreductas"],
            FunctionalCategory.GENOME_PRESERVATION: ["dna", "repair", "recombinas", "replicat", "division"],
        }.items():
            if any(kw in func_lower for kw in keywords):
                category = cat
                break
        if category == FunctionalCategory.UNKNOWN and confidence != "none":
            category = FunctionalCategory.PREDICTED

    if not evidence_summary:
        evidence_summary.append("No homologs, domains, or distinguishing features found — truly unknown")

    # Build convergence result
    tier = classify_confidence_tier(convergence_score)
    convergence_result = ConvergenceResult(
        score=convergence_score,
        confidence_tier=tier,
        n_evidence_sources=len(evidence_records),
    )

    return FunctionalPrediction(
        locus_tag=gene.locus_tag,
        confidence=confidence,
        predicted_function=predicted_function,
        evidence_summary=evidence_summary,
        blast_hits=blast_hits,
        domain_hits=domains,
        protein_features=features,
        suggested_category=category,
        evidence=evidence_records,
        convergence=convergence_result,
        hypothesis=hypothesis,
    )


async def run_single_gene(
    locus_tag: str,
    protein_sequence: str,
    gene_name: str = "",
    product: str = "",
    http: httpx.AsyncClient | None = None,
) -> AsyncGenerator[PipelineEvent, None]:
    """Deep analysis of a single gene — all 5 phases, no tiering limits.

    Triggered when the user clicks an unknown gene in the genome view.
    Unlike the batch ``run()`` below, every phase runs at full depth.
    """
    gene = GenomeGene(
        locus_tag=locus_tag,
        protein_sequence=protein_sequence,
        protein_length=len(protein_sequence),
        gene_name=gene_name,
        product=product,
    )

    # --- Phase 1: Protein features (instant) ---
    yield PipelineEvent(
        stage="gene_analysis", status=StageStatus.RUNNING, progress=0.05,
        data={"message": "Phase 1/5: Analyzing protein properties...", "phase": 1, "locus_tag": locus_tag},
    )
    features = analyze_protein_features(protein_sequence)
    yield PipelineEvent(
        stage="gene_analysis", status=StageStatus.RUNNING, progress=0.10,
        data={"message": "Phase 1 complete: protein properties analyzed", "phase": 1, "locus_tag": locus_tag},
    )

    # --- Phase 2: CDD domain search + BLAST ---
    domains: list[DomainHit] = []
    blast_hits: list[BlastHit] = []
    if http:
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.12,
            data={"message": "Phase 2/5: Searching conserved domains (CDD)...", "phase": 2, "locus_tag": locus_tag},
        )
        try:
            domains = await search_cdd(http, protein_sequence)
        except Exception:
            pass
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.22,
            data={"message": f"Phase 2: CDD found {len(domains)} domain(s), running BLAST...", "phase": 2, "locus_tag": locus_tag},
        )
        try:
            blast_hits = await blast_search(http, protein_sequence)
        except Exception:
            pass
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.30,
            data={"message": f"Phase 2 complete: {len(domains)} domain(s), {len(blast_hits)} BLAST hit(s)", "phase": 2, "locus_tag": locus_tag},
        )

    # --- Phase 3: Multi-source evidence (InterPro, STRING, UniProt, literature) ---
    external: list[dict[str, Any]] = []
    if http:
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.32,
            data={"message": "Phase 3/5: Collecting evidence (InterPro, STRING, UniProt, literature)...", "phase": 3, "locus_tag": locus_tag},
        )
        try:
            external = await collect_evidence_for_gene(
                http,
                protein_seq=protein_sequence,
                gene_name=gene_name,
                product=product,
                locus_tag=locus_tag,
                run_interpro=True,
                run_string=True,
                run_uniprot=True,
                run_literature=True,
            )
        except Exception as e:
            logger.debug(f"Evidence collection failed for {locus_tag}: {e}")
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.60,
            data={"message": f"Phase 3 complete: {len(external)} external evidence source(s)", "phase": 3, "locus_tag": locus_tag},
        )

    # --- Phase 4: Normalization + convergence ---
    yield PipelineEvent(
        stage="gene_analysis", status=StageStatus.RUNNING, progress=0.62,
        data={"message": "Phase 4/5: Computing evidence convergence...", "phase": 4, "locus_tag": locus_tag},
    )
    evidence_records = _build_evidence_records(gene, features, domains, blast_hits, external)
    if len(evidence_records) >= 2:
        convergence_score = compute_convergence([r.payload for r in evidence_records])
    else:
        convergence_score = 0.0
    yield PipelineEvent(
        stage="gene_analysis", status=StageStatus.RUNNING, progress=0.70,
        data={"message": f"Phase 4 complete: convergence = {convergence_score:.3f}", "phase": 4, "locus_tag": locus_tag},
    )

    # --- Phase 5: LLM synthesis ---
    hypothesis: Hypothesis | None = None
    llm_available = bool(config.llm.anthropic_api_key or config.llm.openai_api_key)
    if llm_available and http and convergence_score > 0.05:
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.72,
            data={"message": "Phase 5/5: AI synthesis — generating hypothesis...", "phase": 5, "locus_tag": locus_tag},
        )
        try:
            prompt = llm_synthesis.build_evidence_prompt(
                locus_tag=locus_tag,
                product=product,
                protein_length=len(protein_sequence),
                evidence_list=[r.payload for r in evidence_records],
                convergence_score=convergence_score,
            )
            response = await llm_synthesis.synthesize(
                http, prompt, purpose="gene_synthesis", gene_locus_tag=locus_tag,
            )
            hypothesis = Hypothesis(
                predicted_function=llm_synthesis.extract_predicted_function(response),
                raw_response=response,
                confidence_score=llm_synthesis.extract_confidence(response),
                suggested_category=llm_synthesis.extract_category(response),
            )
        except Exception as e:
            logger.warning(f"LLM synthesis failed for {locus_tag}: {e}")
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.95,
            data={"message": "Phase 5 complete: hypothesis generated", "phase": 5, "locus_tag": locus_tag},
        )
    else:
        reason = "no API key configured" if not llm_available else "insufficient evidence"
        yield PipelineEvent(
            stage="gene_analysis", status=StageStatus.RUNNING, progress=0.95,
            data={"message": f"Phase 5/5: Skipped LLM synthesis ({reason})", "phase": 5, "locus_tag": locus_tag},
        )

    # --- Build final prediction ---
    prediction = synthesize_prediction(
        gene, features, domains, blast_hits, evidence_records, convergence_score, hypothesis,
    )
    prediction.prediction_source = "genelife"

    yield PipelineEvent(
        stage="gene_analysis",
        status=StageStatus.COMPLETED,
        progress=1.0,
        data=prediction.model_dump(),
    )


async def run(
    genome: GenomeRecord, http: httpx.AsyncClient
) -> AsyncGenerator[PipelineEvent, None]:
    """Full mystery gene analysis pipeline with evidence + convergence + LLM.

    Phase 1: Local protein analysis (all genes, instant)
    Phase 2: CDD domain search (first 10 genes)
    Phase 3: Multi-source evidence (InterPro, STRING, UniProt, lit — first 15 genes)
    Phase 4: Convergence scoring (all genes with evidence)
    Phase 5: LLM synthesis (top mystery genes by convergence)
    """
    unknown_genes = [
        g for g in genome.genes
        if g.functional_category == FunctionalCategory.UNKNOWN and g.protein_sequence
    ]

    total = len(unknown_genes)
    if total == 0:
        yield PipelineEvent(
            stage="functional_prediction",
            status=StageStatus.COMPLETED,
            data=GenomeFunctionalAnalysis().model_dump(),
            progress=1.0,
        )
        return

    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.0,
        data={"message": f"Analyzing {total} genes of unknown function — 5-phase evidence pipeline..."},
    )

    analysis = GenomeFunctionalAnalysis(total_analyzed=total)

    # Collect per-gene data
    gene_features: dict[str, ProteinFeatures] = {}
    gene_domains: dict[str, list[DomainHit]] = {}
    gene_blast: dict[str, list[BlastHit]] = {}
    gene_external: dict[str, list[dict]] = {}
    gene_evidence: dict[str, list[EvidenceRecord]] = {}
    gene_convergence: dict[str, float] = {}

    # --- Phase 1: Local protein analysis (instant, all genes) ---
    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.02,
        data={"message": "Phase 1/5: Analyzing protein properties...", "phase": 1},
    )

    for gene in unknown_genes:
        gene_features[gene.locus_tag] = analyze_protein_features(gene.protein_sequence)

    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.10,
        data={"message": f"Phase 1 complete: {total} proteins analyzed locally", "phase": 1},
    )

    # --- Phase 2: CDD domain search (first 10 genes, ~2-20s each) ---
    cdd_limit = min(total, 10)
    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.12,
        data={"message": f"Phase 2/5: CDD domain search ({cdd_limit} genes)...", "phase": 2},
    )

    for i, gene in enumerate(unknown_genes[:cdd_limit]):
        try:
            domains = await search_cdd(http, gene.protein_sequence)
            gene_domains[gene.locus_tag] = domains
        except Exception:
            gene_domains[gene.locus_tag] = []

        if (i + 1) % 3 == 0:
            yield PipelineEvent(
                stage="functional_prediction",
                status=StageStatus.RUNNING,
                progress=0.12 + (i + 1) / cdd_limit * 0.18,
                data={"message": f"Phase 2: CDD searched {i + 1}/{cdd_limit}", "phase": 2},
            )

    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.30,
        data={"message": f"Phase 2 complete: {cdd_limit} genes searched in CDD", "phase": 2},
    )

    # --- Phase 3: Multi-source evidence collection (first 15 genes) ---
    evidence_limit = min(total, 15)
    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.32,
        data={"message": f"Phase 3/5: Collecting evidence from InterPro, STRING, UniProt, literature ({evidence_limit} genes)...", "phase": 3},
    )

    for i, gene in enumerate(unknown_genes[:evidence_limit]):
        try:
            external = await collect_evidence_for_gene(
                http,
                protein_seq=gene.protein_sequence,
                gene_name=gene.gene_name,
                product=gene.product,
                locus_tag=gene.locus_tag,
                run_interpro=(i < 5),   # InterPro is slow — only first 5
                run_string=True,
                run_uniprot=True,
                run_literature=True,
            )
            gene_external[gene.locus_tag] = external
        except Exception as e:
            logger.debug(f"Evidence collection failed for {gene.locus_tag}: {e}")
            gene_external[gene.locus_tag] = []

        if (i + 1) % 3 == 0 or i == evidence_limit - 1:
            yield PipelineEvent(
                stage="functional_prediction",
                status=StageStatus.RUNNING,
                progress=0.32 + (i + 1) / evidence_limit * 0.28,
                data={"message": f"Phase 3: Evidence collected for {i + 1}/{evidence_limit} genes", "phase": 3},
            )

    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.60,
        data={"message": "Phase 3 complete: Multi-source evidence collected", "phase": 3},
    )

    # --- Phase 4: Normalization + Convergence scoring (all genes) ---
    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.62,
        data={"message": "Phase 4/5: Computing evidence convergence scores...", "phase": 4},
    )

    for gene in unknown_genes:
        tag = gene.locus_tag
        features = gene_features.get(tag, ProteinFeatures())
        domains = gene_domains.get(tag, [])
        blast = gene_blast.get(tag, [])
        external = gene_external.get(tag, [])

        evidence_records = _build_evidence_records(gene, features, domains, blast, external)
        gene_evidence[tag] = evidence_records

        # Compute convergence from evidence payloads
        if len(evidence_records) >= 2:
            payloads = [r.payload for r in evidence_records]
            gene_convergence[tag] = compute_convergence(payloads)
        else:
            gene_convergence[tag] = 0.0

    # Compute mean convergence
    conv_values = [v for v in gene_convergence.values() if v > 0]
    mean_conv = sum(conv_values) / len(conv_values) if conv_values else 0.0

    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.RUNNING,
        progress=0.70,
        data={
            "message": f"Phase 4 complete: Mean convergence {mean_conv:.3f} across {len(conv_values)} genes",
            "phase": 4,
            "mean_convergence": round(mean_conv, 3),
        },
    )

    # --- Phase 5: LLM synthesis (top mystery genes) ---
    llm_available = bool(config.llm.anthropic_api_key or config.llm.openai_api_key)
    max_synth = config.llm.max_synthesis_genes

    # Rank genes by convergence (higher = more evidence to synthesize from)
    ranked = sorted(
        unknown_genes,
        key=lambda g: gene_convergence.get(g.locus_tag, 0),
        reverse=True,
    )
    # Only synthesize genes that have meaningful evidence
    synth_candidates = [g for g in ranked if gene_convergence.get(g.locus_tag, 0) > 0.05][:max_synth]

    hypotheses: dict[str, Hypothesis] = {}

    if llm_available and synth_candidates:
        yield PipelineEvent(
            stage="functional_prediction",
            status=StageStatus.RUNNING,
            progress=0.72,
            data={
                "message": f"Phase 5/5: LLM synthesis for {len(synth_candidates)} top mystery genes...",
                "phase": 5,
            },
        )

        for i, gene in enumerate(synth_candidates):
            tag = gene.locus_tag
            try:
                prompt = llm_synthesis.build_evidence_prompt(
                    locus_tag=tag,
                    product=gene.product,
                    protein_length=gene.protein_length,
                    evidence_list=[r.payload for r in gene_evidence.get(tag, [])],
                    convergence_score=gene_convergence.get(tag, 0),
                )
                response = await llm_synthesis.synthesize(
                    http, prompt, purpose="gene_synthesis", gene_locus_tag=tag,
                )

                hypotheses[tag] = Hypothesis(
                    predicted_function=llm_synthesis.extract_predicted_function(response),
                    raw_response=response,
                    confidence_score=llm_synthesis.extract_confidence(response),
                    suggested_category=llm_synthesis.extract_category(response),
                )
            except Exception as e:
                logger.warning(f"LLM synthesis failed for {tag}: {e}")

            if (i + 1) % 2 == 0 or i == len(synth_candidates) - 1:
                yield PipelineEvent(
                    stage="functional_prediction",
                    status=StageStatus.RUNNING,
                    progress=0.72 + (i + 1) / len(synth_candidates) * 0.23,
                    data={
                        "message": f"Phase 5: Synthesized {i + 1}/{len(synth_candidates)} hypotheses",
                        "phase": 5,
                    },
                )
    else:
        if not llm_available:
            yield PipelineEvent(
                stage="functional_prediction",
                status=StageStatus.RUNNING,
                progress=0.95,
                data={
                    "message": "Phase 5/5: Skipped LLM synthesis (no API key configured)",
                    "phase": 5,
                },
            )

    # --- Build final predictions ---
    for gene in unknown_genes:
        tag = gene.locus_tag
        features = gene_features.get(tag, ProteinFeatures())
        domains = gene_domains.get(tag, [])
        blast = gene_blast.get(tag, [])
        evidence = gene_evidence.get(tag, [])
        convergence = gene_convergence.get(tag, 0.0)
        hyp = hypotheses.get(tag)

        prediction = synthesize_prediction(
            gene, features, domains, blast, evidence, convergence, hyp,
        )
        prediction.prediction_source = "genelife"
        analysis.predictions.append(prediction)

        # Update genome gene with prediction
        if prediction.suggested_category != FunctionalCategory.UNKNOWN:
            gene.functional_category = prediction.suggested_category
            gene.prediction_source = "genelife"
            gene.color = {
                FunctionalCategory.GENE_EXPRESSION: "#22d3ee",
                FunctionalCategory.CELL_MEMBRANE: "#a78bfa",
                FunctionalCategory.METABOLISM: "#34d399",
                FunctionalCategory.GENOME_PRESERVATION: "#60a5fa",
                FunctionalCategory.PREDICTED: "#fb923c",
            }.get(prediction.suggested_category, "#fb923c")

    # --- Include prior-knowledge predictions for genes already reclassified ---
    prior = get_prior_knowledge()
    predicted_genes = [
        g for g in genome.genes
        if g.functional_category == FunctionalCategory.PREDICTED and g.protein_sequence
    ]
    for gene in predicted_genes:
        pk = prior.get(gene.locus_tag)
        if pk:
            conf = "high" if pk.confidence_score >= 0.7 else "medium" if pk.confidence_score >= 0.4 else "low"
            tier = pk.tier if pk.tier in (1, 2, 3, 4) else 3
            is_curated = pk.source.startswith("curated:")
            source_label = "curated" if is_curated else "dnasyn"
            analysis.predictions.append(FunctionalPrediction(
                locus_tag=gene.locus_tag,
                confidence=conf,
                predicted_function=pk.proposed_function,
                prediction_source=source_label,
                evidence_summary=[
                    f"Source: {pk.source}",
                    f"Method: {pk.method}",
                    f"Evidence from {pk.evidence_count} source(s), convergence: {pk.convergence_score:.3f}",
                ],
                suggested_category=FunctionalCategory.PREDICTED,
                convergence=ConvergenceResult(
                    score=pk.convergence_score,
                    confidence_tier=tier,
                    n_evidence_sources=pk.evidence_count,
                ),
            ))

    # Summary
    for pred in analysis.predictions:
        cat = pred.suggested_category.value
        analysis.category_summary[cat] = analysis.category_summary.get(cat, 0) + 1

    analysis.total_analyzed = len(unknown_genes) + len(predicted_genes)
    analysis.mean_convergence = round(mean_conv, 3)
    analysis.genes_with_hypothesis = len(hypotheses)

    yield PipelineEvent(
        stage="functional_prediction",
        status=StageStatus.COMPLETED,
        progress=1.0,
        data=analysis.model_dump(),
    )
