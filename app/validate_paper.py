#!/usr/bin/env python3
"""Validate a Moonlight paper.json (schema, required fields, sid uniqueness,
image paths). Exit 0 if valid, 1 with a list of problems otherwise.

Usage:  python3 validate_paper.py <output_dir>/paper.json
"""
import json
import sys
from pathlib import Path


def validate(path: Path):
    errs = []
    try:
        paper = json.loads(path.read_text())
    except Exception as e:
        return [f"JSON 파싱 실패: {e}"]

    for k in ("titleEn", "titleKo", "blocks"):
        if k not in paper:
            errs.append(f"최상위 필수 필드 누락: {k}")
    if not isinstance(paper.get("blocks"), list) or not paper.get("blocks"):
        return errs + ["blocks 가 비어 있거나 리스트가 아님"]

    base = path.parent
    seen = set()
    for i, b in enumerate(paper["blocks"]):
        t = b.get("type")
        loc = f"blocks[{i}](type={t})"
        if t == "h2":
            for k in ("sid", "en", "ko"):
                if not b.get(k):
                    errs.append(f"{loc}: {k} 누락")
        elif t == "p":
            if not isinstance(b.get("ss"), list) or not b["ss"]:
                errs.append(f"{loc}: ss 비어 있음")
            for j, s in enumerate(b.get("ss", [])):
                if not s.get("sid"):
                    errs.append(f"{loc}.ss[{j}]: sid 누락")
                if not s.get("en") or not s.get("ko"):
                    errs.append(f"{loc}.ss[{j}]: en/ko 누락")
        elif t == "figure":
            img = b.get("img")
            if img and not (base / img).exists():
                errs.append(f"{loc}: 이미지 파일 없음 → {img}")
            if not (b.get("capEn") and b.get("capKo")):
                errs.append(f"{loc}: capEn/capKo 누락")
        elif t == "table":
            if not isinstance(b.get("rows"), list):
                errs.append(f"{loc}: rows 누락")
        elif t == "eq":
            if not b.get("tex"):
                errs.append(f"{loc}: tex 누락")
        else:
            errs.append(f"{loc}: 알 수 없는 type")

        # sid uniqueness across h2 + sentences
        sids = [b["sid"]] if t == "h2" and b.get("sid") else \
               [s.get("sid") for s in b.get("ss", [])] if t == "p" else []
        for sid in sids:
            if sid in seen:
                errs.append(f"{loc}: 중복 sid → {sid}")
            seen.add(sid)
    return errs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_paper.py <paper.json>"); sys.exit(2)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"파일 없음: {p}"); sys.exit(1)
    problems = validate(p)
    if problems:
        print(f"❌ {len(problems)}개 문제:")
        for e in problems:
            print("  -", e)
        sys.exit(1)
    print(f"✅ 유효한 paper.json ({p})")
    sys.exit(0)
