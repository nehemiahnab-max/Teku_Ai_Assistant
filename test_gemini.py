import asyncio

from ai.gemini_service import GeminiService


async def main():

    gemini = GeminiService()

    response = await gemini.ask(
        "Jibu kwa Kiswahili: TEKU ni nini?"
    )

    print("\nGEMINI RESPONSE:")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
