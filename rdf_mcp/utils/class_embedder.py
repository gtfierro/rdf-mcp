from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from txtai import Embeddings


class ClassEmbedder:
    """Indexes instances of one or more classes and exposes semantic lookup."""

    def __init__(
        self,
        graph: Graph,
        class_types: Sequence[URIRef | str],
        properties: Sequence[URIRef | str],
        embeddings_config: Optional[dict] = None,
        include_fallback_label: bool = True,
    ) -> None:
        self.graph = graph
        self.class_types = [self._to_uri(term) for term in class_types]
        self.properties = [self._to_uri(term) for term in properties]
        self.include_fallback_label = include_fallback_label
        self.embeddings = Embeddings(**(embeddings_config or {}))
        self._index()

    def _index(self) -> None:
        rows = []
        for subject in self._iter_subjects():
            text = self._build_text(subject)
            if not text:
                continue
            rows.append((str(subject), text))
        self.embeddings.index(rows)

    def _iter_subjects(self) -> Iterable[URIRef]:
        subjects = set()
        for class_type in self.class_types:
            for subject in self.graph.subjects(RDF.type, class_type):
                subjects.add(subject)
        return sorted(subjects, key=lambda term: str(term))

    def _build_text(self, subject: URIRef) -> str:
        parts: list[str] = []
        for predicate in self.properties:
            for obj in self.graph.objects(subject, predicate):
                value = self._term_to_text(obj)
                if value:
                    parts.append(value)

        if not parts and self.include_fallback_label:
            label = self.graph.value(subject=subject, predicate=RDFS.label)
            if label:
                parts.append(str(label))
            else:
                fallback = self._local_name(subject)
                if fallback:
                    parts.append(fallback)

        if not parts:
            return ""

        seen = set()
        deduped = []
        for value in parts:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return " ".join(deduped).strip()

    def _term_to_text(self, term) -> str:
        if isinstance(term, Literal):
            return str(term)
        if isinstance(term, URIRef):
            label = self.graph.value(subject=term, predicate=RDFS.label)
            if label:
                return str(label)
            return self._local_name(term)
        return str(term)

    def _local_name(self, term) -> str:
        value = str(term)
        if "#" in value:
            return value.rsplit("#", 1)[-1]
        if "/" in value:
            return value.rsplit("/", 1)[-1]
        return value

    def get(self, query: str, k: int = 5) -> Tuple[list[URIRef], list[float]]:
        results = self.embeddings.search(query, k)
        classes: list[URIRef] = []
        scores: list[float] = []
        for result in results:
            if isinstance(result, dict):
                rid = result.get("id")
                score = result.get("score")
            else:
                rid, score = result
            if rid is None:
                continue
            classes.append(URIRef(rid))
            scores.append(float(score))
        return classes, scores

    def close(self) -> None:
        if hasattr(self.embeddings, "close"):
            self.embeddings.close()

    @staticmethod
    def _to_uri(term: URIRef | str) -> URIRef:
        if isinstance(term, URIRef):
            return term
        if isinstance(term, str):
            return URIRef(term)
        return term
