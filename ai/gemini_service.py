# ai/gemini_service.py

import os
from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY haijapatikana kwenye .env"
            )

        self.client = genai.Client(api_key=api_key)

        self.models = [
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
        ]

    async def ask_with_context(self, question, context):
        prompt = f"""
Wewe ni TEKU Assistant, msaidizi rasmi wa taarifa
za Teofilo Kisanji University (TEKU).

JIBU KWA KISWAHILI isipokuwa mtumiaji ametumia Kiingereza.

MUHIMU SANA:
1. Tumia taarifa zilizopo kwenye TEKU Knowledge Base
   kama chanzo kikuu cha ukweli.
2. Usibuni taarifa ambazo hazipo kwenye context.
3. Kama taarifa haipo, sema wazi kuwa haijapatikana
   kwenye TEKU Knowledge Base.
4. Kwa taarifa zinazobadilika kama ada, admission,
   deadlines na academic year, taja mwaka husika
   kama umeonekana kwenye source.
5. Usidai kuwa taarifa ni ya sasa kabisa kama source
   haijathibitisha hilo.
6. Jibu kwa ufupi lakini kwa msaada.
7. Usirudie swali la mtumiaji bila sababu lakini pia;
- Usidai kuwa una taarifa fulani ikiwa huna ushahidi wa kutosha.
- hifadhie maadili ya TEKU na usiingie kwenye mazungumzo yasiyo ya heshima au yasiyo ya kimaadili.
- tunza mazungumzo ya awali na usisahau muktadha wa mazungumzo ya awali.
- uko chinii ya usimamizi wa TEKU, hivyo usijaribu kutoa maoni binafsi au ya kisiasa.
- umetengenezwa na mwanachuo wa Teku aitwae 'Nehemiah Alelneh Aloyce' wa computer science.


TEKU KNOWLEDGE BASE:
--------------------
{context}
--------------------

SWALI LA MTUMIAJI:
{question}

Toa jibu bora sasa.
"""

        last_error = None

        for model in self.models:
            try:
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                )

                text = getattr(response, "text", None)

                if text:
                    return text.strip()

            except Exception as error:
                last_error = error
                print(
                    f"Gemini model failed: {model} -> {error}"
                )
                continue

        # Safe fallback
        if context and "Hakuna taarifa" not in context:
            return (
                "Samahani, huduma ya AI haipatikani kwa sasa. "
                "Tafadhali jaribu tena baada ya muda mfupi."
            )

        if last_error:
            print("Gemini final error:", last_error)

        return (
            "Samahani, sijaweza kupata jibu kwa sasa. "
            "Tafadhali jaribu tena."
        )