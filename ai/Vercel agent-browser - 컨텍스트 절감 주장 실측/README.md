# PoC 재현 방법

[Vercel agent-browser - 컨텍스트 절감 주장 실측.md](Vercel%20agent-browser%20-%20%EC%BB%A8%ED%85%8D%EC%8A%A4%ED%8A%B8%20%EC%A0%88%EA%B0%90%20%EC%A3%BC%EC%9E%A5%20%EC%8B%A4%EC%B8%A1.md)의 "직접 실험" 절을 재현한다.

검증 대상은 [agent-browser.dev](https://agent-browser.dev)의 주장이다.

> 텍스트 출력이 컨텍스트 사용을 최소화한다 — ~200–400 토큰 vs 전체 DOM ~3,000–5,000 토큰

## 측정 환경 (원 실험)

| 항목 | 값 |
|---|---|
| agent-browser | v0.36.0 |
| Chrome for Testing | 152.0.7977.75 |
| 플랫폼 | macOS ARM64 (Darwin 23.1.0) |
| 토크나이저 | `tiktoken` `o200k_base` |
| 측정일 | 2026-09-02 |

## 준비

```bash
mkdir abtest && cd abtest
npm init -y
npm i agent-browser
./node_modules/.bin/agent-browser install   # Chrome for Testing 179MB 다운로드
```

> **Volta 사용자 주의**: `npm i -g agent-browser`와 `volta install agent-browser` 모두 등록은 되지만 실행 시
> `Volta error: Could not execute command`로 실패한다. 네이티브 Rust 바이너리를 Volta 심이 처리하지 못한다.
> 위처럼 프로젝트 로컬로 설치하고 `./node_modules/.bin/agent-browser`를 직접 호출한다.

토크나이저:

```bash
python3 -m venv .venv
./.venv/bin/pip install tiktoken
```

이 디렉터리의 `bench.sh`, `count.py`를 `abtest/`로 복사한다.

## 실행

```bash
bash bench.sh          # 4개 페이지 × 6가지 표현을 out/ 에 수집
./.venv/bin/python count.py   # 토큰 계수 + 절감률 표 출력
```

`bench.sh`가 페이지마다 수집하는 표현:

| 파일 접미사 | 명령 |
|---|---|
| `__rawdom` | `eval "document.documentElement.outerHTML"` |
| `__read` | `read` |
| `__snap` | `snapshot` |
| `__snap_c` | `snapshot -c` |
| `__snap_i` | `snapshot -i` |
| `__snap_ic` | `snapshot -i -c` |

`eval`은 JSON 문자열을 반환하므로 `count.py`가 이스케이프를 풀어서 계수한다. 이 처리를 빼면 raw DOM이 백슬래시만큼 부풀려져 절감률이 과대평가된다.

## 셸 주의사항

`bench.sh`는 **bash로 실행해야 한다.** fish에서는 변수 확장 시 단어 분리가 일어나지 않아
`$AB snapshot $opt` 같은 형태가 옵션 전체를 하나의 인자로 넘기고, 결과가 조용히 전체 스냅샷으로 떨어진다.
(원 실험에서 실제로 한 번 겪은 오류다.)

## 결과 재현 확인 포인트

원 실험의 핵심 결과 세 가지:

1. **절대 수치 반증** — 실제 페이지의 `snapshot`은 HN 7,281 / 위키백과 19,907 / GitHub 47,751 토큰이다. "~200–400"에 해당하는 건 example.com뿐이다.
2. **상대 절감은 성립** — GitHub 453,878 → 47,751 (89.5%↓), `-i`까지 쓰면 14,628 (96.8%↓).
3. **절감률은 DOM 비대에 비례** — DOM이 이미 얇은 HN은 36.8%로 가장 낮다.

## 추가 측정 (`-s` 버그 재현)

문서화된 `-s <selector>` 옵션이 출력을 2~4배 **늘린다.**

```bash
bash -c '
AB=./node_modules/.bin/agent-browser
$AB open "https://en.wikipedia.org/wiki/Web_browser" >/dev/null 2>&1
$AB wait --load networkidle >/dev/null 2>&1
sleep 2
echo -n "main 개수: "; $AB eval "document.querySelectorAll(\"main\").length"
$AB snapshot         --max-output 100000000 > out/wiki_full.txt
$AB snapshot -s main --max-output 100000000 > out/wiki_smain.txt
$AB close >/dev/null 2>&1
'
```

중복 방출 확인:

```bash
./.venv/bin/python -c "
import re, tiktoken
enc = tiktoken.get_encoding('o200k_base')
for f in ['out/wiki_full.txt', 'out/wiki_smain.txt']:
    s = open(f, encoding='utf-8', errors='replace').read()
    r = re.findall(r'ref=e(\d+)', s)
    print(f'{f:<22} {len(enc.encode(s)):>8,} tok  refs={len(r):>5}  unique={len(set(r)):>5}')
"
```

기대 결과 — `main`이 페이지에 **1개뿐인데도**:

| | 토큰 | ref 줄 | 고유 ref |
|---|---:|---:|---:|
| `snapshot` | 19,908 | 547 | 547 (중복 0) |
| `snapshot -s main` | **38,824** | 1,045 | 504 (약 2배 중복) |

GitHub 페이지에서는 47,752 → 212,341 토큰(4.45배), ref 줄 4,430 / 고유 913으로 더 심하게 나타난다.

## 정리 (선택)

```bash
cd .. && rm -rf abtest
rm -rf ~/.agent-browser        # 다운로드한 Chrome 179MB 제거
```
