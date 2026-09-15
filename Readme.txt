TEKU ASSISTANT - CORRECTED PROJECT FILES

Replace the corresponding Python/config files in the existing project.
DO NOT replace your .env, PDF, generated knowledge files, vector_store, database, or assets unless you intentionally want to rebuild them.

Required assets:
assets/icons/teku_logo.jpg
assets/icons/images3.jpeg
assets/images/teku_background.jpeg
assets/images/teku_building.jpeg

Commands:
1) pip install -r requirements.txt
2) python extract_pdf.py
3) python chunk_knowledge.py
4) python build_embeddings.py   # only if chunks changed or vectors are missing
5) python -m py_compile main.py ai/gemini_service.py ai/rag_service.py database/chat_database.py extract_pdf.py chunk_knowledge.py build_embeddings.py
6) python test_gemini.py
7) python test_rag_gemini.py
8) uvicorn main:app --host 0.0.0.0 --port 8550

Open: http://127.0.0.1:8550

For Render, use the same Uvicorn command with $PORT:
uvicorn main:app --host 0.0.0.0 --port $PORT

Never commit .env or GEMINI_API_KEY.