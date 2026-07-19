# Playwright E2E 테스트 속도 개선 - 병렬화·리소스 차단·인증 재사용으로 피드백 루프 단축하기

## 출처
- **아티클/논문**: How To Speed Up Playwright Tests: 7 Tips From Experts
- **저자/출처**: Currents.dev Blog
- **링크**: https://currents.dev/posts/how-to-speed-up-playwright-tests

---

## AI 요약

### 1. 왜 E2E 테스트 속도가 문제인가?

E2E(End-to-End) 테스트는 실제 브라우저를 띄우고, 네트워크 왕복을 하고, 페이지를 렌더링한다. 단위 테스트와 달리 **한 테스트당 수 초~수십 초**가 기본이라, 테스트 수가 늘어나면 CI 피드백 루프가 급격히 길어진다.

> 예시: 30초짜리 테스트 100개를 **단일 워커**로 돌리면 약 50분. 워커를 4개로 늘리면 **12~15분**으로 단축.

속도 개선의 핵심은 두 축이다.

| 축 | 개념 | 대표 기법 |
|---|---|---|
| **더 많이 동시에** | 병렬성 확보 | workers, fullyParallel, sharding |
| **각 테스트를 더 가볍게** | 낭비 제거 | 리소스 차단, 인증 재사용, 불필요한 reload 제거 |

아래 7가지는 이 두 축을 조합한 실전 최적화 목록이다.

---

### 2. 병렬성(Parallelism)을 제대로 활용하라

가장 효과가 큰 지렛대. Playwright는 **worker**(단일 머신 내 프로세스 병렬)와 **sharding**(여러 머신 분산)을 제공한다.

```javascript
// playwright.config.ts
export default defineConfig({
  workers: process.env.CI ? 4 : undefined, // CI에선 고정, 로컬은 자동
  fullyParallel: true,                     // 파일 내 테스트까지 병렬화
});
```

```bash
# 여러 머신으로 분산 (sharding)
npx playwright test --shard=1/4
npx playwright test --shard=2/4
```

```
단일 워커                     4 워커 (fullyParallel)
┌──────────────────────┐     ┌─────┬─────┬─────┬─────┐
│ t1 t2 t3 ... t100    │     │ W1  │ W2  │ W3  │ W4  │
│  ───────────────►    │     │ t1  │ t2  │ t3  │ t4  │
│      ~50분           │     │ t5  │ t6  │ ... │ ... │
└──────────────────────┘     └─────┴─────┴─────┴─────┘
                                    ~12~15분
```

**트레이드오프**: 워커 1개당 브라우저 인스턴스가 하나씩 뜬다. 과도한 병렬화는 **CPU 경합·메모리 압박·OOM**을 유발한다. 또 sharding을 파일명 사전순(lexical)으로 나누면 부하가 한쪽으로 쏠린다.
> 실제 사례: 워커 4개에선 통과하던 테스트가 15~20개에서 CPU 경합으로 브라우저 렌더링이 밀려 실패.
> **경험칙**: 물리 코어 4개 → 워커 2~4개, 8코어 → 6~8개가 효율 한계.

---

### 3. 불필요한 페이지 reload를 피하라

`page.goto()` 한 번은 **DNS 조회 → 네트워크 왕복 → JS 실행 → 렌더링** 전체를 다시 돈다. 테스트마다 반복하면 낭비다.

```javascript
// 공통 준비는 beforeEach로 모으고, 쿠키를 미리 주입
test.beforeEach(async ({ page, context }) => {
  await context.addCookies(preAuthCookies);
  await page.goto("https://example.com/dashboard");
});

// 전체 로드 대신 DOM 준비 시점까지만 대기
await page.goto("https://example.com", { waitUntil: "domcontentloaded" });
```

**트레이드오프**: 일부 앱은 모든 리소스가 로드돼야 정상 동작한다. `domcontentloaded`가 오히려 flaky를 만들 수 있으니 대상별로 확인.

---

### 4. CI에서는 headless로 돌려라

Headless 모드는 화면 렌더링을 건너뛰어 headed 대비 **10~30% 빠르다**. Playwright는 CI에서 기본 headless.

```javascript
export default defineConfig({
  use: { headless: process.env.CI ? true : false },
});
```

**트레이드오프**: GPU 가속 애니메이션·Canvas 렌더링 결과가 달라질 수 있어, **비주얼 회귀(visual regression) 테스트**는 headed가 필요할 수 있다.

---

### 5. Fail-Fast: 일정 실패 수에서 조기 종료

전부 실패한 뒤에야 결과를 보는 대신, N개 실패 시 즉시 멈춰 **낭비되는 CI 시간을 절약**한다.

```javascript
export default defineConfig({
  maxFailures: process.env.CI ? 10 : undefined,
});
```
```bash
npx playwright test --max-failures=10
```

**트레이드오프**: 나머지 실패를 가린다. Flaky 테스트가 많으면 일시적 실패 하나로 전체가 조기 종료돼 오히려 손해일 수 있다.

---

### 6. 변경된 테스트만 실행 (`--only-changed`)

Playwright v1.46+ 부터 코드 변경의 영향을 받는 테스트만 실행 가능.

```bash
npx playwright test --only-changed=origin/main
```
```yaml
# GitHub Actions
- name: Run changed tests
  run: npx playwright test --only-changed=origin/${{ github.base_ref }}
```

**트레이드오프**: **정적 파일 의존성 분석**에 의존한다. 런타임 import, 환경 변수 기반 동작, 백엔드 주도 UI 변경, 공유 설정/서비스의 간접 영향은 감지하지 못한다. → PR 게이트로는 유용하지만 **머지 전 full run은 별도로** 두는 게 안전.

---

### 7. 인증(Auth) 상태를 저장해 재사용하라

매 테스트마다 로그인 플로우를 반복하면 큰 비용이다.
> 100개 테스트 기준, **인증에만 8~25분**이 소모될 수 있다.

로그인은 한 번만 수행하고 상태(storageState)를 저장해 모든 테스트가 재사용한다.

```javascript
// auth.setup.ts
import { test as setup } from "@playwright/test";
const authFile = "playwright/.auth/user.json";

setup("authenticate", async ({ page }) => {
  await page.goto("https://example.com/login");
  await page.fill("#email", "test@example.com");
  await page.fill("#password", "password");
  await page.click('button[type="submit"]');
  await page.waitForURL("https://example.com/dashboard");
  await page.context().storageState({ path: authFile }); // 쿠키·localStorage 저장
});
```

```javascript
// playwright.config.ts — setup을 의존성으로 연결
export default defineConfig({
  projects: [
    { name: "setup", testMatch: /.*\.setup\.ts/ },
    {
      name: "chromium",
      use: { storageState: "playwright/.auth/user.json" },
      dependencies: ["setup"],
    },
  ],
});
```

**트레이드오프**: 로그인/인가 플로우 자체는 우회된다(그 경로는 별도 테스트 필요). 토큰 만료 시 주기적 재생성 필요. sessionStorage 복원은 `addInitScript`로 수동 구현해야 한다.

---

### 8. 불필요한 네트워크 리소스를 차단하라

이미지·폰트·애널리틱스·서드파티 스크립트를 가로채 로딩 자체를 막는다.

```javascript
// 리소스 타입 기준 차단
await page.route("**/*", (route) => {
  const type = route.request().resourceType();
  if (["image", "stylesheet", "font"].includes(type)) route.abort();
  else route.continue();
});

// 특정 도메인 기준 차단
await page.route("**/*", (route) => {
  const url = route.request().url();
  const blocked = ["google-analytics.com", "googletagmanager.com"];
  if (blocked.some((d) => url.includes(d))) route.abort();
  else route.continue();
});
```

**트레이드오프**: CSS·폰트까지 공격적으로 막으면 레이아웃/가시성(visibility) 검증이 깨진다. 비주얼 테스트는 이미지·폰트가 필요하므로 프로젝트별로 분리 적용.

---

### 9. 요약 표: 7가지 기법 한눈에

| # | 기법 | 효과 축 | 주의점 |
|---|------|---------|--------|
| 1 | workers / fullyParallel / sharding | 병렬성 | CPU 경합·OOM, 부하 불균형 |
| 2 | 불필요한 reload 제거 | 낭비 제거 | 전체 로드 필요한 앱은 예외 |
| 3 | CI headless | 낭비 제거(10~30%) | 비주얼 테스트는 headed |
| 4 | fail-fast (maxFailures) | 낭비 제거 | flaky 많으면 역효과 |
| 5 | `--only-changed` | 실행 범위 축소 | 정적 분석 한계, full run 병행 |
| 6 | 인증 상태 재사용 | 낭비 제거(8~25분) | 인증 플로우 우회, 토큰 만료 |
| 7 | 리소스 차단 | 낭비 제거 | 레이아웃/비주얼 검증 영향 |

> **일반 권고**: 평균 테스트 소요시간·flaky 비율·CI 자원 사용량을 **지속 모니터링**하라. 스위트가 커지면 속도는 다시 떨어진다. 개선은 한 번에 하나씩 적용하고 효과를 측정한 뒤 다음으로 넘어가라.

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **"더 많이 동시에" vs "각 테스트를 가볍게"는 별개의 축이다**
   - 병렬화(worker/shard)는 총 처리량을 늘리지만, 각 테스트가 무거우면 머신만 더 태울 뿐이다.
   - 리소스 차단·인증 재사용·reload 제거는 **테스트당 비용 자체**를 줄인다. 병렬화 전에 이걸 먼저 하면 같은 워커 수로 더 많은 테스트를 처리할 수 있어 **비용 효율이 더 좋다**.
   - 순서 권고: ①테스트 경량화 → ②worker 병렬화 → ③(한계 도달 시) sharding.

2. **병렬성은 숨은 결합(coupling)을 드러내는 리트머스지다**
   - 직렬로는 통과하던 테스트가 `fullyParallel`/sharding에서 깨진다면, 그건 병렬화 버그가 아니라 **원래 공유 상태에 의존하던 테스트**였다는 신호다.
   - 속도 개선 작업이 곧 테스트 격리 품질 점검이 되는 셈. 실패를 "롤백" 신호가 아니라 "설계 결함 발견" 신호로 읽어야 한다.

3. **워커 수는 코어 수에 물리적으로 묶인다 — 무한 확장이 아니다**
   - 4코어 → 2~4워커, 8코어 → 6~8워커가 한계. 이 이상은 CPU 경합으로 렌더링이 밀려 **오히려 flaky·timeout이 늘어난다**.
   - 단일 머신 한계에 부딪히면 워커를 더 늘릴 게 아니라 **sharding으로 수평 확장**해야 한다. (관련: sharding vs workers는 별도 심층 주제)

### 실무 적용 관점

1. **인증 재사용과 리소스 차단이 "가성비 1위"**
   - 설정 난이도는 낮은데 절감 효과가 크다(인증만 8~25분). 병렬 인프라를 늘리기 전에 이 두 개부터 적용하는 게 ROI가 가장 높다.

2. **`--only-changed`는 PR 게이트용, full run은 반드시 병행**
   - 정적 분석이 놓치는 간접 의존(백엔드 주도 UI, 환경변수, 공유 설정)이 실무에선 흔하다. "빠른 PR 피드백"과 "머지 전 안전망"을 분리 설계하지 않으면 회귀를 놓친다.

3. **최적화는 "한 번에 하나씩 + 측정"**
   - fail-fast는 flaky가 많으면 역효과, 리소스 차단은 비주얼 테스트를 깨뜨린다. 모든 기법이 트레이드오프를 갖는다.
   - 여러 개를 한꺼번에 켜면 어떤 것이 flaky를 유발했는지 추적 불가. **하나 적용 → 소요시간·flaky율 측정 → 다음** 사이클을 지켜야 한다.

### 트레이드오프 관점

| 결정 | 얻는 것 | 잃는 것 / 리스크 |
|------|---------|------------------|
| 워커 증설 | 처리량 | CPU 경합, flaky/timeout 증가 |
| headless | 10~30% 속도 | 비주얼/GPU 렌더링 정확도 |
| fail-fast | CI 시간 절약 | 나머지 실패 가림, flaky에 취약 |
| `--only-changed` | 실행 범위 축소 | 간접 의존 회귀 누락 |
| 리소스 차단 | 테스트 경량화 | 레이아웃/가시성 검증 신뢰도 |

→ 결론: **속도와 신뢰도(정확성)는 상충한다.** "얼마나 빠르게"만이 아니라 "어떤 테스트는 느려도 정확해야 하는가"를 먼저 분류하고, 스위트를 (빠른 스모크 / 정밀 비주얼·인증) 계층으로 나눠 각 계층에 맞는 최적화를 적용하는 게 정석이다.
