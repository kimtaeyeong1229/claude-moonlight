#!/usr/bin/env python3
"""Moonlight dashboard server.

Serves the two-pane bilingual paper viewer and a small dashboard. Adding a paper
enqueues a job that an interactive Claude worker (worker.py) processes by driving
an interactive `claude` REPL in a PTY — never `claude -p` (see plans/v0.3.md §C).

Output of the pipeline is an aligned `paper.json` (sentence-level EN<->KO map),
which the viewer renders side-by-side with hover highlighting.

Run:  python3 server.py            # http://127.0.0.1:8090
"""
import datetime
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from aiohttp import web

BASE = Path(__file__).parent
STATIC_DIR = BASE / "static"
DATA = Path(os.environ.get("MOONLIGHT_DATA", BASE.parent / "data"))
PAPERS_DIR = DATA / "papers"
JOBS_DIR = DATA / "jobs"
REGISTRY = DATA / "papers.json"
SAMPLE_DIR = BASE / "sample"

PORT = int(os.environ.get("DASHBOARD_PORT", "8090"))
# Bind 127.0.0.1 for local runs; the container sets SERVER_HOST=0.0.0.0 so the
# published (host-loopback-only) port can reach it.
HOST = os.environ.get("SERVER_HOST", "127.0.0.1")
SECONDS_PER_PAGE = int(os.environ.get("ETA_SECONDS_PER_PAGE", "75"))
ETA_BASE = 60

for d in [PAPERS_DIR, JOBS_DIR / "pending", JOBS_DIR / "processing",
          JOBS_DIR / "done", JOBS_DIR / "failed"]:
    d.mkdir(parents=True, exist_ok=True)


# ----------------------------- helpers -----------------------------

def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def load_registry() -> list:
    try:
        return json.loads(REGISTRY.read_text()).get("papers", [])
    except (OSError, json.JSONDecodeError):
        return []


def save_registry(ids: list):
    tmp = REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"papers": ids}, ensure_ascii=False, indent=2))
    tmp.replace(REGISTRY)


def read_meta(pid: str):
    try:
        return json.loads((PAPERS_DIR / pid / "meta.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None


def write_meta(pid: str, meta: dict):
    d = PAPERS_DIR / pid
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    tmp.replace(d / "meta.json")


def arxiv_id_from_url(url: str):
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", url)
    return m.group(0) if m else None


def make_slug(arxiv_url: str, existing: set) -> str:
    aid = arxiv_id_from_url(arxiv_url)
    base = re.sub(r"[^A-Za-z0-9._-]", "-",
                  ("arxiv-" + aid) if aid else "paper").strip("-") or "paper"
    slug, n = base, 2
    while slug in existing:
        slug, n = f"{base}-{n}", n + 1
    return slug


def estimate_eta(start: int, end: int) -> int:
    return ETA_BASE + max(1, end - start + 1) * SECONDS_PER_PAGE


KNOWN_VENUES = ["NeurIPS", "NIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV", "ACL",
                "EMNLP", "NAACL", "AAAI", "IJCAI", "KDD", "WWW", "TMLR", "JMLR",
                "AISTATS", "COLM", "SIGGRAPH", "INTERSPEECH", "ICASSP"]


def detect_venue(text: str) -> str:
    if not text:
        return ""
    for v in KNOWN_VENUES:
        if re.search(r"\b" + re.escape(v) + r"\b", text, re.I):
            ym = re.search(r"(19|20)\d{2}", text)
            return f"{v} {ym.group(0)}" if ym else v
    return ""


async def fetch_arxiv_meta(session_factory, arxiv_id: str) -> dict:
    fallback_year = ""
    mm = re.match(r"(\d{2})(\d{2})", arxiv_id)
    if mm:
        fallback_year = "20" + mm.group(1)
    out = {"title": f"arXiv:{arxiv_id}", "venue": "arXiv preprint", "year": fallback_year}
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        import aiohttp
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
            out["venue"] = detect_venue(blob) or (
                jref.text.strip().split(",")[0][:48] if jref is not None and jref.text
                else "arXiv preprint")
    except Exception:
        pass
    return out


def enrich(meta: dict) -> dict:
    m = dict(meta)
    if m.get("status") == "processing":
        try:
            txt = (PAPERS_DIR / m["id"] / "stage.txt").read_text().strip()
            if txt:
                m["stage"] = txt.splitlines()[-1][:60]
        except OSError:
            pass
        started, eta_total = m.get("started_ts"), m.get("eta_seconds") or 0
        if started:
            elapsed = max(0, time.time() - started)
            m["remaining_seconds"] = max(0, int(eta_total - elapsed))
            if eta_total > 0:
                m["progress"] = max(int(m.get("progress", 0)),
                                    min(95, int(elapsed / eta_total * 100)))
    return m


def ensure_sample():
    """Preload a bundled aligned sample so the app is usable immediately."""
    src = SAMPLE_DIR / "paper.json"
    if not src.exists():
        return
    pid = "sample-sparse-attention"
    d = PAPERS_DIR / pid
    if (d / "paper.json").exists():
        return
    d.mkdir(parents=True, exist_ok=True)
    (d / "paper.json").write_text(src.read_text())
    paper = json.loads(src.read_text())
    write_meta(pid, {
        "id": pid, "title": paper.get("titleEn", "Sample"),
        "venue": "NeurIPS 2025 (sample)", "year": "2025",
        "status": "done", "progress": 100, "stage": "완료",
        "created_at": now_iso(),
    })
    ids = load_registry()
    if pid not in ids:
        ids.append(pid)
        save_registry(ids)


# ----------------------------- API -----------------------------

async def index(request):
    return web.FileResponse(STATIC_DIR / "index.html")


async def api_health(request):
    return web.json_response({"ok": True, "time": now_iso()})


async def api_list(request):
    out = []
    for pid in load_registry():
        meta = read_meta(pid)
        if meta:
            out.append(enrich(meta))
    out.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return web.json_response(out)


async def api_get(request):
    meta = read_meta(request.match_info["id"])
    if not meta:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(enrich(meta))


async def api_add(request):
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
    if not arxiv_url or not arxiv_id_from_url(arxiv_url):
        return web.json_response({"error": "valid arXiv URL required"}, status=400)
    if start_page < 1 or end_page < start_page:
        return web.json_response({"error": "invalid page range"}, status=400)

    ids = load_registry()
    slug = make_slug(arxiv_url, set(ids))
    aid = arxiv_id_from_url(arxiv_url)
    am = await fetch_arxiv_meta(None, aid)
    eta = estimate_eta(start_page, end_page)

    write_meta(slug, {
        "id": slug, "title": body.get("title") or am["title"],
        "venue": am["venue"], "year": am["year"], "arxiv_url": arxiv_url, "arxiv_id": aid,
        "start_page": start_page, "end_page": end_page, "description": description,
        "status": "queued", "progress": 0, "stage": "대기 중",
        "eta_seconds": eta, "created_at": now_iso(),
    })
    job = {"id": slug, "arxiv_url": arxiv_url, "arxiv_id": aid,
           "start_page": start_page, "end_page": end_page, "description": description,
           "output_dir": str(PAPERS_DIR / slug), "created_at": now_iso()}
    tmp = JOBS_DIR / "pending" / f"{slug}.json.tmp"
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2))
    tmp.replace(JOBS_DIR / "pending" / f"{slug}.json")

    ids.append(slug)
    save_registry(ids)
    return web.json_response({"id": slug, "eta_seconds": eta}, status=201)


async def api_delete(request):
    pid = request.match_info["id"]
    ids = load_registry()
    if pid in ids:
        ids.remove(pid)
        save_registry(ids)
    jf = JOBS_DIR / "pending" / f"{pid}.json"
    if jf.exists():
        jf.unlink()
    import shutil
    shutil.rmtree(PAPERS_DIR / pid, ignore_errors=True)
    return web.json_response({"ok": True})


def create_app():
    ensure_sample()
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/api/health", api_health)
    app.router.add_get("/api/papers", api_list)
    app.router.add_post("/api/papers", api_add)
    app.router.add_get("/api/papers/{id}", api_get)
    app.router.add_delete("/api/papers/{id}", api_delete)
    app.router.add_static("/papers/", PAPERS_DIR, show_index=False)
    app.router.add_static("/static/", STATIC_DIR, show_index=False)
    return app


if __name__ == "__main__":
    print(f"\n  🌙 Moonlight  →  http://127.0.0.1:{PORT}  (bind {HOST})\n")
    web.run_app(create_app(), host=HOST, port=PORT, print=None)
