import json
import os

import tiktoken

enc = tiktoken.get_encoding("o200k_base")

PAGES = [
    ("example_com", "example.com"),
    ("news_ycombinator_com", "news.ycombinator.com"),
    ("github_com_vercel_labs_agent_browser", "github.com/vercel-labs/agent-browser"),
    ("en_wikipedia_org_wiki_Web_browser", "wikipedia.org/wiki/Web_browser"),
]
MODES = [
    ("rawdom", "raw DOM (outerHTML)"),
    ("read", "read (본문 텍스트)"),
    ("snap", "snapshot (전체 a11y 트리)"),
    ("snap_c", "snapshot -c (compact)"),
    ("snap_i", "snapshot -i (상호작용 요소만)"),
]


def load(slug, mode):
    p = f"out/{slug}__{mode}.txt"
    if not os.path.exists(p):
        return None
    s = open(p, encoding="utf-8", errors="replace").read().strip()
    # eval 은 JSON 문자열로 반환하므로 이스케이프를 풀어 공정하게 비교한다
    if mode == "rawdom" and s.startswith('"'):
        try:
            s = json.loads(s)
        except Exception:
            pass
    return s


rows = []
for slug, name in PAGES:
    base = None
    rec = {"page": name}
    for mode, _label in MODES:
        s = load(slug, mode)
        n = len(enc.encode(s)) if s is not None else None
        rec[mode] = n
        if mode == "rawdom":
            base = n
    rec["base"] = base
    rows.append(rec)

hdr = f"{'페이지':<38}" + "".join(f"{lab:>26}" for _, lab in MODES)
print(hdr)
print("-" * len(hdr))
for r in rows:
    line = f"{r['page']:<38}"
    for mode, _ in MODES:
        n = r[mode]
        if n is None:
            line += f"{'-':>26}"
        elif mode == "rawdom":
            line += f"{n:>26,}"
        else:
            pct = 100.0 * (1 - n / r["base"]) if r["base"] else 0.0
            line += f"{f'{n:,} ({pct:.1f}%↓)':>26}"
    print(line)

print()
print("절감률 = raw DOM 대비 토큰 감소 (tiktoken o200k_base 기준)")
print()
print("공식 주장: snapshot ~200-400 tokens vs full DOM ~3,000-5,000 tokens")
print()
for r in rows:
    print(
        f"  {r['page']:<38} raw={r['rawdom']:>8,}  snapshot={r['snap']:>8,}  -i={r['snap_i']:>8,}"
    )
