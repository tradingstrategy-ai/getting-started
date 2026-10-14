"""Keep the complete scatter catalogue in small, self-contained research notebooks."""

import base64
import io
import json
from pathlib import Path

import nbformat
from PIL import Image as PILImage
from IPython.display import Image, display

from score_forecast_visualisation import (
    SHORT_PERIOD,
    method_name,
    render_method_appendix,
    scatter_description,
    scatter_figure,
)


def visual_review_status(artifact_dir):
    """Reuse individual inspections only while the reviewed image bytes match."""
    import hashlib
    import pandas as pd

    artifact_dir = Path(artifact_dir)
    manifest_path = artifact_dir / "scatter-figure-manifest.csv"
    if not manifest_path.exists():
        return {"complete": False, "scatter_images": 0, "overview_images": 0}
    expected = {Path(p).name for p in pd.read_csv(manifest_path)["path"]}
    inspected = set()
    for filename in ("individual-first-review.json", "individual-middle-review.json", "individual-last-review.json"):
        path = artifact_dir / "visual-review" / filename
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        for row in record.get("files", record.get("images", record.get("rows", []))):
            name = Path(row.get("file", row.get("path"))).name
            figure = artifact_dir / "figures" / name
            if figure.exists() and hashlib.sha256(figure.read_bytes()).hexdigest() == row["sha256"]:
                inspected.add(name)
    overview = artifact_dir / "visual-review" / "individual-overview-review.json"
    overview_record = json.loads(overview.read_text()) if overview.exists() else {}
    overview_count = sum((artifact_dir / "figures" / row["file"]).exists() and hashlib.sha256((artifact_dir / "figures" / row["file"]).read_bytes()).hexdigest() == row["sha256"] for row in overview_record.get("files", []))
    return {"complete": expected <= inspected and overview_count == 24, "scatter_images": len(expected & inspected), "overview_images": overview_count, "interactive_charts": overview_record.get("interactive_charts", 0)}


def preview_bytes(path):
    """Compress one plot without merging it with any other image."""
    output = io.BytesIO()
    with PILImage.open(path) as raster:
        raster.thumbnail((1000, 1000), PILImage.Resampling.LANCZOS)
        raster.convert("RGB").save(output, format="JPEG", quality=82, optimize=True)
    return output.getvalue()


def display_catalogue_chart(data, method_id, horizon, target, view, folder, frames):
    """Regenerate a single separate chart when a catalogue cell is rerun."""
    from score_forecast_statistics import join_method

    key = (method_id, horizon)
    if key not in frames:
        frames[key] = join_method(data, method_id, horizon, period="2026")
    path = scatter_figure(data, method_id, horizon, frames[key], folder, target=target, view=view)
    display(Image(data=preview_bytes(path), format="jpeg", width=1000))


def write_scatter_catalogue(data, method_ids, figure_folder, catalogue_folder, methods_per_page=4):
    """Export all figures into bounded notebook pages, preserving executable cells."""
    from tqdm_loggable.auto import tqdm

    catalogue_folder = Path(catalogue_folder)
    catalogue_folder.mkdir(exist_ok=True)
    records, pages = [], []
    progress = tqdm(total=len(method_ids), desc="Separate scatter catalogue")
    try:
        for start in range(0, len(method_ids), methods_per_page):
            ids = method_ids[start : start + methods_per_page]
            page_number = start // methods_per_page + 1
            filename = f"08-scatter-{page_number:02d}.ipynb"
            cells = [nbformat.v4.new_markdown_cell(f"# Experiment 08 scatter catalogue — page {page_number}\n\n" f"Period: **{SHORT_PERIOD}**. Four-day forecast cadence.\n\n" "[Main research notebook](../08-research-score-forecast-thresholds.ipynb) · [Catalogue index](index.ipynb)\n\n" "Every image is separate, with its own heading and description. CAGR zooms use the common −100% to +300% range; " "the following full-range audit retains every extreme. Sharpe uses a signed-log scale. " "The saved images are embedded and require no kernel to view. Running cells regenerates them from the pinned data.")]
            setup = nbformat.v4.new_code_cell("""from pathlib import Path
import sys
RESEARCH_DIR = Path.cwd()
if not (RESEARCH_DIR / 'score_forecast_data.py').exists():
    if (RESEARCH_DIR.parent / 'score_forecast_data.py').exists():
        RESEARCH_DIR = RESEARCH_DIR.parent
    else:
        RESEARCH_DIR = RESEARCH_DIR / 'scratchpad' / 'hyperliquid-vov-2nd'
sys.path.insert(0, str(RESEARCH_DIR))
from score_forecast_data import prepare_data, ARTIFACT_DIR
from score_forecast_catalogue import display_catalogue_chart
data = prepare_data()
FIGURE_DIR = ARTIFACT_DIR / 'figures'
frames = {}
""")
            setup.metadata["jupyter"] = {"source_hidden": True}
            cells.append(setup)
            page_records = []
            for method_id in ids:
                generated = render_method_appendix(data, [method_id], figure_folder, display_output=False)
                for record in generated:
                    horizon, target, view = record["lookahead_days"], record["outcome"], record["view"]
                    label = "CAGR: zoomed view" if view == "focus" else "CAGR: full-range audit" if target == "future_cagr" else "Sharpe"
                    cells.append(nbformat.v4.new_markdown_cell(f"### {method_name(data, method_id)} · {horizon}-day lookahead · {label} — {SHORT_PERIOD}\n\n" + scatter_description(target, view, horizon)))
                    code = nbformat.v4.new_code_cell(f"display_catalogue_chart(data, {method_id!r}, {horizon}, {target!r}, {view!r}, FIGURE_DIR, frames)")
                    code.metadata["jupyter"] = {"source_hidden": True}
                    encoded = base64.b64encode(preview_bytes(record["path"])).decode()
                    code.outputs = [nbformat.v4.new_output("display_data", data={"image/jpeg": encoded, "text/plain": f"<Separate scatter plot: {label}>"}, metadata={"image/jpeg": {"width": 1000}})]
                    cells.append(code)
                    record["catalogue_notebook"] = filename
                    page_records.append(record)
                progress.update(1)
            notebook = nbformat.v4.new_notebook(cells=cells)
            notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
            notebook.metadata.language_info = {"name": "python"}
            notebook.metadata.research_generation = {"data_fingerprint": data["provenance"]["fingerprint"], "embedded_plots": len(page_records)}
            nbformat.write(notebook, catalogue_folder / filename)
            records.extend(page_records)
            pages.append({"page": page_number, "notebook": filename, "methods": "; ".join(method_name(data, m) for m in ids), "images": len(page_records)})
    finally:
        progress.close()
    import pandas as pd

    index = pd.DataFrame(pages)
    index_text = "# Experiment 08 scatter catalogue\n\n" f"Period: **{SHORT_PERIOD}**. **{len(method_ids)} methods × 3 lookaheads × 3 separate views = {len(records):,} images.**\n\n" "Each image has its own heading and description; no merged images or collations. " "The catalogue is split into small notebooks so VS Code does not need to render all images at once.\n\n" "[Main research notebook](../08-research-score-forecast-thresholds.ipynb)\n\n" + "\n".join(f'- [Page {r["page"]:02d}]({r["notebook"]}) — {r["methods"]}' for r in pages) + "\n"
    (catalogue_folder / "README.md").write_text(index_text)
    nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(index_text)]), catalogue_folder / "index.ipynb")
    return records, index
