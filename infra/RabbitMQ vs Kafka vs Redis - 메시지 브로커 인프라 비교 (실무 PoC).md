# RabbitMQ vs Kafka vs Redis - 메시지 브로커 인프라 비교 (실무 PoC)

## 출처
- **아티클/논문**: Redis Pub/Sub vs Kafka vs RabbitMQ — Message Broker Comparison (2026)
- **저자/출처**: index.dev (Skill-vs-Skill 시리즈). 보조 근거로 designgurus "Push vs. Pull: Understanding the Internals of Distributed Messaging"의 *push/pull* 프레이밍을 참조.
- **링크**: https://www.index.dev/skill-vs-skill/redis-pubsub-vs-kafka-vs-rabbitmq

> 본 문서는 위 아티클의 "세 브로커는 결국 **전달 모델(push/pull)·저장 모델(log/queue/in-memory)·전달 보장**이 다른 물건"이라는 핵심을
> 중심으로, **세 브로커를 실제로 Docker로 띄워놓고 직접 측정한 PoC**를 곁들여 정리했다.
> 모든 PoC는 **macOS 14 + Docker Desktop(11 vCPU / 8GB), 단일 노드, Python 클라이언트로 직접 실행해 검증**했다.
> 처리량 절대수치는 노트북·클라이언트 바운드라 브로커의 최대치가 아니다 — **상대적 형태(shape)와 결정론적 동작**에 주목할 것.

---

## AI 요약

### 0. 한 장 요약

| 질문 | 핵심 답 |
|------|---------|
| 셋의 본질적 차이는? | **저장 모델**이다. Redis Pub/Sub=무저장 브로드캐스트, RabbitMQ=소비되면 사라지는 **큐**, Kafka=지워지지 않는 **로그(offset)** |
| 누가 "민다(push)"? | Redis·RabbitMQ는 브로커가 소비자에게 **push**, Kafka는 소비자가 **pull**(자기 속도로 fetch) |
| 소비자가 잠깐 죽으면? | Redis Pub/Sub은 **그 사이 메시지 영구 소실**, RabbitMQ는 큐에 쌓임, Kafka는 로그에 남고 **나중에 재생(replay)** 가능 |
| 누가 제일 빠른가? | 질문이 틀렸다. **지연**은 Redis≪RabbitMQ<Kafka, **지속성 있는 처리량**은 Kafka가 압도 |
| Kafka가 왜 느려 보이나? | 처리량을 위해 **배치·로그 append**에 최적화 → 단건 왕복 지연은 RabbitMQ보다 느림 |
| 실무 선택 한 줄 | 작업 분배·라우팅·요청응답=**RabbitMQ**, 이벤트 로그·재생·고처리량=**Kafka**, 캐시 무효화·실시간 알림(유실 허용)=**Redis** |

### 1. 세 가지는 사실 "다른 카테고리"다

같은 "메시지 브로커"로 묶이지만 저장 모델이 다르고, 그래서 전달 보장도 다르다.

```
 Redis Pub/Sub          RabbitMQ (AMQP)            Kafka (log)
 ─────────────          ──────────────            ────────────
 pub ──┐                pub → exchange            pub → topic/partition
       │ 즉시 broadcast        │ 라우팅(key)              │ append-only 로그
       ▼                      ▼                          ▼
 [구독자 A][B][C]        [queue]──push──▶소비자     [ 0 1 2 3 4 5 ... ]  ← offset
   (지금 연결된                  │ ack 받으면 삭제        ▲      ▲
    사람만 받음)                                     groupA  groupB
 ✗ 저장 안 함            ✓ 소비 전까지 큐에 보관      각자 offset으로 독립 소비
 ✗ 유실                  ✓ at-least-once            ✓ 보존 + 재생(replay)
```

| 축 | Redis Pub/Sub | RabbitMQ | Kafka |
|----|---------------|----------|-------|
| 전달 모델 | push(broadcast) | push(queue) | **pull**(consumer fetch) |
| 저장 모델 | 없음(in-memory 순간) | 큐(소비 시 삭제) | 로그(보존, 시간/크기 기준) |
| 전달 보장 | at-most-once | at-least-once(+ack) | at-least-once / **exactly-once**(트랜잭션) |
| 순서 | 보장 안 함 | 단일 큐 내 보장 | **파티션 내 보장** |
| 소비자 확장 | 전원이 동일 복사본 | 경쟁 소비(competing) | **consumer group + 파티션 분배** |
| 재생(replay) | 불가 | 불가(ack되면 끝) | **가능**(offset seek) |
| 본업 | in-memory KV/캐시 | AMQP 메시지 큐 | 분산 이벤트 스트리밍 로그 |

> ※ Redis는 Pub/Sub 외에 **Streams**(`XADD`/`XREAD`)도 있다. Streams는 Kafka처럼 로그에 적재·보존되며
> consumer group도 지원한다. 즉 "Redis=무조건 유실"이 아니라 **어떤 자료구조를 쓰느냐**의 문제다.
> (PoC 3에서 Pub/Sub과 Streams의 차이를 직접 확인한다.)

### 2. push vs pull — 백프레셔가 갈린다

- **push(RabbitMQ)**: 브로커가 소비자에게 밀어넣는다. 빠른 응답·복잡한 라우팅에 유리하지만, 소비자가 느리면
  브로커가 부담을 떠안는다 → `prefetch(QoS)`로 미전달 메시지 수를 제한해 **백프레셔**를 건다.
- **pull(Kafka)**: 소비자가 자기 속도로 `fetch`한다. 느린 소비자는 그냥 **자기 offset이 뒤처질 뿐**(lag),
  브로커는 영향이 없다. → 소비자를 추가해도 브로커 부하가 비례해 늘지 않는다(로그를 읽을 뿐이므로).
- **Redis Pub/Sub**: 백프레셔 개념 자체가 없다. 못 받으면 그냥 **버려진다**.

```
느린 소비자가 생겼을 때:
 RabbitMQ → 큐가 쌓임(메모리/디스크 압박) → prefetch로 제어
 Kafka    → consumer lag만 증가, 브로커는 평온 (디스크에 이미 다 있음)
 Redis P/S→ 소비자 버퍼 넘치면 연결 끊고 메시지 유실
```

---

## PoC: 셋을 실제로 띄워놓고 측정하기

### 0. 환경 구성 (`docker-compose.yml`)

```yaml
services:
  redis:    { image: redis:7-alpine, ports: ["6379:6379"],
              command: ["redis-server","--appendonly","no","--save",""] }
  rabbitmq: { image: rabbitmq:3.13-management, ports: ["5672:5672","15672:15672"] }
  kafka:                                   # KRaft 모드 단일 노드 (ZooKeeper 불필요)
    image: apache/kafka:3.9.0
    ports: ["9092:9092"]
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      # (리스너/보안맵 등 단일노드 필수값 생략)
```

```bash
docker compose up -d
pip install redis pika kafka-python-ng   # 순수 파이썬 클라이언트(컴파일 불필요)
```

### PoC ①: 인제스트 처리량 (durable, 256B × 30,000건)

각 브로커에 "안전하게(지속성 켜고)" 3만 건을 밀어넣는 데 걸린 시간으로 초당 처리량을 쟀다.
단, **Redis만은 compose 설정상 지속성이 꺼져 있다**(`--appendonly no --save ""`) — 순수 메모리 쓰기 수치이므로 durable 비교에서는 제외하고 봐야 한다.

| 방식 | 처리량(msg/s) | 메모 |
|------|--------------:|------|
| Redis Stream (`XADD`, 파이프라인) | **~36,300** | RESP 파이프라인으로 왕복 압축. ⚠️ **지속성 off**(디스크 안 씀) |
| RabbitMQ (persist, **confirm 안 함**) | ~5,200 | pika BlockingConnection 단일스레드 한계 |
| RabbitMQ (persist, **동기 publisher confirm**) | **~324** | 메시지마다 브로커 ack 왕복 대기 |
| Kafka (`acks=1`, 배치/linger) | **~28,600** | 배치로 묶어 append |

> **핵심은 RabbitMQ의 두 줄.** 같은 코드에서 `confirm_delivery()` 하나 켰을 뿐인데 **5,200 → 324 (약 16배)** 로 추락했다.
> 이건 "RabbitMQ가 느리다"가 아니라 **"동기 publisher confirm은 메시지마다 RTT를 무는 latency-bound 작업"**이라는 뜻이다.
> 실무 교훈: 안전(confirm)과 처리량을 동시에 원하면 **비동기 confirm 또는 배치 confirm**으로 파이프라이닝해야 한다.
> Kafka가 빠른 것도 브로커가 마법이어서가 아니라 **클라이언트가 배치로 묶어 보내기** 때문 — `acks=all`로 바꾸면 떨어진다.
>
> ⚠️ 절대수치는 Docker Desktop(VM 네트워크) + 파이썬 클라이언트 + 11vCPU 공유 환경이라 **노이즈가 크다**(Redis는
> 다른 실행에서 11만 msg/s도 나왔다). 브로커 자체 한계가 아니라 **클라이언트·환경 바운드**임을 전제로 읽을 것.

### PoC ②: 종단 지연 — 단건 왕복 (200회, ms)

발행 → 소비 한 건의 왕복 시간. 처리량과 **반대 그림**이 나온다.

| 브로커 | p50 | p99 | min |
|--------|----:|----:|----:|
| Redis Pub/Sub | **0.074** | 0.386 | 0.057 |
| RabbitMQ | 0.342 | 1.402 | 0.285 |
| Kafka | 1.629 | 9.167 | 1.018 |

```
지연(낮을수록 좋음):  Redis ▏0.07   RabbitMQ ▍0.34   Kafka █████ 1.63 (p50, ms)
```

> PoC ①에서 **지속성을 켠 브로커 중 처리량 1등**이던 Kafka가 **단건 지연에선 꼴찌**다.
> (표 숫자상 최고는 Redis Stream이지만 그건 지속성 off 상태의 메모리 쓰기 — durable 처리량 비교에선 Kafka가 1등이다.)
> Kafka는 로그 append + fetch 폴링 구조라 단건 왕복에 불리하다.
> 아티클의 *"Kafka는 throughput-optimized이지 latency-optimized가 아니다"* 가 그대로 재현됐다.
> **요청-응답/태스크 디스패치처럼 건당 지연이 중요한 패턴엔 RabbitMQ(또는 Redis)** 가 맞고,
> **대량 이벤트를 흘려보내는 파이프라인엔 Kafka**가 맞다. "빠르다"를 처리량/지연 중 무엇으로 정의하느냐의 문제다.

### PoC ③: 소비자 부재 시 보존/재생 — **결정론적 핵심 실험**

소비자를 **하나도 띄우지 않은 채** 5건을 발행한 뒤, 나중에 붙어서 몇 건을 받는지 봤다. (환경 노이즈와 무관하게 항상 같은 결과)

| 브로커 | 동작 | 결과 |
|--------|------|:----:|
| **Redis Pub/Sub** | 발행 후 구독 → 수신 | **0 / 5** ❌ 영구 소실 |
| **Redis Stream** | 소비자 없이 적재 → `XREAD 0` | 5 / 5 ✅ 보존 |
| **RabbitMQ** (durable queue) | 소비자 없이 적재 → 큐 깊이 | 5 / 5 ✅ 보존 |
| **Kafka** | 첫 소비 → **offset 0부터 재소비** | 5 / 5 → **재생 5 / 5** ✅ 보존+재생 |

```
발행 시점에 소비자가 없었다면?
 Redis Pub/Sub : m0 m1 m2 m3 m4  →  (구독)  →  ∅        "그 순간 안 들었으면 끝"
 RabbitMQ      : m0 m1 m2 m3 m4  →  큐에 적재 →  5건 소비   "소비되기 전까진 보관"
 Kafka         : m0 m1 m2 m3 m4  →  로그 보존 →  5건 소비
                                     └ 소비 후에도 offset 0으로 seek → 또 5건  "지워지지 않음"
```

> 이 한 실험이 세 브로커의 정체성을 가른다. **Redis Pub/Sub의 0/5는 버그가 아니라 설계다** — fire-and-forget.
> "Redis로 알림 보냈는데 가끔 안 와요"의 정체가 바로 이것(발행 순간 구독자가 없었음).
> 유실이 곤란하면 같은 Redis라도 **Streams**를 쓰거나(5/5), RabbitMQ/Kafka로 가야 한다.
> 그리고 **재소비 후 또 읽히는 건 Kafka뿐** — 감사 로그·이벤트 소싱·재처리(reprocessing)가 필요하면 Kafka여야 하는 이유.

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **"메시지 브로커"라는 한 단어가 셋을 같은 선반에 올려놔서 비교가 어긋난다.**
   - 진짜 비교축은 속도가 아니라 **저장 모델**이다: 무저장 브로드캐스트(Redis P/S) / 소비되면 삭제(RabbitMQ 큐) / 안 지워지는 로그(Kafka).
   - 저장 모델이 정해지면 전달 보장·순서·재생·확장 모델이 **거의 자동으로 따라온다.** 그래서 "어느 게 좋냐"가 아니라 "**내 메시지는 유실되면 안 되나? 재생이 필요한가?**"를 먼저 답해야 한다.

2. **push vs pull은 곧 "백프레셔를 누가 떠안느냐"다.**
   - push(RabbitMQ)는 느린 소비자가 브로커 큐를 부풀린다 → `prefetch`로 막아야 한다.
   - pull(Kafka)은 느린 소비자가 자기 lag만 키운다 → 브로커는 평온. 소비자 추가가 브로커 부하로 직결되지 않는 게 Kafka 확장성의 본질.

### 실무 트레이드오프 관점

3. **"안전 옵션"은 공짜가 아니다 — PoC ①에서 confirm 하나로 16배가 날아갔다.**
   - RabbitMQ 동기 confirm, Kafka `acks=all`, Redis `appendfsync always`는 전부 **내구성↔처리량**을 맞바꾸는 손잡이다.
   - 처리량이 필요한데 안전도 포기 못 하면 답은 **파이프라이닝**(비동기/배치 confirm). "느리다"의 원인이 브로커가 아니라 **동기 클라이언트 패턴**인 경우가 많다.

4. **"빠르다"를 처리량으로 말하는지 지연으로 말하는지부터 합의하라.**
   - durable 처리량 1등(PoC ①의 Kafka)과 지연 1등(PoC ②의 Redis)이 **정반대**였다. 벤치마크를 인용할 땐 항상 어느 축인지, 그리고 **지속성 조건이 같은지** 확인.
   - 요청-응답·작업 큐 = 지연 민감 → RabbitMQ/Redis / 로그 적재·스트리밍 = 처리량 민감 → Kafka.

5. **선택 가이드(실무 디폴트).**
   - **RabbitMQ**: 복잡한 라우팅, 작업 분배, per-message ack, 워크플로 오케스트레이션. "이 작업을 누군가 정확히 한 번 처리".
   - **Kafka**: 이벤트 로그, 여러 컨슈머가 같은 스트림을 독립 소비, 재처리/감사, 초당 수십만+ 이벤트.
   - **Redis**: 캐시 무효화, 실시간 대시보드, presence/알림 등 **유실 허용·초저지연** 용도. 유실이 곤란하면 Pub/Sub 말고 **Streams**.

6. **운영 비용/복잡도도 선택의 일부다.**
   - Redis는 대개 이미 캐시로 떠 있어 **추가 인프라 0**에 가깝다(그래서 "일단 Redis Pub/Sub" 유혹이 크고, 그게 유실 사고로 이어진다).
   - Kafka는 가장 강력하지만 파티션·offset·consumer group·보존정책 등 **운영 표면적이 가장 넓다.** 단순 작업 큐에 Kafka를 쓰는 건 과설계인 경우가 많다.

---

> **재현 메모**: `docker compose up -d` 후 `python poc.py`(처리량/지연/보존 통합 스크립트)로 위 표가 그대로 재생된다.
> PoC ③(보존/재생)은 환경과 무관하게 항상 동일하고, PoC ①②의 절대수치는 ±수십% 흔들리니 **순위와 형태**로 읽을 것.
