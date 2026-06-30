# Plan: notebook static viewer server

## Goal

Provide a small internal viewer for saved notebook outputs.

The server renders existing `.ipynb` files to HTML without executing notebooks, serves only `notebooks/` and `scratchpad/`, and gives agents a stable URL to report after a notebook run.

## Design

- Entry point: `poetry run notebook-static-server`.
- Implementation: `getting_started/notebook_static_server.py`.
- Supported roots:
  - `notebooks/`
  - `scratchpad/`
- Default bind: `0.0.0.0`.
- Default port: `8765`.
- Authentication: hardcoded Basic Auth `viewer:viewer`.
- Client allowlist: loopback and Tailscale IPv4 range `100.64.0.0/10`.
- Rendering: `nbformat.read(..., as_version=4)` plus `nbconvert.HTMLExporter`.
- Execution: no kernel start, no `jupyter execute`, no `ExecutePreprocessor`.
- Security: do not expose through a public unauthenticated tunnel.

## Commands

Start the server:

```shell
poetry run notebook-static-server --port 8765
```

Start in the background:

```shell
setsid poetry run notebook-static-server --port 8765 > /tmp/notebook-static-server.log 2>&1 & echo $! > /tmp/notebook-static-server.pid
```

Get a local URL for a notebook:

```shell
poetry run notebook-static-server --port 8765 --public-base-url http://127.0.0.1:8765 --url-for notebooks/single-backtest/moving-average.ipynb
```

Stop the background server:

```shell
kill $(cat /tmp/notebook-static-server.pid)
```

## Example URLs

- `http://127.0.0.1:8765/`
- `http://127.0.0.1:8765/view/notebooks/single-backtest/moving-average.ipynb`
- `http://127.0.0.1:8765/view/scratchpad/xchain2/04-backtest-3m-score-weightings.ipynb`

## Skill integration

Update `run-variant-cycle` so it:

- reports the notebook viewer URL after a successful run
- includes the viewer URL in chat output
- includes the viewer URL in PR comments when a PR exists
- tells the user how to start the server if it is not running
- states that viewer URLs are internal tailnet URLs

## Verification

- `poetry run python -m py_compile getting_started/notebook_static_server.py`
- `poetry run notebook-static-server --help`
- unauthenticated `GET /` returns `401`
- authenticated `GET /` returns `200`
- authenticated notebook view returns `200`
- path outside `notebooks/` and `scratchpad/` returns `403`
- CRLF in request paths does not inject headers
- rendered PNG chart outputs are present in the served HTML
