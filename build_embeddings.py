import json
import asyncio
from pathlib import Path

import numpy as np
from google import genai
from dotenv import load_dotenv


# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

API_KEY = __import__("os").getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY haijawekwa kwenye .env")

client = genai.Client(api_key=API_KEY)

INPUT_FILE = Path("data/processed/teku_chunks.json")
OUTPUT_DIR = Path("data/vector_store")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = "gemini-embedding-001"


# ==========================================
# EMBEDDING FUNCTION
# ==========================================

async def create_embedding(text: str):

    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )

    return response.embeddings[0].values


# ==========================================
# MAIN
# ==========================================

async def main():

    print("========================================")
    print("TEKU VECTOR STORE BUILDER")
    print("========================================")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"File haipo: {INPUT_FILE}"
        )

    chunks = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    print(f"Chunks found : {len(chunks)}")
    print(f"Embedding model : {EMBEDDING_MODEL}")
    print("----------------------------------------")

    embeddings = []

    for index, chunk in enumerate(chunks, start=1):

        print(
            f"[{index}/{len(chunks)}] "
            f"Embedding page {chunk['page']}..."
        )

        try:

            vector = await create_embedding(
                chunk["text"]
            )

            embeddings.append(vector)

        except Exception as error:

            print(
                f"ERROR kwenye chunk {index}: {error}"
            )

            # Stop immediately rather than creating
            # an incomplete vector store.
            raise

        # Small delay to reduce API pressure
        await asyncio.sleep(0.15)

    # ======================================
    # SAVE VECTORS
    # ======================================

    vectors = np.array(
        embeddings,
        dtype=np.float32
    )

    np.save(
        OUTPUT_DIR / "embeddings.npy",
        vectors
    )

    # Save chunks separately
    (OUTPUT_DIR / "chunks.json").write_text(
        json.dumps(
            chunks,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # ======================================
    # INFO
    # ======================================

    print("----------------------------------------")
    print("VECTOR STORE BUILD COMPLETE")
    print("----------------------------------------")

    print(f"Vectors : {vectors.shape}")
    print(
        f"Embeddings : {OUTPUT_DIR / 'embeddings.npy'}"
    )
    print(
        f"Chunks     : {OUTPUT_DIR / 'chunks.json'}"
    )

    print("========================================")


if __name__ == "__main__":
    asyncio.run(main())
