# Vite 내부 구조 - 네이티브 ESM 개발 서버와 의존성 사전 번들링은 어떻게 동작하는가

## 출처
- **아티클/논문**: How Vite Works: ES Modules, Dependency Pre-Bundling, and the Architecture Behind the Fastest Dev Server
- **저자/출처**: Let's Build Solutions (Web Engineering Blog)
- **링크**: https://letsbuildsolutions.com/blog/web-engineering/how-vite-works-es-modules-dependency-pre-bundling-and-the-architecture-behind-the-fastest-dev-server/

---

## AI 요약

### 1. Vite란?

Vite(프랑스어로 "빠르다", "비트"라고 읽는다)는 Vue 창시자 Evan You가 만든 **프론트엔드 빌드 도구**다. webpack처럼 "개발 서버 + 프로덕션 번들러" 역할을 하지만, 접근 방식이 근본적으로 다르다.

| 특성 | 내용 |
|---|---|
| 핵심 아이디어 | 개발 중에는 번들링하지 않고, 브라우저의 **네이티브 ES Module**을 그대로 활용 |
| 개발 서버 | 파일을 요청받을 때만(on-demand) 변환해서 ESM으로 서빙 |
| 의존성 처리 | esbuild(Go 기반, JS 번들러 대비 10~100배 빠름)로 사전 번들링 |
| 프로덕션 빌드 | Rollup 기반 (최신 버전은 Rust 기반 Rolldown으로 통합 중) |
| 위치 | React/Vue/Svelte 등 프레임워크 불문, 현대 프론트엔드의 사실상 표준 빌드 도구 |

한 줄 요약: **"개발할 때는 번들을 만들지 않는 번들러"**.

### 2. 기존 번들러 기반 개발 서버의 문제

webpack 시대의 개발 서버는 브라우저에 뭔가를 보여주기 전에 **앱 전체의 모듈 그래프를 처리**해야 했다.

```
[webpack dev server]

  entry.js ─┬─> 모든 모듈 파싱/변환/번들링 ──> bundle.js ──> 브라우저
            │   (앱이 클수록 오래 걸림)
  수백~수천 개 모듈
```

- 앱이 커질수록 서버 기동이 느려진다 (수십 초~분 단위).
- 파일 하나를 고쳐도 번들 일부를 다시 만들어야 해서 HMR도 앱 크기에 비례해 느려진다.

### 3. Vite의 해법: 소스는 네이티브 ESM으로, 의존성은 사전 번들링

Vite는 코드를 두 종류로 나눠서 다르게 취급한다.

```
[Vite dev server]

  의존성(node_modules)          소스 코드(내 코드)
  ── 자주 안 바뀜               ── 자주 바뀜
  ── esbuild로 1회 사전 번들링    ── 번들링 없이 요청 시 변환
        │                            │
        v                            v
  node_modules/.vite/deps/     HTTP로 개별 ESM 서빙
        └──────────┬────────────────┘
                   v
        브라우저가 <script type="module">로
        import 체인을 따라가며 직접 로드
```

- **소스 코드**: 각 파일을 개별 ES 모듈로 서빙하고, 모듈 그래프 해석은 브라우저에 맡긴다. 브라우저가 요청한 파일만 그 순간에 변환하므로, 서버 기동이 앱 크기와 무관하게 거의 즉시 끝난다.
- **의존성**: CommonJS로 배포된 패키지는 브라우저 ESM에서 그대로 못 쓰므로, esbuild로 ESM으로 변환·번들링해 `node_modules/.vite/deps/`에 캐시한다. lockfile과 설정의 해시로 캐시 유효성을 추적한다. (수백 개 내부 모듈을 가진 lodash-es 같은 패키지를 하나로 합쳐 HTTP 요청 폭발도 막는다.)

### 4. HMR: 모듈 그래프와 HMR 경계

Vite 서버는 모듈 간 import 관계를 **모듈 그래프**로 명시적으로 추적한다. 파일이 바뀌면:

```
변경된 파일
    │  import 체인을 거슬러 올라감
    v
가장 가까운 "HMR 경계" 탐색
(import.meta.hot.accept() 핸들러가 있는 모듈)
    │
    v
해당 모듈만 브라우저에서 교체 (전체 리로드 없음)
```

경계 탐색이 그래프 지역 탐색이라 **HMR 속도가 앱 전체 크기와 무관**하다. React Fast Refresh, Vue SFC 등 프레임워크 플러그인이 컴포넌트 파일마다 자동으로 경계를 심어준다.

### 5. 플러그인 파이프라인: Rollup 훅 + Vite 전용 훅

Vite 플러그인은 Rollup 플러그인 인터페이스의 확장이다.

| 훅 | 역할 |
|---|---|
| `resolveId()` | import 문자열을 실제 파일(또는 가상 모듈)로 매핑 |
| `load()` | 해당 id의 소스 코드를 반환 |
| `transform()` | 소스 코드 변환 (TS 컴파일, JSX 등) |
| `configureServer()` | (Vite 전용) 개발 서버 미들웨어 확장 |
| `transformIndexHtml()` | (Vite 전용) HTML 조작 |
| `handleHotUpdate()` | (Vite 전용) HMR 동작 커스터마이즈 |

가상 모듈은 `\0` 접두사 컨벤션으로 실제 파일과 구분한다. 덕분에 Rollup 생태계 플러그인 상당수를 개발/빌드 양쪽에서 재사용할 수 있다.

### 6. 프로덕션 빌드는 왜 여전히 번들링하는가, 왜 Rollup인가

- **번들링이 필요한 이유**: 비번들 ESM을 프로덕션에 그대로 내보내면 중첩 import마다 네트워크 왕복이 발생해 비효율적이다. 배포용은 여전히 번들이 유리하다.
- **esbuild가 아니라 Rollup인 이유**: esbuild는 빠르지만, 설계 당시 기준으로 고급 코드 스플리팅, CSS 추출, 트리셰이킹 엣지 케이스 등 최적화 품질에서 Rollup에 밀렸고, JS 플러그인 생태계도 Rollup 쪽이 훨씬 풍부했다. 즉 **개발은 속도(esbuild), 배포는 최적화 품질(Rollup)**로 역할을 분담한 것.
- **Rolldown으로의 통합**: dev와 build가 다른 도구를 쓰면 미묘한 동작 불일치가 생긴다. 그래서 Vite 팀은 Rust 기반이면서 Rollup 플러그인 API와 호환되는 **Rolldown**을 만들어 두 역할을 하나로 합치는 중이다 (파싱/변환은 Oxc).

### 7. 경쟁 도구와의 비교

| 항목 | Vite | webpack | esbuild 단독 | Turbopack |
|---|---|---|---|---|
| 서버 기동 | 즉시 (비번들) | 느림 (전체 번들) | 빠름 | 빠름 (증분) |
| HMR | 앱 크기 무관 | 앱 크기 비례 | 제한적 | 빠름 |
| 프로덕션 최적화 | Rollup 수준 | 성숙함 | 기본적 | 발전 중 |
| 플러그인 생태계 | Rollup 호환, 큼 | 가장 큼 | 작음 | Next.js 중심 |
| 설정 복잡도 | 낮음 | 높음 | 낮음 | 낮음 |

아티클은 Vite가 맞지 않는 경우도 짚는다: 성숙한 webpack 설정을 가진 대형 레거시, IE11 지원 요구, 특수한 모노레포 구성 등.

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **"일을 없애는" 최적화가 "일을 빨리 하는" 최적화를 이긴다**
   - webpack → esbuild는 같은 일을 빨리 하는 개선이지만, Vite의 본질은 개발 중 번들링이라는 일 자체를 브라우저(네이티브 ESM)에 위임해 없앤 것이다. 플랫폼이 새 기능을 얻으면 도구 계층의 일을 통째로 걷어낼 수 있는지 먼저 물어야 한다.

2. **변화 빈도로 데이터를 나누는 캐싱 전략**
   - "의존성은 거의 안 바뀌니 1회 사전 번들링 + 해시 캐시, 소스는 자주 바뀌니 on-demand 변환"이라는 이분법은 빌드 도구 밖에서도 통하는 일반 원칙이다 (CDN 캐싱, 도커 레이어 순서 등과 같은 사고방식).

3. **dev/prod 파이프라인 이원화의 비용**
   - esbuild(dev)와 Rollup(prod)의 분담은 각자 최적이지만 "개발에선 됐는데 빌드에서 깨진다"는 불일치를 낳았고, 결국 Rolldown이라는 단일 파이프라인으로 회귀 중이다. 두 경로를 두는 설계는 언젠가 일관성 비용을 청구한다.

### 이 저장소 문서와의 연결 (electron-vite)

1. **Vite는 Electron 개념이 아니다**
   - [Electron 소스코드 보호 문서](Electron%20데스크탑%20앱%20소스코드%20보호%20-%20V8%20바이트코드%20컴파일과%20ASAR%20무결성%20검증.md)에 나오는 electron-vite는, 범용 빌드 도구인 Vite를 Electron의 3개 진입점(main / preload / renderer)에 맞게 감싼 별도 프로젝트다.
   - renderer는 브라우저 환경이라 Vite의 ESM dev 서버·HMR을 그대로 쓰고, main/preload는 Node 환경이라 번들 빌드를 쓴다. V8 바이트코드 컴파일 같은 보호 기능은 Vite 본체가 아니라 electron-vite가 빌드 파이프라인 끝에 얹은 것이다.

### 실무 적용 관점

1. **플러그인 호환성이 생태계 승부를 갈랐다**
   - Vite가 Rollup 플러그인 인터페이스를 채택한 덕에 기존 생태계를 흡수하며 출발했고, Rolldown조차 Rollup API 호환을 최우선으로 설계됐다. 새 도구를 만들 때 "기존 확장 생태계와의 호환 계층"은 성능만큼 중요한 채택 요인이다.

2. **HMR이 느려지면 경계를 의심하라**
   - HMR 속도는 앱 크기가 아니라 변경 지점에서 가장 가까운 HMR 경계까지의 거리에 좌우된다. 특정 파일 수정 시 전체 리로드가 난다면 그 import 체인에 `import.meta.hot.accept()` 경계가 없는 것이므로, 상태를 가진 모듈을 경계로 분리하는 식으로 구조를 손봐야 한다.
