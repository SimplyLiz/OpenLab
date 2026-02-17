"""Export threads as RO-Crate 1.1 JSON-LD or plain JSON-LD."""

from __future__ import annotations

from typing import Any


def export_ro_crate(thread_data: dict[str, Any]) -> dict[str, Any]:
    """Export a thread as RO-Crate 1.1 JSON-LD.

    RO-Crate spec: https://www.researchobject.org/ro-crate/1.1/
    """
    return {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@type": "CreativeWork",
                "@id": "ro-crate-metadata.json",
                "about": {"@id": "./"},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            },
            {
                "@type": "Dataset",
                "@id": "./",
                "name": thread_data.get("title", "Research Thread"),
                "description": thread_data.get("summary", ""),
                "identifier": str(thread_data.get("thread_id", "")),
                "dateCreated": str(thread_data.get("created_at", "")),
                "hasPart": [
                    {"@id": "#dossier"},
                    {"@id": "#claims"},
                    {"@id": "#provenance"},
                ],
            },
            {
                "@type": "CreativeWork",
                "@id": "#dossier",
                "name": f"Gene Dossier: {thread_data.get('gene_symbol', '')}",
                "about": {
                    "@type": "Gene",
                    "name": thread_data.get("gene_symbol", ""),
                },
            },
            {
                "@type": "ItemList",
                "@id": "#claims",
                "name": "Research Claims",
                "numberOfItems": len(thread_data.get("claims_snapshot", []) or []),
                "itemListElement": [
                    {
                        "@type": "Claim",
                        "text": c.get("claim_text", ""),
                        "confidence": c.get("confidence", 0.0),
                    }
                    for c in (thread_data.get("claims_snapshot", []) or [])
                ],
            },
            {
                "@type": "ItemList",
                "@id": "#provenance",
                "name": "Provenance Chain",
                "numberOfItems": len(thread_data.get("evidence_snapshot", []) or []),
            },
        ],
    }


def export_json_ld(thread_data: dict[str, Any]) -> dict[str, Any]:
    """Export a thread as plain JSON-LD."""
    return {
        "@context": {
            "@vocab": "https://schema.org/",
            "gene": "https://identifiers.org/ncbigene/",
            "claim": "https://schema.org/Claim",
        },
        "@type": "ScholarlyArticle",
        "@id": f"thread:{thread_data.get('thread_id', '')}",
        "name": thread_data.get("title", ""),
        "description": thread_data.get("summary", ""),
        "about": {
            "@type": "Gene",
            "name": thread_data.get("gene_symbol", ""),
        },
        "dateCreated": str(thread_data.get("created_at", "")),
        "claims": thread_data.get("claims_snapshot", []),
    }
