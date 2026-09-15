# ============================================================
# TEKU AI ASSISTANT
# RAG SERVICE
# ============================================================

import os
from pathlib import Path
import re
import json

import numpy as np
from dotenv import load_dotenv
from google import genai


# ============================================================
# PATHS & ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"
VECTOR_DIR = BASE_DIR / "data" / "vector_store"

load_dotenv(ENV_FILE)


# ============================================================
# CONFIGURATION
# ============================================================

EMBEDDING_MODEL = "gemini-embedding-001"

TOP_K = 3
CANDIDATE_K = 20
MIN_SCORE = 0.35


# ============================================================
# RAG SERVICE
# ============================================================

class RAGService:

    def __init__(self):

        # ----------------------------------------------------
        # Load Gemini API key
        # ----------------------------------------------------

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY haijapatikana kwenye .env"
            )

        # ----------------------------------------------------
        # Gemini client
        # ----------------------------------------------------

        self.client = genai.Client(
            api_key=api_key
        )

        # ----------------------------------------------------
        # Vector store files
        # ----------------------------------------------------

        self.embeddings_path = (
            VECTOR_DIR / "embeddings.npy"
        )

        self.chunks_path = (
            VECTOR_DIR / "chunks.json"
        )

        # ----------------------------------------------------
        # Validate files
        # ----------------------------------------------------

        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                f"Embeddings file haipo: "
                f"{self.embeddings_path}"
            )

        if not self.chunks_path.exists():
            raise FileNotFoundError(
                f"Chunks file haipo: "
                f"{self.chunks_path}"
            )

        # ----------------------------------------------------
        # Load embeddings
        # ----------------------------------------------------

        self.embeddings = np.load(
            self.embeddings_path
        )

        # ----------------------------------------------------
        # Load chunks
        # ----------------------------------------------------

        with open(
            self.chunks_path,
            "r",
            encoding="utf-8"
        ) as f:

            self.chunks = json.load(f)

        # ----------------------------------------------------
        # Validate vector/chunk count
        # ----------------------------------------------------

        if len(self.embeddings) != len(self.chunks):

            raise ValueError(
                "Idadi ya embeddings na chunks "
                "hazilingani. "
                f"Embeddings={len(self.embeddings)}, "
                f"Chunks={len(self.chunks)}"
            )

        # ----------------------------------------------------
        # Normalize embeddings
        # ----------------------------------------------------

        self.embeddings = self._normalize(
            self.embeddings
        )


    # ========================================================
    # NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize(vectors):

        vectors = np.asarray(
            vectors,
            dtype=np.float32
        )

        norms = np.linalg.norm(
            vectors,
            axis=1,
            keepdims=True
        )

        norms[norms == 0] = 1

        return vectors / norms


    # ========================================================
    # CREATE QUERY EMBEDDING
    # ========================================================

    async def embed_query(self, text):

        if not text or not text.strip():

            raise ValueError(
                "Swali la mtumiaji haliwezi kuwa tupu."
            )

        result = await self.client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text.strip(),
        )

        if not result.embeddings:

            raise RuntimeError(
                "Gemini haikurudisha embedding."
            )

        vector = np.array(
            result.embeddings[0].values,
            dtype=np.float32,
        )

        norm = np.linalg.norm(vector)

        if norm == 0:

            raise RuntimeError(
                "Query embedding ina zero norm."
            )

        vector = vector / norm

        return vector


    # ========================================================
    # INTENT DETECTION
    # ========================================================

    def _detect_intent(self, query):

        q = query.lower().strip()

        # ----------------------------------------------------
        # Fees
        # ----------------------------------------------------

        if any(
            x in q
            for x in [
                "ada",
                "fee",
                "fees",
                "gharama",
                "malipo",
                "tuition",
                "cost",
                "pay",
                "bei",
            ]
        ):

            return "fee"


        # ----------------------------------------------------
        # Admission
        # ----------------------------------------------------

        if any(
            x in q
            for x in [
                "admission",
                "kuomba",
                "application",
                "apply",
                "udahili",
                "joining",
                "join",
            ]
        ):

            return "admission"


        # ----------------------------------------------------
        # Programmes
        # ----------------------------------------------------

        if any(
            x in q
            for x in [
                "course",
                "programme",
                "program",
                "kozi",
                "masomo",
                "bachelor",
                "diploma",
                "degree",
            ]
        ):

            return "programme"


        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        if any(
            x in q
            for x in [
                "wapi",
                "location",
                "mahali",
                "ipo",
                "anwani",
                "address",
                "located",
            ]
        ):

            return "location"


        # ----------------------------------------------------
        # Registration
        # ----------------------------------------------------

        if any(
            x in q
            for x in [
                "registration",
                "usajili",
                "jisajili",
                "register",
            ]
        ):

            return "registration"


        # ----------------------------------------------------
        # Calendar
        # ----------------------------------------------------

        if any(
            x in q
            for x in [
                "calendar",
                "semester",
                "academic year",
                "mwaka wa masomo",
                "academic calendar",
            ]
        ):

            return "calendar"


        # ----------------------------------------------------
        # Identity
        # ----------------------------------------------------

        if any(
            x in q
            for x in [
                "teku",
                "teofilo kisanji",
                "chuo",
                "university",
            ]
        ):

            return "identity"


        return "general"


    # ========================================================
    # KEYWORDS
    # ========================================================

    def _keywords(self, query):

        words = re.findall(
            r"[a-zA-Z0-9]+",
            query.lower()
        )

        stopwords = {
            "na",
            "ni",
            "ya",
            "wa",
            "za",
            "kwa",
            "katika",
            "hii",
            "hicho",
            "hivi",
            "hapo",
            "the",
            "is",
            "of",
            "to",
            "a",
            "an",
            "and",
            "or",
            "in",
            "on",
            "what",
            "how",
            "where",
            "can",
            "i",
            "are",
            "do",
            "does",
            "does",
        }

        return {
            word
            for word in words
            if len(word) > 2
            and word not in stopwords
        }


    # ========================================================
    # RERANK RESULTS
    # ========================================================

    def _rerank(self, query, candidates):

        intent = self._detect_intent(
            query
        )

        keywords = self._keywords(
            query
        )

        ranked = []

        intent_words = {

            "fee": [
                "fee",
                "fees",
                "ada",
                "tuition",
                "cost",
                "malipo",
                "gharama",
            ],

            "admission": [
                "admission",
                "application",
                "apply",
                "joining",
                "udahili",
            ],

            "programme": [
                "programme",
                "program",
                "course",
                "kozi",
                "bachelor",
                "degree",
                "diploma",
            ],

            "location": [
                "location",
                "mbeya",
                "address",
                "mahali",
            ],

            "identity": [
                "university",
                "teku",
                "teofilo",
                "kisanji",
                "chuo",
            ],

            "registration": [
                "registration",
                "register",
                "usajili",
                "jisajili",
            ],

            "calendar": [
                "calendar",
                "semester",
                "academic",
                "mwaka",
            ],
        }


        for item in candidates:

            chunk = item["chunk"]

            metadata = chunk.get(
                "metadata",
                {}
            )

            text = chunk.get(
                "text",
                ""
            )

            section = str(
                metadata.get(
                    "section"
                ) or ""
            )

            content_type = str(
                metadata.get(
                    "content_type"
                ) or ""
            )

            combined = (
                f"{text} "
                f"{section} "
                f"{content_type}"
            ).lower()


            # ------------------------------------------------
            # Original similarity score
            # ------------------------------------------------

            similarity = float(
                item.get(
                    "similarity",
                    item.get("score", 0.0)
                )
            )

            score = similarity


            # ------------------------------------------------
            # Keyword boost
            # ------------------------------------------------

            keyword_hits = sum(
                1
                for keyword in keywords
                if keyword in combined
            )

            score += min(
                keyword_hits * 0.025,
                0.15
            )


            # ------------------------------------------------
            # Intent boost
            # ------------------------------------------------

            for word in intent_words.get(
                intent,
                []
            ):

                if word in combined:

                    score += 0.02


            # ------------------------------------------------
            # Penalize table of contents
            # ------------------------------------------------

            if metadata.get(
                "is_contents"
            ):

                score -= 0.10


            # ------------------------------------------------
            # Penalize glossary
            # ------------------------------------------------

            if metadata.get(
                "is_glossary"
            ):

                score -= 0.05


            # ------------------------------------------------
            # Store both fields
            # ------------------------------------------------

            item["similarity"] = similarity
            item["score"] = score

            ranked.append(item)


        # ----------------------------------------------------
        # Sort highest score first
        # ----------------------------------------------------

        ranked.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return ranked[:TOP_K]


    # ========================================================
    # SEARCH KNOWLEDGE BASE
    # ========================================================

    async def search(self, query):

        if not query or not query.strip():

            return []


        # ----------------------------------------------------
        # Embed query
        # ----------------------------------------------------

        query_vector = await self.embed_query(
            query
        )


        # ----------------------------------------------------
        # Cosine similarity
        # ----------------------------------------------------

        similarities = (
            self.embeddings @ query_vector
        )


        # ----------------------------------------------------
        # Select candidates
        # ----------------------------------------------------

        candidate_indices = np.argsort(
            similarities
        )[
            -CANDIDATE_K:
        ][::-1]


        candidates = []


        # ----------------------------------------------------
        # Build candidate list
        # ----------------------------------------------------

        for index in candidate_indices:

            similarity = float(
                similarities[index]
            )

            candidates.append({

                "chunk": self.chunks[index],

                # Original vector similarity
                "similarity": similarity,

                # Keep score for compatibility
                "score": similarity,
            })


        # ----------------------------------------------------
        # Rerank
        # ----------------------------------------------------

        ranked = self._rerank(
            query,
            candidates
        )


        # ----------------------------------------------------
        # Minimum score filtering
        # ----------------------------------------------------

        results = [

            result

            for result in ranked

            if result["score"] >= MIN_SCORE

        ]


        return results[:TOP_K]


    # ========================================================
    # BUILD GEMINI CONTEXT
    # ========================================================

    def build_context(self, results):

        if not results:

            return (
                "Hakuna taarifa inayohusiana "
                "iliyopatikana kwenye "
                "TEKU Knowledge Base."
            )


        sections = []


        for i, result in enumerate(
            results,
            start=1
        ):

            chunk = result["chunk"]

            metadata = chunk.get(
                "metadata",
                {}
            )


            page = metadata.get(
                "page",
                "N/A"
            )

            section = metadata.get(
                "section",
                "N/A"
            )

            year = metadata.get(
                "academic_year",
                "N/A"
            )

            source_type = metadata.get(
                "source_type",
                "N/A"
            )


            text = chunk.get(
                "text",
                ""
            ).strip()


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


        return "\n\n".join(
            sections
        )


    # ========================================================
    # GET SOURCES
    # ========================================================

    def get_sources(self, results):

        sources = []


        for result in results:

            chunk = result["chunk"]

            metadata = chunk.get(
                "metadata",
                {}
            )


            source = {

                "page": metadata.get(
                    "page"
                ),

                "section": metadata.get(
                    "section"
                ),

                "academic_year": metadata.get(
                    "academic_year"
                ),

                "source_type": metadata.get(
                    "source_type"
                ),

            }


            if source not in sources:

                sources.append(
                    source
                )


        return sources