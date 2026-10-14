"""Audit saved notebook outputs and prepare chart sheets for visual inspection."""

import base64
import io
import json
import re

import nbformat
from PIL import Image, ImageDraw

from repaired_data_replay import RESEARCH_DIR, RUN_ROOT


def main():
    """Read saved outputs without launching or changing research kernels."""
    folder = RUN_ROOT / "chart-review"
    folder.mkdir(exist_ok=True)
    records = []
    for path in sorted(RESEARCH_DIR.glob("0*.ipynb")):
        notebook = nbformat.read(path, 4)
        cells = [c for c in notebook.cells if c.cell_type == "code"]
        complete = all(c.execution_count is not None for c in cells)
        if not complete:
            records.append({"notebook": path.name, "complete": False})
            continue
        assert not any(o.output_type == "error" for c in cells for o in c.outputs)
        images = []
        warnings = []
        for index, cell in enumerate(notebook.cells):
            if cell.cell_type != "code":
                continue
            compile(cell.source, str(path), "exec")
            for output in cell.outputs:
                text = output.get("text", "")
                if isinstance(text, list):
                    text = "".join(text)
                warnings.extend(re.findall(r".*(?:Warning:|FutureWarning|RuntimeWarning|UserWarning).*", text))
                encoded = output.get("data", {}).get("image/png")
                if encoded:
                    if isinstance(encoded, list):
                        encoded = "".join(encoded)
                    image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
                    destination = folder / f"{path.stem}-cell-{index:02d}-{len(images):02d}.png"
                    image.save(destination)
                    images.append((destination, image))
        for start in range(0, len(images), 6):
            sheet = Image.new("RGB", (1500, 1500), "white")
            draw = ImageDraw.Draw(sheet)
            for slot, (image_path, image) in enumerate(images[start : start + 6]):
                x, y = slot % 2 * 750, slot // 2 * 500
                draw.text((x + 8, y + 4), image_path.name, fill="black")
                image.thumbnail((740, 470))
                sheet.paste(image, (x + (750 - image.width) // 2, y + 25))
            sheet.save(folder / f"{path.stem}-sheet-{start // 6:02d}.png")
        records.append({"notebook": path.name, "complete": True, "code_cells": len(cells), "png_charts": len(images), "warnings": warnings})
    (RUN_ROOT / "saved-output-audit.json").write_text(json.dumps(records, indent=2))
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
