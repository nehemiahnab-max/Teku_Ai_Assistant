import asyncio
from ai.gemini_service import GeminiService


async def main():
    gemini = GeminiService()
    response = await gemini.ask_with_context(
        question="TEKU ni nini?",
        context="TEKU ni Teofilo Kisanji University.",
    )
    print("\nGEMINI RESPONSE:\n")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())