import glob
import subprocess
import sys
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

def is_grid_search(notebook_path):
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)
        for cell in nb.cells:
            if cell.cell_type == 'code' and 'perform_grid_search' in cell.source:
                return True
    return False

def run_notebook(notebook_path):
    try:
        with open(notebook_path) as f:
            nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
        ep.preprocess(nb, {'metadata': {'path': './'}})
        return True
    except Exception as e:
        print(f"Error running {notebook_path}: {e}")
        return False

def main():
    notebooks = glob.glob('**/*.ipynb', recursive=True)
    failing_notebooks = []

    for notebook in notebooks:
        if not is_grid_search(notebook):
            print(f"Running {notebook}...")
            if not run_notebook(notebook):
                failing_notebooks.append(notebook)
        else:
            # TODO remove
            print(f"Skipping {notebook} (grid search notebook)...")

    if failing_notebooks:
        print("Failing notebooks:")
        for notebook in failing_notebooks:
            print(notebook)
        sys.exit(1)
    else:
        print("All notebooks ran successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
