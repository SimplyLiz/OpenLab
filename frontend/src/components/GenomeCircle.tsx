import { useRef, useEffect, useCallback } from "react";
import { useGeneStore } from "../store";
import { useGeneAnalysis } from "../hooks/useGeneAnalysis";

const CATEGORY_COLORS: Record<string, string> = {
  gene_expression: "#22d3ee",
  cell_membrane: "#a78bfa",
  metabolism: "#34d399",
  genome_preservation: "#60a5fa",
  predicted: "#fb923c",
  unknown: "#f87171",
};

const CATEGORY_LABELS: Record<string, string> = {
  gene_expression: "Gene Expression",
  cell_membrane: "Cell Membrane",
  metabolism: "Metabolism",
  genome_preservation: "Genome Preservation",
  predicted: "Predicted Function",
  unknown: "Unknown Function",
};

export function GenomeCircle() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { genome, selectedGene, selectGene, essentiality, predictions } = useGeneStore();
  const { analyzeGene } = useGeneAnalysis();

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !genome) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(cx, cy) - 80;
    const geneWidth = 18;

    // Clear
    ctx.fillStyle = "#0a0e17";
    ctx.fillRect(0, 0, w, h);

    // Draw backbone circle
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw genes as arcs
    for (const gene of genome.genes) {
      const startAngle = (gene.start / genome.genome_length) * Math.PI * 2 - Math.PI / 2;
      const endAngle = (gene.end / genome.genome_length) * Math.PI * 2 - Math.PI / 2;

      const isSelected = selectedGene?.locus_tag === gene.locus_tag;
      const r = gene.strand === 1 ? radius + geneWidth / 2 + 2 : radius - geneWidth / 2 - 2;

      ctx.beginPath();
      ctx.arc(cx, cy, r, startAngle, endAngle);
      ctx.strokeStyle = isSelected ? "#ffffff" : (gene.color || CATEGORY_COLORS[gene.functional_category] || "#888");
      ctx.lineWidth = isSelected ? geneWidth + 4 : geneWidth;
      ctx.globalAlpha = isSelected ? 1.0 : gene.functional_category === "unknown" ? 0.9 : 0.7;
      ctx.stroke();
      ctx.globalAlpha = 1.0;
    }

    // Center text
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "bold 18px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const orgName = genome.organism.replace("Synthetic Mycoplasma mycoides ", "");
    ctx.fillText(orgName, cx, cy - 30);

    ctx.font = "13px Inter, sans-serif";
    ctx.fillStyle = "#94a3b8";
    ctx.fillText(`${genome.genome_length.toLocaleString()} bp`, cx, cy - 8);
    ctx.fillText(`${genome.total_genes} genes`, cx, cy + 12);

    ctx.font = "12px Inter, sans-serif";
    ctx.fillStyle = "#f87171";
    ctx.fillText(`${genome.genes_unknown} unknown`, cx, cy + 32);

    // Essentiality inner ring
    if (essentiality) {
      const essRadius = radius - 36;
      for (const gene of genome.genes) {
        const startAngle = (gene.start / genome.genome_length) * Math.PI * 2 - Math.PI / 2;
        const endAngle = (gene.end / genome.genome_length) * Math.PI * 2 - Math.PI / 2;
        const isEssential = essentiality.predictions[gene.locus_tag] ?? true;

        ctx.beginPath();
        ctx.arc(cx, cy, essRadius, startAngle, endAngle);
        ctx.strokeStyle = isEssential ? "#f87171" : "#334155";
        ctx.lineWidth = 6;
        ctx.globalAlpha = isEssential ? 0.7 : 0.3;
        ctx.stroke();
        ctx.globalAlpha = 1.0;
      }
    }

    // Tick marks every 50kb
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1;
    ctx.font = "9px JetBrains Mono, monospace";
    ctx.fillStyle = "#64748b";
    for (let pos = 0; pos < genome.genome_length; pos += 50000) {
      const angle = (pos / genome.genome_length) * Math.PI * 2 - Math.PI / 2;
      const x1 = cx + Math.cos(angle) * (radius - 30);
      const y1 = cy + Math.sin(angle) * (radius - 30);
      const x2 = cx + Math.cos(angle) * (radius - 25);
      const y2 = cy + Math.sin(angle) * (radius - 25);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      const lx = cx + Math.cos(angle) * (radius - 42);
      const ly = cy + Math.sin(angle) * (radius - 42);
      ctx.fillText(`${pos / 1000}k`, lx, ly);
    }

    // Legend
    const legendX = 15;
    let legendY = h - 15 - Object.keys(CATEGORY_COLORS).length * 20;
    for (const [cat, color] of Object.entries(CATEGORY_COLORS)) {
      ctx.fillStyle = color;
      ctx.fillRect(legendX, legendY, 12, 12);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "11px Inter, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(CATEGORY_LABELS[cat] ?? cat, legendX + 18, legendY + 10);
      legendY += 20;
    }
  }, [genome, selectedGene, essentiality]);

  useEffect(() => {
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [draw]);

  // Click detection
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!genome || !canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cx = rect.width / 2;
      const cy = rect.height / 2;
      const radius = Math.min(cx, cy) - 80;

      // Convert click to angle
      const dx = x - cx;
      const dy = y - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < radius - 30 || dist > radius + 30) {
        selectGene(null);
        return;
      }

      let angle = Math.atan2(dy, dx) + Math.PI / 2;
      if (angle < 0) angle += Math.PI * 2;
      const clickPos = (angle / (Math.PI * 2)) * genome.genome_length;

      // Find gene at this position
      const hit = genome.genes.find(
        (g) => clickPos >= g.start && clickPos <= g.end
      );
      selectGene(hit ?? null);

      // Auto-trigger deep analysis for unknown genes without existing predictions
      if (hit && hit.functional_category === "unknown" && hit.protein_sequence) {
        const existing = predictions.get(hit.locus_tag);
        const needsAnalysis = !existing || existing.evidence.length <= 1;
        if (needsAnalysis) {
          analyzeGene(hit);
        }
      }
    },
    [genome, selectGene, analyzeGene, predictions]
  );

  return (
    <canvas
      ref={canvasRef}
      className="genome-circle-canvas"
      onClick={handleClick}
      style={{ width: "100%", height: "600px", cursor: "pointer" }}
    />
  );
}
