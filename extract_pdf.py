import fitz
from pathlib import Path

PDF_PATH = Path("data/raw/TEKU_AI_Assistant_Master_Knowledge_Book_2026.pdf")
OUTPUT_PATH = Path("data/processed/teku_knowledge.txt")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

doc = fitz.open(PDF_PATH)

all_text = []

for page_number, page in enumerate(doc, start=1):
    text = page.get_text("text").strip()

    if text:
        all_text.append(
            f"\n\n===== PAGE {page_number} =====\n\n{text}"
        )

full_text = "".join(all_text)

OUTPUT_PATH.write_text(full_text, encoding="utf-8")

print("========================================")
print("TEKU PDF EXTRACTION COMPLETE")
print("========================================")
print(f"Pages      : {len(doc)}")
print(f"Characters : {len(full_text):,}")
print(f"Output     : {OUTPUT_PATH}")
print("========================================")
