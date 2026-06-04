# 일렉트론(Electron) 데스크탑 앱의 구조와 원리 - 멀티 프로세스 모델로 이해하기

## 출처
- **아티클**: Process Model (Electron Tutorial)
- **저자/출처**: Electron 공식 문서 (electronjs.org)
- **링크**: https://www.electronjs.org/docs/latest/tutorial/process-model

---

## AI 요약

### 1. Electron이란?

Electron은 **웹 기술(HTML/CSS/JavaScript)로 데스크탑 앱을 만드는 프레임워크**다.
핵심은 단 두 가지 기술을 합쳤다는 것:

- **Chromium**: 구글 크롬의 오픈소스 버전 → "화면을 그리는 브라우저 엔진"
- **Node.js**: 서버용 자바스크립트 런타임 → "파일 읽기/OS 접근 등 시스템 기능"

VS Code, Slack, Discord, Notion 같은 앱들이 모두 Electron으로 만들어졌다.
즉 우리가 쓰는 "데스크탑 앱"의 상당수는 사실 **포장된 웹 페이지 + 시스템 권한**이다.

| 특성 | 설명 |
|------|------|
| 렌더링 | Chromium이 담당 (브라우저와 동일하게 웹 표준으로 화면 그림) |
| 시스템 접근 | Node.js가 담당 (파일시스템, OS 정보 등) |
| 크로스 플랫폼 | 하나의 코드로 Windows / macOS / Linux 빌드 |
| 아키텍처 | Chromium에서 물려받은 **멀티 프로세스 모델** |

---

### 2. 왜 "멀티 프로세스"인가? — 브라우저 비유

Electron의 구조를 이해하는 가장 쉬운 길은 **"크롬 브라우저"를 떠올리는 것**이다.

```
        [ 크롬 브라우저 ]                      [ Electron 앱 ]
   ┌──────────────────────┐            ┌──────────────────────┐
   │  브라우저 본체         │   ≈        │  Main Process        │
   │  (탭 관리, 메뉴, 창)   │            │  (앱 생명주기, 창 관리)│
   ├──────────────────────┤            ├──────────────────────┤
   │  탭 1  │ 탭 2 │ 탭 3   │   ≈        │ Renderer │ Renderer  │
   │ (웹페이지 각각 별도프로세스)│         │ (창마다 별도 프로세스) │
   └──────────────────────┘            └──────────────────────┘
```

**왜 굳이 프로세스를 쪼개나?**
과거 브라우저는 단일 프로세스였다. 그런데 탭 하나가 죽으면 **브라우저 전체가 죽었다.**
크롬은 "탭마다 별도 프로세스"로 분리해 이 문제를 풀었다.

> 한 프로세스가 크래시(또는 악성 코드 실행)되어도 **피해가 그 프로세스 안에 갇힌다.**
> 이게 멀티 프로세스 아키텍처를 쓰는 핵심 이유: **안정성 + 보안 격리.**

Electron은 이 설계를 그대로 물려받았다.

---

### 3. Main Process (메인 프로세스) — 앱의 "관리자"

- 앱마다 **정확히 하나**만 존재한다. 앱의 **진입점(entry point)**.
- **Node.js 환경**에서 실행된다 → `require`와 모든 Node.js API 사용 가능 (`fs`, `os` 등).
- 하는 일:
  - **창 생성/관리** (`BrowserWindow` 모듈)
  - **앱 생명주기 제어** (`app` 모듈 — 시작, 종료, 활성화)
  - **네이티브 데스크탑 기능 노출** — 메뉴, 다이얼로그, 트레이 아이콘, 글로벌 단축키

```javascript
// main.js — 메인 프로세스
const { app, BrowserWindow } = require('electron')

app.whenReady().then(() => {
  const win = new BrowserWindow({ width: 800, height: 600 })
  win.loadFile('index.html')   // 이 순간 Renderer 프로세스가 생성됨
})
```

> ⚠️ **주의**: CPU 집약적 작업을 메인 프로세스에서 돌리면 **모든 창(Renderer)이 멈춘다.**
> 메인은 "교통 정리"만 하고, 무거운 일은 별도 프로세스(아래 Utility Process)로 보내야 한다.

---

### 4. Renderer Process (렌더러 프로세스) — "화면 그리는 일꾼"

- `BrowserWindow` 인스턴스 **하나당 하나씩** 생성된다.
- HTML/CSS/JavaScript로 **UI를 그리는 일만** 한다. (= 브라우저 탭과 동일)
- 웹 표준(Chromium이 구현한 그대로)으로 동작하며 **DOM API** 사용 가능.
- **보안상 의도적으로 Node.js 직접 접근이 막혀 있다.**

여기서 중요한 개념 하나:
> **프로세스들은 메모리를 공유하지 않는다.**
> 같은 모듈을 main과 renderer에서 각각 `require` 하면 **literally 두 개의 인스턴스**가 따로 돈다.
> renderer에서 카운터를 +1 해도 main 쪽 카운터는 그대로다. 둘은 완전히 분리된 메모리 공간이다.

```
┌─────────────────────────────────────────────────────────┐
│                      Main Process                        │
│            (Node.js 풀 권한, fs/os 접근 가능)              │
└────────────────────────┬────────────────────────────────┘
                         │  IPC (프로세스 간 통신)
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  ┌──────────┐    ┌──────────┐     ┌──────────┐
  │ Renderer │    │ Renderer │     │ Renderer │
  │  (창 1)   │    │  (창 2)   │     │  (창 3)   │
  │ DOM만 접근 │    │ DOM만 접근 │     │ DOM만 접근 │
  └──────────┘    └──────────┘     └──────────┘
```

---

### 5. 보안의 핵심 — Renderer는 왜 Node.js를 못 쓰게 막았나?

Renderer는 **임의의 웹 콘텐츠(외부 URL 등)를 로드**할 수 있다.
만약 Renderer가 Node.js의 `fs`에 자유롭게 접근할 수 있다면?
→ 악성 웹페이지 한 줄로 **사용자 디스크의 파일을 읽거나 지울 수 있다.**

그래서 Electron은 여러 겹의 방어막을 둔다:

| 장치 | 역할 |
|------|------|
| **Context Isolation** | preload 스크립트와 웹페이지의 JS 세계(main world)를 격리. 특권 API가 웹 콘텐츠로 새지 않게 함 |
| **Preload Script** | 웹 콘텐츠 로드 **전에** renderer 컨텍스트에서 실행. Node.js 접근 권한을 가진 "다리" 역할 |
| **contextBridge** | preload가 **선별한 안전한 API만** renderer에 노출. window 객체에 직접 붙이지 않음 |

```javascript
// preload.js — 안전하게 필요한 기능만 골라서 노출
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('myAPI', {
  saveFile: (data) => ipcRenderer.invoke('save-file', data)
  // renderer는 fs에 직접 접근 못 함. 오직 saveFile()이라는 "구멍"만 허용됨
})
```

> 설계 원칙: **"renderer를 신뢰하지 않는다(untrusted)"** 를 기본 전제로 깔고,
> 필요한 권한만 명시적으로, 최소한으로 뚫어준다. (= 최소 권한 원칙)

---

### 6. IPC — 프로세스끼리 어떻게 대화하나?

프로세스들은 메모리를 공유하지 않으므로, 대화하려면 **IPC(Inter-Process Communication)**가 필요하다.

- Electron의 IPC는 Chromium처럼 **named pipe(이름 있는 파이프)**를 기반으로 한다.
  - 셸의 `ls | grep foo` 에서 `|` 와 같은 개념. 네트워크 프로토콜보다 **빠르고 안전**하다.
- 동작 방식: **채널 이름 + 데이터**를 메시지로 주고받음 (postMessage와 비슷).
- 양방향이며 동기/비동기 모두 가능.

```javascript
// renderer (preload 통해): "save-file" 채널로 메인에 요청
await window.myAPI.saveFile(content)

// main: 그 채널을 듣고 있다가 실제 파일 저장 수행
ipcMain.handle('save-file', async (event, data) => {
  await fs.promises.writeFile('out.txt', data)   // Node.js 권한은 여기서만!
})
```

흐름 요약:
```
[Renderer]  "이 파일 좀 저장해줘"  ──IPC(save-file 채널)──▶  [Main]
   (권한 없음)                                              (fs로 실제 저장)
[Renderer]  ◀────────── "저장 완료" 응답 ──────────────────  [Main]
```

---

### 7. Utility Process — 무거운 일을 위한 별도 일꾼

CPU 집약적이거나, 크래시 위험이 있거나, 신뢰할 수 없는 작업은
**Main에서 돌리면 앱 전체가 멈출 위험**이 있다.

- `UtilityProcess` API로 **별도의 Node.js 자식 프로세스**를 띄울 수 있다.
- 과거 Main에 몰려 있던 무거운/위험한 작업을 여기로 분리.
- 장점: **MessagePort**를 이용해 Renderer와 **직접 통신 채널**을 맺을 수 있어, 메인을 거치지 않는다.

```
              ┌──────────┐
              │   Main   │
              └────┬─────┘
         ┌─────────┼──────────────┐
         ▼         ▼              ▼
  ┌──────────┐         ┌─────────────────┐
  │ Renderer │◀──MessagePort──▶│ Utility Process │
  └──────────┘         │ (무거운 작업 전담) │
                       └─────────────────┘
```

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **"단일 프로세스의 단일 장애점(SPOF)을 쪼개서 격리한다"는 보편 원리의 데스크탑 버전**
   - 분산 시스템에서 서비스를 쪼개 장애를 격리하듯, Electron도 창마다 프로세스를 쪼갠다.
   - 같은 문제(한 곳의 실패가 전체로 전파)를 같은 방법(격리)으로 푸는 것. 도메인만 다를 뿐 패턴은 동일하다.

2. **"화면 그리기"와 "시스템 권한"을 물리적으로 분리한 게 설계의 핵심**
   - Renderer = 신뢰 불가 영역(웹 콘텐츠), Main = 신뢰 영역(시스템 권한).
   - 권한 경계를 프로세스 경계와 일치시킨 것이 보안 모델의 뼈대다. "권한이 다르면 프로세스를 나눈다."

### 보안 관점

3. **기본값을 "불신(untrusted)"으로 깔고 화이트리스트로 뚫는 설계**
   - contextBridge는 "전부 막고 필요한 구멍만 명시적으로 뚫는" 화이트리스트 방식.
   - 블랙리스트(위험한 것만 막기)는 빠뜨리면 뚫리지만, 화이트리스트는 깜빡해도 안전 쪽으로 실패한다. **fail-safe 기본값**의 좋은 예.

4. **편의성과 보안의 트레이드오프 — `nodeIntegration`의 함정**
   - 옛 Electron은 renderer에서 Node.js를 바로 쓰게 허용(`nodeIntegration: true`)해 편했지만, XSS 한 방이 곧 RCE(원격 코드 실행)였다.
   - 지금의 context isolation + preload + IPC 구조는 **불편함을 감수하고 보안을 택한 결과**. "편하면 위험하다"는 보안 설계의 전형.

### 실무 관점

5. **"무거운 일은 Main에 두지 마라"는 성능 함정 회피**
   - Main이 멈추면 모든 창이 얼어붙는다. CPU 작업은 Utility Process나 Worker로 분리해야 한다.
   - 이벤트 루프 하나가 전체 UI 반응성을 좌우한다는 점에서, 싱글스레드 JS의 한계를 멀티프로세스로 우회하는 전형적 패턴.

6. **Electron 앱이 "메모리를 많이 먹는다"는 평판의 구조적 이유**
   - 창마다 별도 Chromium 렌더러 프로세스 + 각자 독립 메모리 공간. 안정성/보안을 위해 메모리를 희생한 의도된 트레이드오프다.
   - "왜 Slack/Discord가 RAM을 많이 쓰지?"의 답이 바로 이 아키텍처에 있다.
