from pathlib import Path
import re
import json


INPUT_PATH = Path("data/processed/teku_knowledge.txt")
OUTPUT_PATH = Path("data/processed/teku_chunks.json")

MAX_CHARS = 2200
OVERLAP = 300


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_page_blocks(text: str):
    pattern = r"===== PAGE (\d+) ====="
    parts = re.split(pattern, text)

    pages = []

    for i in range(1, len(parts), 2):
        page_number = int(parts[i])
        page_text = clean_text(parts[i + 1])

        if page_text:
            pages.append({
                "page": page_number,
                "text": page_text
            })

    return pages


def detect_section(text: str):
    patterns = [
        r"(CHAPTER\s+\d+:[^\n]+)",
        r"(CURRENT OFFICIAL WEB UPDATE\s+\d+:[^\n]+)",
        r"(APPENDIX\s+[A-Z]:[^\n]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

    return "General"


def split_text(text: str):
    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + MAX_CHARS,
            len(text)
        )

        chunk = text[start:end]

        if end < len(text):

            breaks = [
                chunk.rfind("\n\n"),
                chunk.rfind(". "),
                chunk.rfind(" ")
            ]

            best_break = max(breaks)

            if best_break > MAX_CHARS * 0.55:
                end = start + best_break + 1
                chunk = text[start:end]

        chunk = chunk.strip()

        if chunk:
            chunks.append(chunk)

        next_start = end - OVERLAP

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def main():

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file haipo: {INPUT_PATH}"
        )

    raw_text = INPUT_PATH.read_text(
        encoding="utf-8"
    )

    pages = get_page_blocks(raw_text)

    chunks = []
    chunk_number = 0

    for page in pages:

        page_number = page["page"]
        page_text = page["text"]

        section = detect_section(
            page_text
        )

        page_chunks = split_text(
            page_text
        )

        for local_number, chunk_text in enumerate(
            page_chunks,
            start=1
        ):

            chunk_number += 1

            # Identify pages that are mainly
            # contents/glossary/reference material.
            lower_text = chunk_text.lower()

            is_glossary = (
                "retrieval aliases" in lower_text
                or "canonical teku concept" in lower_text
            )

            is_contents = (
                "contents" in lower_text
                and "chapter" in lower_text
            )

            chunks.append({
                "chunk_id": (
                    f"teku-{page_number}-"
                    f"{local_number}-{chunk_number}"
                ),

                "page": page_number,

                "section": section,

                "text": chunk_text,

                "metadata": {
                    "document_id": (
                        "teku_master_knowledge_book_2026"
                    ),
                    "title": (
                        "TEKU AI Assistant "
                        "Master Knowledge Book 2026"
                    ),
                    "source_type": (
                        "user_supplied_knowledge_book"
                    ),
                    "academic_year": "2026/2027",
                    "language": "sw",
                    "page": page_number,
                    "section": section,

                    # Retrieval hints
                    "is_glossary": is_glossary,
                    "is_contents": is_contents,
                }
            })

    OUTPUT_PATH.write_text(
        json.dumps(
            chunks,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("=" * 50)
    print("TEKU CHUNKING V2 COMPLETE")
    print("=" * 50)
    print(f"Pages  : {len(pages)}")
    print(f"Chunks : {len(chunks)}")
    print(f"Output : {OUTPUT_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    main()