"""De-noised plain-text rendering of an executed notebook, for independent review.

An executed notebook in this track is 6-7 MB, almost all of it base64 images, tqdm progress
frames and the same 40-indicator "Reading cached indicators ..." banner repeated once per
backtest. A reviewer needs the markdown, the code and the actual numeric output, and nothing
else. This strips the rest and caps any single output so one runaway table cannot crowd out the
notebook's conclusions.

Usage:
    python extract_nb.py ../21-backtest-vol-matched-family.ipynb > /tmp/nb21.txt
"""
import json
import re
import sys

#: Output lines matching any of these are noise, not results.
NOISE = re.compile(
    r"Reading cached indicators|Calculating indicators|Downloading vault dataset|"
    r"^\s*\d+%\|| it/s\]|it/s,|Trade quantity and reserve match|"
    r"^\s*Estimated (reserve|quantity)|^\s*Reserve drift|"
    r"tradeexecutor\.strategy\.runner\s+WARNING|"
    r"^<IPython\.core\.display|^<pandas\.io\.formats\.style\.Styler"
)
ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
#: Longest single output kept in full, in characters.
MAX_OUTPUT = 12000


def clean(text: str) -> str:
    text = ANSI.sub("", text)
    kept = [line for line in text.splitlines() if line.strip() and not NOISE.search(line)]
    out = "\n".join(kept)
    if len(out) > MAX_OUTPUT:
        head, tail = out[: MAX_OUTPUT // 2], out[-MAX_OUTPUT // 2:]
        out = f"{head}\n\n[... {len(out) - MAX_OUTPUT} characters elided ...]\n\n{tail}"
    return out


def render(path: str) -> str:
    notebook = json.load(open(path))
    chunks = []
    for index, cell in enumerate(notebook["cells"]):
        source = "".join(cell["source"]).rstrip()
        if cell["cell_type"] == "markdown":
            chunks.append(f"===== CELL {index} (markdown) =====\n{source}")
            continue
        if not source.strip():
            continue
        chunks.append(f"===== CELL {index} (code) =====\n{source}")
        pieces = []
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                pieces.append("ERROR: " + "\n".join(output.get("traceback", []))[:4000])
                continue
            text = "".join(output.get("text", []))
            plain = output.get("data", {}).get("text/plain")
            if plain:
                text += "".join(plain)
            cleaned = clean(text)
            if cleaned:
                pieces.append(cleaned)
        if pieces:
            chunks.append(f"----- output of cell {index} -----\n" + "\n".join(pieces))
    return "\n\n".join(chunks)


if __name__ == "__main__":
    print(render(sys.argv[1]))
