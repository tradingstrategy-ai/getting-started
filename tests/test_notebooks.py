import glob
import os
import pytest
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

NOTEBOOK_GLOB_PATTERN = "notebooks/**/*.ipynb"

# Notebooks containing any of these strings will be skipped
# - Fix issues in these notebooks (related to the skip strings) to enable them to run successfully
# - Notebooks requiring perform_gride_search and prefilter- scripts may need to be run manually due to long runtimes
SKIP_NOTEBOOK_STRINGS = ["perform_grid_search", "prefilter-", "create_binance_universe", "df_trend_polygon", "polygon_token_list", "filter_scams", "demeter"]

def contains_code(notebook_path: str, search_strings: list[str]) -> bool:
    """Check if notebook contains any code strings."""
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)
        for cell in nb.cells:
            if cell.cell_type == "code":
                if any(search_string in cell.source for search_string in search_strings):
                    return True
    return False

def get_notebooks_to_test():
    """Get list of notebooks to test (excluding notebooks containing "skip" strings)."""
    all_notebooks = glob.glob(NOTEBOOK_GLOB_PATTERN, recursive=True)
    return [nb for nb in all_notebooks if not contains_code(nb, SKIP_NOTEBOOK_STRINGS)]

def run_notebook(notebook_path: str):
    """Execute a notebook and return True if successful."""
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4) # type: ignore

    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    notebook_dir = os.path.dirname(notebook_path)
    ep.preprocess(nb, {"metadata": {"path": notebook_dir}})

    return True

# Dynamic test generation
@pytest.mark.parametrize("notebook_path", get_notebooks_to_test())
def test_notebook_execution(notebook_path: str):
    """Test that a notebook executes successfully without errors."""
    try:
        success = run_notebook(notebook_path)
        assert success, f"Notebook {notebook_path} failed to execute"
    except Exception as e:
        pytest.fail(f"Notebook {notebook_path} failed with error: {str(e)}")

