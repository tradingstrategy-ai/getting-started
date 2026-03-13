# Instructions to work with the code base

## English

- Use UK/British English instead of US English
- Say things like `visualise` instead of `visualize`
- For headings, only capitalise the first letter of heading, do not use title case

## Running notebooks

You can test if a notebook runs from the command line with `jupyter` command.

Example:

```shell
poetry run jupyter execute my-notebook.ipynb --inplace --timeout=900
```

- `--inplace` overwrites the notebook with executed results (cell outputs)
- `--timeout=900` sets a 15 minute per-cell execution timeout (use `-1` to disable for long-running optimisers)


Never use `ipython` command as it does not work with multiprocessing.

Alternative if you have IDE access, you can use the IDE to run the notebook.

## Running Python scripts

When running a Python script use `poetry run python` command instead of plain `python` command, so that the virtual environment is activated.

```shell
poetry run python scripts/logos/post-process-logo.py
```

## Formatting code

Don't format code.

## Pull requests

- Never push directly to a master, and open a pull request when asked.
- Do not include test plan in a pull request description
- If the user ask to open a pull request as feature then start the PR title with "feat:" prefix and also add one line about the feature into `CHANGELOG.md`
- Each changelog entry should follow the date of the PR in YYYY-MM-DD format. Example: Something was updated (2026-01-01).
- Before opening or updating a pull request, format the code

### datetime

- Use naive UTC datetimes everywhere
- When using datetime class use `import datetime.datetime` and use `datetime.datetime` and `datetime.timedelta` as type hints
- Instead of `datetime.datetime.utcnow()` use `native_datetime_utc_now()` that is compatible across Python versions

### Enum

- For string enums, both members and values must in snake_case

### pyproject.toml

- When adding or updating dependencies in `pyproject.toml`, always add a comment why this dependency is needed for this project

## Python notebooks

- Whenever possible, prefer table output instead of print(). Use Pandas DataFrame and notebook's built-in display() function to render tabular data.

## Editing files

- When you need to modify files the editable Python packages live under ~/code/trade-executor
- Never edit files under ~/code/docs
