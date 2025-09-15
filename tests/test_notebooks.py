import glob
import os
import pytest
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

# Reduce multiprocessing warnings (from Jupyter subprocess)
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning:multiprocessing.resource_tracker"

# Scope to single-backtest notebooks for now
NOTEBOOK_GLOB_PATTERN = "notebooks/single-backtest/*.ipynb"

def parse_pragma_from_line(line: str):
    """Parse @ts pragma from a code line. Returns (pragma_type, reason) or (None, None)."""
    line = line.strip()

    if line.startswith('# @ts ') and ':' in line:
        # Extract everything between '@ts ' and ':'
        pragma_part = line[5:]  # Remove '# @ts '
        pragma_type, reason = pragma_part.split(':', 1)
        return pragma_type.strip(), reason.strip()

    return None, None

def should_skip_notebook(notebook_path: str):
    """Check if notebook should be skipped based on @ts pragmas in code cells."""
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    for cell in nb.cells:
        if cell.cell_type == "code":
            for line in cell.source.splitlines():
                pragma_type, reason = parse_pragma_from_line(line)

                if pragma_type == 'skip-test':
                    return True, f"Always skip: {reason}"
                elif pragma_type == 'skip-test-ci' and os.environ.get('CI'):
                    return True, f"CI skip: {reason}"

    return False, None

def get_notebook_test_params():
    """Get list of notebooks to test with skip markers applied."""
    notebooks = glob.glob(NOTEBOOK_GLOB_PATTERN, recursive=True)
    params = []

    for notebook in notebooks:
        should_skip, reason = should_skip_notebook(notebook)
        if should_skip:
            params.append(pytest.param(notebook, marks=pytest.mark.skip(reason=reason)))
        else:
            params.append(notebook)

    return params

def run_notebook(notebook_path: str):
    """Execute a notebook and return True if successful."""
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4) # type: ignore

    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    notebook_dir = os.path.dirname(notebook_path)
    ep.preprocess(nb, {"metadata": {"path": notebook_dir}})

    return True

# Dynamic test generation
@pytest.mark.parametrize("notebook_path", get_notebook_test_params())
def test_notebook_execution(notebook_path: str):
    """Test that a notebook executes successfully without errors."""
    try:
        success = run_notebook(notebook_path)
        assert success, f"Notebook {notebook_path} failed to execute"
    except Exception as e:
        pytest.fail(f"Notebook {notebook_path} failed with error: {str(e)}")
