import glob
import os
import pytest
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

NOTEBOOK_GLOB_PATTERN = "notebooks/single-backtest/*.ipynb"

def is_grid_search(notebook_path: str):
    """Check if notebook contains grid search functionality."""
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)
        for cell in nb.cells:
            if cell.cell_type == "code" and "perform_grid_search" in cell.source:
                return True
    return False

def get_notebooks_to_test():
    """Get list of notebooks to test (excluding grid search notebooks)."""
    all_notebooks = glob.glob(NOTEBOOK_GLOB_PATTERN, recursive=True)
    return [nb for nb in all_notebooks if not is_grid_search(nb)]

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

