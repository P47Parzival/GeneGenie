"""Gene knowledge-graph lookup (Week 4).

Loads the prebuilt knowledge_graph.json (gene -> diseases/drugs/pathways/stats)
into memory and serves gene nodes. Built by app.build_kg from ClinVar + Reactome
+ curated drug associations.
"""

from __future__ import annotations

import json
from pathlib import Path


class KnowledgeGraph:
    def __init__(self, path: Path | None):
        self.path = Path(path) if path else None
        self._genes: dict[str, dict] = {}
        self._loaded = False

    def load(self) -> None:
        if self.path and self.path.exists():
            with open(self.path) as fh:
                payload = json.load(fh)
            self._genes = payload.get("genes", {})
            self._loaded = True

    @property
    def available(self) -> bool:
        return self._loaded and bool(self._genes)

    @property
    def gene_count(self) -> int:
        return len(self._genes)

    def get_gene(self, symbol: str) -> dict | None:
        if not self._genes:
            return None
        # Case-insensitive symbol match (gene symbols are conventionally upper).
        node = self._genes.get(symbol) or self._genes.get(symbol.upper())
        return node
