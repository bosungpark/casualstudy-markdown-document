# 데스크탑 앱의 프로세스 간 통신(IPC) - 신뢰 경계를 넘나드는 메시지 패턴

## 출처
- **아티클/문서**: Inter-Process Communication (Electron Tutorial)
- **저자/출처**: Electron 공식 문서
- **링크**: https://www.electronjs.org/docs/latest/tutorial/ipc

---

## AI 요약

### 1. IPC란 왜 데스크탑 앱의 핵심인가?

웹 기술 기반 데스크탑 앱(Electron 등)은 Chromium에서 물려받은 **멀티 프로세스 구조**를 쓴다. UI를 그리는 **렌더러 프로세스**는 보안상 OS·파일시스템에 직접 손댈 수 없고, 시스템 권한을 가진 **메인 프로세스**만 그 일을 한다. 그래서 "버튼을 눌러 파일을 저장한다" 같은 평범한 동작조차 두 프로세스가 **메시지를 주고받아야(IPC)** 성립한다.

| 프로세스 | 권한 | 역할 |
|---|---|---|
| **Main** | 신뢰됨, Node.js 전권 | 파일/메뉴/창/네이티브 API |
| **Renderer** | 비신뢰, 샌드박스 | HTML/CSS/JS로 UI 렌더링 |
| **Preload** | 제한적 다리 | contextBridge로 안전한 API만 노출 |

**핵심**: IPC는 단순한 함수 호출이 아니라, **신뢰 경계(trust boundary)를 넘나드는 메시지 전달**이다. 이 경계를 어떻게 설계하느냐가 곧 앱의 보안 수준이다.

---

### 2. 안전한 IPC를 위한 3층 구조

```
┌──────────────── Renderer (비신뢰, 샌드박스) ────────────────┐
│  window.api.saveFile(data)   ← 노출된 안전한 API만 호출      │
└───────────────────────────┬─────────────────────────────────┘
                            │ contextBridge 경계
┌───────────────────────────▼─────────────────────────────────┐
│  Preload (격리된 world)                                      │
│  contextBridge.exposeInMainWorld('api', {                    │
│     saveFile: (d) => ipcRenderer.invoke('save-file', d)      │
│  })                                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │ IPC 채널 ('save-file')
┌───────────────────────────▼─────────────────────────────────┐
│  Main (신뢰됨, Node.js 전권)                                 │
│  ipcMain.handle('save-file', (e, d) => fs.writeFile(...))    │
└──────────────────────────────────────────────────────────────┘
```

**Context Isolation**: 프리로드 스크립트는 렌더러의 main world와 격리되어, 특권 API가 웹 콘텐츠 코드로 새지 않게 한다. 기본적으로 렌더러는 Node.js·Electron 모듈에 접근할 수 없고, 개발자가 `contextBridge`로 **고른 API만** 노출한다. 이는 프로토타입 오염과 특권 API 유출을 막는다.

---

### 3. 네 가지 IPC 패턴

| 패턴 | 방향 | API (보내는 쪽 → 받는 쪽) | 용도 |
|---|---|---|---|
| **① Renderer → Main (단방향)** | R→M | `ipcRenderer.send` → `ipcMain.on` | 결과가 필요 없는 통지 (예: 로그, 설정 변경) |
| **② Renderer → Main (양방향)** | R⇄M | `ipcRenderer.invoke` → `ipcMain.handle` | 결과를 기다림 (예: 파일 읽기, DB 조회) |
| **③ Main → Renderer** | M→R | `webContents.send` → `ipcRenderer.on` | 메인이 렌더러에 알림 (예: 메뉴 클릭, 진행률) |
| **④ Renderer ⇄ Renderer** | R⇄R | `MessagePort` (메인이 중개) | 창 간 직접 통신 |

#### ① 단방향: send / on
```js
// preload
contextBridge.exposeInMainWorld('api', {
  setTitle: (t) => ipcRenderer.send('set-title', t)
})
// main
ipcMain.on('set-title', (event, title) => {
  BrowserWindow.fromWebContents(event.sender).setTitle(title)
})
```

#### ② 양방향: invoke / handle (가장 권장)
```js
// preload
contextBridge.exposeInMainWorld('api', {
  openFile: () => ipcRenderer.invoke('dialog:openFile')  // Promise 반환
})
// main
ipcMain.handle('dialog:openFile', async () => {
  const { filePaths } = await dialog.showOpenDialog()
  return filePaths[0]   // 렌더러의 await로 돌아감
})
```
> `invoke/handle`는 `Promise` 기반이라 요청-응답을 자연스럽게 await할 수 있어 **양방향 통신의 표준 패턴**이다. send/on으로 양방향을 흉내내면 응답 채널을 수동으로 관리해야 해 장황하고 버그를 부른다.

#### ③ Main → Renderer
```js
// main: 메뉴 클릭 시 렌더러에 통지
menuItem.click = () => win.webContents.send('update-counter', 1)
// preload: 콜백을 안전하게 노출
contextBridge.exposeInMainWorld('api', {
  onUpdateCounter: (cb) => ipcRenderer.on('update-counter', (_e, v) => cb(v))
})
```

---

### 4. 왜 이렇게 번거롭게 만들었나 - 멀티 프로세스의 이유

```
단일 프로세스 모델 (옛 브라우저)
┌────────────────────────────────┐
│  탭A + 탭B + UI + 파일접근       │
│  → 한 탭이 죽으면 앱 전체 크래시 │
│  → XSS 1건이 파일시스템 장악     │
└────────────────────────────────┘
            ↓ Chromium의 답
멀티 프로세스 모델
┌─────────┐  ┌─────────┐  ┌──────────────┐
│ 렌더러A │  │ 렌더러B │  │     메인     │
│ 샌드박스│  │ 샌드박스│  │ (파일/시스템)│
└────┬────┘  └────┬────┘  └──────┬───────┘
     └── IPC ─────┴──── IPC ──────┘
  렌더러가 죽어도 앱은 산다 / XSS는 샌드박스에 갇힌다
```

멀티 프로세스 구조의 보안적 이득: 렌더러는 샌드박스에 갇혀 있고 **파일시스템은 오직 메인만 만진다.** 누군가 XSS 취약점을 찾아내도 그는 **파일 접근 권한 없는 Chromium 샌드박스 안에 갇힌다.** IPC는 이 격리를 유지하면서도 필요한 작업만 메인에 위임하는 통로다.

---

### 5. Utility Process - 제3의 프로세스

Electron은 비신뢰 서비스·CPU 집약 작업·크래시가 잦은 컴포넌트를 위해 **Utility Process**를 띄울 수 있다. 일반 Node.js 자식 프로세스와 달리, Utility Process는 `MessagePort`를 통해 **렌더러와 직접** 통신할 수 있다. 무거운 작업을 메인에서 떼어내 메인의 응답성을 지킨다.

---

### 6. IPC 설계의 보안 원칙

| 원칙 | 이유 |
|---|---|
| `sender` 검증 | 비신뢰 프레임이 특권 동작을 트리거하지 못하게 모든 IPC의 발신자를 확인 |
| 최소 API 노출 | contextBridge로 노출하는 표면을 최소화 (raw ipcRenderer 통째 노출 금지) |
| 입력 검증 | 채널로 들어온 인자(경로 등)를 메인에서 반드시 sanitize |
| 채널 화이트리스트 | 임의 채널명을 그대로 전달하지 말고 허용 목록으로 제한 |

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **IPC는 "함수 호출의 흉내"가 아니라 "신뢰 경계의 강제"다**
   - `invoke('save-file')`은 함수처럼 보이지만, 실제로는 비신뢰 영역에서 신뢰 영역으로 메시지를 던지는 행위다. **편의 문법(Promise) 뒤에 OS 프로세스 경계가 있다는 사실**을 잊으면 보안 설계가 무너진다.

2. **격리와 통신은 한 쌍이다**
   - 렌더러를 샌드박스에 가두는 것만으로는 앱이 동작하지 않는다. 격리(샌드박스)와 통제된 통로(IPC)는 항상 함께 설계되어야 한다. **"무엇을 막을 것인가"와 "무엇만 허용할 것인가"는 같은 동전의 양면**이다.

### 설계 패턴 관점

1. **invoke/handle를 기본으로 삼아라**
   - send/on으로 요청-응답을 구현하면 응답 채널을 수동 관리해야 해 상태가 꼬인다. Promise 기반 invoke/handle은 **요청-응답이라는 의도를 코드 구조로 표현**한다. 단방향(send/on)은 정말 결과가 필요 없을 때만.

2. **contextBridge는 "API 게이트웨이"처럼 다뤄라**
   - 마이크로서비스의 API 게이트웨이가 내부 서비스를 직접 노출하지 않듯, preload도 raw `ipcRenderer`를 노출하면 안 된다. **도메인 의도가 담긴 좁은 함수(`saveFile`, `openDialog`)만** 노출해 공격면을 최소화한다.

### 실무 적용 관점

1. **모든 IPC 핸들러에서 sender와 인자를 검증하라**
   - 메인의 `handle` 콜백은 사실상 **권한 상승 지점**이다. 들어온 파일 경로를 그대로 `fs`에 넘기면 path traversal로 임의 파일 접근이 열린다. 백엔드 API의 입력 검증을 그대로 IPC 경계에 적용해야 한다.

2. **무거운 작업은 Utility Process로 떼어내 메인을 지켜라**
   - 메인 프로세스가 블로킹되면 모든 창이 멈춘다. CPU 집약 작업·크래시 위험 코드는 Utility Process로 격리하고 MessagePort로 통신하면, **메인의 응답성과 앱 전체 안정성**을 함께 지킬 수 있다.
