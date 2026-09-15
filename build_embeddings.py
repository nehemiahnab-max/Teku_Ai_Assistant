from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

INPUT_FILE = BASE_DIR / "data" / "processed" / "teku_chunks.json"
OUTPUT_DIR = BASE_DIR / "data" / "vector_store"
EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 8
MAX_RETRIES = 3


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY haijapatikana kwenye .env")
    return genai.Client(api_key=api_key)


async def embed_batch(client: genai.Client, texts: list[str]) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await asyncio.to_thread(
                client.models.embed_content,
                model=EMBEDDING_MODEL,
                contents=texts,
            )
            embeddings = getattr(response, "embeddings", None)
            if not embeddings or len(embeddings) != len(texts):
                raise ValueError("Gemini ilirudisha idadi isiyolingana ya embeddings.")
            return [list(item.values) for item in embeddings]
        except Exception as error:
            last_error = error
            print(f"Batch attempt {attempt}/{MAX_RETRIES} failed: {error}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"Embedding batch imeshindikana: {last_error}")


async def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"File haipo: {INPUT_FILE}")

    chunks = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    if not chunks:
        raise ValueError("teku_chunks.json haina chunks.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = get_client()
    embeddings: list[list[float]] = []

    print("=" * 50)
    print("TEKU VECTOR STORE BUILDER")
    print("=" * 50)
    print(f"Chunks : {len(chunks)}")
    print(f"Model  : {EMBEDDING_MODEL}")

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]
        batch_vectors = await embed_batch(client, texts)
        embeddings.extend(batch_vectors)
        print(f"Embedded {len(embeddings)}/{len(chunks)}")

    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.ndim != 2 or len(vectors) != len(chunks):
        raise ValueError(f"Vector store shape si sahihi: {vectors.shape}")

    np.save(OUTPUT_DIR / "embeddings.npy", vectors)
    (OUTPUT_DIR / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 50)
    print("VECTOR STORE BUILD COMPLETE")
    print(f"Vectors : {vectors.shape}")
    print(f"Saved   : {OUTPUT_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())