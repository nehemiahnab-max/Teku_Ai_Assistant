import flet as ft
from pathlib import Path
import asyncio
import importlib
import threading
import os
import tempfile

from dotenv import load_dotenv

try:
    sd = importlib.import_module("sounddevice")
except (ImportError, OSError):
    sd = None

try:
    sf = importlib.import_module("soundfile")
except (ImportError, OSError):
    sf = None

try:
    from google import genai
except ImportError:
    genai = None

from ai.gemini_service import GeminiService
from ai.rag_service import RAGService
from database.chat_database import ChatDatabase


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

LOGO = "assets/icons/teku_logo.jpg"
PROFILE = "assets/icons/images3.jpeg"
BACKGROUND = "assets/images/teku_background.jpeg"
BUILDING = "assets/images/teku_building.jpeg"


# ============================================================
# APP
# ============================================================
def main(page: ft.Page):

    gemini = GeminiService()
    rag = RAGService()
    db = ChatDatabase()
    page.title = "TEKU Assistant"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#F7F9FC"
    page.theme_mode = ft.ThemeMode.LIGHT

    # --------------------------------------------------------
    # THEME COLORS
    # --------------------------------------------------------

    state = {
        "dark": False
    }

    LIGHT = {
        "background": "#F7F9FC",
        "surface": "#FFFFFF",
        "surface2": "#F1F4F7",
        "text": "#172033",
        "muted": "#6B7280",
        "border": "#E2E7EF",
        "green": "#087F5B",
        "green_dark": "#056B4C",
        "assistant_bubble": "#FFFFFF",
    }

    DARK = {
        "background": "#0D1117",
        "surface": "#161B22",
        "surface2": "#21262D",
        "text": "#F0F6FC",
        "muted": "#8B949E",
        "border": "#30363D",
        "green": "#20C997",
        "green_dark": "#12A879",
        "assistant_bubble": "#161B22",
    }

    def C(name):
        return (DARK if state["dark"] else LIGHT)[name]

    # --------------------------------------------------------
    # CHAT LIST
    # --------------------------------------------------------

    chat_list = ft.ListView(
        expand=True,
        spacing=16,
        auto_scroll=True,
        padding=20,
    )

    # --------------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------------

    chat_history = db.get_chats()

    current_chat = {
        "id": None,
        "title": "New Chat",
        "messages": []
    }

    selected_upload = {
        "path": None,
        "name": None,
    }

    voice_state = {
        "recording": False,
        "stream": None,
        "frames": [],
        "path": None,
    }

    def show_snack(message):
        try:
            page.snack_bar = ft.SnackBar(content=ft.Text(message))
            page.snack_bar.open = True
            page.update()
        except Exception as error:
            print("SNACKBAR ERROR:", error)

    def save_current_chat():

        if not current_chat["messages"]:
            return

        if current_chat["id"] is None:
            current_chat["id"] = db.create_chat(current_chat["title"])
            for message in current_chat["messages"]:
                db.add_message(
                    current_chat["id"],
                    message["role"],
                    message["text"],
                )
        else:
            db.update_chat(
                current_chat["id"],
                current_chat["title"],
            )

        chat_history.clear()
        chat_history.extend(db.get_chats())

        # Messages tayari zimehifadhiwa wakati zinaongezwa.

    def history_item(chat):
        return ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=C("surface") if chat["id"] == current_chat["id"] else None,
            ink=True,
            on_click=lambda e, chat_id=chat["id"]: open_history(chat_id),
            content=ft.Row(
                spacing=9,
                controls=[
                    ft.Icon(
                        ft.Icons.CHAT_BUBBLE_OUTLINE,
                        size=17,
                        color=C("muted"),
                    ),
                    ft.Text(
                        chat["title"],
                        size=13,
                        color=C("text"),
                        overflow=ft.TextOverflow.ELLIPSIS,
                        expand=True,
                    ),
                ],
            ),
        )

    def open_history(chat_id):
        nonlocal current_chat
        selected = next((x for x in chat_history if x["id"] == chat_id), None)
        if not selected:
            return
        messages = db.get_messages(chat_id)
        current_chat = {
            "id": selected["id"],
            "title": selected["title"],
            "messages": list(messages),
        }

        chat_list.controls.clear()

        for message in current_chat["messages"]:
            if message["role"] == "user":
                add_user_message(message["text"], save=False)
            else:
                add_bot_message(message["text"], save=False)

        refresh_ui()

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    message_input = ft.TextField(
        hint_text="Andika ujumbe wako hapa...",
        border=ft.InputBorder.NONE,
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=5,
        content_padding=10,
    )

    # --------------------------------------------------------
    # WELCOME
    # --------------------------------------------------------

    def welcome_view():

        return ft.Container(
            expand=True,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                controls=[
                    ft.Container(
                        width=170,
                        height=115,
                        border_radius=22,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        content=ft.Image(
                            src=BUILDING,
                            width=170,
                            height=115,
                            fit=ft.BoxFit.COVER,
                        ),
                    ),

                    ft.Container(height=18),

                    ft.Text(
                        "Karibu TEKU Assistant 👋",
                        size=30,
                        weight=ft.FontWeight.BOLD,
                        color=C("text"),
                        text_align=ft.TextAlign.CENTER,
                    ),

                    ft.Container(height=8),

                    ft.Text(
                        "Nipo hapa kukusaidia. Andika ujumbe wako kuanza.",
                        size=14,
                        color=C("muted"),
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    # --------------------------------------------------------
    # USER MESSAGE
    # --------------------------------------------------------

    def add_user_message(text, save=True):

        if save:
            current_chat["messages"].append({"role": "user", "text": text})

            if current_chat["id"] is None:
                current_chat["id"] = db.create_chat(current_chat["title"])

            db.add_message(current_chat["id"], "user", text)

        bubble = ft.Container(
            padding=ft.Padding.symmetric(
                horizontal=16,
                vertical=12,
            ),
            border_radius=18,
            bgcolor=C("green"),
            content=ft.Text(
                text,
                size=15,
                color="#FFFFFF",
            ),
        )

        row = ft.Row(
            alignment=ft.MainAxisAlignment.END,
            controls=[
                ft.Container(
                    content=bubble,
                    width=min(max(len(text) * 7, 120), 520),
                )
            ],
        )

        chat_list.controls.append(row)

    # --------------------------------------------------------
    # BOT MESSAGE
    # --------------------------------------------------------

    def add_bot_message(
            text,
            save=True,
            sources=None,
            ):
        if sources is None:
            sources = []

            source_controls = []

        if sources:

            source_controls.append(
                ft.Container(
                 content=ft.Text(
                    "📚 Vyanzo vya TEKU",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=C("muted"),
                    ),
                  margin=ft.Margin.only(
                    top=8,
                    bottom=3,
                    ),
                )
            )

        for source in sources:

            page_number = source.get(
                "page",
                "N/A",
            )

            year = source.get(
                "academic_year",
                None,
            )

            if year:
                label = (
                    f"• TEKU Knowledge Base — "
                    f"Page {page_number} ({year})"
                )
            else:
                label = (
                    f"• TEKU Knowledge Base — "
                    f"Page {page_number}"
                )

            source_controls.append(
                ft.Text(
                    label,
                    size=10,
                    color=C("muted"),
                )
            )

        message_content = ft.Column(
            controls=[
                ft.Markdown(
                    text,
                    selectable=True,
                    extension_set="gitHubWeb",),
            *source_controls,
        ],
        spacing=2,
         )

        bubble = ft.Container(
            content=message_content,
            padding=ft.Padding.symmetric(
                 horizontal=14,
                vertical=10,
            ),
            border_radius=16,
            bgcolor=C("assistant_bubble"),
        )

        row = ft.Row(
            controls=[
                ft.Container(
                    content=bubble,
                    width=700,
            )
        ],
        alignment=ft.MainAxisAlignment.START,
         )

        chat_list.controls.append(row)

        if save and current_chat["id"]:

            db.add_message(
                current_chat["id"],
                "assistant",
                 text,
            )

    page.update()

    # --------------------------------------------------------
    # TYPING INDICATOR
    # --------------------------------------------------------

    def show_typing():

        typing = ft.Row(
            controls=[
                ft.Container(
                    width=36,
                    height=36,
                    border_radius=18,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Image(
                        src=LOGO,
                        width=36,
                        height=36,
                        fit=ft.BoxFit.COVER,
                    ),
                ),
                ft.Container(
                    padding=12,
                    bgcolor=C("surface2"),
                    border_radius=18,
                    content=ft.Row(
                        spacing=4,
                        controls=[
                            ft.Text("●", color=C("muted")),
                            ft.Text("●", color=C("muted")),
                            ft.Text("●", color=C("muted")),
                        ],
                    ),
                ),
            ],
        )

        chat_list.controls.append(typing)
        page.update()

        return typing

    # --------------------------------------------------------
    # SEND
    # --------------------------------------------------------

    async def delayed_response(typing, text):
        try:
            # ====================================================
            # 1. SEARCH TEKU KNOWLEDGE BASE
            # ====================================================

            results = await rag.search(text)

            # ====================================================
            # 2. BUILD CONTEXT
            # ====================================================

            if results:
                context = rag.build_context(results)
                sources = rag.get_sources(results)
            else:
                context = (
                    "Hakuna taarifa inayohusiana iliyopatikana "
                    "kwenye TEKU Knowledge Base."
                )
                sources = []
            # ====================================================
            # 3. SEND QUESTION + CONTEXT TO GEMINI
            # ====================================================

            response = await gemini.ask_with_context(
                question=text,
                context=context,
            )

            # ====================================================
            # 4. REMOVE TYPING INDICATOR
            # ====================================================

            if typing in chat_list.controls:
                chat_list.controls.remove(typing)

            # ====================================================
            # 5. SHOW RESPONSE
            # ====================================================

            add_bot_message(response, sources=sources)
                
            # ====================================================
            # 6. DEBUG INFORMATION
            # ====================================================

            print("\n" + "=" * 70)
            print("TEKU RAG SEARCH")
            print("=" * 70)
            print(f"Question: {text}")
            print(f"Results : {len(results)}")

            for i, result in enumerate(results, start=1):
                metadata = result["chunk"].get("metadata", {})

                print(
                    f"{i}. "
                    f"Page={metadata.get('page')} | "
                    f"Score={result['score']:.4f} | "
                    f"Section={metadata.get('section')}"
                )

            print("=" * 70)

        except Exception as error:
            if typing in chat_list.controls:
                chat_list.controls.remove(typing)

            add_bot_message(
                "Samahani, nimepata tatizo wakati wa "
                "kutafuta taarifa au kuwasiliana na huduma ya AI. "
                "Tafadhali jaribu tena."
            )

            print("\nTEKU ASSISTANT ERROR:")
            print(error)

        page.update()

    def send_message(e=None):

        text = message_input.value.strip()

        if not text:
            return

        if selected_upload["name"]:
            uploaded_name = selected_upload["name"]
            if text.startswith("📎 "):
                text = (
                    f"Nimeambatisha file: {uploaded_name}. "
                    "Tafadhali nisaidie kulielewa."
                )
            else:
                text = f"{text}\n\n📎 File: {uploaded_name}"

            selected_upload["path"] = None
            selected_upload["name"] = None

        # Remove welcome screen.
        if len(chat_list.controls) == 1:
            chat_list.controls.clear()

        if not current_chat["messages"]:
            current_chat["title"] = text[:32] + ("..." if len(text) > 32 else "")

        add_user_message(text)

        message_input.value = ""

        typing = show_typing()

        page.run_task(
            delayed_response,
            typing,
            text,
        )

        page.update()

    message_input.on_submit = send_message

    # --------------------------------------------------------
    # CHAT MANAGEMENT
    # --------------------------------------------------------

    def new_chat(e=None):
        save_current_chat()

        current_chat["id"] = None
        current_chat["title"] = "New Chat"
        current_chat["messages"] = []

        chat_list.controls.clear()
        chat_list.controls.append(welcome_view())
        refresh_ui()

    def clear_current_chat(e=None):
        current_chat["messages"] = []
        chat_list.controls.clear()
        chat_list.controls.append(welcome_view())
        refresh_ui()
        show_snack("Mazungumzo ya sasa yamefutwa.")

    def delete_current_chat(e=None):
        chat_id = current_chat.get("id")

        if chat_id is not None:
            db.delete_chat(chat_id)

        current_chat["id"] = None
        current_chat["title"] = "New Chat"
        current_chat["messages"] = []

        chat_history.clear()
        chat_history.extend(db.get_chats())

        chat_list.controls.clear()
        chat_list.controls.append(welcome_view())
        refresh_ui()
        show_snack("Chat imefutwa.")

    def delete_all_history(e=None):
        def confirm_delete(ev):
            db.delete_all_chats()

            current_chat["id"] = None
            current_chat["title"] = "New Chat"
            current_chat["messages"] = []

            chat_history.clear()
            chat_list.controls.clear()
            chat_list.controls.append(welcome_view())

            page.pop_dialog()
            refresh_ui()
            show_snack("Historia yote ya chats imefutwa.")

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Futa historia yote"),
                content=ft.Text(
                    "Una uhakika unataka kufuta mazungumzo yote? "
                    "Kitendo hiki hakiwezi kutenduliwa."
                ),
                actions=[
                    ft.TextButton(
                        "Ghairi",
                        on_click=lambda e: page.pop_dialog(),
                    ),
                    ft.TextButton(
                        "Futa Yote",
                        on_click=confirm_delete,
                    ),
                ],
            )
        )

    def show_about(e=None):
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "TEKU Assistant",
                    weight=ft.FontWeight.BOLD,
                ),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text("Msaidizi wa Teofilo Kisanji University"),
                        ft.Text(""),
                        ft.Text(
                            "TEKU Assistant hutumia TEKU Knowledge Base "
                            "pamoja na Gemini AI kutoa majibu."
                        ),
                        ft.Text(""),
                        ft.Text(
                            "Majibu ya taarifa nyeti za muda kama ada, "
                            "admission na deadlines yanapaswa kuthibitishwa "
                            "kwenye chanzo rasmi cha TEKU."
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton(
                        "Funga",
                        on_click=lambda e: page.pop_dialog(),
                    )
                ],
            )
        )

    def show_settings(e=None):
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Settings"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            "Muonekano wa mfumo",
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Row(
                            controls=[
                                ft.Text("Dark / Light Mode"),
                                ft.Switch(
                                    value=state["dark"],
                                    on_change=lambda ev: (
                                        toggle_theme(ev),
                                        page.pop_dialog(),
                                    ),
                                ),
                            ]
                        ),
                        ft.Text(""),
                        ft.Text(
                            "TEKU Assistant • RAG + Gemini + SQLite",
                            size=11,
                            color=C("muted"),
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton(
                        "Funga",
                        on_click=lambda e: page.pop_dialog(),
                    )
                ],
            )
        )

    # --------------------------------------------------------
    # FILE UPLOAD
    # --------------------------------------------------------

    # Flet 1.x FilePicker is a service and uses an async API.
    # Keeping one picker instance also prevents the old
    # "Unknown control: FilePicker" panel from appearing in the UI.
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    async def pick_file(e=None):
        try:
            # Flet versions differ in the async method name.
            if hasattr(file_picker, "pick_files_async"):
                files = await file_picker.pick_files_async(
                    allow_multiple=False,
                    allowed_extensions=["pdf", "txt", "csv", "docx", "xlsx", "json"],
                )
            else:
                result = file_picker.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["pdf", "txt", "csv", "docx", "xlsx", "json"],
                )
                if hasattr(result, "__await__"):
                    result = await result
                files = result

            if not files:
                return

            selected = files[0]
            selected_upload["path"] = getattr(selected, "path", None)
            selected_upload["name"] = getattr(selected, "name", "Uploaded file")

            message_input.value = (
                f"📎 {selected_upload['name']}\n"
                "Andika swali kuhusu file hili kisha bonyeza Send."
            )
            message_input.focus()
            page.update()
            show_snack(f"File imechaguliwa: {selected_upload['name']}")

        except Exception as error:
            print("FILE PICKER ERROR:", error)
            show_snack(
                "File picker haikufunguka. "
                "Kwenye Linux hakikisha Zenity imewekwa: "
                "sudo apt install zenity"
            )

    # --------------------------------------------------------
    # VOICE RECORDING
    # --------------------------------------------------------

    def _finish_voice_recording():
        if not voice_state["frames"] or sd is None or sf is None:
            return None

        try:
            audio = __import__("numpy").concatenate(voice_state["frames"], axis=0)
            path = Path(tempfile.gettempdir()) / "teku_assistant_voice.wav"
            sf.write(str(path), audio, 16000)
            return str(path)
        except Exception as error:
            print("AUDIO SAVE ERROR:", error)
            return None

    async def _transcribe_voice(audio_path):
        if not audio_path:
            return None

        if genai is None:
            return None

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            load_dotenv(BASE_DIR / ".env", override=True)
            api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None

        try:
            client = genai.Client(api_key=api_key)

            uploaded = await asyncio.to_thread(
                client.files.upload,
                file=audio_path,
            )

            prompt = (
                "Transcribe this audio exactly as spoken. "
                "The speaker may use Kiswahili or English. "
                "Return only the transcription text, with no explanation."
            )

            models = [
                "gemini-3.5-flash-lite",
                "gemini-3.6-flash",
                "gemini-3.7-flash",
            ]

            for model_name in models:
                try:
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=model_name,
                        contents=[uploaded, prompt],
                    )
                    result = getattr(response, "text", None)
                    if result and result.strip():
                        return result.strip()
                except Exception as model_error:
                    print(f"VOICE TRANSCRIPTION {model_name} ERROR:", model_error)

        except Exception as error:
            print("VOICE TRANSCRIPTION ERROR:", error)

        return None

    async def _voice_worker(audio_path):
        try:
            transcription = await _transcribe_voice(audio_path)

            if transcription:
                message_input.value = transcription
                page.update()
                show_snack("Sauti imebadilishwa kuwa maandishi. Bonyeza Send.")
            else:
                # Even when transcription is unavailable, keep the recording attached.
                selected_upload["path"] = audio_path
                selected_upload["name"] = Path(audio_path).name
                message_input.value = (
                    "🎤 Sauti imerekodiwa. "
                    "Andika swali kuhusu recording kisha bonyeza Send."
                )
                page.update()
                show_snack("Sauti imehifadhiwa, lakini transcription haikupatikana.")
        except Exception as error:
            print("VOICE WORKER ERROR:", error)
            show_snack("Kuna tatizo kwenye voice transcription.")

    def voice_recording(e=None):
        if sd is None or sf is None:
            show_snack(
                "Voice recording haija-installiwa. Run: "
                "pip install sounddevice soundfile"
            )
            return

        if not voice_state["recording"]:
            try:
                voice_state["recording"] = True
                voice_state["frames"] = []

                def callback(indata, frames, time_info, status):
                    if status:
                        print("MIC STATUS:", status)
                    if voice_state["recording"]:
                        voice_state["frames"].append(indata.copy())

                voice_state["stream"] = sd.InputStream(
                    samplerate=16000,
                    channels=1,
                    dtype="float32",
                    callback=callback,
                )
                voice_state["stream"].start()

                show_snack("🎙️ Inarekodi... Bonyeza mic tena kumaliza.")
                refresh_ui()
            except Exception as error:
                voice_state["recording"] = False
                voice_state["stream"] = None
                print("VOICE START ERROR:", error)
                show_snack(
                    "Imeshindikana kuanza microphone. "
                    "Hakikisha Linux imeipa app ruhusa ya kutumia microphone."
                )
        else:
            try:
                voice_state["recording"] = False

                stream = voice_state.get("stream")
                voice_state["stream"] = None

                if stream:
                    stream.stop()
                    stream.close()

                audio_path = _finish_voice_recording()
                voice_state["path"] = audio_path

                if audio_path:
                    show_snack("⏳ Inachakata sauti...")
                    refresh_ui()
                    page.run_task(_voice_worker, audio_path)
                else:
                    show_snack("Hakuna sauti iliyorekodiwa.")
            except Exception as error:
                voice_state["recording"] = False
                voice_state["stream"] = None
                print("VOICE STOP ERROR:", error)
                show_snack("Imeshindikana kumaliza recording.")

    # --------------------------------------------------------
    # THEME
    # --------------------------------------------------------

    def toggle_theme(e):

        state["dark"] = not state["dark"]

        page.bgcolor = C("background")

        refresh_ui()

    # --------------------------------------------------------
    # REFRESH
    # --------------------------------------------------------

    def refresh_ui():

        # Update page background
        page.bgcolor = C("background")

        # Rebuild application
        page.controls.clear()

        build_app()

        page.update()

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    def sidebar():

        return ft.Container(
            width=275,
            bgcolor=C("surface2"),
            padding=18,
            content=ft.Column(
                spacing=0,
                controls=[

                    # BRAND
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                width=44,
                                height=44,
                                border_radius=22,
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                content=ft.Image(
                                    src=LOGO,
                                    width=44,
                                    height=44,
                                    fit=ft.BoxFit.COVER,
                                ),
                            ),

                            ft.Column(
                                spacing=0,
                                controls=[
                                    ft.Text(
                                        "TEKU",
                                        size=19,
                                        weight=ft.FontWeight.BOLD,
                                        color=C("text"),
                                    ),
                                    ft.Text(
                                        "Assistant",
                                        size=12,
                                        color=C("green"),
                                    ),
                                ],
                            ),
                        ],
                    ),

                    ft.Container(height=24),

                    # NEW CHAT
                    ft.Container(
                        padding=13,
                        border_radius=13,
                        bgcolor=C("surface"),
                        border=ft.Border.all(
                            1,
                            C("border"),
                        ),
                        ink=True,
                        on_click=new_chat,
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.ADD,
                                    size=20,
                                    color=C("green"),
                                ),
                                ft.Text(
                                    "New Chat",
                                    size=14,
                                    color=C("text"),
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                    ),

                    ft.Container(height=25),

                    ft.Text(
                        "CHATS",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=C("muted"),
                    ),

                    ft.Container(height=8),

                    ft.Column(
                        spacing=2,
                        controls=(
                            [history_item(chat) for chat in chat_history]
                            if chat_history
                            else [
                                ft.Text(
                                    "Hakuna mazungumzo bado",
                                    size=12,
                                    color=C("muted"),
                                )
                            ]
                        ),
                    ),

                    ft.Container(expand=True),

                    # THEME BUTTON
                    ft.Container(
                        padding=11,
                        border_radius=12,
                        ink=True,
                        on_click=toggle_theme,
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.DARK_MODE_OUTLINED
                                    if not state["dark"]
                                    else ft.Icons.LIGHT_MODE_OUTLINED,
                                    size=19,
                                    color=C("muted"),
                                ),
                                ft.Text(
                                    "Dark / Light Mode",
                                    size=13,
                                    color=C("text"),
                                ),
                            ],
                        ),
                    ),

                    ft.Container(height=8),

                    # PROFILE
                    ft.Container(
                        padding=10,
                        border_radius=14,
                        bgcolor=C("surface"),
                        border=ft.Border.all(
                            1,
                            C("border"),
                        ),
                        content=ft.Row(
                            spacing=10,
                            controls=[
                                ft.Container(
                                    width=38,
                                    height=38,
                                    border_radius=19,
                                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                    content=ft.Image(
                                        src=PROFILE,
                                        width=38,
                                        height=38,
                                        fit=ft.BoxFit.COVER,
                                    ),
                                ),

                                ft.Column(
                                    spacing=1,
                                    controls=[
                                        ft.Text(
                                            "TEKU User",
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color=C("text"),
                                        ),
                                        ft.Text(
                                            "Student",
                                            size=11,
                                            color=C("muted"),
                                        ),
                                    ],
                                ),

                                ft.Container(expand=True),

                                ft.PopupMenuButton(
                                    icon=ft.Icons.MORE_HORIZ,
                                    icon_color=C("muted"),
                                    tooltip="User menu",
                                    items=[
                                        ft.PopupMenuItem(
                                            content=ft.Text("New Chat"),
                                            icon=ft.Icons.ADD,
                                            on_click=new_chat,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("Clear Chat"),
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            on_click=clear_current_chat,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("Settings"),
                                            icon=ft.Icons.SETTINGS,
                                            on_click=show_settings,
                                        ),
                                        ft.PopupMenuItem(
                                            content=ft.Text("About"),
                                            icon=ft.Icons.INFO_OUTLINE,
                                            on_click=show_about,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    def header():

        return ft.Container(
            height=70,
            bgcolor=C("surface"),
            border=ft.Border.only(
                bottom=ft.BorderSide(
                    1,
                    C("border"),
                )
            ),
            padding=ft.Padding.symmetric(
                horizontal=22,
            ),
            content=ft.Row(
                controls=[

                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                "TEKU Assistant",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=C("text"),
                            ),
                            ft.Text(
                                "Msaidizi wa Teofilo Kisanji University",
                                size=11,
                                color=C("muted"),
                            ),
                        ],
                    ),

                    ft.Container(expand=True),

                    ft.IconButton(
                        icon=ft.Icons.MIC_NONE,
                        tooltip="Voice",
                        icon_color=C("muted"),
                        on_click=voice_recording,
                    ),

                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_color=C("muted"),
                        tooltip="Menu",
                        items=[
                            ft.PopupMenuItem(
                                content=ft.Text("New Chat"),
                                icon=ft.Icons.ADD,
                                on_click=new_chat,
                            ),
                            ft.PopupMenuItem(
                                content=ft.Text("Clear Chat"),
                                icon=ft.Icons.DELETE_OUTLINE,
                                on_click=clear_current_chat,
                            ),
                            ft.PopupMenuItem(
                                content=ft.Text("Settings"),
                                icon=ft.Icons.SETTINGS,
                                on_click=show_settings,
                            ),
                            ft.PopupMenuItem(
                                content=ft.Text("About"),
                                icon=ft.Icons.INFO_OUTLINE,
                                on_click=show_about,
                            ),
                        ],
                    ),
                ],
            ),
        )

    # --------------------------------------------------------
    # COMPOSER
    # --------------------------------------------------------

    def composer():

        return ft.Container(
            padding=ft.Padding.symmetric(
                horizontal=20,
                vertical=12,
            ),
            bgcolor=C("surface"),
            content=ft.Container(
                padding=ft.Padding.symmetric(
                    horizontal=8,
                    vertical=4,
                ),
                border_radius=22,
                bgcolor=C("surface2"),
                border=ft.Border.all(
                    1,
                    C("border"),
                ),
                content=ft.Row(
                    spacing=2,
                    controls=[

                        ft.IconButton(
                            icon=ft.Icons.ATTACH_FILE,
                            tooltip="Upload file",
                            icon_color=C("muted"),
                            on_click=pick_file,
                        ),

                        message_input,

                        ft.IconButton(
                            icon=(
                                ft.Icons.STOP_CIRCLE_OUTLINED
                                if voice_state["recording"]
                                else ft.Icons.MIC_NONE
                            ),
                            tooltip=(
                                "Acha recording"
                                if voice_state["recording"]
                                else "Voice recording"
                            ),
                            icon_color=(
                                C("green")
                                if voice_state["recording"]
                                else C("muted")
                            ),
                            on_click=voice_recording,
                        ),

                        ft.IconButton(
                            icon=ft.Icons.SEND,
                            tooltip="Send",
                            icon_color=C("green"),
                            on_click=send_message,
                        ),
                    ],
                ),
            ),
        )

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    def build_app():

        # background layer
        background = ft.Container(
            expand=True,
            bgcolor=C("background"),
        )

        # Background image
        background_image = ft.Container(
            expand=True,
            opacity=0.08 if not state["dark"] else 0.04,
            content=ft.Image(
                src=BACKGROUND,
                fit=ft.BoxFit.COVER,
                width=float("inf"),
                height=float("inf"),
            ),
        )

        # Main chat
        if not chat_list.controls:
            chat_list.controls.append(welcome_view())

        chat_area = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header(),
                ft.Stack(
                    expand=True,
                    controls=[
                        background,
                        background_image,
                        chat_list,
                    ],
                ),
                composer(),
            ],
        )

        page.add(
            ft.Row(
                expand=True,
                spacing=0,
                controls=[
                    sidebar(),
                    chat_area,
                ],
            )
        )

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    build_app()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    ft.run(main)