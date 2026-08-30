# Zabbix Agent Active vs Passive - 연결 방향이 방화벽·확장성·데이터 유실을 결정한다

## 출처

- **아티클**: Zabbix Agent: Active vs. Passive
- **저자/출처**: Dmitry Lambert, Zabbix Blog
- **링크**: https://blog.zabbix.com/zabbix-agent-active-vs-passive/9207/

> 원문은 2020년 글이라 그 사이 동작이 바뀐 부분이 있다. 이 문서는 **Zabbix 7.0 LTS 기준**으로 정리하고, 원문과 달라진 지점은 해당 항목에서 그때그때 짚었다. PoC는 `zabbix_server 7.0.30` / `zabbix_agent2 7.0.30`에서 돌렸다.
>
> 범위는 agent의 active/passive 수집 모델 하나다.

---

## AI 요약

### 0. 차이는 연결 방향 하나다

프론트엔드 아이템 타입 드롭다운에서 `Zabbix agent`와 `Zabbix agent (active)`는 한 칸 차이다. 실제로 바뀌는 것도 하나뿐이다.

```text
passive  : Zabbix server ──── connect ───▶ agent:10050     (서버가 들어간다)
active   : Zabbix server ◀─── connect ──── agent → :10051  (에이전트가 나간다)
```

변수는 하나인데 딸려오는 결과가 셋이다. 방화벽에 어떤 룰이 필요한가, 중앙 서버를 어떻게 늘리는가, 망이 끊겼을 때 데이터가 남는가. 이 문서는 그 순서로 간다.

### 1. 두 모드의 동작

#### Passive

서버(또는 프록시)의 poller가 에이전트의 10050/TCP에 접속해 값을 묻고, 받으면 연결을 닫는다. 값 하나당 연결 하나다.

```ini
Server=10.0.0.10,10.0.1.0/24
ListenPort=10050
```

`Server`는 접속할 대상이 아니라 **접속을 허용할 출발지** 목록이다. allow-list에 가까운 필드인데 이름이 `Server`라서, active의 `ServerActive`와 헷갈려 사고가 난다. `Server=`만 적어두고 아이템을 active로 만들면 에이전트는 나갈 주소를 모르니 아무것도 보내지 않는다.

이 모델에서는 서버가 아이템 목록도, `delay`도, 수집 타이밍도 전부 들고 있다. 에이전트는 물어볼 때만 일하는 센서다. 그래서 두 가지 성질이 따라온다.

- 서버가 IP/DNS로 찾아가므로 에이전트 쪽 `Hostname`은 아무 의미가 없다. 오타가 있어도 상관없다.
- 에이전트가 상태를 갖지 않는다. **"못 보낸 값"이라는 개념 자체가 없다.** 서버가 안 물어본 시각의 값은 애초에 존재한 적이 없다.

7.0부터는 passive의 요청/응답도 JSON 포맷이다.

#### Active

방향이 반대라서 단계가 두 개다. 에이전트는 자기가 뭘 수집해야 하는지 모르므로, 목록부터 받아와야 한다.

```text
[1단계] 설정 받기
  agent ──▶ server:10051   {"request":"active checks", "host":"web-01",
                            "config_revision":1, "session":"e3dc..."}
  agent ◀── server         {"response":"success", "config_revision":2,
                            "data":[{"key":"system.uptime","itemid":1234,"delay":"10s"}],
                            "commands":[]}

[2단계] 값 올리기
  agent ──▶ server:10051   {"request":"agent data",
                            "data":[{"itemid":5678,"value":"...",
                                     "clock":1712830783,"ns":76808644}],
                            "host":"web-01"}
```

```ini
ServerActive=10.0.0.10        # 나갈 주소 (server/proxy 의 trapper 포트)
Hostname=web-01               # 프론트엔드 host name 과 대소문자까지 일치해야 한다
RefreshActiveChecks=5         # 설정 동기화 주기 (7.0 기본값)
```

여기서 짚을 게 셋이다.

**`Hostname`이 조인 키다.** passive는 서버가 IP로 찾아가니 상대가 누군지 이미 알지만, active는 서버 앞에 웬 연결이 하나 들어온 상황이라 에이전트가 자기 이름을 대야 한다. 이름이 한 글자만 달라도 `host [web-01] not found`가 찍히고 아이템은 영원히 `No data`다. active 도입에서 제일 많이 밟는 지뢰라, active를 기본으로 쓰는 조직은 대개 `HostMetadata` 기반 autoregistration을 같이 켠다. 사람이 이름을 두 군데에 손으로 맞추는 구조를 없애는 것이다.

**값마다 `clock`(epoch 초)과 `ns`가 실려 간다.** 서버는 도착 시각이 아니라 이 `clock`으로 history에 적는다. active는 값이 만들어진 시각과 도착한 시각이 다를 수 있기 때문이다. 버퍼에 밀렸다가 한꺼번에 올라온 값들이 그래프를 망가뜨리지 않는 이유가 이 필드다. 4장의 되채움이 성립하는 전제이기도 하다.

**설정 동기화는 증분이다.** 6.4부터 `config_revision`과 `session`으로 바뀐 것만 받는다. 서버 리비전이 같으면 목록을 아예 보내지 않으니 5초 주기가 부담이 되지 않는다. 다만 동기화가 **실패하면 재시도는 하드코딩된 60초**다. `RefreshActiveChecks`를 줄여놔도 이건 안 줄어든다.

> **원문과 다른 점**: 원문의 "2분마다 전체 설정을 다시 받는다"는 지금 동작이 아니다.

#### 한눈에

| 항목 | Passive | Active |
| --- | --- | --- |
| 연결 방향 | server → agent:10050 | agent → server:10051 |
| 필수 설정 | `Server` (허용 출발지) | `ServerActive` + `Hostname` |
| 상대 식별 | 서버가 IP로 찾아감 | 에이전트가 이름을 댐 |
| 스케줄 주인 | 서버 | 에이전트 (목록만 받아옴) |
| history의 시각 | 서버 도착 시각 | 값에 실린 `clock` |
| 에이전트 상태 | 없음 | 버퍼 있음 |

### 2. 방화벽

passive는 "서버가 에이전트에 들어갈 수 있다"를 전제한다. 이게 안 되는 환경이 흔하다. NAT 뒤 지사 장비, 고객사 폐쇄망, inbound를 안 열어주는 보안 정책.

```text
active  :  agent → server:10051     ← 에이전트가 10대든 1만 대든 룰 하나
passive :  server → agent-01:10050
           server → agent-02:10050
           ...                       ← 대상이 늘 때마다 경로를 관리해야 하고
                                        NAT 뒤 호스트는 아예 불가능
```

나가는 연결은 대부분 열려 있으니, 방향만 뒤집으면 방화벽 협의 자체가 사라진다. PoC 시나리오 A가 이 전제를 그대로 검증한다.

### 3. 확장성

원문은 병목이 양쪽에 다르게 생긴다고 봤다. passive는 서버가 병목이지만 `StartPollers`를 올려 대응할 수 있고, active는 에이전트가 병목인데 프로세스가 하나뿐이라 손댈 방법이 없다는 것. 그래서 "느리고 병렬성이 필요한 체크는 passive"가 결론이었다.

7.0에서는 양쪽 다 바뀌었다.

**서버 쪽.** 7.0 기본 설정을 보면 숫자가 안 맞는 것처럼 보인다.

```ini
# zabbix_server.conf (7.0.30 기본값)
StartPollers=5                      # 기존 동기 poller
StartAgentPollers=1                 # 새로 생긴 비동기 agent poller
MaxConcurrentChecksPerPoller=1000   # 그 프로세스 하나가 동시에 처리하는 체크 수
```

프로세스 1개에 동시 체크 1000개다. 가능한 이유는 서버 입장에서 passive 체크가 거의 전부 대기이기 때문이다. 공식 문서 표현으로 "동기 poller 프로세스는 한 번에 하나의 체크만 실행할 수 있고 대부분의 시간을 응답 대기로 쓴다". 계산은 에이전트가 하고 서버는 기다린다. 15초짜리 체크에서 서버가 실제로 일하는 시간은 거의 0이다.

```text
동기 poller 1개
  [체크A ──── 15초 대기 ────][체크B ──── 15초 대기 ────]
                              ↑ B는 A가 끝날 때까지 시작도 못 함

비동기 agent poller 1개
  [체크A ──────── 15초 대기 ────────]
  [체크B ──────── 15초 대기 ────────]
  [체크C ──────── 15초 대기 ────────]   ← 대기는 겹쳐도 공짜
```

7.0 이상으로 올렸다면 passive 확장 계획을 `StartPollers` 증설이 아니라 `StartAgentPollers` × `MaxConcurrentChecksPerPoller`로 다시 계산해야 한다.

**에이전트 쪽.** 원문의 "프로세스가 하나뿐이라 못 늘린다"는 C로 작성된 클래식 `zabbix_agentd` 기준이다. Go로 다시 쓴 `zabbix_agent2`는 플러그인 단위로 동시성을 갖는다. 기동 로그에 그대로 찍힌다.

```text
using plugin 'Agent' (built-in) providing following interfaces: exporter, maximum capacity: 1000
using plugin 'Cpu'   (built-in) providing following interfaces: exporter, collector, runner, maximum capacity: 1000
```

`maximum capacity`가 플러그인별 동시 실행 상한이다. 그래서 "느린 체크가 있으니 passive"라는 판단은 agent2에서는 근거가 약하다. 클래식 agentd를 아직 쓴다면 원문 지적이 그대로 유효하다.

> **원문과 다른 점**: 확장성만 놓고 보면 두 모드의 차이가 거의 사라졌다. 원문 결론의 절반이 여기서 없어진다.

### 4. 데이터 유실 - 버퍼

passive는 에이전트가 상태를 갖지 않으니 단절 구간이 통째로 사라진다. active만 버퍼가 있다. 원문은 이걸 한 줄로 짚고 넘어가는데, 실무에서는 여기가 제일 크게 갈린다.

| 파라미터 | 7.0 기본값 | 의미 |
| --- | --- | --- |
| `BufferSize` | `1000` | 메모리에 쌓아둘 수 있는 값의 최대 **개수** |
| `BufferSend` | `5` | 버퍼를 서버로 밀어내는 주기(초) |
| `EnablePersistentBuffer` | `0` | 1이면 못 보낸 값을 SQLite 파일에도 적는다 |
| `PersistentBufferPeriod` | `1h` | 연결이 없을 때 보관할 최대 기간 |

`BufferSend=5` 덕에 평상시 버퍼는 거의 비어 있다. 쌓이는 건 서버가 안 받아줄 때뿐이라, `BufferSize`는 몇 년을 돌려도 존재감이 없다가 장애가 나서야 의미가 생긴다. 그래서 손대지 않은 채로 남아 있기 쉽다.

문제는 이게 시간이 아니라 개수라는 것이다.

```text
버틸 수 있는 시간(초) ≈ BufferSize ÷ (active 아이템 수 ÷ 평균 delay)

아이템 200개, 평균 delay 60초  →  초당 3.33건  →  1000 ÷ 3.33 ≈ 300초 (5분)
아이템 200개, 평균 delay 10초  →  초당 20건    →  1000 ÷ 20   ≈  50초
```

같은 호스트, 같은 기본값인데 5분과 50초다. 촘촘히 볼수록 안전망이 짧아진다. 버퍼가 차면 오래된 값부터 버리므로, 야간 회선 작업이 20분이면 기본값으로는 마지막 50초만 남는다. "active니까 망 끊겨도 괜찮다"는 말의 실제 유효기간이 이 정도다.

`EnablePersistentBuffer`는 보통 재시작 대비 옵션으로 소개되는데, 더 중요한 효과는 **보관 한도를 개수에서 시간으로 바꾸는 것**이다. 메모리는 1000건이 상한이지만 디스크는 `PersistentBufferPeriod` 동안 계속 받는다. 야간 작업이 30분 걸리는 환경이라면 선택이 아니라 필수다.

#### 버퍼가 지키지 않는 것

여기 함정이 하나 있다. 버퍼가 지키는 건 **이미 수집한 값**이지 **수집할 수 있는 상태**가 아니다.

active 에이전트는 아이템 목록을 서버에서 받아 메모리에만 들고 있다. 서버가 유일한 원천이고 에이전트는 캐시일 뿐인데, 이 캐시는 영속화되지 않는다.

```text
평상시
  에이전트 메모리: [아이템 목록] + [수집한 값들]
                        ↑              ↓
                   서버에서 받음   영속 버퍼가 지킴 (디스크)

서버가 죽은 동안 에이전트가 재시작되면
  에이전트 메모리: [        ] + [        ]
                      ↑ 날아감    ↑ 디스크에서 복구됨
                      ↑
                 서버가 없어 다시 못 받음  →  수집 자체가 멈춤
```

그래서 영속 버퍼를 켜뒀어도 재시작 이후 구간은 한 건도 안 남는다. 값을 잃은 게 아니라 애초에 만들어지지 않은 것이다. 문서에 크게 강조된 내용이 아니라서 PoC 시나리오 C로 직접 확인했다.

| 상황 | 메모리 버퍼만 | 영속 버퍼 |
| --- | --- | --- |
| 망 단절, 에이전트 정상 | `BufferSize` 한도까지 (개수) | `PersistentBufferPeriod` 한도까지 (시간) |
| 망 단절 + 재시작, 재시작 **이전** 수집분 | 잃는다 | 지킨다 |
| 망 단절 + 재시작, 재시작 **이후** 구간 | 잃는다 | 똑같이 잃는다 |

### 5. remote command는 더 이상 판단 기준이 아니다

원문 시점에는 active로 remote command를 보낼 수 없었다. 서버가 에이전트에게 말을 걸 방법이 없으니 당연했고, "자동 복구 스크립트가 필요하면 passive"가 합리적인 결론이었다.

7.0의 what's new에는 `Script execution on active agents`가 새 기능으로 올라와 있다. 방식은 1장에서 지나친 그 빈 배열이다. 서버가 먼저 말을 걸 수 없으니, **에이전트가 설정을 물으러 온 편에 실어 보낸다.**

```json
{"response":"success", "config_revision":2, "data":[...], "commands":[]}
                                                          ^^^^^^^^^^^
```

에이전트는 실행하고 결과까지 돌려보낸다. 그러니 "자동 복구 때문에 passive로 가야 한다"는 논리는 7.0 이상에서 성립하지 않는다.

다만 켤 때 알아둘 게 있다. `system.run` 계열은 설정 파일에 아무것도 안 적어도 기본이 거부다. 맨 끝에 `DenyKey=system.run[*]`가 있는 것처럼 동작한다. 즉 손대지 않은 에이전트는 이미 막혀 있고, 자동 복구를 쓰려면 명시적으로 열어야 한다.

```ini
# 나쁜 예: 사실상 임의 shell 실행을 허용한다
AllowKey=system.run[*]

# 좋은 예: 검토한 wrapper 하나만 허용하고, 나머지는 포괄 거부
AllowKey=system.run[/usr/local/bin/zbx-remediate.sh *]
DenyKey=system.run[*]
```

규칙은 위에서부터 평가하다 **첫 매치에서 멈춘다.** 순서를 뒤집어 `DenyKey`를 위에 두면 무엇이든 먼저 매치되어 `AllowKey`는 영원히 도달하지 못한다. 허용 규칙이 멀쩡히 적혀 있는데 아무것도 안 되는 상태가 되니, 원인 찾기가 성가시다.

그리고 이건 active가 안전해졌다는 뜻이 아니다. remote command를 켠다는 건 중앙 서버가 원격 호스트에서 코드를 실행할 수 있게 만드는 것이고, 위험은 연결 방향과 무관하다. 실행 범위를 검토된 wrapper 하나로 좁히는 건 어느 쪽을 쓰든 해야 한다.

### 6. 실무 기본값

앞의 세 축을 합치면 답은 "active 전용"이 아니다.

```text
기본:  거의 모든 수집 아이템 → Zabbix agent (active)
예외:  호스트 도달성 확인 1~2개 → Zabbix agent (passive)
```

active를 기본에 두는 이유는 방화벽 룰이 한 줄로 끝나고, 수집 타이밍 계산이 에이전트로 분산되고, 단절 구간이 되채워지기 때문이다. 확장성 논쟁이 정리된 지금 남은 비대칭은 사실상 방화벽 관리 비용과 버퍼 두 개뿐인데, 둘 다 active 쪽이다.

그런데도 passive를 완전히 없애면 안 되는 이유가 하나 있다. **active 전용 호스트는 "장비가 죽은 것"과 "설정이 안 맞는 것"이 똑같이 `No data`로 보인다.** `Hostname` 오타 하나로 아이템이 조용히 멈춰도, 화면상으로는 호스트가 죽은 것과 구분되지 않는다. 그리고 그래프가 빈 걸 매일 들여다보는 사람이 없으면 몇 달이 지나도 모른다.

passive는 서버가 직접 접속해보기 때문에 값과 별개로 "연결이 되더라/안 되더라"라는 신호를 만든다. 인터페이스 availability다. active는 이걸 만들 수 없다. 그래서 호스트마다 passive `agent.ping` 하나를 남겨두면 두 신호가 생기고, 교차하면 원인이 특정된다.

| 상황 | passive `agent.ping` | active 아이템 | 진단 |
| --- | --- | --- | --- |
| 정상 | 응답 | 값 들어옴 | — |
| 호스트 다운 | unavailable | No data | 장비 문제 |
| `Hostname` 오타 | 응답 | No data | 설정 문제 |
| inbound만 차단 | unavailable | 값 들어옴 | 네트워크 정책 문제 |

여기에 active 아이템에는 `nodata()` 트리거를 따로 건다. 도달성은 인터페이스 availability로, 수집 정상성은 `nodata()`로 판정하는 것이다. 호스트당 아이템 하나 늘리는 비용보다 원인이 구분된다는 값이 크다.

---

## PoC - 직접 띄워서 확인한 것

### 구성

`docker compose`로 Zabbix 7.0.30 한 벌과 성격이 다른 에이전트 4대를 띄운다.

```text
  postgres:16 ── zabbix-server 7.0.30 ── zabbix-web (:8080, API 프로비저닝용)
                        │
      ┌─────────────────┼─────────────────┬─────────────────────┐
      │                 │                 │                     │
 agent-passive   agent-active-mem  agent-active-disk  agent-inbound-blocked
 Server= 만       ServerActive      ServerActive       ServerActive
 (ServerActive    EnablePersistent  EnablePersistent   ListenIP=127.0.0.1
  없음)            Buffer=0          Buffer=1           (inbound 차단 재현)
```

측정 아이템은 전부 `system.localtime`, `delay=5s`, value type unsigned다. 이 키를 고른 건 **값 자체가 수집 시각(epoch)** 이라서, history에 저장된 `clock`과 값을 비교하면 "언제 수집했는지"와 "언제 저장했는지"를 한 번에 볼 수 있기 때문이다.

호스트/아이템 생성, 단절 유발, DB 조회, 판정은 전부 `verify.py`가 한다.

```bash
./run.sh          # 기동 + 검증 (약 6분)
./run.sh down     # 정리
```

> 아래 수치는 특정 1회 실행 결과다. 재실행하면 건수는 몇 건씩 흔들리지만 대소 관계는 그대로다. 클린 상태에서 2회 돌려 둘 다 11/11 통과했고, 두 번째 실행의 inbound 차단 호스트 누적은 passive 0건 / active 63건이었다.

### A. inbound가 막히면 무엇이 죽는가

`agent-inbound-blocked`는 `ListenIP=127.0.0.1`로 묶여 있어 10050이 루프백에만 떠 있다.

```text
$ docker exec zbxpoc-agent-inbound-blocked cat /proc/net/tcp
  sl  local_address rem_address   st ...
   0: 0100007F:2742 00000000:0000 0A ...      # 0100007F = 127.0.0.1, 2742 = 10050
```

이 호스트 하나에 같은 값을 재는 아이템 두 개를 걸었다. 하나는 passive(`system.localtime[utc]`), 하나는 active(`system.localtime`).

```text
[PASS] inbound 차단 시 passive 아이템: 45초 동안 수집값 0건 (기대: 0건)
[PASS] inbound 차단 시 active 아이템: 45초 동안 수집값 7건 (기대: 5건 이상)
[PASS] inbound 차단 호스트의 agent 인터페이스 상태: available=2 (2 = unavailable 기대)
```

전체 실행(약 6분) 누적으로는 passive 0건, active 65건이다. 서버가 남긴 인터페이스 에러도 원인을 그대로 말해준다.

```text
Get value from agent failed: Cannot establish TCP connection to
[[zbxpoc-agent-inbound-blocked]:10050]: [111] Connection refused
```

에이전트 프로세스는 살아 있고 값을 만들 능력도 있다. 죽은 건 "서버가 들어올 수 있는가" 하나다. 6장 표의 마지막 줄(inbound만 차단 → passive unavailable / active 정상)이 실제로 재현된 셈이다.

### B. 중앙이 60초 사라졌을 때 무엇이 남는가

`zabbix-server` 컨테이너를 60초 정지시켰다 다시 올린다. 에이전트 3대는 계속 살아 있다.

```text
[15:53:19]   서버 정지 (t=1788072799)
[15:54:20]   서버 기동 (t=1788072859), 정착 대기 65초

[PASS] passive: 단절 구간 수집값: 0건 (기대: 0건, 최대 공백 56초)
[PASS] active + 메모리 버퍼: 단절 구간 되채움: 12건 / 기대 약 12건, 최대 공백 5초
[PASS] active + 메모리 버퍼: 되채운 값의 타임스탬프: 수집시각과 저장 clock 최대 오차 0초
[PASS] active + 디스크 버퍼: 단절 구간 되채움: 12건 / 기대 약 12건, 최대 공백 5초
[PASS] active + 디스크 버퍼: 되채운 값의 타임스탬프: 수집시각과 저장 clock 최대 오차 0초
```

history의 `clock`을 서버 정지 시각 기준 상대초로 늘어놓으면 차이가 눈에 보인다.

```text
passive     : -19 -14 -9 -4 │                                   │ 66 71 76 81 86 91 96
active+disk : -17 -12 -7 -2 │ 3 8 13 18 23 28 33 38 43 48 53 58 │ 63 68 73 78 83 88 93 98
                            └─────── 서버 부재 구간 60초 ───────┘
```

**passive의 구멍이 단절 시간보다 길다(70초 > 60초).** 서버가 살아나도 즉시 재개되지 않기 때문이다. 폴링에 실패한 호스트는 unreachable을 거쳐 unavailable로 내려가고, 그 뒤로는 `UnreachableDelay`/`UnavailableDelay` 주기로만 재시도한다. 이 PoC는 실험 회전 때문에 이 값들을 기본값보다 훨씬 짧게 줄여 뒀는데도 10초가 더 붙었다.

| `zabbix_server.conf` | 7.0 기본값 | 이 PoC |
| --- | --- | --- |
| `UnreachablePeriod` | 45 | 15 |
| `UnreachableDelay` | 15 | 5 |
| `UnavailableDelay` | 60 | 10 |

기본값이었다면 재개까지의 추가 지연은 더 커진다. 장애 시간이 곧 데이터 구멍이 아니라, **장애 시간 + 가용성 복구 지연**이 데이터 구멍이다.

반대로 active의 되채움은 시계열을 왜곡하지 않았다. `system.localtime` 값(수집 시각)과 history의 `clock`(저장 시각) 오차가 0초다. 버퍼에 있던 값이 60초 뒤 한꺼번에 도착했지만 서버는 도착 시각이 아니라 `agent data` 안의 `clock`으로 적었다. 1장에서 본 그 필드가 여기서 값을 한다. 그래서 그래프에 60초짜리 평평한 선이나 스파이크가 생기지 않고, 트리거 계산도 원래 시각 기준으로 맞는다.

```text
06:53:24 [101] history upload to [zabbix-server:10051] [poc-active-disk] started to fail
06:54:38 [101] history upload to [zabbix-server:10051] [poc-active-disk] is working again
```

### C. 단절 중에 에이전트가 재시작되면

같은 60초 단절을 다시 만들되, 단절 25초 시점에 active 에이전트 두 대를 `docker restart` 한다. 야간 단절 중에 배포나 OOM으로 에이전트가 재기동되는 상황이다.

```text
[PASS] 메모리 버퍼: 재시작 전 수집분: 0건 남음 (기대: 0건 - 프로세스와 함께 소실)
[PASS] 디스크 영속 버퍼: 재시작 전 수집분: 5건 남음 (기대: 2건 이상 - SQLite 에서 복구)
[PASS] 영속 버퍼가 지켜주지 않는 것: 재시작 이후 구간: 0건
```

```text
$ docker exec zbxpoc-agent-active-disk ls -l /tmp/
-rw-r--r-- 1 zabbix zabbix 36864 Aug 30 06:57 agent2-buffer.db   # EnablePersistentBuffer=1

$ docker exec zbxpoc-agent-active-mem ls -l /tmp/
(버퍼 파일 없음)                                                  # EnablePersistentBuffer=0
```

세 번째 결과가 이 PoC에서 제일 건진 부분이다. **영속 버퍼를 켠 에이전트조차 "재시작 이후 ~ 서버 복귀" 구간은 0건이었다.** 4장에서 설명한 그 함정이고, 로그가 이유를 말해준다.

```text
06:55:51 Zabbix Agent 2 stopped. (7.0.30)
06:55:51 Starting Zabbix Agent 2 (7.0.30)
06:55:53 [101] cannot connect to [zabbix-server:10051]: ... no such host
06:55:53 [101] active check configuration update from host [poc-active-disk] started to fail
06:56:55 [101] active check configuration update from [zabbix-server:10051] is working again
```

재시작으로 아이템 목록이 비었는데 서버가 없어 다시 받지 못하니 수집이 멈춘다. 복구도 즉시가 아니다. 1장에서 본 하드코딩된 60초 재시도 때문에 `06:55:53` 실패 이후 `06:56:55`, 정확히 62초 뒤에야 회복됐다.

---

## 내가 얻은 인사이트

**드롭다운 한 칸이 아니라 네트워크 계약을 고르는 것이다.** 아이템 타입을 `Zabbix agent`로 두면 "서버가 이 호스트에 들어갈 수 있다"를 전제로 삼는 것이고, `(active)`로 두면 "이 호스트가 서버로 나갈 수 있다"를 전제로 삼는 것이다. 모니터링 도구 설정처럼 보이지만 실제로는 방화벽팀·보안팀과 맺는 계약에 가깝다. 그래서 되돌리기가 비싸다. 수천 대에 passive로 깔아둔 뒤 "NAT 뒤 지사도 봐야 한다"가 나오면, 아이템 타입만 바꾸는 게 아니라 모든 호스트의 `Hostname` 정합성을 새로 맞춰야 한다.

**확장성 논쟁이 끝나고 남은 건 방화벽 룰 개수다.** 7.0의 비동기 agent poller가 나오면서 "passive는 서버가 병목"이라는 근거는 상당 부분 사라졌다. 그런데 네트워크 쪽 비대칭은 그대로다. active는 에이전트가 몇 대로 늘어나든 룰 하나지만, passive는 대상이 늘 때마다 inbound 경로를 관리해야 한다. 성능 얘기인 줄 알았던 선택이 사실은 운영 비용 얘기였던 셈이다.

**버전이 다르면 원문의 결론도 다르다는 걸 문서에 박아둬야 한다.** 이번 정리에서 원문 결론을 떠받치던 근거 두 개(remote command 불가, active 직렬 처리)가 7.0에서 뒤집혔다. 2020년 글을 읽고 "자동 복구가 필요하니 passive"라고 결정한 조직이 있다면, 그 결정은 근거가 사라진 채로 남아 있는 것이다. "왜 이 선택을 했는가"를 버전과 함께 적어두지 않으면 근거가 만료돼도 결론만 계속 상속된다.

**장애 시간과 데이터 구멍은 같지 않다.** PoC에서 60초 단절에 passive의 실제 구멍은 70초였다. `UnreachableDelay`/`UnavailableDelay`를 기본값보다 훨씬 짧게 줄여 뒀는데도 그랬으니, 기본값 환경에서 짧은 회선 flap이 나면 실제 구멍은 체감보다 훨씬 길다. 사후 분석에서 "그래프가 비어 있는 구간 = 장애 구간"으로 읽으면 안 된다.

**`BufferSize`는 개수가 아니라 시간으로 환산해서 봐야 한다.** 아이템 200개를 10초 주기로 도는 호스트라면 기본 버퍼는 50초밖에 못 버틴다. "active면 망 끊겨도 괜찮다"는 통념이 여기서 깨진다. 그리고 영속 버퍼를 켜도 단절 중 에이전트가 재기동되면 그 이후 구간은 한 건도 안 남는다. 아이템 목록이 메모리에만 있고 서버에서 다시 받아야 하는데 서버가 없기 때문이다. 결국 야간 회선 작업 창과 배포·패치 창을 겹치지 않게 잡는 것이 설정 튜닝보다 효과가 크다.

**모니터링은 "못 보고 있다"는 상태도 관측해야 한다.** active 전용으로 가면 호스트가 죽은 것과 `Hostname` 오타로 값이 안 올라오는 것이 똑같이 `No data`다. PoC의 `poc-inbound-blocked`가 이 구도를 보여줬다 — active 아이템 65건이 멀쩡히 들어오는 동안 passive 아이템은 0건이었고, 인터페이스만 `Connection refused`로 원인을 말해줬다. 그래서 실무 기본값은 active 중심에 도달성 확인용 passive 하나를 붙이는 쪽이다. 진단 신호 두 개를 분리해 두는 값이 아이템 하나 비용보다 크다.
