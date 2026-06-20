#!/usr/bin/env python3
"""Moonlight worker — drives an INTERACTIVE `claude` REPL in a PTY.

Ported from claude-web-papers-kr/worker.py (the translation engine is reused
verbatim, per plans/v0.3.md §C). It NEVER uses `claude -p` / headless mode.

Per job it:
  1. writes job.json into the paper's output dir,
  2. spawns interactive claude (Opus 4.8, --dangerously-skip-permissions),
  3. enables ultracode via `/effort ultracode`,
  4. sends a one-line task prompt pointing at process_paper_prompt.md,
  5. waits for <output_dir>/DONE (or FAILED),
  6. updates meta.json and moves the job file.

The only change vs. the reference: the pipeline emits an ALIGNED paper.json
(sentence-level EN<->KO) instead of paper.html.
"""
import fcntl
import json
import os
import pty
import select
import shutil
import signal
import struct
import termios
import threading
import time
from pathlib import Path

BASE = Path(__file__).parent
DATA = Path(os.environ.get("MOONLIGHT_DATA", BASE.parent / "data"))
PAPERS_DIR = DATA / "papers"
JOBS = DATA / "jobs"
PROMPT_FILE = BASE / "process_paper_prompt.md"

CLAUDE = os.environ.get("CLAUDE_CMD") or shutil.which("claude") or "claude"
MODEL = os.environ.get("WORKER_MODEL", "claude-opus-4-8")
SPAWN_CWD = os.environ.get("WORKER_CWD", str(BASE))
# Reasoning effort for the interactive session. Default: Opus 4.8 at "high".
EFFORT = os.environ.get("WORKER_EFFORT", "high").strip().lower()
JOB_TIMEOUT = int(os.environ.get("WORKER_JOB_TIMEOUT", "3600"))
CONCURRENCY = max(1, int(os.environ.get("WORKER_CONCURRENCY", "2")))
POLL = 2.0
STOP = threading.Event()


def log(msg):
    print(f"[worker {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def read_meta(pid):
    try:
        return json.loads((PAPERS_DIR / pid / "meta.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def update_meta(pid, **fields):
    meta = read_meta(pid)
    meta.update(fields)
    d = PAPERS_DIR / pid
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    tmp.replace(d / "meta.json")


# --------------------------- PTY claude ---------------------------

def spawn_claude(cwd, extra_args):
    """Spawn interactive claude in a PTY. env/argv built in PARENT (we fork from
    worker threads, so the child must do almost nothing before execvpe)."""
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    argv = [CLAUDE, *extra_args]
    master_fd, slave_fd = pty.openpty()
    pid = os.fork()
    if pid == 0:  # child
        os.close(master_fd)
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0); os.dup2(slave_fd, 1); os.dup2(slave_fd, 2)
        if slave_fd > 2:
            os.close(slave_fd)
        os.chdir(cwd)
        try:
            os.execvpe(CLAUDE, argv, env)
        except Exception:
            os._exit(127)
    os.close(slave_fd)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
    return pid, master_fd


def drain(fd, logf, seconds):
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                return
            if data:
                logf.write(data); logf.flush()


def send(fd, text):
    os.write(fd, text.encode())


def submit(fd, logf, text, settle=1.5):
    """Type text, let it settle, then send Enter SEPARATELY — claude's TUI treats
    a paste+CR burst as one block and never submits (do NOT optimize away)."""
    send(fd, text)
    drain(fd, logf, settle)
    send(fd, "\r")


def kill(pid, fd):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            break
        time.sleep(0.4)
    try:
        os.close(fd)
    except OSError:
        pass


# --------------------------- job processing ---------------------------

def process(job_file: Path):
    job = json.loads(job_file.read_text())
    pid_slug = job["id"]
    # Derive the output dir from THIS process's data root, not job["output_dir"]
    # (which may hold a container path while the worker runs on the host).
    out = PAPERS_DIR / pid_slug
    (out / "figures").mkdir(parents=True, exist_ok=True)
    for s in ("DONE", "FAILED"):
        (out / s).unlink(missing_ok=True)
    (out / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2))
    (out / "stage.txt").write_text("시작하는 중")
    update_meta(pid_slug, status="processing", started_ts=time.time(),
                progress=0, stage="시작하는 중")
    log(f"▶ {pid_slug} (pages {job['start_page']}-{job['end_page']})")

    extra = ["--dangerously-skip-permissions"]
    if MODEL:
        extra += ["--model", MODEL]
    child_pid, fd = spawn_claude(SPAWN_CWD, extra)
    logf = open(out / "worker.log", "wb")
    try:
        drain(fd, logf, 7)
        if EFFORT and EFFORT != "none":
            submit(fd, logf, f"/effort {EFFORT}")
            drain(fd, logf, 3)
            send(fd, "\x1b")  # ESC: dismiss slash menu
            drain(fd, logf, 0.6)
        prompt = (
            f"You are processing a paper-translation job for the Moonlight reader. "
            f"Read the pipeline instructions in {PROMPT_FILE} and the job parameters "
            f"in {out / 'job.json'}, then carry out ALL steps exactly (download the "
            f"arXiv PDF, read pages {job['start_page']}-{job['end_page']}, translate to "
            f"Korean as a SENTENCE-ALIGNED {out / 'paper.json'}, extract referenced "
            f"figures/tables into {out / 'figures'}, validate with validate_paper.py). "
            f"Write {out / 'DONE'} when complete, or {out / 'FAILED'} with a short reason. "
            f"Begin now."
        )
        submit(fd, logf, prompt)
        log(f"  sent task prompt; waiting for DONE/FAILED (timeout {JOB_TIMEOUT}s)")

        deadline = time.time() + JOB_TIMEOUT
        result = None
        while time.time() < deadline:
            drain(fd, logf, POLL)
            if (out / "DONE").exists():
                result = "done"; break
            if (out / "FAILED").exists():
                result = "failed"; break
            try:
                if os.waitpid(child_pid, os.WNOHANG)[0] != 0:
                    result = "dead"; break
            except ChildProcessError:
                result = "dead"; break

        if result == "done":
            ok = (out / "paper.json").exists()
            update_meta(pid_slug, status="done" if ok else "failed",
                        progress=100 if ok else read_meta(pid_slug).get("progress", 0),
                        stage="완료" if ok else "paper.json 누락",
                        error=None if ok else "paper.json이 생성되지 않았습니다",
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            dest = JOBS / ("done" if ok else "failed")
            log(f"✔ {pid_slug} done (paper.json={'ok' if ok else 'MISSING'})")
        elif result == "failed":
            reason = (out / "FAILED").read_text().strip()[:200] or "처리 실패"
            update_meta(pid_slug, status="failed", stage="실패", error=reason,
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            dest = JOBS / "failed"; log(f"✘ {pid_slug} failed: {reason}")
        else:
            why = "claude 세션이 예기치 않게 종료됨" if result == "dead" else "시간 초과"
            update_meta(pid_slug, status="failed", stage="실패", error=why,
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            dest = JOBS / "failed"; log(f"✘ {pid_slug} {why}")
    finally:
        logf.close()
        kill(child_pid, fd)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        job_file.replace(dest / job_file.name)
    except OSError:
        pass


def claim_next():
    entries = []
    for p in (JOBS / "pending").glob("*.json"):
        try:
            entries.append((p.stat().st_mtime, p))
        except OSError:
            continue
    entries.sort(key=lambda t: t[0])
    for _, job_file in entries:
        proc = JOBS / "processing" / job_file.name
        try:
            job_file.replace(proc)  # atomic claim
            return proc
        except OSError:
            continue
    return None


def worker_loop(idx):
    while not STOP.is_set():
        try:
            job = claim_next()
        except Exception as e:
            log(f"!! [w{idx}] claim error: {e!r}"); STOP.wait(POLL); continue
        if job is None:
            STOP.wait(POLL); continue
        try:
            process(job)
        except Exception as e:
            log(f"!! [w{idx}] error: {e!r}")
            try:
                update_meta(json.loads(job.read_text())["id"], status="failed",
                            stage="실패", error=str(e)[:200])
            except Exception:
                pass
            (JOBS / "failed").mkdir(parents=True, exist_ok=True)
            try:
                job.replace(JOBS / "failed" / job.name)
            except OSError:
                pass


def main():
    for d in ("pending", "processing", "done", "failed"):
        (JOBS / d).mkdir(parents=True, exist_ok=True)
    if os.environ.get("WORKER_REQUEUE", "1") != "0":
        for jf in (JOBS / "processing").glob("*.json"):
            try:
                jf.replace(JOBS / "pending" / jf.name)
            except OSError:
                pass
    log(f"worker up. CLAUDE={CLAUDE} MODEL={MODEL} effort={EFFORT} "
        f"concurrency={CONCURRENCY} cwd={SPAWN_CWD}")
    threads = [threading.Thread(target=worker_loop, args=(i,), daemon=True, name=f"w{i}")
               for i in range(CONCURRENCY)]
    for t in threads:
        t.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        STOP.set()
        log("stopping…")


if __name__ == "__main__":
    main()
