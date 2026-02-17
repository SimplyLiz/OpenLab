"""Static HTML report generator with color-coded genome map.

Generates a self-contained HTML file summarizing genome annotation status,
evidence coverage, and hypothesis confidence.

Usage:
    python report.py [output.html]
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from biolab.db.engine import get_session_factory
from biolab.db.models.evidence import Evidence
from biolab.db.models.gene import Gene
from biolab.db.models.hypothesis import Hypothesis
from sqlalchemy import func


def generate_report(output_path: str = "report.html"):
    """Generate a static HTML report."""
    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        genes = db.query(Gene).order_by(Gene.start).all()
        total_genes = len(genes)
        total_evidence = db.query(Evidence).count()
        total_hypotheses = db.query(Hypothesis).count()
        graduated = sum(1 for g in genes if g.graduated_at is not None)

        ev_counts = dict(
            db.query(Evidence.gene_id, func.count())
            .group_by(Evidence.gene_id)
            .all()
        )

        ev_by_source = dict(
            db.query(Evidence.source_ref, func.count())
            .group_by(Evidence.source_ref)
            .all()
        )

        genome_size = max((g.end for g in genes), default=543000)

        # Build gene data for visualization
        gene_data = []
        for g in genes:
            ev_count = ev_counts.get(g.gene_id, 0)
            product = g.product or "hypothetical protein"

            if g.graduated_at:
                color = "#2ecc71"
                status = "graduated"
            elif ev_count >= 5:
                color = "#3498db"
                status = "evidence-rich"
            elif ev_count > 0:
                color = "#f39c12"
                status = "partial"
            elif "hypothetical" in product.lower():
                color = "#e74c3c"
                status = "unknown"
            else:
                color = "#95a5a6"
                status = "annotated"

            gene_data.append({
                "locus_tag": g.locus_tag,
                "name": g.name or "",
                "product": product,
                "start": g.start,
                "end": g.end,
                "strand": g.strand,
                "evidence_count": ev_count,
                "color": color,
                "status": status,
                "proposed_function": g.proposed_function or "",
            })

        gene_json = json.dumps(gene_data)

        report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BioLab Genome Report</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: #0e1117; color: #fafafa; }}
    .header {{ text-align: center; margin-bottom: 30px; }}
    .metrics {{ display: flex; gap: 20px; justify-content: center; margin: 20px 0; }}
    .metric {{ background: #1a1f2e; padding: 20px; border-radius: 8px; text-align: center; min-width: 150px; }}
    .metric .value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
    .metric .label {{ color: #888; font-size: 0.9em; }}
    .genome-map {{ width: 100%; height: 60px; background: #1a1f2e; border-radius: 8px; position: relative; overflow: hidden; margin: 20px 0; }}
    .gene-block {{ position: absolute; height: 100%; cursor: pointer; transition: opacity 0.2s; }}
    .gene-block:hover {{ opacity: 0.8; }}
    .tooltip {{ display: none; position: fixed; background: #2a2f3e; padding: 10px; border-radius: 6px; z-index: 1000; font-size: 0.85em; max-width: 300px; }}
    .legend {{ display: flex; gap: 15px; justify-content: center; margin: 10px 0; }}
    .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 0.85em; }}
    .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #2a2f3e; }}
    th {{ background: #1a1f2e; color: #888; }}
    .source-bar {{ display: flex; gap: 5px; margin: 20px 0; flex-wrap: wrap; }}
    .source-chip {{ background: #1a1f2e; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="header">
    <h1>BioLab Genome Report</h1>
    <p>JCVI-syn3A Functional Annotation Status</p>
</div>

<div class="metrics">
    <div class="metric"><div class="value">{total_genes}</div><div class="label">Genes</div></div>
    <div class="metric"><div class="value">{total_evidence}</div><div class="label">Evidence</div></div>
    <div class="metric"><div class="value">{total_hypotheses}</div><div class="label">Hypotheses</div></div>
    <div class="metric"><div class="value">{graduated}</div><div class="label">Graduated</div></div>
</div>

<h2>Genome Map</h2>
<div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#2ecc71"></div> Graduated</div>
    <div class="legend-item"><div class="legend-dot" style="background:#3498db"></div> Evidence-rich</div>
    <div class="legend-item"><div class="legend-dot" style="background:#f39c12"></div> Partial</div>
    <div class="legend-item"><div class="legend-dot" style="background:#e74c3c"></div> Unknown</div>
    <div class="legend-item"><div class="legend-dot" style="background:#95a5a6"></div> Annotated</div>
</div>
<div class="genome-map" id="genomeMap"></div>
<div class="tooltip" id="tooltip"></div>

<h2>Evidence Sources</h2>
<div class="source-bar">
{''.join(f'<div class="source-chip">{html.escape(src or "unknown")}: {cnt}</div>' for src, cnt in sorted(ev_by_source.items(), key=lambda x: -(x[1] or 0)))}
</div>

<script>
const genes = {gene_json};
const genomeSize = {genome_size};
const map = document.getElementById('genomeMap');
const tooltip = document.getElementById('tooltip');

genes.forEach(g => {{
    const block = document.createElement('div');
    block.className = 'gene-block';
    block.style.left = (g.start / genomeSize * 100) + '%';
    block.style.width = Math.max(0.2, (g.end - g.start) / genomeSize * 100) + '%';
    block.style.backgroundColor = g.color;
    block.style.top = g.strand === 1 ? '0' : '50%';
    block.style.height = '50%';

    block.addEventListener('mouseenter', (e) => {{
        tooltip.style.display = 'block';
        tooltip.innerHTML = '<b>' + g.locus_tag + '</b><br>' +
            g.product + '<br>' +
            'Evidence: ' + g.evidence_count + '<br>' +
            (g.proposed_function ? 'Proposed: ' + g.proposed_function : '');
    }});
    block.addEventListener('mousemove', (e) => {{
        tooltip.style.left = (e.clientX + 10) + 'px';
        tooltip.style.top = (e.clientY + 10) + 'px';
    }});
    block.addEventListener('mouseleave', () => {{
        tooltip.style.display = 'none';
    }});

    map.appendChild(block);
}});
</script>
</body>
</html>"""

        Path(output_path).write_text(report_html)
        print(f"Report generated: {output_path}")

    finally:
        db.close()


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "report.html"
    generate_report(output)
