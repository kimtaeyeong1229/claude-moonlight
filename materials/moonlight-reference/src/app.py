#!/usr/bin/env python3
"""Paper Dashboard server.

A web dashboard to translate arXiv papers into Korean (Medium-style HTML),
reusing the DeepSeek-R1 pipeline. Adding a paper enqueues a job that an
interactive Claude worker (worker.py) processes — never via `claude -p`.

Run:  python3 app.py            # serves http://127.0.0.1:8090
"""
import json
import os
import re
import time
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

import aiohttp
from aiohttp import web

BASE = Path(__file__).parent
STATIC_DIR = BASE / "static"
PAPERS_DIR = BASE / "papers"
JOBS_DIR = BASE / "jobs"
REGISTRY = BASE / "papers.json"

PORT = int(os.environ.get("DASHBOARD_PORT", "8090"))
# Rough ETA model: per-page seconds for the full translate+figures+build pipeline.
SECONDS_PER_PAGE = int(os.environ.get("ETA_SECONDS_PER_PAGE", "75"))
ETA_BASE = 60  # fixed overhead (download, spawn, build)

for d in [PAPERS_DIR, JOBS_DIR / "pending", JOBS_DIR / "processing",
          JOBS_DIR / "done", JOBS_DIR / "failed"]:
    d.mkdir(parents=True, exist_ok=True)


# ----------------------------- helpers -----------------------------

def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def load_registry() -> list[str]:
    try:
        return json.loads(REGISTRY.read_text()).get("papers", [])
    except (OSError, json.JSONDecodeError):
        return []


def save_registry(ids: list[str]):
    tmp = REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"papers": ids}, ensure_ascii=False, indent=2))
    tmp.replace(REGISTRY)


def read_meta(pid: str) -> dict | None:
    f = PAPERS_DIR / pid / "meta.json"
    try:
        return json.loads(f.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def write_meta(pid: str, meta: dict):
    d = PAPERS_DIR / pid
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    tmp.replace(d / "meta.json")


def read_tags(pid: str) -> list:
    """Custom user tags, stored SEPARATELY from meta.json so worker writes
    (status/stage) and tag writes never clobber each other."""
    try:
        t = json.loads((PAPERS_DIR / pid / "tags.json").read_text())
        return t if isinstance(t, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def write_tags(pid: str, tags: list) -> bool:
    d = PAPERS_DIR / pid
    if not d.exists():
        return False
    tmp = d / "tags.json.tmp"
    tmp.write_text(json.dumps(tags, ensure_ascii=False, indent=2))
    tmp.replace(d / "tags.json")
    return True


def read_en_title(pid: str):
    """Original English title, kept in a sidecar so the worker (which may write a
    Korean title into meta.json) can never overwrite the display title."""
    try:
        t = (PAPERS_DIR / pid / "en_title.txt").read_text().strip()
        return t or None
    except OSError:
        return None


def write_en_title(pid: str, title: str):
    d = PAPERS_DIR / pid
    if d.exists():
        (d / "en_title.txt").write_text(title or "")


def arxiv_id_from_url(url: str) -> str | None:
    """Extract an arXiv id like 2501.12948 (optionally with version) from a URL/string."""
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", url)
    return m.group(0) if m else None


def make_slug(arxiv_url: str, existing: set[str]) -> str:
    aid = arxiv_id_from_url(arxiv_url)
    base = ("arxiv-" + aid) if aid else "paper"
    base = re.sub(r"[^A-Za-z0-9._-]", "-", base).strip("-") or "paper"
    slug = base
    n = 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    return slug


def estimate_eta(start: int, end: int) -> int:
    pages = max(1, end - start + 1)
    return ETA_BASE + pages * SECONDS_PER_PAGE


KNOWN_VENUES = [
    "NeurIPS", "NIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV", "WACV", "ACL",
    "EMNLP", "NAACL", "COLING", "AAAI", "IJCAI", "KDD", "WWW", "SIGGRAPH",
    "TMLR", "JMLR", "AISTATS", "UAI", "COLM", "ECML", "INTERSPEECH", "ICASSP",
    "SIGIR", "RecSys", "CoRL", "RSS", "ICRA", "IROS", "MICCAI", "MLSys",
]


def detect_venue(text: str) -> str:
    """Pick a known venue (+ nearby year) out of journal_ref/comment text."""
    if not text:
        return ""
    for v in KNOWN_VENUES:
        if re.search(r"\b" + re.escape(v) + r"\b", text, re.I):
            ym = re.search(r"(19|20)\d{2}", text)
            return f"{v} {ym.group(0)}" if ym else v
    return ""


async def fetch_arxiv_meta(arxiv_id: str) -> dict:
    """Best-effort (title, venue, year) from the arXiv API. Robust fallbacks."""
    fallback_year = ""
    mm = re.match(r"(\d{2})(\d{2})", arxiv_id)
    if mm:
        fallback_year = "20" + mm.group(1)  # arXiv id encodes YYMM
    out = {"title": f"arXiv:{arxiv_id}", "venue": "arXiv preprint", "year": fallback_year}
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url) as r:
                xml = await r.text()
        ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        entry = ET.fromstring(xml).find("a:entry", ns)
        if entry is not None:
            t = entry.find("a:title", ns)
            if t is not None and t.text:
                out["title"] = " ".join(t.text.split())
            pub = entry.find("a:published", ns)
            if pub is not None and pub.text:
                out["year"] = pub.text[:4]
            jref = entry.find("arxiv:journal_ref", ns)
            comment = entry.find("arxiv:comment", ns)
            blob = " ".join(x.text for x in (jref, comment) if x is not None and x.text)
            v = detect_venue(blob)
            if v:
                out["venue"] = v
            elif jref is not None and jref.text:
                out["venue"] = jref.text.strip().split(",")[0][:48]
            else:
                out["venue"] = "arXiv preprint"
    except Exception:
        pass
    return out


def enrich_status(meta: dict) -> dict:
    """Add a derived live ETA (remaining seconds) for processing papers."""
    m = dict(meta)
    if m.get("status") == "processing":
        # live stage text written by the worker's Claude session (advisory display)
        stage_file = PAPERS_DIR / m["id"] / "stage.txt"
        try:
            txt = stage_file.read_text().strip()
            if txt:
                m["stage"] = txt.splitlines()[-1][:60]
        except OSError:
            pass
        started = m.get("started_ts")
        eta_total = m.get("eta_seconds") or 0
        if started:
            elapsed = max(0, time.time() - started)
            m["elapsed_seconds"] = int(elapsed)
            m["remaining_seconds"] = max(0, int(eta_total - elapsed))
            # progress floor based on time if worker hasn't reported a higher value
            if eta_total > 0:
                time_pct = min(95, int(elapsed / eta_total * 100))
                m["progress"] = max(int(m.get("progress", 0)), time_pct)
    return m


# ----------------------------- API -----------------------------

async def index(request):
    return web.FileResponse(STATIC_DIR / "index.html")


async def api_list_papers(request):
    out = []
    for pid in load_registry():
        meta = read_meta(pid)
        if meta:
            m = enrich_status(meta)
            m["tags"] = read_tags(pid)
            m["en_title"] = read_en_title(pid)
            out.append(m)
    # newest first
    out.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return web.json_response(out)


async def api_get_paper(request):
    pid = request.match_info["id"]
    meta = read_meta(pid)
    if not meta:
        return web.json_response({"error": "not found"}, status=404)
    m = enrich_status(meta)
    m["tags"] = read_tags(pid)
    m["en_title"] = read_en_title(pid)
    return web.json_response(m)


async def api_set_tags(request):
    pid = request.match_info["id"]
    if read_meta(pid) is None:
        return web.json_response({"error": "not found"}, status=404)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)
    raw = body.get("tags", [])
    if not isinstance(raw, list):
        return web.json_response({"error": "tags must be a list"}, status=400)
    clean = []
    for t in raw[:10]:  # cap at 10
        if not isinstance(t, dict):
            continue
        text = str(t.get("text", "")).strip()[:30]
        try:
            color = int(t.get("color", 0))
        except (TypeError, ValueError):
            color = 0
        color = color if 0 <= color <= 4 else 0
        if text:
            clean.append({"text": text, "color": color})
    write_tags(pid, clean)
    return web.json_response({"ok": True, "tags": clean})


async def api_add_paper(request):
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)

    arxiv_url = (body.get("arxiv_url") or "").strip()
    description = (body.get("description") or "").strip()
    try:
        start_page = int(body.get("start_page"))
        end_page = int(body.get("end_page"))
    except (TypeError, ValueError):
        return web.json_response({"error": "start_page/end_page must be integers"}, status=400)

    if not arxiv_url:
        return web.json_response({"error": "arxiv_url is required"}, status=400)
    if not arxiv_id_from_url(arxiv_url):
        return web.json_response({"error": "could not find an arXiv id in the URL"}, status=400)
    if start_page < 1 or end_page < start_page:
        return web.json_response({"error": "invalid page range"}, status=400)

    ids = load_registry()
    slug = make_slug(arxiv_url, set(ids))
    eta = estimate_eta(start_page, end_page)
    aid = arxiv_id_from_url(arxiv_url)

    # Pull the real title / venue / year from the arXiv API (best-effort).
    am = await fetch_arxiv_meta(aid)

    meta = {
        "id": slug,
        "title": body.get("title") or am["title"],
        "venue": am["venue"],
        "year": am["year"],
        "arxiv_url": arxiv_url,
        "arxiv_id": aid,
        "start_page": start_page,
        "end_page": end_page,
        "description": description,
        "status": "queued",
        "progress": 0,
        "stage": "대기 중",
        "eta_seconds": eta,
        "created_at": now_iso(),
    }
    write_meta(slug, meta)
    write_en_title(slug, am["title"])  # original English title (sidecar)

    job = {
        "id": slug,
        "arxiv_url": arxiv_url,
        "arxiv_id": arxiv_id_from_url(arxiv_url),
        "start_page": start_page,
        "end_page": end_page,
        "description": description,
        "output_dir": str(PAPERS_DIR / slug),
        "created_at": now_iso(),
    }
    tmp = JOBS_DIR / "pending" / f"{slug}.json.tmp"
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2))
    tmp.replace(JOBS_DIR / "pending" / f"{slug}.json")

    ids.append(slug)
    save_registry(ids)

    return web.json_response({"id": slug, "eta_seconds": eta}, status=201)


async def api_delete_paper(request):
    pid = request.match_info["id"]
    ids = load_registry()
    if pid in ids:
        ids.remove(pid)
        save_registry(ids)
    # remove queued job if any (don't kill in-flight processing dir)
    for sub in ("pending",):
        jf = JOBS_DIR / sub / f"{pid}.json"
        if jf.exists():
            jf.unlink()
    import shutil
    d = PAPERS_DIR / pid
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    return web.json_response({"ok": True})


def create_app():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/api/papers", api_list_papers)
    app.router.add_post("/api/papers", api_add_paper)
    app.router.add_get("/api/papers/{id}", api_get_paper)
    app.router.add_post("/api/papers/{id}/tags", api_set_tags)
    app.router.add_delete("/api/papers/{id}", api_delete_paper)
    app.router.add_static("/papers/", PAPERS_DIR, show_index=False)
    app.router.add_static("/static/", STATIC_DIR, show_index=False)
    return app


if __name__ == "__main__":
    print(f"\n  Paper Dashboard")
    print(f"  http://127.0.0.1:{PORT}\n")
    web.run_app(create_app(), host="127.0.0.1", port=PORT, print=None)
