#!/usr/bin/env python3
"""Paper Dashboard worker.

Watches jobs/pending/ and processes one job at a time by spawning an
**interactive** `claude` REPL in a pseudo-terminal (PTY) — exactly like
claude-web-terminal. It NEVER uses `claude -p` / headless mode.

Per job it:
  1. writes job.json into the paper's output dir,
  2. spawns interactive claude (Opus 4.8, --dangerously-skip-permissions),
  3. enables ultracode via `/effort ultracode`,
  4. sends a one-line task prompt pointing at process_paper_prompt.md,
  5. waits for the <output_dir>/DONE (or FAILED) sentinel,
  6. updates the paper's meta.json and moves the job file.

Run:  python3 worker.py
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
PAPERS_DIR = BASE / "papers"
JOBS = BASE / "jobs"
PROMPT_FILE = BASE / "process_paper_prompt.md"

CLAUDE = os.environ.get("CLAUDE_CMD") or shutil.which("claude") or "claude"
MODEL = os.environ.get("WORKER_MODEL", "claude-opus-4-8")
SPAWN_CWD = os.environ.get("WORKER_CWD", str(BASE.parent))  # a trusted dir
USE_ULTRACODE = os.environ.get("WORKER_ULTRACODE", "1") != "0"
JOB_TIMEOUT = int(os.environ.get("WORKER_JOB_TIMEOUT", "3600"))  # seconds
CONCURRENCY = max(1, int(os.environ.get("WORKER_CONCURRENCY", "2")))  # parallel jobs
POLL = 2.0
STOP = threading.Event()


def log(msg):
    print(f"[worker {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------- meta helpers ---------------------------

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
    return meta


# --------------------------- PTY claude ---------------------------

def spawn_claude(cwd, extra_args):
    """Spawn interactive claude in a PTY. Returns (pid, master_fd).

    env/argv are built in the PARENT so the post-fork child does almost no work
    before execvpe — important since we fork from worker threads.
    """
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
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        if slave_fd > 2:
            os.close(slave_fd)
        os.chdir(cwd)
        try:
            os.execvpe(CLAUDE, argv, env)
        except Exception:
            os._exit(127)
    # parent
    os.close(slave_fd)
    winsize = struct.pack("HHHH", 50, 160, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    return pid, master_fd


def drain(fd, logf, seconds):
    """Read and log PTY output for `seconds`, keeping the pipe from blocking."""
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                return
            if data:
                logf.write(data)
                logf.flush()


def send(fd, text):
    os.write(fd, text.encode())


def submit(fd, logf, text, settle=1.5):
    """Type `text` into the REPL, let it settle, then send Enter SEPARATELY.

    Claude's TUI treats a paste+CR burst as one block (the CR becomes a literal
    newline and the message is never submitted), so the Enter must be its own
    write after a short delay.
    """
    send(fd, text)
    drain(fd, logf, settle)
    send(fd, "\r")


def kill(pid, fd):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    time.sleep(0.5)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass


# --------------------------- job processing ---------------------------

def process(job_file: Path):
    job = json.loads(job_file.read_text())
    pid_slug = job["id"]
    out = Path(job["output_dir"])
    out.mkdir(parents=True, exist_ok=True)

    # clear stale sentinels
    for s in ("DONE", "FAILED"):
        (out / s).unlink(missing_ok=True)
    (out / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2))
    (out / "stage.txt").write_text("시작하는 중")

    update_meta(pid_slug, status="processing", started_ts=time.time(),
                progress=0, stage="시작하는 중")
    log(f"▶ processing {pid_slug} (pages {job['start_page']}-{job['end_page']})")

    extra = ["--dangerously-skip-permissions"]
    if MODEL:
        extra += ["--model", MODEL]
    child_pid, fd = spawn_claude(SPAWN_CWD, extra)
    logf = open(out / "worker.log", "wb")

    try:
        drain(fd, logf, 7)  # let the REPL initialize
        if USE_ULTRACODE:
            submit(fd, logf, "/effort ultracode")
            drain(fd, logf, 3)
            send(fd, "\x1b")          # ESC: dismiss any lingering slash menu
            drain(fd, logf, 0.6)

        prompt = (
            f"You are processing a paper-translation job for a dashboard. "
            f"Read the full pipeline instructions in {PROMPT_FILE} and the job "
            f"parameters in {out / 'job.json'}, then carry out ALL steps exactly "
            f"(download the arXiv PDF, read pages {job['start_page']}-{job['end_page']}, "
            f"translate to Korean honoring the description, extract referenced figures/tables, "
            f"build {out / 'paper.html'} with build_paper.py). "
            f"Write {out / 'DONE'} when fully complete, or {out / 'FAILED'} with a short reason "
            f"if you cannot continue. Begin now."
        )
        submit(fd, logf, prompt)
        log(f"  sent task prompt; waiting for DONE/FAILED (timeout {JOB_TIMEOUT}s)")

        deadline = time.time() + JOB_TIMEOUT
        result = None
        while time.time() < deadline:
            drain(fd, logf, POLL)
            if (out / "DONE").exists():
                result = "done"
                break
            if (out / "FAILED").exists():
                result = "failed"
                break
            # child died unexpectedly
            try:
                wpid, _ = os.waitpid(child_pid, os.WNOHANG)
                if wpid != 0:
                    result = "dead"
                    break
            except ChildProcessError:
                result = "dead"
                break

        if result == "done":
            html_ok = (out / "paper.html").exists()
            meta = read_meta(pid_slug)
            update_meta(pid_slug,
                        status="done" if html_ok else "failed",
                        progress=100 if html_ok else meta.get("progress", 0),
                        stage="완료" if html_ok else "HTML 누락",
                        error=None if html_ok else "paper.html이 생성되지 않았습니다",
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            log(f"✔ {pid_slug} done (html={'ok' if html_ok else 'MISSING'})")
            dest = JOBS / ("done" if html_ok else "failed")
        elif result == "failed":
            reason = (out / "FAILED").read_text().strip()[:200] or "처리 실패"
            update_meta(pid_slug, status="failed", stage="실패", error=reason,
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            log(f"✘ {pid_slug} failed: {reason}")
            dest = JOBS / "failed"
        else:
            why = "claude 세션이 예기치 않게 종료됨" if result == "dead" else "시간 초과"
            update_meta(pid_slug, status="failed", stage="실패", error=why,
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            log(f"✘ {pid_slug} {why}")
            dest = JOBS / "failed"
    finally:
        logf.close()
        kill(child_pid, fd)

    dest.mkdir(parents=True, exist_ok=True)
    try:
        job_file.replace(dest / job_file.name)
    except OSError:
        pass


def claim_next() -> Path | None:
    # Build (mtime, path) safely: a file may vanish between glob and stat when
    # another thread/worker claims it concurrently — skip those rather than crash.
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
            continue  # lost the race — try the next candidate
    return None


def worker_loop(idx: int):
    while not STOP.is_set():
        try:
            job = claim_next()
        except Exception as e:
            log(f"!! [w{idx}] claim error: {e!r}")
            STOP.wait(POLL)
            continue
        if job is None:
            STOP.wait(POLL)
            continue
        try:
            process(job)
        except Exception as e:
            log(f"!! [w{idx}] unexpected error: {e!r}")
            try:
                pid_slug = json.loads(job.read_text())["id"]
                update_meta(pid_slug, status="failed", stage="실패", error=str(e)[:200])
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
    # crash recovery: requeue anything stuck in processing/ from a previous run.
    # Skip when joining a live worker pool (WORKER_REQUEUE=0) so in-flight jobs
    # owned by another worker are not yanked back to pending.
    if os.environ.get("WORKER_REQUEUE", "1") != "0":
        for jf in (JOBS / "processing").glob("*.json"):
            try:
                jf.replace(JOBS / "pending" / jf.name)
            except OSError:
                pass
    log(f"worker up. CLAUDE={CLAUDE} MODEL={MODEL} ultracode={USE_ULTRACODE} "
        f"concurrency={CONCURRENCY} cwd={SPAWN_CWD}")
    log(f"watching jobs/pending/ with {CONCURRENCY} parallel slot(s) … (Ctrl-C to stop)")
    threads = [threading.Thread(target=worker_loop, args=(i,), daemon=True, name=f"w{i}")
               for i in range(CONCURRENCY)]
    for t in threads:
        t.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        STOP.set()
        log("stopping… (running jobs finish in the background)")


if __name__ == "__main__":
    main()
