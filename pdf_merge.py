# merge_pdfs_no_argparse.py
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import re, sys

# --- CONFIG (edit these or pass args) ---
INPUT_DIR = Path("Serway Solution/")          # folder with PDFs
OUTPUT    = Path("Serway 10 E Solution.pdf") # output file
RECURSIVE = False              # set True to include subfolders
ADD_BOOKMARKS = True           # add a bookmark per source file
# ---------------------------------------

# Optional: allow positional args: script.py <input_dir> [output.pdf]
if len(sys.argv) >= 2:
    INPUT_DIR = Path(sys.argv[1])
if len(sys.argv) >= 3:
    OUTPUT = Path(sys.argv[2])

def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def list_pdfs(root: Path, recursive: bool):
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted((p for p in root.glob(pattern) if p.is_file()),
                  key=lambda p: natural_key(p.name))

def add_bookmark(writer: PdfWriter, title: str, page_index: int):
    """Work across pypdf versions (add_outline_item vs addBookmark)."""
    try:
        writer.add_outline_item(title, page_index)  # pypdf ≥ 4
    except Exception:
        try:
            writer.addBookmark(title, page_index)   # older API
        except Exception:
            pass

def main():
    if not INPUT_DIR.exists():
        raise SystemExit(f"Input dir not found: {INPUT_DIR}")

    files = list_pdfs(INPUT_DIR, RECURSIVE)
    if not files:
        raise SystemExit("No PDFs found.")

    writer = PdfWriter()
    added_any = False

    for pdf in files:
        try:
            r = PdfReader(str(pdf))
            if getattr(r, "is_encrypted", False):
                try:
                    r.decrypt("")  # try empty password
                except Exception:
                    print(f"[skip] Encrypted (no empty password): {pdf.name}")
                    continue

            start = len(writer.pages)
            for page in r.pages:
                writer.add_page(page)
            if ADD_BOOKMARKS:
                add_bookmark(writer, pdf.stem, start)
            print(f"[add] {pdf.stem} (+{len(r.pages)} pages)")
            added_any = True
        except Exception as e:
            print(f"[skip] {pdf.name}: {e}")

    if not added_any:
        raise SystemExit("Nothing was merged.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "wb") as f:
        writer.write(f)
    print(f"[ok] Wrote: {OUTPUT.resolve()}")

if __name__ == "__main__":
    main()
