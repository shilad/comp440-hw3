# The results viewer

Pages in your browser for reading your own runs: what is saved in `runs/`. It only reads those
files, never changes them, and makes no network calls. Reload a page to see new results.

## Open it

- From the homework page: click **Results**, or the **Open these results** link on a step that
  saves results. The pages are at `/results/` on the homework page's address.
- On its own, from the repository's folder, when the homework page is not running:

  ```
  uv run python -m viewer
  ```

  It opens `http://127.0.0.1:8452/` (or the next free port) in your browser. Add `--no-open`
  to keep the browser closed. Stop it with Ctrl-C.

## What each page shows

| Page | What it shows |
|---|---|
| **Your runs** | Everything in `runs/`, part by part: the single checks from Part 0, your lookups by hand from step 1b, and each run (when it was made, which versions, how many claims are done, how many verdicts matched the label). |
| **One run** | The same accuracy table `evaluate.py` prints, by the number of articles a claim needs and by the dataset's label; lookups and time per claim and in total (and tokens and cost, once your loop counts tokens in step 3b); the claims with no verdict; then every claim in a table you can filter and sort. A run without `report.txt` is marked as not finished. |
| **One claim** | The claim, the dataset's label, the articles the dataset lists for it (and which ones the agent read), and each version's verdict, explanation, quoted evidence, lookups and time side by side (and tokens and cost, once your loop counts them). Below, the agent's trace one entry at a time (an entry is a lookup or an answer), with each quote highlighted where it appears in what the agent read. Previous and Next keep your filters. |
| **One check** | The same, for one file saved by `check.py`. |
| **Compare two runs** | Two runs side by side (for example the agent before and after a change): accuracy, lookups and time in each (and cost, once your loop counts tokens), the difference, and every claim whose verdict changed, with both traces. |

A ✓ means a verdict matched the dataset's label. It says nothing more than that.

## Files

- `app.py`: the pages. `handle(method, path, query, repo)` answers one request; the homework
  page serves it under `/results`.
- `runs.py`: reading the run files, and the numbers. It uses `is_correct()`, `group_of()` and
  `report()` from `evaluate.py`, so its numbers are the ones `evaluate.py` prints.
- `__main__.py`: the server for running it on its own (this computer only, 127.0.0.1).
- `static/`: the style sheet and a few lines of script (filters, folding, arrow keys).
