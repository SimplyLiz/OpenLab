"""Dagster asset: LLM hypothesis synthesis."""

from dagster import asset, AssetExecutionContext

from openlab.pipelines.resources import DatabaseResource
from openlab.pipelines.assets.homology import ncbi_blast, hmmer_search, hhpred_search
from openlab.pipelines.assets.structure import esmfold_structures, alphafold_structures, foldseek_search
from openlab.pipelines.assets.context import literature_search, eggnog_annotations, operon_predictions
from openlab.pipelines.assets.localization import deeptmhmm_topology, signalp_predictions
from openlab.pipelines.assets.local_homology import hhblits_search, prost_search
from openlab.pipelines.assets.synwiki_asset import synwiki_annotations


@asset(
    group_name="synthesis",
    kinds={"llm"},
    deps=[
        ncbi_blast, hmmer_search, hhpred_search,
        esmfold_structures, alphafold_structures, foldseek_search,
        literature_search, eggnog_annotations, operon_predictions,
        deeptmhmm_topology, signalp_predictions,
        hhblits_search, prost_search,
        synwiki_annotations,
    ],
)
def llm_hypothesis_synthesis(context: AssetExecutionContext, database: DatabaseResource):
    """LLM-based function prediction from all collected evidence."""
    from openlab.db.models.evidence import Evidence
    from openlab.db.models.gene import Gene
    from openlab.services import gene_service, hypothesis_service, llm_service
    from openlab.services.convergence import compute_convergence
    from openlab.services.llm_synthesis import build_evidence_prompt

    db = database.get_session()
    try:
        genes = gene_service.list_genes(db, unknown_only=True, limit=500)
        count = 0

        for gene in genes:
            existing = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
            if existing:
                continue

            evidence_rows = (
                db.query(Evidence)
                .filter(Evidence.gene_id == gene.gene_id)
                .order_by(Evidence.evidence_type)
                .all()
            )
            if not evidence_rows:
                continue

            evidence_list = [
                {"source": (ev.payload or {}).get("source", ev.source_ref or ""), **(ev.payload or {})}
                for ev in evidence_rows
            ]
            conv_score = compute_convergence(evidence_list)

            prompt = build_evidence_prompt(
                locus_tag=gene.locus_tag,
                product=gene.product or "hypothetical protein",
                protein_length=gene.length or 0,
                evidence_list=evidence_list,
                convergence_score=conv_score,
            )

            try:
                response = llm_service.synthesize(
                    prompt, purpose="dagster_synthesis", gene_locus_tag=gene.locus_tag,
                )

                import re
                conf_match = re.search(r"[Cc]onfidence[:\s]+(\d+\.?\d*)", response)
                confidence = float(conf_match.group(1)) if conf_match else 0.5
                if confidence > 1.0:
                    confidence /= 100.0

                evidence_ids = [ev.evidence_id for ev in evidence_rows]
                hypothesis_service.create_hypothesis(
                    db=db,
                    title=f"Predicted function for {gene.locus_tag}",
                    description=response,
                    confidence_score=confidence,
                    evidence_ids=evidence_ids,
                    gene_id=gene.gene_id,
                )
                count += 1
                context.log.info(f"Synthesized {gene.locus_tag}: conf={confidence:.2f}")

            except Exception as e:
                context.log.warning(f"Synthesis failed for {gene.locus_tag}: {e}")

        context.log.info(f"Total hypotheses created: {count}")
        return count

    finally:
        db.close()
