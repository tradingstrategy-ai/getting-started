# Instructions to work with the code base

## Skills

Codex autodiscovers repo-local skills from `.codex/skills/`.

In this repository, `.codex/skills` is a symlink to `.claude/skills` so the same skill set works for both Codex and Claude tooling.

When adding or updating a skill, edit the files under `.claude/skills/` and keep the `SKILL.md` file in each skill directory as the entrypoint.

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

When running multiple notebooks with subagents, use max 3 agents to avoid exhausting RAM and crashing the computer.

### Watching optimiser progress

All notebooks use [`tqdm_loggable`](https://github.com/tradingstrategy-ai/tqdm-loggable). Always use `TQDM_LOGGABLE_FORCE=stdout` and keep the command in the foreground:

```shell
TQDM_LOGGABLE_FORCE=stdout poetry run jupyter execute my-notebook.ipynb --inplace --timeout=900
```

This forces terminal progress output so the optimiser progress bar is visible from the calling terminal. Do not rely on notebook widgets alone.

### Multiple agents and kernels

If multiple agents are running notebooks concurrently:

- Never kill all `ipykernel` processes broadly
- Identify the exact `jupyter execute ... my-notebook.ipynb` parent process first, then match its child kernel by PID/start time
- If kernel ownership is ambiguous, do not kill any — prefer leaving a stale kernel over killing another agent's live backtest

```shell
ps -Ao pid,ppid,%cpu,etime,command | rg 'jupyter-execute|ipykernel|ipykernel_launcher'
```

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

## Indicator cache

If the notebook crashes because of what looks like indicator cache issue: we have added or edited indicators and the data is not correctly recalculated, you can clear the indicator cache wtih `clear-backtesting-cache` skill. 

This skill should not be used unless the notebook crashes because of indicator data problems.

### Code comments

- For code comments, Use Sphinx restructured text style
- For documenting dataclass and Enum members, use Sphinx `#: comment here` line comment above variable, not `:param:`
- If a. class function overloads a function inherited from the parent, and there is nothing to comment, do not repeat the code comment and leave it empty instead

### Type hinting

- Use type-specific typehints like `Percent`, `USDollarAmount`, `USDollarPrice`, `HexAddress` instead of `str` or `float` when possible
