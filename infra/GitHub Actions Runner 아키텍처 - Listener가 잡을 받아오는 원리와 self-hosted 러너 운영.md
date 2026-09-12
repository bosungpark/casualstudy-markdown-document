# GitHub Actions Runner 아키텍처 - Listener가 잡을 받아오는 원리와 self-hosted 러너 운영

## 출처
- **아티클/논문**: GitHub Actions Runner architecture: The Listener (Part 1)
- **저자/출처**: Depot (depot.dev 엔지니어링 블로그, 2025-08)
- **링크**: https://depot.dev/blog/github-actions-runner-architecture-part-1-the-listener

> 이 문서의 "AI 요약"은 위 아티클 한 편의 내용만 정리한 것이다.
> 아티클에 없지만 운영에 필요한 사실은 "내가 얻은 인사이트" 아래에 출처를 따로 밝혀 구분했다.

---

## AI 요약

### 1. 한 줄 요약

GitHub Actions 러너는 **GitHub이 내 서버로 잡을 밀어넣는(push) 구조가 아니다.**
러너 쪽 프로세스가 GitHub에 계속 "일 있어요?"라고 **물어보러 나가는(pull/long-poll)** 구조다.
이 한 가지 사실이 self-hosted 러너의 방화벽 정책, 장애 증상, 스케일링 방식 전부를 결정한다.

### 2. 러너는 프로세스가 두 개다

러너를 설치하면 실행 파일이 두 개 돈다.

| 프로세스 | 역할 |
|----------|------|
| **Listener** (`Runner.Listener`) | 러너를 등록하고, GitHub API에 롱폴링으로 일감을 물어보고, 세션과 잡 락(lock)을 유지하고, 잡을 Worker에게 넘긴다 |
| **Worker** (`Runner.Worker`) | 넘겨받은 잡의 step들을 실제로 실행한다 (아티클 Part 2 주제) |

이 아티클은 **Listener만** 다룬다. 즉 "빌드가 어떻게 돌아가는가"가 아니라 **"빌드가 어떻게 내 서버까지 도달하는가"**의 이야기다.

### 3. 등록(config.sh)이 실제로 하는 일

등록은 GitHub API를 호출해 **JIT(just-in-time) 러너 구성**을 만드는 것으로 시작한다.
흥미로운 점은, GitHub 백엔드가 내부적으로 **Azure DevOps 에이전트 등록**을 호출한다는 것이다. Actions의 뿌리가 Azure Pipelines라는 계보가 여기서 드러난다.

등록이 끝나면 러너 쪽에 이런 값들이 떨어진다.

| 항목 | 의미 |
|------|------|
| `ServerUrl` | Azure Pipeline API URL (레거시 경로) |
| Authorization URL | 토큰 갱신용 인증 엔드포인트 |
| **RSA private key** | JWT 서명용 개인키 |
| OAuth access token | 이후 요청의 Bearer 인증에 사용 |
| `ServerUrlV2` | 신규 **GitHub Actions Broker API** 주소 |
| `UseV2Flow` | true면 Azure DevOps 레거시 엔드포인트 대신 Broker API를 쓰라는 스위치 |

구성 필드는 다음과 같은 것들이다.

```
AgentId, AgentName, PoolId, WorkFolder, GitHubUrl, ServerUrlV2, UseV2Flow
```

이 구성은 **CLI 인자로 Listener 프로세스에 전달**된다.

> 핵심: 등록 토큰은 "등록할 때 한 번" 쓰이고 끝이다. 이후 통신은 위의 OAuth 토큰과 RSA 키로 이뤄진다.

### 4. 세션 생성 — 러너가 "출근 도장"을 찍는 단계

Listener는 먼저 Azure의 **ConnectionData**를 내려받는다. 리소스 URL 경로를 동적으로 만들어내는 REST 스키마다.
그다음 세션을 만든다.

```http
POST ${ServerUrlV2}/sessions HTTP/1.1
Authorization: Bearer {OAUTH_TOKEN}
```

요청 본문에 들어가는 것:

| 필드 | 내용 |
|------|------|
| `sessionId` | UUID |
| `ownerName` | **호스트명 + PID** |
| `agent.id` / `agent.name` | 등록 시 받은 AgentId / AgentName |
| `agent.version` | 예: `2.327.1` |
| `agent.osDescription` | OS 정보 |
| `agent.ephemeral` | 1회용 러너 여부 |
| `agent.status` | 상태 |
| `useFipsEncryption` | FIPS 암호화 사용 여부 |

서버는 `sessionId`를 되돌려주고, **이후 모든 API 호출은 이 sessionId를 달고 간다.**

여기서 **러너 버전 검증**이 일어난다. 버전이 너무 낡으면 서버는 `400 Bad Request`를 준다.
UI에 "Offline"만 뜨고 이유를 모르는 상황의 상당수가 이 단계다.

### 5. 롱폴링 — 50초짜리 "일 있어요?"

세션이 열리면 Listener는 메시지를 계속 물어본다.

```http
GET ${ServerUrlV2}/message
      ?sessionId=${sessionId}
      &status=Online
      &runnerVersion=2.327.1
      &os=Linux
      &architecture=X64
      &disableUpdate=true
```

동작 방식:

| 상황 | 서버 동작 |
|------|-----------|
| 일감 없음 | 연결을 **최대 50초간 붙잡고 있다가** 빈 응답 + `202 Accepted` 반환 |
| 일감 있음 | 즉시 메시지 본문 반환 |

응답이 오면 이런 모양이다.

```json
{
  "messageId": 12345,
  "messageType": "RunnerJobRequest",
  "body": "{\"runner_request_id\":\"<UUID>\",\"run_service_url\":\"<URL>\",\"billing_owner_id\":\"<ID>\"}"
}
```

여기서 중요한 제약: **메시지를 받은 뒤 약 2분 안에 잡을 획득하고 시작해야 한다.**

> `status=Online`을 매 폴링마다 실어 보내는 것이 곧 하트비트다. 즉 "러너가 살아 있다"는 신호와 "일 달라"는 요청이 같은 요청 하나로 처리된다.

### 6. 잡 획득(acquirejob) — 실제 잡 내용은 여기서 온다

폴링으로 온 메시지는 **"일이 있다"는 알림일 뿐, 잡 내용이 아니다.** 내용은 별도 호출로 가져온다.

```http
POST ${run_service_url}/acquirejob
```
```json
{
  "jobMessageId": "${runner_request_id}",
  "runnerOS": "Linux",
  "billingOwnerId": "${billing_owner_id}"
}
```

응답은 아티클 표현으로 **"매우 큰(very large)"** 본문이며, 잡을 실행하는 데 필요한 모든 지시가 들어 있다.
여기서 `planId`를 얻는데, 응답 헤더 `x-plan-id`와 본문 `.plan.planId` 양쪽에 들어 있다.

이 응답을 받은 뒤에야 Listener는 Worker 프로세스를 띄운다.

### 7. 잡 락 갱신(renewjob) — "나 아직 살아서 돌리고 있어요"

잡을 획득한 **즉시** Listener는 백그라운드 갱신 태스크를 시작한다.

```http
POST ${run_service_url}/renewjob
```
```json
{ "planId": "${x-plan-id}", "jobId": "${runner_request_id}" }
```
```json
{ "lockedUntil": "2006-01-02T15:04:05.000000000Z" }
```

| 항목 | 값 |
|------|-----|
| 갱신 주기 | **1분마다** (잡이 끝날 때까지) |
| 락 만료 | 보통 갱신 시점으로부터 **10분 후** |
| 락 안에 잡을 시작 못하면 | **서버가 잡을 취소** |

즉 러너가 죽거나 네트워크가 끊기면 락이 자연 만료되고, 서버는 그 잡을 회수한다. 이게 Actions가 "먹통 러너"를 정리하는 메커니즘이다.

### 8. V1 → V2(Broker API) 마이그레이션

`ServerUrlV2` / `UseV2Flow`가 붙은 이유는, 레거시 Azure DevOps 엔드포인트가 **GitHub Actions Broker API**로 교체되고 있기 때문이다.
아티클의 정리: **Listener가 하는 일의 원리(물어보고 → 복호화/획득하고 → 넘기고 → 결과 보고)는 그대로지만, 그 아래 배관은 완전히 다르다.** 요청·응답 포맷이 다르고, 신규 API는 Azure가 되돌려주던 일부 필드를 생략한다.

### 9. 전체 흐름 한눈에

```
[내 리눅스 서버]                                  [GitHub]
     │
  config.sh  ──── 등록 토큰 ──────────────────────▶  JIT runner config 생성
     │                                              (내부적으로 Azure DevOps
     │  ◀── OAuth token, RSA key, ServerUrlV2 ───     agent 등록 호출)
     │
  Runner.Listener 기동
     │
     ├─ GET ConnectionData ────────────────────────▶
     ├─ POST /sessions ────────────────────────────▶  버전 검증 (낡으면 400)
     │  ◀── sessionId ────────────────────────────
     │
     ├─ GET /message?sessionId=...&status=Online ──▶  ┐
     │  ◀── (50초 대기 후) 202 Accepted, 빈 본문 ──   │ 일감 없으면
     ├─ GET /message ... ──────────────────────────▶  │ 계속 반복
     │  ◀── RunnerJobRequest ──────────────────────   ┘
     │        { runner_request_id, run_service_url, billing_owner_id }
     │
     │   ※ 여기서부터 약 2분 안에 시작해야 함
     │
     ├─ POST /acquirejob ─────────────────────────▶
     │  ◀── 거대한 잡 정의 + x-plan-id ────────────
     │
     ├─ POST /renewjob (1분마다, 락 10분) ─────────▶
     │
     └─▶ Runner.Worker 프로세스 기동 → step 실행
```

---

## 내가 얻은 인사이트

### 관점 A. 리눅스에 러너를 직접 띄우는 입장에서

1. **인바운드 포트를 열 이유가 전혀 없다 — 풀 모델의 직접적 귀결**
   - 아티클의 모든 통신이 러너 → GitHub 방향이다. 세션 생성도, 폴링도, acquirejob도, renewjob도 전부 러너가 건다.
   - 그래서 러너를 **NAT 뒤, 사설망, 심지어 공인 IP 없는 사내망**에 둬도 된다. VPN이나 bastion, 인그레스 설정이 필요 없다.
   - (공식 문서 확인) GitHub 문서도 "호스트는 443 아웃바운드 HTTPS만 가능하면 되고, GitHub이 러너로 인바운드 연결을 맺을 필요는 없다"고 명시한다. `*.actions.githubusercontent.com` 접근이 필수다. → https://docs.github.com/en/actions/concepts/runners/communicating-with-self-hosted-runners
   - **실전 결론**: 러너가 안 붙으면 방화벽 인바운드부터 보지 말고, **아웃바운드 443과 프록시/SSL 인터셉션**을 먼저 의심한다. 사내 프록시가 TLS를 뜯어보는 환경이면 50초 롱폴링을 중간에 끊어버리는 경우가 흔하다.

2. **"러너가 Idle인데 잡을 안 물어요"는 3단계로 쪼개서 본다**

   | 증상 | 실패한 단계 | 확인 포인트 |
   |------|-------------|-------------|
   | UI에 Offline | `POST /sessions` 실패 | 러너 버전(400 Bad Request), 토큰 만료, 아웃바운드 차단 |
   | Idle인데 잡이 안 옴 | `GET /message`는 도는데 매칭 실패 | `runs-on` 라벨 오타, runner group 권한, 다른 러너가 먼저 가져감 |
   | 잡을 잡았다가 바로 취소 | acquire/renew 단계 | 2분 안에 시작 못함, 락 갱신 실패(네트워크 끊김), Worker 기동 실패 |

   로그가 `_diag/Runner_*.log`(Listener)와 `_diag/Worker_*.log`(Worker)로 나뉘어 있다는 사실도 이 2-프로세스 구조에서 나온다. **잡을 못 받는 문제는 Runner 로그, 잡이 실패하는 문제는 Worker 로그**다.

3. **2분 / 10분이라는 숫자가 오토스케일링 설계를 규정한다**
   - 메시지를 받고 잡을 시작하기까지 약 2분, 락은 10분.
   - "잡이 큐에 쌓이면 그때 VM을 부팅한다"는 순진한 오토스케일링은 **VM 부팅 + 러너 등록이 2분을 넘기는 순간 무너진다.**
   - 그래서 실전에서는 (a) **warm pool**을 최소 1~2대 유지하거나, (b) 이미 떠 있는 러너가 메시지를 받은 뒤 다음 러너를 미리 준비시키는 식으로 간다.
   - AMI/이미지에 러너 바이너리와 도커 이미지를 미리 구워두는 게 "최적화"가 아니라 **타임아웃을 넘기지 않기 위한 필수 조건**인 이유가 여기 있다.

4. **버전 업그레이드는 선택이 아니다**
   - 세션 생성에서 버전 검증이 일어나고 낡으면 400이다. 즉 **낡은 러너는 조용히 느려지는 게 아니라 아예 붙지 못한다.**
   - 폴링 쿼리에 `disableUpdate=true`가 보이는데, 자동 업데이트를 끄고 운영한다면 러너 버전 모니터링을 직접 해야 한다는 뜻이다. 컨테이너/이미지로 러너를 굽는 팀이라면 **이미지 재빌드 주기를 러너 릴리스에 맞춰 잡아야 한다.**

5. **`agent.ephemeral` 필드가 세션에 들어간다는 건, 1회용이 1급 개념이라는 뜻**
   - (공식 문서 확인) REST API로 **JIT 러너**를 만들면 최대 한 개의 잡만 처리하고 자동으로 제거된다. → https://docs.github.com/en/actions/reference/security/secure-use
   - 다만 **ephemeral 등록 ≠ 깨끗한 컴퓨트**다. 러너 등록만 1회용이고 그 아래 VM·노드·도커 데몬·캐시·볼륨을 재사용하면 잡 사이에 상태가 샌다.
   - **실전 결론**: 1회용으로 쓸 거면 러너 등록이 아니라 **머신(또는 Pod) 자체를 버려야** 의미가 있다.

### 관점 B. 보안 — 직접 돌릴 때 가장 비싼 함정

6. **퍼블릭 레포에 self-hosted 러너를 붙이지 않는다**
   - (공식 문서 확인) GitHub은 "퍼블릭 저장소에는 self-hosted 러너를 거의 절대 쓰지 말라"고 못 박는다. 누구나 PR을 열 수 있고, PR의 코드가 곧 러너 위에서 실행되기 때문이다. → https://docs.github.com/en/actions/reference/security/secure-use
   - 러너가 **아웃바운드로 GitHub에 붙는다**는 바로 그 성질이, 침해당했을 때 공격자에게도 훌륭한 아웃바운드 채널이 된다. 인바운드가 막혀 있으니 안전하다는 직관은 틀렸다.
   - 프라이빗 레포라도 `pull_request_target`, fork PR, 서드파티 action 핀 고정(`uses: org/action@<full-sha>`)은 똑같이 챙겨야 한다.

7. **러너 디렉터리 자체가 크리덴셜 저장소다**
   - 등록 시 **RSA private key와 OAuth 토큰**이 러너 머신에 파일로 떨어진다(`.credentials`, `.credentials_rsaparams`, `.runner`).
   - 잡이 이 파일들을 읽을 수 있으면 러너 신원 자체가 탈취된다. → 러너 프로세스 전용 유저로 돌리고, 잡이 러너 설치 디렉터리에 접근하지 못하게 권한을 분리한다. `_work` 아래에서만 작업하게 두는 게 기본이다.

### 관점 C. 운영 형태 선택

8. **VM에 직접 vs ARC(Kubernetes), 판단 기준**

   | 기준 | VM + systemd 서비스 | ARC (Actions Runner Controller) |
   |------|--------------------|--------------------------------|
   | 시작 비용 | 낮음 (`svc.sh install`로 끝) | 높음 (클러스터 + 컨트롤러 운영) |
   | 잡 간 격리 | 약함 (같은 머신 재사용) | 강함 (Pod 단위 1회용) |
   | 스케일 0 | 어려움 | 쉬움 |
   | 도커 빌드 | 자연스러움 | DinD/rootless 고민 필요 |

   - **입문 추천**: 리눅스 VM 1~2대에 systemd 서비스로 올리고, 라벨을 목적별로 붙여 `runs-on: [self-hosted, linux, x64, gpu]`처럼 라우팅하는 것부터 시작한다. 위 아키텍처를 이해했다면 이 단계에서 생기는 문제의 90%는 진단 가능하다.
   - (운영 팁, 공식 문서 확인) 서비스로 돌릴 때는 커스텀 설정을 하더라도 반드시 `runsvc.sh`를 엔트리포인트로 써야 한다. Debian 계열에서는 `needrestart`가 잡 실행 중에 러너 서비스를 재시작해버릴 수 있어 제외 설정이 필요하다. → https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application

9. **이 아키텍처를 알고 나면 달라지는 질문**
   - 기존: "러너가 왜 느리지?" → 막연히 CPU를 올린다.
   - 이후: "느린 게 **잡 도달(Listener)**인가 **잡 실행(Worker)**인가?"로 먼저 쪼갠다.
     - 잡 대기 시간이 긴가 → 러너 대수/warm pool/라벨 매칭 문제
     - 잡 자체가 긴가 → 캐시·디스크 I/O·도커 레이어 문제
   - 이 구분이 self-hosted 러너 튜닝에서 가장 먼저 해야 할 일이다.

### 남은 질문 (Part 2에서 확인할 것)
- Worker가 step을 어떻게 실행하고, 로그를 어떤 주기로 업로드하는가
- 컴포지트 액션/컨테이너 액션의 실행 경계
- 잡 취소 신호가 Worker까지 전달되는 경로
