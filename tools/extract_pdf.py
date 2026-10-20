from pathlib import Path
import argparse
from pypdf import PdfReader


parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()

reader = PdfReader(args.source)
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("w", encoding="utf-8", newline="\n") as stream:
    for page_number, page in enumerate(reader.pages, 1):
        stream.write(f"\n\n===== PDF PAGE {page_number} =====\n\n")
        text = page.extract_text() or "[NO EXTRACTABLE TEXT]"
        stream.write(text.replace("\x00", ""))

print(f"pages={len(reader.pages)}")
print(f"output={args.output}")
print(f"bytes={args.output.stat().st_size}")
