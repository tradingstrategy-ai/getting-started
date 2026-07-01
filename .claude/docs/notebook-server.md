# Notebook server

Use `poetry run notebook-static-server` to view saved notebook outputs from a browser.

The server renders existing `.ipynb` files to static HTML. It does not rerun notebooks, start kernels, call `jupyter execute`, or refresh stale outputs. Run the notebook separately first if you need fresh results.

Always use this static server for notebook previews. Do not start `jupyter notebook`, `jupyter lab`, or another live kernel server when the task is only to preview saved notebook outputs.

## Supported notebooks

The server only serves notebooks from these repository folders:

- `notebooks/`
- `scratchpad/`

Paths outside these folders are rejected.

## Start the server

Start from the repository root:

```shell
poetry run notebook-static-server --port 8765
```

Do not pass `--host 127.0.0.1` for normal preview use. By default the server binds to all IPv4 network interfaces with `0.0.0.0` on the selected port, so the preview is reachable through loopback and Tailscale. In socket terms this means all available IPv4 addresses, not a single local address. If `8765` is already in use, choose another port with `--port`.

Open:

```text
http://127.0.0.1:8765/
```

Log in with:

```text
viewer
viewer
```

The server rejects clients that are not loopback or Tailscale addresses. The hardcoded Basic Auth credentials assume access happens through a trusted intranet or Tailscale.

The default `0.0.0.0` bind is IPv4-only.

## Background server

Start the server in the background:

```shell
setsid poetry run notebook-static-server --port 8765 > /tmp/notebook-static-server.log 2>&1 & echo $! > /tmp/notebook-static-server.pid
```

Check it:

```shell
curl -u viewer:viewer http://127.0.0.1:8765/
```

Stop it:

```shell
kill $(cat /tmp/notebook-static-server.pid)
```

If the PID file is missing, identify the exact process before killing anything:

```shell
ps -Ao pid,ppid,etime,command | rg 'notebook-static-server|getting_started.notebook_static_server'
```

## View example notebooks

View an example notebook from `notebooks/`:

```text
http://127.0.0.1:8765/view/notebooks/single-backtest/moving-average.ipynb
```

View an example notebook from `scratchpad/`:

```text
http://127.0.0.1:8765/view/scratchpad/xchain2/04-backtest-3m-score-weightings.ipynb
```

Per-notebook links use URL-escaped relative paths under `/view/`.

## Get a notebook URL

Use `--url-for` to derive the viewer URL after a notebook run:

```shell
poetry run notebook-static-server --port 8765 --url-for scratchpad/xchain2/04-backtest-3m-score-weightings.ipynb
```

By default, the URL uses the machine's Tailscale MagicDNS hostname from `tailscale status --json`, for example:

```text
http://brian.tail71b97.ts.net:8765/view/scratchpad/xchain2/04-backtest-3m-score-weightings.ipynb
```

If the `*.ts.net` hostname is not available, the script falls back to `tailscale ip -4`, then to `127.0.0.1`.

For a purely local URL, pass an explicit base URL:

```shell
poetry run notebook-static-server --port 8765 --public-base-url http://127.0.0.1:8765 --url-for scratchpad/xchain2/04-backtest-3m-score-weightings.ipynb
```

Tailscale URLs are internal links. They are useful in chat and internal PR comments, but external GitHub reviewers cannot open them unless they are on the same tailnet.

## Verify the notebook is served

Always verify the exact per-notebook URL before reporting it. Starting the server is not proof the notebook is reachable: another server from a different (sometimes deleted) checkout can already hold the port and answer requests, so the index page loads but the specific notebook returns `404`.

After starting the server and deriving the URL with `--url-for`, fetch the notebook path itself and confirm both the HTTP status and that the rendered HTML actually contains the notebook's own title.

First check the status code:

```shell
curl -s -o /dev/null -w "%{http_code}\n" -u viewer:viewer \
  "http://127.0.0.1:8765/view/scratchpad/xchain2/08-backtest-capped-waterfall.ipynb"
```

Interpret the status code:

- `200` — the server answered. Continue to the title check below.
- `401` — Basic Auth failed. Use the `viewer:viewer` credentials.
- `404` — the notebook is not found on the server answering this port. This usually means a stale server from another checkout owns the port. Do not report the URL.

A `200` alone is not enough: a stale or misconfigured server can return `200` with the wrong notebook, an error page, or empty output. Confirm the response body contains the notebook's own title (its first Markdown heading), so you know the correct notebook is served:

```shell
curl -s -u viewer:viewer \
  "http://127.0.0.1:8765/view/scratchpad/xchain2/08-backtest-capped-waterfall.ipynb" \
  | rg -q "Cross-chain master vault CCTP backtest" && echo "title OK" || echo "WRONG CONTENT"
```

Use the target notebook's actual first heading as the search string. Only report the URL when the status is `200` **and** the title check prints `title OK`. If it prints `WRONG CONTENT`, treat it like a `404`: find which checkout owns the port before doing anything else.

If you get `404`, confirm which checkout owns the port before doing anything else:

```shell
ss -ltnp | rg ':8765'                      # find the listening PID
ls -l /proc/<pid>/cwd                       # show that server's working directory
```

If the working directory is a different or deleted checkout, do not kill it blindly (it may belong to another agent). Instead start your server on a free port with `--port` and re-derive the URL there, then re-run both the status-code and title checks until the status is `200` and the title check prints `title OK`.

Do not expose this server through a public unauthenticated tunnel. If you use Omnara Live Preview, keep the preview access-controlled and remember that rendered notebook HTML is trusted internal content, not sanitised public content.

## Omnara

When running under Omnara, start the notebook server in the same repository checkout where the notebook was generated. Then expose port `8765` with an access-controlled Omnara Live Preview, or report the Tailscale URL generated by `--url-for`.
