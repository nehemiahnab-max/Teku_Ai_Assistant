import asyncio

from ai.rag_service import RAGService
from ai.gemini_service import GeminiService


async def main():

    print("=" * 70)
    print("TEKU RAG + GEMINI INTEGRATION TEST")
    print("=" * 70)

    # Load RAG
    rag = RAGService()

    # Load Gemini
    gemini = GeminiService()

    question = "Ada ya BSc Computer Science ni kiasi gani?"

    print(f"\nUSER QUESTION:")
    print(question)

    print("\nSearching TEKU Knowledge Base...")

    results = await rag.search(question)

    if not results:
        print("\nHakuna RAG results zilizopatikana.")
        return

    print(f"\nRAG RESULTS: {len(results)}")

    for i, result in enumerate(results, start=1):

        chunk = result["chunk"]
        metadata = chunk.get("metadata", {})

        print("\n" + "-" * 70)
        print(f"RESULT {i}")
        print(f"Score      : {result['score']:.4f}")
        print(f"Similarity : {result['similarity']:.4f}")
        print(f"Page       : {metadata.get('page')}")
        print(f"Section    : {metadata.get('section')}")
        print(f"Academic   : {metadata.get('academic_year')}")

    # Build context
    context = rag.build_context(results)

    print("\n")
    print("=" * 70)
    print("SENDING CONTEXT TO GEMINI...")
    print("=" * 70)

    answer = await gemini.ask_with_context(
        question=question,
        context=context,
    )

    print("\n")
    print("=" * 70)
    print("GEMINI ANSWER")
    print("=" * 70)

    print(answer)

    print("\n")
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
