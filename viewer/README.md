# The results viewer

Pages in your browser for reading your own runs: what is saved in `runs/`. It only reads those
files, never changes them, and makes no network calls. Reload a page to see new results.

## Open it

- From the homework page: the **Results** pages are at `/results/` on the same address, and a
  step that saves results has a link to them.
- On its own, from the repository's folder, when the homework page is not running:

  ```
  uv run python -m viewer
  ```

  It opens `http://127.0.0.1:8452/` (or the next free port) in your browser. Add `--no-open`
  to keep the browser closed. Stop it with Ctrl-C.

## What each page shows

| Page | What it shows |
|---|---|
| **Your runs** | Every evaluation run (when it was made, which methods, how many claims are done, how many were correct), every single check from `check.py`, and the lookups you made by hand. |
| **One run** | The same accuracy table `evaluate.py` prints, by the number of articles a claim needs; cost per claim and in total; the claims that failed or gave no verdict; then every claim in a table you can filter and sort. |
| **One claim** | The claim and its label, each method's verdict, explanation, quoted evidence, tokens, cost and time side by side, and the agent's trace one call at a time. Each quote is highlighted where it appears in what the agent read. Previous and Next keep your filters. |
| **One check** | The same, for one file saved by `check.py`. |
| **Two runs** | Two runs side by side (for example the agent before and after a change): accuracy and cost in each, the difference, and every claim whose verdict changed, with both traces. |

*Correct* means only that a verdict matches the dataset's label. For your own claims, the label
is the verdict you gave.

## Files

- `app.py`: the pages. `handle(method, path, query, repo)` answers one request; the homework
  page serves it under `/results`.
- `runs.py`: reading the run files, and the numbers. It uses `is_correct()`, `group_of()` and
  `report()` from `evaluate.py`, so its numbers are the ones `evaluate.py` prints.
- `__main__.py`: the server for running it on its own (this computer only, 127.0.0.1).
- `static/`: the style sheet and a few lines of script (filters, folding, arrow keys).
