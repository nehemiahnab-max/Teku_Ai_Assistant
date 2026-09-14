# ai/rag_service.py

import os
from pathlib import Path
import re
import json
import numpy as np
from dotenv import load_dotenv
from google import genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = BASE_DIR / "data" / "vector_store"

EMBEDDING_MODEL = "gemini-embedding-001"

TOP_K = 3
CANDIDATE_K = 20
MIN_SCORE = 0.35


class RAGService:
    def __init__(self):
        self.client = genai.Client()

        self.embeddings_path = VECTOR_DIR / "embeddings.npy"
        self.chunks_path = VECTOR_DIR / "chunks.json"

        self.embeddings = np.load(self.embeddings_path)

        with open(self.chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        self.embeddings = self._normalize(self.embeddings)

    @staticmethod
    def _normalize(vectors):
        vectors = np.asarray(vectors, dtype=np.float32)

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1

        return vectors / norms

    async def embed_query(self, text):
        result = await self.client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )

        vector = np.array(
            result.embeddings[0].values,
            dtype=np.float32,
        )

        vector = vector / max(np.linalg.norm(vector), 1e-12)

        return vector

    def _detect_intent(self, query):
        q = query.lower()

        if any(x in q for x in [
            "ada", "fee", "fees", "gharama", "malipo",
            "tuition", "cost"
        ]):
            return "fee"

        if any(x in q for x in [
            "admission", "kuomba", "application",
            "apply", "udahili", "joining"
        ]):
            return "admission"

        if any(x in q for x in [
            "course", "programme", "program", "kozi",
            "masomo", "bachelor", "diploma", "degree"
        ]):
            return "programme"

        if any(x in q for x in [
            "wapi", "location", "mahali", "ipo", "anwani"
        ]):
            return "location"

        if any(x in q for x in [
            "registration", "usajili", "jisajili"
        ]):
            return "registration"

        if any(x in q for x in [
            "calendar", "semester", "academic year",
            "mwaka wa masomo"
        ]):
            return "calendar"

        if any(x in q for x in [
            "teku", "teofilo kisanji", "chuo"
        ]):
            return "identity"

        return "general"

    def _keywords(self, query):
        words = re.findall(r"[a-zA-Z0-9]+", query.lower())

        stopwords = {
            "na", "ni", "ya", "wa", "za", "kwa", "katika",
            "hii", "hicho", "hivi", "the", "is", "of", "to",
            "a", "an", "and", "or", "in", "on", "what",
            "how", "where", "can", "i"
        }

        return {
            word for word in words
            if len(word) > 2 and word not in stopwords
        }

    def _rerank(self, query, candidates):
        intent = self._detect_intent(query)
        keywords = self._keywords(query)

        ranked = []

        for item in candidates:
            chunk = item["chunk"]
            metadata = chunk.get("metadata", {})

            text = chunk.get("text", "")
            section = str(metadata.get("section") or "")
            content_type = str(metadata.get("content_type") or "")

            combined = f"{text} {section} {content_type}".lower()

            keyword_hits = sum(
                1 for keyword in keywords
                if keyword in combined
            )

            score = float(item["score"])

            # Small keyword boost
            score += min(keyword_hits * 0.025, 0.15)

            # Intent-specific boost
            intent_words = {
                "fee": [
                    "fee", "fees", "ada", "tuition",
                    "cost", "malipo"
                ],
                "admission": [
                    "admission", "application",
                    "joining", "udahili"
                ],
                "programme": [
                    "programme", "program", "course",
                    "bachelor", "degree", "diploma"
                ],
                "location": [
                    "location", "mbeya", "address"
                ],
                "identity": [
                    "university", "university", "teku",
                    "teofilo"
                ],
            }

            for word in intent_words.get(intent, []):
                if word in combined:
                    score += 0.02

            # Penalize contents / glossary chunks
            if metadata.get("is_contents"):
                score -= 0.10

            if metadata.get("is_glossary"):
                score -= 0.05

            item["score"] = score
            ranked.append(item)

        ranked.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return ranked[:TOP_K]

    async def search(self, query):
        query_vector = await self.embed_query(query)

        similarities = self.embeddings @ query_vector

        candidate_indices = np.argsort(
            similarities
        )[-CANDIDATE_K:][::-1]

        candidates = []

        for index in candidate_indices:
            score = float(similarities[index])

            candidates.append({
                "chunk": self.chunks[index],
                "score": score,
            })

        ranked = self._rerank(query, candidates)

        return [
            result
            for result in ranked
            if result["score"] >= MIN_SCORE
        ][:TOP_K]

    def build_context(self, results):
        if not results:
            return (
                "Hakuna taarifa inayohusiana iliyopatikana "
                "kwenye TEKU Knowledge Base."
            )

        sections = []

        for i, result in enumerate(results, start=1):
            chunk = result["chunk"]
            metadata = chunk.get("metadata", {})

            page = metadata.get("page", "N/A")
            section = metadata.get("section", "N/A")
            year = metadata.get("academic_year", "N/A")
            source_type = metadata.get("source_type", "N/A")

            text = chunk.get("text", "").strip()

            sections.append(
                f"""
SOURCE {i}
Page: {page}
Section: {section}
Academic Year: {year}
Source Type: {source_type}

{text}
""".strip()
            )

        return "\n\n".join(sections)

    def get_sources(self, results):
        sources = []

        for result in results:
            chunk = result["chunk"]
            metadata = chunk.get("metadata", {})

            source = {
                "page": metadata.get("page"),
                "section": metadata.get("section"),
                "academic_year": metadata.get("academic_year"),
                "source_type": metadata.get("source_type"),
            }

            if source not in sources:
                sources.append(source)

        return sources