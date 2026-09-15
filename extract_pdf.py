from pathlib import Path
import fitz

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "data" / "raw" / "TEKU_AI_Assistant_Master_Knowledge_Book_2026.pdf"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "teku_knowledge.txt"


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF haipo: {PDF_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(PDF_PATH) as doc:
        all_text = []
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                all_text.append(f"\n\n===== PAGE {page_number} =====\n\n{text}")
        full_text = "".join(all_text)
        page_count = len(doc)

    if not full_text.strip():
        raise ValueError("PDF imesomwa lakini haijatoa text yoyote.")

    OUTPUT_PATH.write_text(full_text, encoding="utf-8")

    print("========================================")
    print("TEKU PDF EXTRACTION COMPLETE")
    print("========================================")
    print(f"Pages      : {page_count}")
    print(f"Characters : {len(full_text):,}")
    print(f"Output     : {OUTPUT_PATH}")
    print("========================================")


if __name__ == "__main__":
    main()