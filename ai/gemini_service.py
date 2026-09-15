import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# PATHS & ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# GEMINI SERVICE
# ============================================================

class GeminiService:

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY haijapatikana kwenye .env"
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

        # Models za kujaribu kwa mpangilio
        self.models = [
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
        ]

        # Simple response cache
        self.cache = {}
        self.cache_max_size = 50


    # ========================================================
    # MAIN ASK METHOD
    # ========================================================

    async def ask_with_context(
        self,
        question: str,
        context: str = "",
    ) -> str:

        question = question.strip()

        if not question:
            return "Tafadhali andika swali lako."


        # ----------------------------------------------------
        # CACHE
        # ----------------------------------------------------

        cache_key = question.lower()

        if cache_key in self.cache:
            return self.cache[cache_key]


        # ----------------------------------------------------
        # SYSTEM / BEHAVIOR PROMPT
        # ----------------------------------------------------

        prompt = f"""
Wewe ni TEKU AI Assistant, msaidizi wa akili bandia
anayesaidia watumiaji kupata taarifa kuhusu
Teofilo Kisanji University (TEKU).

Jibu kwa Kiswahili fasaha, rahisi kueleweka,
cha moja kwa moja na cha kirafiki.

TUMIA CONTEXT iliyotolewa hapa chini kama chanzo
kikuu cha kujibu swali.

========================
KANUNI MUHIMU ZA MAJIBU
========================

1. Jibu swali moja kwa moja bila maneno mengi yasiyo
   ya lazima.

2. Usibuni taarifa ambazo hazipo kwenye context.

3. Kama taarifa haipatikani kwenye context, sema wazi
   kuwa taarifa hiyo haijapatikana kwenye taarifa
   nilizonazo.

4. Usirudie taarifa ileile ndani ya jibu.

5. Usiongeze hitimisho lisiloombwa.

6. USITAJE mwaka wa masomo kama hauhusiani moja kwa moja
   na swali la mtumiaji.

7. Usimalizie kila jibu kwa sentensi inayotaja
   "2026/2027".

8. Taja mwaka wa masomo PEKEE pale ambapo:
   - mtumiaji ameuliza mwaka fulani,
   - taarifa hiyo inategemea mwaka fulani,
   - ada inahusiana na mwaka fulani,
   - admission inahusiana na mwaka fulani,
   - academic calendar inahusiana na mwaka fulani,
   - au mwaka ni muhimu ili jibu liwe sahihi.

9. Kama swali halihitaji mwaka, usiuongeze.

10. Usiseme kila mwisho wa jibu:
    "Kwa mwaka wa masomo 2026/2027..."
    isipokuwa kama ni muhimu kwa swali.

11. Usiongeze disclaimer au taarifa zisizoombwa.

12. Kama mtumiaji anauliza kwa Kiingereza, unaweza kujibu
    kwa Kiingereza. Kama anauliza kwa Kiswahili, jibu
    kwa Kiswahili.

13. Kama swali linahitaji orodha, tumia bullet points.

14. Kama swali linahitaji hatua, tumia namba:
    1.
    2.
    3.

15. Dumisha majibu mafupi lakini yenye taarifa muhimu.

========================
CONTEXT
========================

{context}

========================
SWALI LA MTUMIAJI
========================

{question}

========================
JIBU
========================
"""

        # ----------------------------------------------------
        # TRY GEMINI MODELS
        # ----------------------------------------------------

        last_error = None

        for model in self.models:

            try:

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=prompt,
                )

                answer = getattr(
                    response,
                    "text",
                    None
                )

                if not answer:
                    continue

                answer = answer.strip()

                # ------------------------------------------------
                # CACHE RESPONSE
                # ------------------------------------------------

                if len(self.cache) >= self.cache_max_size:

                    oldest_key = next(
                        iter(self.cache)
                    )

                    del self.cache[oldest_key]

                self.cache[cache_key] = answer

                return answer

            except Exception as ex:

                last_error = ex

                print(
                    f"Gemini model {model} failed: {ex}"
                )

                continue


        # ----------------------------------------------------
        # ALL MODELS FAILED
        # ----------------------------------------------------

        if last_error:

            raise RuntimeError(
                "Huduma ya Gemini haikupatikana kwa sasa."
            ) from last_error

        raise RuntimeError(
            "Gemini haikutoa jibu."
        )