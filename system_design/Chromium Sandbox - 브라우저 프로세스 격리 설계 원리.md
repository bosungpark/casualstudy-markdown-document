# Chromium Sandbox - 브라우저 프로세스 격리 설계 원리

## 출처
- **아티클**: Sandbox (Chromium Design Document)
- **저자/출처**: The Chromium Projects
- **링크**: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/design/sandbox.md

---

## AI 요약

### 1. Chromium Sandbox란?

Chromium Sandbox는 **렌더러 같은 신뢰할 수 없는 코드가 무엇을 입력받든 시스템에 영구적인 변경을 가하거나 기밀 정보에 접근하지 못하도록 강제하는 하드 보안 경계**다. 자체 보안 모델을 새로 짜는 대신, OS가 이미 제공하는 메커니즘(토큰, Job Object, Integrity Level, Desktop)을 조합해서 "프로세스 단위"의 최소 권한 환경을 만든다.

| 특성 | 설명 |
|------|------|
| 동작 단위 | 프로세스 (스레드 X) |
| 권한 요구 | 일반 사용자 모드 (관리자/커널 드라이버 불필요) |
| OS 지원 | Windows 10+ (32/64bit) |
| 보호 범위 | OS가 보안 검사를 수행하는 모든 securable 리소스 |
| 보호 못 하는 것 | FAT 볼륨, 익명 공유 메모리 등 unsecured 리소스, OS 자체 버그 |

> 핵심 통찰: "Sandbox는 *완벽한 격리*가 아니라 *비용을 강제로 올리는 장치*다. 공격자가 코드 실행에 성공하더라도, 그 결과가 의미 있는 피해로 이어지지 못하게 한다."

---

### 2. 5가지 설계 원칙

```
┌─────────────────────────────────────────────────────────────┐
│  1. OS가 이미 제공하는 보안 메커니즘 활용 (재발명 X)        │
│  2. 샌드박스 안과 밖 모두에 최소 권한 적용                  │
│  3. 샌드박스 내부 코드는 "이미 악성"이라고 가정             │
│  4. 정상 동작의 성능 오버헤드 최소화                        │
│  5. 에뮬레이션 기반 보안 거부 → OS-enforced 경계만 신뢰     │
└─────────────────────────────────────────────────────────────┘
```

특히 5번이 중요하다. API 후킹·시스템 콜 가로채기 같은 "사용자 모드 우회 가능 메커니즘"은 보안 경계로 인정하지 않는다. 가로채기(interception)는 호환성을 위한 장치일 뿐, 보안 자체는 항상 커널이 강제하는 토큰/Job/Integrity로만 성립한다.

---

### 3. 아키텍처 - Broker / Target 두 역할

```
┌────────────────────────────────────────────────────────────────┐
│                    Broker Process (Browser)                    │
│  ─────────────────────────────────────────────                 │
│  ▸ Policy 정의 및 호스팅 (Policy Engine)                       │
│  ▸ Target 프로세스 생성·종료                                   │
│  ▸ IPC 서버                                                    │
│  ▸ Target 대신 정책상 허용된 동작 대리 수행                    │
│  ▸ 권한: 일반 사용자 권한 (관리자 X)                           │
└──────────────────────┬─────────────────────────────────────────┘
                       │  Low-level IPC
                       │  (정책 평가 + 대리 호출)
                       ▼
┌────────────────────────────────────────────────────────────────┐
│            Target Process (Renderer, GPU, Utility ...)         │
│  ─────────────────────────────────────────────                 │
│  ▸ 신뢰할 수 없는 코드 (JS, HTML, image decoder ...)           │
│  ▸ IPC Client + Policy Engine Client                           │
│  ▸ Win32 API Interceptions                                     │
│  ▸ 권한: Restricted Token + Job + Untrusted IL + Alt Desktop   │
└────────────────────────────────────────────────────────────────┘
```

- **Broker**: 권한이 있는 브라우저 프로세스. Target이 "직접 못 하는 작업"을 정책 검증 후 대신 실행해 준다.
- **Target**: 렌더러 같은 격리 대상. 모든 권한이 박탈된 상태에서 시작하며, OS 리소스의 핸들은 Broker가 미리 열어 듀플리케이션해 준 것만 사용한다.

---

### 4. 4개의 핵심 제약 메커니즘

Chromium은 단일 매직 솔루션 대신 4개 OS 메커니즘을 **중첩(defense-in-depth)** 시켜 격리를 만든다.

#### 4-1. Restricted Token

가장 제약된 토큰 구성:

| 항목 | 값 |
|------|-----|
| Mandatory SID | Logon SID 하나만 |
| 그 외 모든 SID | Deny-only |
| Restricted Group | `S-1-0-0` (NULL SID) 단 하나 |
| Privileges | **없음** |
| Integrity Level | Untrusted (가장 낮음) |

> "이런 토큰으로는 OS가 접근을 허가할 기존 리소스를 찾는 것이 거의 불가능하다."

렌더러가 쓰는 거의 모든 리소스는 **Broker가 미리 열어서 핸들을 듀플리케이션**해 주는 방식으로 전달된다. Target은 "스스로 무언가를 열 수 없는" 상태가 기본값이다.

#### 4-2. Job Object

프로세스 단위 글로벌 제약을 강제:

```
[ Job Object 제약 사항 ]
  ✗ SystemParametersInfo() 호출 (시스템 전역 설정 변경)
  ✗ Desktop 생성/전환
  ✗ Clipboard read/write
  ✗ 윈도우 메시지 브로드캐스트
  ✗ SetWindowsHookEx() 전역 훅 설치
  ✗ 글로벌 atom 테이블 접근
  ✗ Job 외부 USER 핸들 접근
  ✗ 자식 프로세스 생성 (active process = 1)
  + CPU/메모리/IO 사용량 제한 가능
```

각 렌더러는 자기만의 Job에 속한다. 자식 프로세스 생성 금지(active process limit = 1)는 "샌드박스 탈출 → 새 권한 있는 프로세스 fork"라는 가장 흔한 공격 패턴을 막는다.

#### 4-3. Alternate Desktop

> "같은 데스크톱에 윈도우를 가진 애플리케이션들은 사실상 같은 보안 컨텍스트다 — 윈도우 메시지 송신에는 보안 검사가 없다."

이게 그 유명한 **Shatter Attack**이다. 낮은 권한 프로세스가 높은 권한 프로세스 윈도우에 메시지를 쏘아 권한 상승을 노리는 공격. Chromium은 사용자가 보는 데스크톱과 분리된 **제3의 데스크톱**을 만들어 Target을 거기 격리시킨다.

| 항목 | 값 |
|------|-----|
| 비용 | 약 4MB RAM (별도 풀에서) |
| 효과 | Shatter attack 완전 차단 |

#### 4-4. Integrity Level (Mandatory Access Control)

```
  System    ┌──────────────────────────────┐
            │                              │ ← 가장 높음
  High      │      서비스/관리자           │
            │                              │
  Medium    │      일반 프로세스 (기본)    │
            │                              │
  Low       │      IE Protected Mode 등    │
            │                              │
  Untrusted │   ◀── Chromium Renderer      │ ← 가장 낮음
            └──────────────────────────────┘
```

렌더러는 **Untrusted** IL로 실행된다. 더 높은 IL이 소유한 객체는 명시적으로 untrusted 라벨이 붙거나 NULL DACL인 경우에만 접근 가능. UIPI(User Interface Privilege Isolation)도 함께 활성화돼 IL이 더 높은 윈도우로 메시지를 보낼 수 없다.

---

### 5. Interception + IPC - 보안이 아닌 호환성 장치

```
[ Target 내부의 호출 흐름 ]

  renderer code
       │
       │  CreateFile("C:\\Users\\bob\\.ssh\\id_rsa")
       ▼
  ┌─────────────────────────────────────┐
  │  Win32 API Interception (hook)      │
  │  ─────────────────────────────────  │
  │  1. Target 측 Policy Engine으로     │
  │     빠른 사전 검사 (성능 최적화용)  │
  │  2. 통과하면 IPC로 Broker에 위임    │
  └──────────────┬──────────────────────┘
                 │  IPC
                 ▼
  ┌─────────────────────────────────────┐
  │  Broker Policy Engine (권위 있는)   │
  │  ─────────────────────────────────  │
  │  ▸ 정책 재평가                      │
  │  ▸ 승인 시 Broker가 직접 실행       │
  │  ▸ 결과 핸들을 Target에 전달        │
  └─────────────────────────────────────┘
```

**핵심 설계 결정**:
> "interception + IPC 메커니즘은 보안을 제공하지 않는다 — 샌드박스 안 코드가 제약을 우회할 수 없을 때 **호환성**을 제공하기 위한 것이다."

Target 쪽 정책 검사는 빠르게 거절하기 위한 캐시일 뿐, 권위 있는 결정은 항상 Broker가 한다. 후킹이 우회되더라도 Restricted Token + Job + IL이 그대로 막아 준다.

---

### 6. Process Mitigation Policies (추가 방어층)

| 분류 | 메커니즘 | 효과 |
|------|----------|------|
| 메모리 레이아웃 | Relocate Images, Bottom-up ASLR, High-entropy ASLR | 익스플로잇 주소 예측 차단 |
| 메모리 안전 | Heap Terminate, Strict Handle Checks | 힙 손상/핸들 오용 시 즉시 종료 |
| 커널 표면 축소 | **Win32k Lockdown** | `win32k.sys` 시스템 콜 전면 차단 |
| 확장 차단 | Extension Point Disable | AppInit DLL, LSP, 전역 훅, 레거시 IME 차단 |
| 제어 흐름 | **CFG** (Control Flow Guard) | 간접 호출 대상 검증 |
| 코드 무결성 | **CIG** (Code Integrity Guard) | 서명 안 된 코드 로드 차단 |
| 코드 변조 | **ACG** (Arbitrary Code Guard) | 코드 페이지 불변화, JIT 공격 차단 |
| 이미지 로딩 | Image Load Restrictions | 원격/저신뢰 이미지 로드 차단 |

특히 **Win32k Lockdown**이 의미가 크다. Windows 커널 익스플로잇의 상당수가 `win32k.sys`의 GDI/USER 서브시스템 버그였는데, 렌더러에서 이걸 통째로 막아 버린다.

---

### 7. AppContainer와 LPAC

Windows 8 이상의 추가 격리층.

```
┌─────────────────────────────────────────────────────────────┐
│  AppContainer (Low Box Token)                               │
│  ───────────────────────────────────────                    │
│  ▸ Low Box 토큰 속성 추가, capabilities는 비어 있음         │
│  ▸ 효과: 커널이 네트워크 접근을 거부                        │
└─────────────────────────────────────────────────────────────┘
                       │ 더 엄격하게
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LPAC (Less Privileged App Container, Win10 RS2+)           │
│  ───────────────────────────────────────                    │
│  ▸ 기본 거부 모델 — 명시적으로 라벨된 객체만 접근 가능      │
│    · ALL RESTRICTED APPLICATION PACKAGES                    │
│    · 특정 package SID                                       │
│  ▸ 프로세스별 고유 SID → 샌드박스 간 파일 격리              │
│  ▸ 인스톨러가 필요한 경로에 적절한 ACL을 미리 박아 줘야 함  │
└─────────────────────────────────────────────────────────────┘
```

LPAC는 "기본 차단"이 디폴트라는 점에서 가장 강력하다. 대신 인스톨러가 ACL을 세팅해 줘야 해서 배포 복잡도가 올라간다.

---

### 8. Sandbox Policy API

거친 단위(coarse-grained) 제어:

```cpp
TargetPolicy::SetTokenLevel(initial, lockdown);  // 7 levels
TargetPolicy::SetJobLevel(level);                // 5 levels
TargetPolicy::SetIntegrityLevel(level);
TargetPolicy::SetDesktop(use_alternate);         // binary
```

세밀한 예외는 `AddRule()`:

```cpp
// 특정 경로의 .dmp 파일만 읽기 허용
AddRule(SUBSYS_FILES,
        FILES_ALLOW_READONLY,
        L"c:\\temp\\app_log\\d*.dmp");
```

지원 서브시스템: Files, Named Pipes, Process Creation, Registry, Sync Objects.

---

### 9. Target Bootstrapping - Dual Token 패턴

문제: 토큰이 너무 제약되면 OS 로더, CRT 초기화조차 못 한다. 이 단계에서 필요한 리소스가 문서화되지 않은 게 많아 "Restricted Token으로 처음부터 띄우기"가 불가능.

해결: **Dual Token 부팅**

```
[ Target 생애주기 ]

  CreateProcess()
        │
        │  메인 스레드에 Initial Token (impersonation, 거의 일반 사용자)
        │  프로세스에 Lockdown Token (Restricted)
        ▼
  ┌──────────────────────────────────────┐
  │  OS Loader · CRT 초기화              │
  │  main() / WinMain() 진입             │
  │  필요한 핸들/리소스 확보             │
  └────────────┬─────────────────────────┘
               │
               │  LowerToken()  ← 비가역!
               ▼
  ┌──────────────────────────────────────┐
  │  Initial Token 폐기                  │
  │  Lockdown Token만 남음               │
  │  진짜 샌드박스 모드 진입             │
  └──────────────────────────────────────┘
```

> ⚠️ **결정적 주의사항**: "Initial Token으로 얻은 민감한 OS 핸들은 LowerToken() 전에 반드시 닫아라. 누수된 핸들 하나가 샌드박스 탈출 통로가 된다."

---

### 10. 알려진 한계

샌드박스가 보호 못 하는 것:

| 항목 | 이유 |
|------|------|
| FAT/FAT32 볼륨 | 보안 디스크립터 자체가 NULL |
| TCP/IP 소켓 (구 Windows) | 보안 검사 대상 아님 |
| 익명 공유 메모리 섹션 | 라벨이 없음 |
| OS 자체 버그 | Windows API 구현 결함은 우회 가능 |
| 서드파티 DLL 인젝션 | 안티멀웨어 등이 새 공격 표면 추가 |

특히 마지막이 골치 아프다. "보안을 위해 설치한" 안티바이러스가 오히려 샌드박스에 백도어를 뚫는 경우가 흔하다.

---

### 11. 진단

- `chrome://sandbox` — 활성 프로세스 정책 확인
- `chrome://tracing` + `--trace-startup=-*,disabled-by-default-sandbox` — 프로세스 시작 시 정책 트레이싱
- `//tools/win/trace-sandbox-viewer.py` — 트레이스 출력 분석

---

## 내가 얻은 인사이트

### 보안 설계 관점

1. **"에뮬레이션 기반 보안 거부"라는 원칙의 무게**
   - 후킹·API 가로채기는 보안 경계가 **아니다**. 우회 가능한 사용자 모드 메커니즘에 보안을 위임하는 순간, 그건 진정한 경계가 아니라 "예의 바른 요청"이 된다.
   - 보안의 권위는 항상 OS 커널의 강제 메커니즘에 있어야 한다는 원칙은 다른 시스템 설계에도 적용된다 — 예: 클라이언트 측 폼 검증은 UX이지 보안이 아니다.

2. **Defense in Depth = 단일 솔루션 없음**
   - Chromium은 Restricted Token + Job + Alt Desktop + Integrity Level + Mitigation Policies + AppContainer를 **모두** 동시에 적용한다. 하나만으로 충분하지 않다는 가정.
   - 어느 한 층이 OS 버그로 뚫려도 다른 층이 남는다. 보안은 곱셈이지 덧셈이 아니다.

3. **"비용을 강제로 올린다"가 현실적 목표**
   - 완벽한 격리는 환상이다. 알려진 한계 섹션이 솔직하다 — OS 버그, 서드파티 DLL, unsecured 리소스는 어쩔 수 없다.
   - 대신 익스플로잇 체인을 강제로 "RCE → 샌드박스 탈출 → 권한 상승" 3단계로 만들어 비용을 폭증시킨다. 이게 현실적인 위협 모델링이다.

### 시스템 설계 관점

1. **Broker / Target 분리는 Capability 시스템의 변형**
   - Target은 스스로 권한을 가질 수 없고, Broker가 "이미 검증된 핸들"만 듀플리케이션해 준다. Object Capability Model과 본질적으로 같다.
   - 마이크로서비스에서 "API Gateway가 토큰 검증 후 다운스트림에 ID만 전달" 패턴과 구조적으로 유사하다. 권위 있는 결정 지점을 하나로 집중시키는 것.

2. **Dual Token Bootstrap의 일반화 가능성**
   - "초기화는 권한 있게, 운영은 권한 없이"라는 패턴은 컨테이너 보안에서도 동일하다 (init container, capabilities drop, seccomp profile 후속 적용).
   - 운영 단계에서 권한을 **비가역적으로 떨어뜨린다**는 점이 핵심. 복구 경로가 있으면 그건 우회 경로가 된다.

3. **호환성 vs 보안의 명시적 분리**
   - Interception + IPC를 "호환성만을 위한 것, 보안 아님"이라고 문서에 못 박는 명료함. 두 관심사를 섞으면 설계 결함의 원인이 된다.
   - 이런 명시적 분리는 코드/시스템 리뷰 시 "이건 어느 쪽 책임인가?"를 물을 수 있게 해 준다.

### 실무 적용 관점

1. **자식 프로세스 금지(active process = 1)의 위력**
   - 가장 흔한 익스플로잇 후 행동이 "권한 있는 새 프로세스 fork"인데, 이걸 OS 레벨에서 막으면 공격 시나리오가 통째로 없어진다.
   - 컨테이너 보안에서도 `--cap-drop=SYS_ADMIN` + no-new-privileges와 같은 효과. **"무엇을 못 하게 할지"가 "무엇을 허용할지"보다 더 강력한 통제일 수 있다.**

2. **Alt Desktop의 교훈 — UI 시스템도 보안 경계다**
   - 윈도우 메시지에 보안 검사가 없다는 것은 OS 설계의 역사적 결함이지만, 한 번 굳어지면 못 고친다. Chromium은 이를 "다른 데스크톱으로 격리"라는 우회로 해결.
   - 레거시 호환성 때문에 고치지 못하는 보안 결함은 격리로 우회한다 — 이게 OS 보안 작업의 현실이다.

3. **로컬 권한 없는 사용자 모드 샌드박스가 가능하다는 사실**
   - 관리자 권한도, 커널 드라이버도 없이 의미 있는 격리를 만들 수 있다. 일반 사용자가 받은 권한만으로도 "더 적은 권한의 자식"을 만들 수 있는 OS 메커니즘이 핵심.
   - 일반 애플리케이션에서도 위험한 작업(파일 파싱, 압축 해제, 이미지 디코딩 등)을 별도 프로세스 + 토큰 제한으로 분리하는 패턴을 적용할 수 있다. 코스트는 IPC 오버헤드뿐.

### 트레이드오프 관점

1. **성능 vs 보안 — 4MB Alt Desktop은 싼 보험료**
   - Shatter attack 완전 차단의 비용이 4MB RAM. 보안 메커니즘의 비용/효과를 정량적으로 평가하는 사고방식.
   - "성능 영향 최소화"가 5대 원칙 중 하나라는 점이 중요. 보안만 외치고 성능 무시하면 결국 우회/비활성화된다.

2. **API 호환성의 비용**
   - Initial Token + LowerToken() 패턴 전체가 "Windows API가 너무 많은 권한을 가정하고 만들어졌기 때문"에 존재한다. 사전에 보안을 고려하지 않은 API의 부채.
   - 새 시스템 설계 시 "최소 권한으로 동작 가능한가"를 API 초기 설계 단계에서 검증해야 한다. 나중에 끼우려면 이런 복잡한 부팅 패턴이 필요해진다.
