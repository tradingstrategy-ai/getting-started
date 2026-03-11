---
name: clear-backtesting-cache
description: Delete cached indicator data used by backtesting and grid search notebooks
---

Delete the indicator cache directory at `~/.cache/indicators/`.

This cache stores pre-calculated indicator results (e.g. from grid search / optimiser runs) as pickle files on disk. Clearing it forces indicators to be recalculated on the next notebook run.

```shell
rm -rf ~/.cache/indicators
```

After deleting, report the size of the deleted directory if available, or confirm deletion.
