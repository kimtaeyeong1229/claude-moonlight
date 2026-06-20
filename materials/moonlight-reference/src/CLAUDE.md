# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is
A local web dashboard that translates arXiv papers into Korean (Medium-style HTML) and collects
them in one place. A user adds a paper from the web UI; a background **worker** spawns an
**interactive `claude` REPL in a PTY** to run the translation pipeline. See `README.md` for full docs.

## How to run
```bash
pip install -r requirements.txt      # aiohttp, markdown, Pillow  (+ system: poppler)
python3 app.py                       # dashboard  → http://127.0.0.1:8090
python3 worker.py                    # worker (separate terminal); WORKER_CONCURRENCY=N for parallel
```
The dashboard (`app.py`) and worker (`worker.py`) are **independent processes** that communicate only
through the filesystem (`jobs/` queue + `papers/<id>/` outputs). You can restart `app.py` without
touching in-flight translation jobs.

## Hard constraints (do not break)
- **NEVER use `claude -p` / headless mode** to run translations. The worker must drive an
  **interactive** `claude` session in a PTY (`pty.openpty()` + `fork` + `execvpe`), like
  `~/claude-web-terminal`. This is a deliberate product requirement.
- Claude's TUI swallows a paste+`\r` burst (the Enter becomes a literal newline). Always submit input
  as **text → short wait → separate `\r`** (see `worker.submit`). Don't "optimize" this away.
- macOS / Linux only (PTY + fork). Don't add Windows-specific assumptions.

## State-file conventions (avoid clobbering running jobs)
Per-paper state is split across files so concurrent writers never fight:
- `meta.json` — status / progress / ETA. **Written by `worker.py`** (start + finish). Don't write this
  from the dashboard for in-flight papers.
- `stage.txt` — current human-readable stage. Written by the pipeline (the interactive claude).
- `tags.json` — user's custom tags. Written by the dashboard only.
- `en_title.txt` — original English title for display. Written at add-time; **the worker must not
  translate/overwrite the sidebar title** (the paper body H1 may be Korean).
When adding a feature, prefer a **new sidecar file** over adding fields the worker also writes.

## The pipeline
`process_paper_prompt.md` is the instruction set handed to the interactive claude. `worker.py` sends a
one-line prompt pointing at it + the job's `job.json`. The pipeline: download PDF → read pages →
translate to Korean Markdown (`paper.md`) → extract figures/tables → `build_paper.py` → write `DONE`.
Edit `process_paper_prompt.md` to change translation behavior (placement rules, what to extract, etc.).

## Layout
`app.py` (server) · `worker.py` (PTY worker) · `build_paper.py` (md→HTML) ·
`process_paper_prompt.md` (pipeline) · `static/index.html` (frontend) ·
`papers/`, `jobs/`, `papers.json` are **runtime, git-ignored**.

## Gotchas
- The job queue is claimed via atomic `rename`; `claim_next()` must tolerate files vanishing mid-scan
  (multiple workers/threads race). Keep it crash-safe.
- `papers/` contains third-party paper excerpts/figures — keep it out of git.
- Default dashboard port is 8090 (8080 is reserved for claude-web-terminal).
