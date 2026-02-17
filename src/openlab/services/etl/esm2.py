"""ESM-2 protein embedding and kNN function prediction — from DNAView.

Optional: gated by ENABLE_ESM2 config flag. Requires torch + transformers.
"""

import asyncio
import logging

import numpy as np

logger = logging.getLogger(__name__)


def _compute_embeddings_sync(
    sequences: dict[str, str],
    model_name: str = "facebook/esm2_t6_8M_UR50D",
    batch_size: int = 8,
) -> dict[str, list[float]]:
    """Compute ESM-2 embeddings (synchronous, runs in thread pool)."""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
    except ImportError:
        logger.warning("torch/transformers not installed; ESM-2 disabled")
        return {}

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    embeddings = {}
    tags = list(sequences.keys())

    for i in range(0, len(tags), batch_size):
        batch_tags = tags[i:i + batch_size]
        batch_seqs = [sequences[t][:1022] for t in batch_tags]

        inputs = tokenizer(batch_seqs, return_tensors="pt", padding=True,
                           truncation=True, max_length=1024)

        with torch.no_grad():
            outputs = model(**inputs)

        mask = inputs["attention_mask"].unsqueeze(-1).expand(outputs.last_hidden_state.size()).float()
        summed = torch.sum(outputs.last_hidden_state * mask, 1)
        counts = torch.clamp(mask.sum(1), min=1e-9)
        means = summed / counts

        for j, tag in enumerate(batch_tags):
            embeddings[tag] = means[j].numpy().tolist()

    return embeddings


def _predict_knn_sync(
    query_emb: dict[str, list[float]],
    ref_emb: dict[str, list[float]],
    ref_functions: dict[str, str],
    k: int = 5,
    threshold: float = 0.5,
) -> dict[str, dict]:
    """Predict functions via kNN in embedding space."""
    from sklearn.neighbors import NearestNeighbors

    ref_tags = list(ref_emb.keys())
    ref_matrix = np.array([ref_emb[t] for t in ref_tags])

    nn = NearestNeighbors(n_neighbors=min(k, len(ref_tags)), metric="cosine")
    nn.fit(ref_matrix)

    predictions = {}
    for tag, emb in query_emb.items():
        distances, indices = nn.kneighbors([emb])
        func_weights: dict[str, float] = {}
        for dist, idx in zip(distances[0], indices[0]):
            func = ref_functions.get(ref_tags[idx], "unknown")
            weight = 1.0 / (1.0 + dist)
            func_weights[func] = func_weights.get(func, 0) + weight

        if not func_weights:
            continue
        total = sum(func_weights.values())
        best = max(func_weights, key=func_weights.get)  # type: ignore[arg-type]
        conf = func_weights[best] / total
        if conf >= threshold:
            predictions[tag] = {
                "predictedFunction": best,
                "confidence": round(conf, 3),
                "distance": round(float(distances[0][0]), 4),
            }
    return predictions


async def run_esm2_predictions(
    reference_seqs: dict[str, str],
    reference_functions: dict[str, str],
    query_seqs: dict[str, str],
) -> dict[str, dict]:
    """Run full ESM-2 pipeline in a thread pool."""
    all_seqs = {**reference_seqs, **query_seqs}
    embeddings = await asyncio.to_thread(_compute_embeddings_sync, all_seqs)
    if not embeddings:
        return {}

    ref_emb = {k: v for k, v in embeddings.items() if k in reference_seqs}
    query_emb = {k: v for k, v in embeddings.items() if k in query_seqs}

    return await asyncio.to_thread(_predict_knn_sync, query_emb, ref_emb, reference_functions)
