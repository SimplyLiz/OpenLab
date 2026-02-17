/**
 * ColonyRenderer — Pure canvas drawing functions for multi-cell colony view.
 * Renders a 2D grid of cells on a nutrient heatmap. Zero React dependencies.
 */

/**
 * Map a value from [min, max] range to a color gradient.
 * green (high nutrients) -> dark (depleted)
 */
function nutrientColor(value, maxVal) {
    const t = Math.min(1, Math.max(0, value / maxVal));
    const r = Math.floor(10 + t * 15);
    const g = Math.floor(14 + t * 60);
    const b = Math.floor(23 + t * 20);
    return `rgb(${r},${g},${b})`;
}

/**
 * Map growth rate to cell color: blue (slow) -> yellow (medium) -> red (fast).
 */
function growthRateColor(rate) {
    const t = Math.min(1, Math.max(0, rate * 5000));
    if (t < 0.5) {
        const s = t * 2;
        const r = Math.floor(96 * (1 - s) + 253 * s);
        const g = Math.floor(165 * (1 - s) + 224 * s);
        const b = Math.floor(250 * (1 - s) + 71 * s);
        return `rgb(${r},${g},${b})`;
    }
    const s = (t - 0.5) * 2;
    const r = Math.floor(253 * (1 - s) + 248 * s);
    const g = Math.floor(224 * (1 - s) + 113 * s);
    const b = Math.floor(71 * (1 - s) + 113 * s);
    return `rgb(${r},${g},${b})`;
}

/**
 * Draw the full colony view.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} w - canvas width
 * @param {number} h - canvas height
 * @param {object} snapshot - PopulationSnapshot
 * @param {number} t - animation time (seconds)
 */
export function drawColony(ctx, w, h, snapshot, t) {
    if (!snapshot || !snapshot.cells) return;

    const gridSize = snapshot.grid_size || 8;
    const padding = 40;
    const availW = w - padding * 2;
    const availH = h - padding * 2 - 40; // leave room for info
    const cellSize = Math.min(availW / gridSize, availH / gridSize);
    const gridW = cellSize * gridSize;
    const gridH = cellSize * gridSize;
    const offsetX = (w - gridW) / 2;
    const offsetY = (h - gridH) / 2 - 15;

    // 1. Draw nutrient heatmap background
    const field = snapshot.nutrient_field;
    if (field && field.length > 0) {
        for (let r = 0; r < gridSize; r++) {
            for (let c = 0; c < gridSize; c++) {
                const val = field[r] ? field[r][c] || 0 : 0;
                ctx.fillStyle = nutrientColor(val, 5.0);
                ctx.fillRect(
                    offsetX + c * cellSize,
                    offsetY + r * cellSize,
                    cellSize,
                    cellSize
                );
            }
        }
    }

    // 2. Draw grid lines
    ctx.strokeStyle = "rgba(255,255,255,0.04)";
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= gridSize; i++) {
        ctx.beginPath();
        ctx.moveTo(offsetX + i * cellSize, offsetY);
        ctx.lineTo(offsetX + i * cellSize, offsetY + gridH);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(offsetX, offsetY + i * cellSize);
        ctx.lineTo(offsetX + gridW, offsetY + i * cellSize);
        ctx.stroke();
    }

    // 3. Draw cells
    for (const cell of snapshot.cells) {
        const cx = offsetX + cell.col * cellSize + cellSize / 2;
        const cy = offsetY + cell.row * cellSize + cellSize / 2;
        const radiusBase = cellSize * 0.35;
        const volumeScale = Math.pow(cell.volume / 0.05, 1 / 3);
        const radius = Math.min(radiusBase * volumeScale, cellSize * 0.45);

        // Cell body
        const wobble = Math.sin(t * 2 + cell.cell_id * 1.7) * 1.5;
        ctx.beginPath();
        ctx.arc(cx + wobble * 0.3, cy, radius, 0, Math.PI * 2);
        ctx.fillStyle = growthRateColor(cell.growth_rate);
        ctx.globalAlpha = 0.85;
        ctx.fill();

        // Membrane
        ctx.beginPath();
        ctx.arc(cx + wobble * 0.3, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(100,255,218,0.4)";
        ctx.lineWidth = 1;
        ctx.globalAlpha = 1;
        ctx.stroke();

        // Generation number inside
        if (radius > 8) {
            ctx.fillStyle = "rgba(255,255,255,0.7)";
            ctx.font = `${Math.max(8, Math.floor(radius * 0.6))}px JetBrains Mono, monospace`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(String(cell.generation), cx + wobble * 0.3, cy);
        }

        // Mutation dots around membrane
        if (cell.mutation_count > 0) {
            const dotCount = Math.min(cell.mutation_count, 6);
            for (let i = 0; i < dotCount; i++) {
                const angle = (i / dotCount) * Math.PI * 2 + t * 0.5;
                const dx = Math.cos(angle) * (radius + 3);
                const dy = Math.sin(angle) * (radius + 3);
                ctx.beginPath();
                ctx.arc(cx + wobble * 0.3 + dx, cy + dy, 1.5, 0, Math.PI * 2);
                ctx.fillStyle = "#fb923c";
                ctx.globalAlpha = 0.8;
                ctx.fill();
            }
        }
    }

    ctx.globalAlpha = 1;

    // 4. Info overlay
    const infoY = h - 30;
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    const timeH = (snapshot.time / 3600).toFixed(1);
    ctx.fillText(
        `t = ${timeH}h    cells = ${snapshot.total_cells}    gen = ${snapshot.generations_max}    mutations = ${snapshot.total_mutations}`,
        w / 2,
        infoY
    );

    // 5. Nutrient legend
    const legendY = h - 12;
    const legendW = 100;
    const legendX = w / 2 - legendW / 2;
    for (let i = 0; i < legendW; i++) {
        ctx.fillStyle = nutrientColor((i / legendW) * 5, 5);
        ctx.fillRect(legendX + i, legendY, 1, 6);
    }
    ctx.fillStyle = "#64748b";
    ctx.font = "8px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("0", legendX - 8, legendY + 5);
    ctx.textAlign = "right";
    ctx.fillText("5mM", legendX + legendW + 16, legendY + 5);
    ctx.textAlign = "center";
    ctx.fillText("glucose", w / 2, legendY + 14);
}
