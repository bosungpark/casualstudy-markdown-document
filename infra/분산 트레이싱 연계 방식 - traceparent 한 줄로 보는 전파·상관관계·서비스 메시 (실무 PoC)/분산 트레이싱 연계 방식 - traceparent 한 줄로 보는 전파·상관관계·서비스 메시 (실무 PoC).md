# 분산 트레이싱 연계 방식 - traceparent 한 줄로 보는 전파·상관관계·서비스 메시

## 출처
- **아티클/논문**: Context Propagation (OpenTelemetry Concepts)
- **저자/출처**: OpenTelemetry 공식 문서. 보조 근거로 Istio *Distributed Tracing FAQ*("사이드카는 인바운드와 아웃바운드를 연결할 방법이 없다")와 W3C *Trace Context* 스펙의 헤더 포맷을 참조.
- **링크**: https://opentelemetry.io/docs/concepts/context-propagation/

> 이 아티클의 한 문장은 **"Propagation is the mechanism that moves context between services and processes"** 이다.
> 즉 분산 트레이싱의 본체는 백엔드도 SDK도 아니고 **서비스 경계를 넘어 다니는 컨텍스트**라는 것.
> 본 문서는 이 주장을 **3-hop 마이크로서비스 체인을 실제로 띄워놓고 6개의 실험으로 검증한 PoC**로 정리했다.
>
> **환경**: macOS 14 + Docker Desktop(11 vCPU / 8GB) · Jaeger **v2.20.0**(OTel Collector 기반 단일 바이너리, 메모리 스토리지) ·
> Envoy 1.31 · Python 3.14 + OpenTelemetry Python SDK 1.44 / instrumentation 0.65b0.
> 앱 3개는 호스트에서, Jaeger·Envoy는 Docker에서 실행.
> **지연 절대수치는 Flask 개발 서버 + Docker Desktop 환경이라 노이즈가 크다.** 반면 PoC ①②④⑤-B는 **환경과 무관하게 항상 같은 결과**가 나온다.

---

## AI 요약

### 0. 한 장 요약

| 질문 | 핵심 답 |
|------|---------|
| 분산 트레이싱에서 제일 중요한 부품은? | 백엔드도 SDK도 아니고 **`traceparent` 헤더 한 줄의 전파**다 |
| 전파가 끊기면 데이터가 사라지나? | **아니다.** 스팬 수는 그대로(PoC ①: 100개 → 100개). 사라지는 건 **간선(edge)**이고, 저장 비용은 그대로 낸다 |
| 표준이 왜 필요한가? | 보내는 쪽과 받는 쪽 포맷이 다르면 그냥 끊긴다(PoC ②: W3C→B3 = 2 trace) |
| 로그와 트레이스는 어떻게 잇나? | 로그 한 줄에 **`trace_id` 필드 하나**. PoC ③에서 검색 정밀도 0.3% → 100% |
| 서비스 메시 깔면 자동으로 되나? | **안 된다.** 메시는 span을 공짜로 주지만 trace는 안 준다(PoC ④: 10요청 → 30 trace) |
| 샘플링은 지연을 줄여주나? | **아니다.** 줄어드는 건 **저장/전송 비용**이지 앱 지연이 아니다(PoC ⑤-A) |
| 샘플링에서 제일 흔한 사고는? | 서비스마다 독립적으로 결정하는 것. PoC ⑤-B에서 **완전한 trace 비율 100% → 2%** |
| 실무 한 줄 | **"헤더를 안 끊기게 넘기는 것"이 90%, 백엔드 고르는 건 10%.** |

### 1. 분산 트레이싱은 4개의 부품으로 되어 있다

```
   [gateway]────HTTP───▶[orders]────HTTP───▶[payments]
      │  ① 계측: 스팬을 만든다 (SDK 또는 사이드카)
      │  ② 전파: traceparent 헤더를 인바운드→아웃바운드로 넘긴다  ← 여기가 끊긴다
      │  ③ 상관관계: 로그/메트릭에 trace_id를 심는다
      ▼                    ▼                    ▼
    span                 span                 span
      └──────── OTLP ──────┴────────────────────┘
                           ▼
                  ④ 백엔드 (Jaeger / Tempo / SigNoz …)
```

| 부품 | 누가 하나 | 실패하면 |
|------|-----------|----------|
| ① 계측(instrumentation) | OTel SDK 자동계측 / eBPF / 사이드카 | 스팬 자체가 없음 |
| ② **전파(propagation)** | **애플리케이션 코드만 할 수 있음** | 스팬은 다 있는데 **따로 논다** |
| ③ 상관관계(correlation) | 로거 설정(MDC / JSON 필드) | 트레이스는 있는데 **왜 실패했는지 모름** |
| ④ 백엔드 | Jaeger / Tempo / SigNoz / 상용 | 저장·검색 비용·보존기간 문제 |

> 실무에서 무너지는 지점은 거의 항상 **②**다. ①③④는 설정(config)이지만 ②만은 **코드**이기 때문이다.

### 2. 전파 프로토콜 — `traceparent` 해부

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ─┬ ────────────┬─────────────────── ───────┬──────── ─┬
              │             │                           │          │
          version      trace-id (16B)            parent-id(8B)  trace-flags
          (현재 00)    요청 전체에서 불변         = "호출한 쪽의   bit0=sampled
                       ← 이게 로그의 trace_id       span-id"       bit1=random
                                                   hop마다 바뀜    (Level 2)
```

- **trace-id는 요청 전체에서 절대 안 바뀐다.** 이게 로그·메트릭과 이어붙이는 **조인 키**다.
- **parent-id는 hop마다 바뀐다.** "직전 스팬이 누구냐"를 알려주는 값이라 부모-자식 트리가 만들어진다.
- `tracestate`는 벤더별 부가 정보(최대 32엔트리)를 실어 나르는 옵션 헤더.
- `baggage`는 별개 헤더로 **임의의 key-value**를 전파한다. 편하지만 **다운스트림·로그에 그대로 노출**되므로 PII·크리덴셜 금지.

| 포맷 | 헤더 | 쓰는 곳 |
|------|------|---------|
| **W3C Trace Context** | `traceparent`, `tracestate` | OTel 기본값, Envoy/Istio 기본값, 사실상 표준 |
| **B3 (multi)** | `x-b3-traceid`, `x-b3-spanid`, `x-b3-sampled` … | Zipkin 계열, 오래된 서비스 |
| **B3 (single)** | `b3: {traceid}-{spanid}-{sampled}` | Zipkin 계열 축약형 |
| Jaeger legacy | `uber-trace-id` | Jaeger v1 클라이언트 (현재 아카이브됨) |

### 3. 사이드카/서비스 메시가 해주는 것과 **못 하는 것**

Istio 공식 FAQ의 문장이 정확하다 — *"사이드카는 인바운드 요청과, 그 요청 때문에 발생한 아웃바운드 요청을 연결할 암묵적인 방법이 없다."*

```
     ┌──────────── Pod ────────────┐
     │  [사이드카]      [앱]        │
 ──▶ │  inbound  ──▶  handler      │   사이드카가 아는 것: "요청 A가 들어왔다"
     │                    │        │                       "요청 B가 나갔다"
     │  outbound ◀──── http call   │   모르는 것: "B가 A 때문인가?"  ← 앱만 안다
     └─────────────────────────────┘
```

| 항목 | 사이드카/메시가 함 | 앱이 해야 함 |
|------|:---:|:---:|
| 스팬 생성·전송 | ✅ | — |
| 요청 ID 발급(`x-request-id`) | ✅ | — |
| 백엔드 연동·샘플링 정책 | ✅ | — |
| **인바운드 헤더 → 아웃바운드 복사** | ❌ | ✅ |
| 비즈니스 단위 스팬(DB 쿼리, 캐시 등) | ❌ | ✅ |

### 4. 로그-트레이스 상관관계

방법은 하나뿐이다: **활성 스팬의 `trace_id`/`span_id`를 로그 레코드에 넣는다.**

```json
{"ts":..., "svc":"payments", "event":"payment_declined",
 "trace_id":"6d96f865763fe72599f895c5efefa3f9", "span_id":"da137e65829df699"}
```

| 언어 | 주입 방식 |
|------|-----------|
| Java | Logback/Log4j2 **MDC**에 자동 주입 (`%X{trace_id}`) |
| Python | `LoggingInstrumentor` 또는 로그 포맷에 직접 |
| Go / Node / .NET | 컨텍스트에서 SpanContext 꺼내 구조화 로그 필드로 |
| 사이드카만 있는 경우 | 앱이 span을 모르므로 **`x-request-id`로 대체** (정확도 낮음) |

> 전제 조건: **로그가 구조화(JSON)돼 있어야 한다.** 비정형 텍스트 로그면 백엔드에서 파싱·인덱싱이 안 된다.
> 메트릭 쪽 대응물은 **exemplar** — 히스토그램 버킷에 대표 trace_id를 붙여 "p99가 튀었다" → "그 요청"으로 점프시킨다.

### 5. 트레이싱 백엔드는 무엇으로 갈리나

| | **Jaeger v2** | **Grafana Tempo** | **SigNoz** |
|---|---|---|---|
| 구조 | OTel Collector 기반 단일 바이너리 | 인덱스 없음, **Parquet 블록 + 오브젝트 스토리지** | ClickHouse 기반 통합 플랫폼 |
| 스토리지 | 메모리/Badger/Cassandra/**ES·OpenSearch**<br>(ClickHouse는 실험적) | S3·GCS·Azure Blob | ClickHouse |
| 검색 | 서비스/오퍼레이션/태그 인덱스 | **TraceQL** (컬럼 스캔) | ClickHouse SQL |
| 강점 | 가볍고 빠른 도입, CNCF 표준 | **비용**(오브젝트 스토리지 + 인덱스 없음) | 트레이스·로그·메트릭 한 UI |
| 주의 | v1은 2025-12-31 EOL, v2로 이관 필요<br>대규모는 Cassandra보다 OpenSearch 권장 | 저지연 임의 검색은 인덱스형보다 불리 | ClickHouse 운영 부담 |

> 실무 선택 기준은 기능이 아니라 대개 **"하루 몇 GB를 며칠 보관할 것인가"** 다 (PoC ⑥ 참고).
> 그리고 어느 쪽을 골라도 **계측은 OTel로 하면 백엔드는 나중에 갈아끼울 수 있다** — 이게 OTel의 실질적 가치다.

---

## PoC: 실제로 띄워놓고 확인하기

> **저장소에서 바로 확인:** 같은 디렉터리의 [`README.md`](README.md)를 참고해 `./run.sh`를 실행하면
> PoC ①의 핵심 결과를 응답 JSON과 Jaeger 양쪽에서 자동 검증한다. 전파 ON/OFF 체인을 동시에 띄우므로 별도 설정 변경 없이 비교할 수 있다.

### 0. 환경 구성

**토폴로지**

```
[클라이언트] ─▶ gateway(8001) ─▶ orders(8002) ─▶ payments(8003)        ← PoC ①②③⑤⑥ (SDK 계측)
[클라이언트] ─▶ envoy(10001) ─▶ gateway ─▶ envoy(10002) ─▶ orders ─▶ …  ← PoC ④ (사이드카 계측)
                                       모두 ──OTLP──▶ Jaeger v2 (16686)
```

```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/jaeger:2.20.0     # v2 = OTel Collector 기반 단일 바이너리
    ports: ["16686:16686", "4317:4317", "4318:4318"]   # UI/Query, OTLP gRPC, OTLP HTTP

  envoy-orders:                            # 사이드카 3개 중 하나 (나머지도 동일 구조)
    image: envoyproxy/envoy:v1.31-latest
    volumes: [./envoy/orders.yaml:/etc/envoy/envoy.yaml:ro]
    command: ["-c","/etc/envoy/envoy.yaml","--service-cluster","envoy-orders"]
    ports: ["10002:10000"]
```

```python
# app.py — 서비스 하나를 환경변수로 조립한다
MODE = os.environ["MODE"]    # otel(=SDK 계측) | plain(=계측 전혀 없음)
PROP = os.environ["PROP"]    # w3c | b3 | composite | none
provider = TracerProvider(resource=Resource.create({"service.name": SVC}), sampler=sampler)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(...)))
set_global_textmap(propagators[PROP])     # ← 실험의 핵심 손잡이
FlaskInstrumentor().instrument_app(app);  RequestsInstrumentor().instrument()
```

```bash
docker compose up -d
python poc1_propagation.py   # … poc6_cost.py 까지
```

---

### PoC ①: 전파가 끊기면 무엇을 잃는가 — **결정론적 핵심 실험**

동일한 3-hop 체인에 요청 20건. 바꾼 건 **전파기(propagator)** 하나뿐이다.

| 설정 | 요청 수 | 생성된 trace 수 | **총 span 수** | 요청당 trace |
|------|--------:|----------------:|---------------:|-------------:|
| 전파 ON (W3C) | 20 | **20** | 100 | 1.0 |
| 전파 OFF | 20 | **60** | **100** | 3.0 |

전파 OFF일 때 trace의 모양:

| spans/trace | trace 안의 서비스 | 개수 |
|---|---|---|
| 2 | gateway | 20 |
| 2 | orders | 20 |
| 1 | payments | 20 |

```
전파 ON                              전파 OFF
trace 4bf92f…                        trace aaa…      trace bbb…      trace ccc…
├─ gateway  GET /work  13.8ms        └ gateway 3ms   └ orders 2ms    └ payments 0.2ms
│  └─ gateway GET      12.7ms
│     └─ orders GET /work  9.8ms      "gateway가 느린데 왜 느린지 모름"
│        └─ orders GET     4.6ms      "payments 에러가 어느 요청인지 모름"
│           └─ payments GET /work
```

> **핵심은 span 수가 100개로 똑같다는 것이다.** 전파가 끊겨도 데이터는 하나도 안 줄고, 스토리지 비용도 그대로 낸다.
> 잃은 것은 **간선(edge)** 뿐이다. 그리고 간선이 없으면 트레이싱의 존재 이유(어느 hop이 느린가/누가 에러를 냈나)가 통째로 사라진다.
> "트레이싱 붙였는데 별로 안 쓸모없더라"의 정체가 대개 이것 — **비용은 다 내고 가치만 못 받는 상태**다.

---

### PoC ②: 와이어에 실제로 뭐가 실리나 + 포맷 상호운용 매트릭스

**A. hop마다 실제로 도착한 헤더**

```
propagator = w3c
  gateway   <- {}                                              ← 최초 진입, 헤더 없음
  orders    <- traceparent: 00-b29328984d63343f512b5df1a7b9fb9a-11d7a938fe33f4ff-03
  payments  <- traceparent: 00-b29328984d63343f512b5df1a7b9fb9a-83294f82dda3941f-03
                               └── trace-id 동일 ──┘           └ parent-id는 바뀜 ┘

propagator = b3
  orders    <- x-b3-traceid: b4ed46dca109a737f19916f83a1d6fb9
               x-b3-spanid : 5425a43dfcdede8c
               x-b3-sampled: 1
```

> `-03`은 `sampled(0x01) | random-trace-id(0x02)`. 루트에서 만든 trace-id가 난수임을 표시하는 Trace Context Level 2 플래그다.

**B. 보내는 포맷 × 읽는 포맷 (gateway가 주입 → orders가 해석)**

| inject \ extract | w3c | b3 | composite(W3C+B3) |
|---|---|---|---|
| **w3c** | 1 trace ✅ | **2 trace ❌** | 1 trace ✅ |
| **b3** | **2 trace ❌** | 1 trace ✅ | 1 trace ✅ |
| **composite** | 1 trace ✅ | 1 trace ✅ | 1 trace ✅ |

> 여기서 **composite 열**과 **composite 행**은 서로 다른 전략이다.
> composite extract(열)는 수신자가 W3C와 B3를 모두 읽기 때문에 어느 단일 포맷 발신자와도 연결된다.
> composite inject(행)는 발신자가 W3C와 B3 헤더를 모두 쓰기 때문에 어느 단일 포맷 수신자와도 연결된다.
>
> 따라서 **"여러 포맷으로 읽고 W3C로만 쓴다"**는 표 전체의 결론이 아니라
> `w3c inject → composite extract` 한 조합이자 마이그레이션의 최종 목표다.
> B3만 읽는 레거시 다운스트림이 남아 있는 전환기에 W3C만 쓰면 `w3c → b3` 조합처럼 trace가 끊긴다.
> 이 기간에는 수신 시 두 포맷을 모두 읽고, 송신 시 상대에 맞는 포맷을 쓰거나 두 헤더를 함께 보내야 한다.
> 모든 다운스트림이 W3C를 읽을 수 있게 된 뒤에야 송신 포맷을 W3C 하나로 통일할 수 있다.

**주의 — composite의 순서가 결과를 바꾼다.** 두 헤더가 **동시에** 왔을 때 어느 쪽이 이기는지 직접 확인해봤다:

```
carrier = { traceparent: 00-aaaa…-1111…-03,  x-b3-traceid: bbbb…, x-b3-spanid: 2222… }

composite([W3C, B3])  ->  trace_id = bbbb…   ← 뒤에 온 B3가 이김
composite([B3, W3C])  ->  trace_id = aaaa…   ← 뒤에 온 W3C가 이김
```

> **나중에 오는 propagator가 덮어쓴다(last-wins).** W3C를 우선하고 싶으면 리스트의 **마지막**에 둬야 한다.
> (OTel Python 1.44 `CompositePropagator` 기준. 위 A의 composite 케이스에서 flags가 `03 → 01`로 바뀐 것도 같은 이유 —
> B3가 이겨서 random 비트가 유실됐다.)

---

### PoC ③: 로그-트레이스 상관관계 — 1,806줄에서 6줄 찾기

동시성 12로 요청 301건(그중 1건만 결제 실패)을 흘리고, **"payments에서 에러 로그 1줄을 발견했다"**에서 수사를 시작한다.

```json
{"ts":1785918778.6583,"svc":"payments","event":"payment_declined","order_id":"ORD-BAD",
 "error":"card_network_timeout","trace_id":"6d96f865763fe72599f895c5efefa3f9","span_id":"da137e65829df699"}
```

| 로그를 좁히는 방법 | 걸린 라인 수 | 무관한 라인 | **정밀도** |
|---|---:|---:|---:|
| 시간 윈도우 ±1000ms | 1,806 | 1,800 | **0.3%** |
| 시간 윈도우 ±100ms | 837 | 831 | **0.7%** |
| **`trace_id`로 필터** | **6** | **0** | **100%** |

`trace_id`로 뽑으면 서비스 3개의 로그가 **인과 순서대로 한 줄로 정렬된다**:

```
gateway   handle            order_id=ORD-BAD
 orders   handle            order_id=ORD-BAD
  payments handle           order_id=ORD-BAD
  payments payment_declined error=card_network_timeout   ← 근본 원인
 orders   downstream_error  status=500
gateway   downstream_error  status=500
```

같은 `trace_id`를 그대로 Jaeger에 던지면 **시간 축**이 붙는다(로그 → 트레이스 점프):

```
+ 0.00ms  gateway   GET /work   dur=13.77ms  <== error
+ 0.92ms  gateway   GET         dur=12.74ms  <== error
+ 3.65ms  orders    GET /work   dur= 9.78ms  <== error
+ 6.75ms  orders    GET         dur= 4.63ms  <== error
+ 9.84ms  payments  GET /work   dur= 0.23ms  <== error   ← 실패는 빨랐다(타임아웃 아님)
```

> 로그는 **"무슨 일이 있었나"**, 트레이스는 **"어디서 얼마나 걸렸나"**. 둘을 잇는 접착제가 `trace_id` **필드 하나**다.
> 비용은 로그 한 줄당 `"trace_id":"<32 hex>"` 약 45바이트, 얻는 건 **검색 정밀도 0.3% → 100%.** 옵저버빌리티 작업 중 ROI가 가장 높은 항목이다.
> 반대 방향(트레이스 → 로그)도 같은 키로 열린다. Grafana의 "trace to logs", Jaeger의 로그 링크가 전부 이걸 쓴다.

---

### PoC ④: 서비스 메시는 트레이싱을 공짜로 주는가 — **가장 흔한 오해**

앱에서 **OTel SDK를 완전히 제거**하고, 각 서비스 앞에 Envoy 사이드카를 세웠다. 스팬은 Envoy만 만든다.

```yaml
# envoy/orders.yaml — 사이드카가 "공짜로" 해주는 부분
tracing:
  random_sampling: { value: 100 }
  provider:
    name: envoy.tracers.opentelemetry
    typed_config:
      "@type": type.googleapis.com/envoy.config.trace.v3.OpenTelemetryConfig
      service_name: orders-sidecar
      grpc_service: { envoy_grpc: { cluster_name: otel_collector } }
```

바꾼 변수는 단 하나 — **앱이 인바운드 헤더를 아웃바운드 호출에 복사하는가**:

```python
# 서비스 메시가 대신 해줄 수 없는 3줄
headers = {h: request.headers[h] for h in
           ("traceparent", "tracestate", "b3", "x-b3-traceid", "x-request-id")
           if h in request.headers}
requests.get(NEXT, headers=headers)
```

| 앱 동작 | 요청 | trace 수 | **span 수** | 요청당 trace |
|---|---:|---:|---:|---:|
| 헤더 전파 안 함 (**메시만 설치**) | 10 | **30** | 30 | 3.0 |
| 헤더 pass-through 3줄 추가 | 10 | **10** | 30 | 1.0 |

앱이 각 hop에서 실제로 받은 헤더:

```
FORWARD=off   ← 사이드카가 매 hop마다 새 trace를 만들어버린다
  gateway  traceparent: 00-4bcad11f8a14f4b489671a7df51062e4-… x-request-id: 4eaf5b60-…
  orders   traceparent: 00-03b8a5784647e5e31abc79386733b66d-… x-request-id: 4e6a35c6-…   ← 다른 trace-id!
  payments traceparent: 00-9be29424886ccb68cd7b13b57e3bbff4-… x-request-id: ea2bde1d-…   ← 또 다름!

FORWARD=on
  gateway  traceparent: 00-4e05233b88192e2b6a3b32694aa0d7b7-c2a827d034709c29-01  x-request-id: 2dcb3a5f-…
  orders   traceparent: 00-4e05233b88192e2b6a3b32694aa0d7b7-ab025cc229b9281c-01  x-request-id: 2dcb3a5f-…
  payments traceparent: 00-4e05233b88192e2b6a3b32694aa0d7b7-f071db59ecdbe37c-01  x-request-id: 2dcb3a5f-…
                           └──────── trace-id 동일 ────────┘ └ parent-id만 갱신 ┘  └ 요청 ID도 동일 ┘
```

> **메시는 span을 공짜로 준다. 하지만 trace는 안 준다.**
> Envoy는 인바운드 요청이 있으면 스팬을 만들 수 있지만, **"이 아웃바운드 호출이 저 인바운드 요청 때문"**이라는 사실은
> 프로세스 안에서만 알 수 있는 정보다. 그건 앱만 안다.
> 그래서 Istio 문서가 명시적으로 요구하는 것도 딱 이것 — `traceparent`/`tracestate`/`x-request-id`(+Zipkin이면 B3)를 **앱이 넘겨라.**
>
> 실무적 의미: **"메시 깔았으니 트레이싱 됩니다"는 검증 없이 믿으면 안 된다.**
> 검증 방법도 간단하다 — 요청 N건을 넣고 **trace 수가 N인지 3N인지** 보면 끝난다.
> (덤: `x-request-id`도 같이 넘기면 SDK 없이도 로그를 요청 단위로 묶을 수 있다 — 사이드카 온리 환경의 차선책.)

---

### PoC ⑤: 계측 오버헤드와 "샘플링은 누가 결정하는가"

**A. 계측 오버헤드** (3-hop 종단 지연, 요청 300건, 워밍업 40건)

| 설정 | p50 | p95 | p99 | min | p50 증가분 |
|---|---:|---:|---:|---:|---:|
| 계측 없음 (plain Flask) | 4.05 | 5.28 | 7.69 | 2.96 | – |
| OTel SDK, 100% 샘플링 | 4.61 | 6.77 | 10.62 | 3.42 | **+0.56ms** |
| OTel SDK, 10% 샘플링 | 4.31 | 5.15 | 6.54 | 3.33 | **+0.26ms** |

> 3 hop 전체에 **+0.3~0.9ms**(hop당 약 0.1~0.3ms). Python은 SDK 오버헤드가 큰 축이고 Go/Java는 더 작다.
> **주목할 점은 "10% 샘플링이 지연을 유의미하게 줄이지 못했다"는 것.** 다른 실행에서는 100%(+0.86ms)보다
> 10%(+0.92ms)가 오히려 느리게 나오기도 했다 — 즉 **차이가 노이즈 범위 안**이다.
> 이유는 구조적이다: 샘플링이 꺼도 **컨텍스트 추출·스팬 컨텍스트 생성·헤더 주입은 그대로 일어나고**,
> 실제로 생략되는 export는 애초에 `BatchSpanProcessor`가 **백그라운드 스레드에서 비동기로** 하던 일이다.
> ⇒ **샘플링은 지연 최적화가 아니라 저장/전송 비용 최적화다.** 이걸 혼동하면 엉뚱한 곳을 튜닝하게 된다.

**B. 샘플링 결정 주체** (요청 200건)

| 샘플러 | trace 수 | **완전한 trace** | 깨진 trace | 완전 비율 | 총 span |
|---|---:|---:|---:|---:|---:|
| `ParentBased(10%)` — 루트만 결정, 자식은 따름 | 18 | **18** | 0 | **100%** | 90 |
| 독립 50% 코인 — 서비스마다 제멋대로 결정 | 193 | **3** | 190 | **2%** | 489 |

독립 결정일 때 나온 trace 모양(일부):

| spans | trace 안의 서비스 | 개수 |
|---|---|---|
| 3 | gateway,orders | 29 |
| 3 | gateway,payments | 4 |
| 2 | orders,payments | 8 |
| 2 | orders | 3 |

> `ParentBased`는 **루트에서 한 번 결정한 `sampled` 비트를 traceparent에 실어 보내고, 하위 서비스는 그대로 따른다.**
> 결과는 **전부 아니면 전무(all-or-nothing)** — 200건 중 18건이 살아남았고 **18건 모두 5스팬 완전체**다.
> 반면 서비스마다 독립적으로 던지면 `gateway,payments`처럼 **중간이 빠진 유령 trace**가 생긴다.
> 최악인 건 비용까지 나쁘다는 것 — 저장한 스팬은 **5.4배(90 → 489)** 인데 쓸 수 있는 trace는 **6분의 1(18 → 3)** 이다.
> **"돈은 더 내고 결과물은 쓰레기"** 가 되는 전형적인 안티패턴.
>
> 참고: 정말 "에러/느린 요청만 저장"하고 싶다면 head 샘플링으로는 불가능하다(요청 시작 시점엔 결과를 모른다).
> 그건 **tail 샘플링**(Collector가 trace 전체를 잠시 버퍼링 후 결정)의 영역이고, 대신 Collector가 상태를 갖게 된다.

---

### PoC ⑥: span 1개의 실제 비용 — 백엔드 선택은 결국 용량 문제

SDK와 Jaeger 사이에 **탭(tap)** 을 끼워 OTLP 페이로드를 그대로 계량했다.

```python
@tap.route("/v1/traces", methods=["POST"])       # 4319에서 받아 4318로 그대로 포워딩
def traces_in():
    raw = request.get_data()
    req = ExportTraceServiceRequest(); req.ParseFromString(raw)
    n = sum(len(ss.spans) for rs in req.resource_spans for ss in rs.scope_spans)
    stats["bytes"] += len(raw); stats["spans"] += n
    stats["gzip_bytes"] += len(gzip.compress(raw))
```

요청 200건 → OTLP 배치 18개 / span 1,000개 / 364,146 bytes (gzip 52,630)

| 항목 | 값 |
|---|---|
| 요청 1건당 span | 5.0 |
| span 1개당 protobuf | **364 B** |
| span 1개당 gzip | **53 B** (약 7배 압축 — 배치 안에서 필드가 반복되므로) |
| OTLP 배치 1개당 span | 55.6 |

이 수치로 환산한 하루 전송량(요청당 span 5개, gzip 기준):

| 트래픽 | 샘플링 | 초당 span | 하루 전송량 |
|---|---|---:|---:|
| 100 rps | 100% | 500 | 2.3 GB/day |
| 1,000 rps | 100% | 5,000 | **22.7 GB/day** |
| 1,000 rps | 10% | 500 | 2.3 GB/day |
| 5,000 rps | 100% | 25,000 | **113.7 GB/day** |
| 5,000 rps | 1% | 250 | 1.1 GB/day |

> ⚠️ 이건 **속성이 거의 없는 최소 스팬** 기준이다. 실제 프로덕션 스팬은 리소스 속성·HTTP 속성·예외 스택트레이스가 붙어
> **2~5배 커진다.** 즉 위 표는 **하한선**으로 읽어야 한다.
>
> 이 표가 백엔드 선택 논의를 현실로 끌어내린다. 1,000 rps 서비스가 100% 샘플링에 30일 보존이면 **원본만 700GB급**이다.
> 그래서 Tempo가 **인덱스를 버리고 오브젝트 스토리지에 Parquet으로 쌓는** 설계를 택한 것이고,
> 그래서 어떤 백엔드를 쓰든 결국 **샘플링 정책이 첫 번째 설계 결정**이 된다.

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **분산 트레이싱의 본체는 백엔드가 아니라 "경계를 넘는 컨텍스트"다.**
   - PoC ①에서 전파 하나를 끄자 span 100개는 그대로인데 trace가 20개 → 60개가 됐다. **데이터는 다 있는데 쓸모가 없어진다.**
   - 아티클의 *"Propagation is the mechanism that moves context between services"* 가 문자 그대로 검증됐다. 백엔드·SDK·UI는 이 메커니즘의 **부속품**이다.
   - 그래서 트레이싱 도입 리뷰에서 첫 질문은 "Jaeger냐 Tempo냐"가 아니라 **"우리 시스템에서 헤더가 끊기는 지점이 어디인가"** 여야 한다.

2. **② 전파만이 "코드"이고, 나머지는 전부 "설정"이다 — 그래서 여기만 무너진다.**
   - 계측·백엔드·샘플링·로그 포맷은 config나 라이브러리로 해결된다. 하지만 **"이 아웃바운드가 저 인바운드 때문"** 이라는 인과 정보는 프로세스 내부에만 존재한다.
   - 이게 **사이드카가 원리적으로 대신해줄 수 없는 이유**다(PoC ④). 메시가 "자동 트레이싱"이라고 광고할 때 실제로는 "자동 **스팬 생성**"인 경우가 대부분이다.
   - 끊기기 쉬운 실제 지점: 스레드풀/`asyncio` 태스크 경계, 메시지 큐(Kafka/RabbitMQ) hop, 배치 잡, 직접 만든 HTTP 클라이언트, 서드파티 SDK.

3. **끊김은 조용히 일어나고, 비용은 계속 나간다.**
   - 전파가 끊겨도 **에러는 하나도 안 난다.** 대시보드에는 span이 잘 들어오고, 스토리지 청구서도 그대로다.
   - 검출 방법은 의외로 단순하다: **요청 N건 → trace 수가 N인가?** PoC ①④에서 쓴 이 한 줄짜리 지표를 CI 스모크 테스트에 넣으면 회귀를 잡을 수 있다.

### 실무 트레이드오프 관점

4. **"읽을 땐 관대하게, 쓸 땐 표준으로"가 전환기의 정답이다.**
   - PoC ② 매트릭스에서 composite 행/열만 전부 초록이었다. 레거시 Zipkin ↔ 신규 OTel이 섞인 조직은 이 설정 하나로 끊김이 사라진다.
   - 단, **composite는 순서가 결과를 바꾼다(last-wins).** 두 헤더가 동시에 오는 프록시 뒤에서는 의도한 포맷을 **리스트 마지막**에 둬야 한다. 이건 문서만 봐서는 절대 안 보이고 직접 헤더를 충돌시켜봐야 나온다.

5. **샘플링은 지연이 아니라 비용을 줄인다 — 그리고 결정 주체가 전부다.**
   - PoC ⑤-A: 100% → 10%로 낮춰도 p50 차이가 노이즈 범위였다. export는 이미 비동기 배치이기 때문. **"느려서 샘플링 낮춘다"는 대개 오진.**
   - PoC ⑤-B: 서비스마다 독립 결정하면 완전한 trace 비율이 **100% → 2%**, 저장량은 **5.4배**. 샘플링 설정은 **비율보다 `ParentBased`인지가 먼저**다.
   - 에러/느린 요청만 남기고 싶다면 head 샘플링으로는 구조적으로 불가능하고 **tail 샘플링(Collector)** 이 필요하다 — 대신 Collector가 상태를 갖는 부담이 생긴다.

6. **로그-트레이스 상관관계는 옵저버빌리티에서 ROI가 가장 높은 한 줄이다.**
   - 로그 라인당 40여 바이트를 더 쓰고 검색 정밀도가 **0.3% → 100%** 가 됐다(PoC ③). 트레이싱 백엔드를 고르기 전에 이것부터 해야 한다.
   - 전제는 **구조화 로그(JSON)** 다. 텍스트 로그에 trace_id를 문자열로 박아두면 사람은 grep할 수 있지만 백엔드는 조인하지 못한다.
   - SDK를 못 넣는 레거시라면 최소한 **`x-request-id`만이라도 전 구간 전파**시키자. 정확도는 떨어져도 "요청 단위로 로그를 모은다"는 목적의 80%는 달성된다.

### 도입/운영 관점

7. **도입 순서는 ③ → ② → ① → ④ 다.**
   - ③ 구조화 로그 + trace_id 주입(가장 싸고 즉시 효과) → ② 전파 검증(N요청 = N trace) → ① 계측 확대 → ④ 백엔드/보존 정책 결정.
   - 흔한 실패 순서는 정반대다. **백엔드부터 고르고 대시보드를 띄운 뒤, 전파가 끊겨 있다는 걸 몇 달 뒤에 발견한다.**

8. **백엔드 선택은 기능 비교표가 아니라 GB/day 계산에서 시작한다.**
   - PoC ⑥ 기준 1,000 rps · 100% 샘플링이면 **하루 22.7GB(최소치)**. 실제 스팬 크기를 감안하면 50~100GB, 30일 보존이면 테라급이다.
   - 이 숫자가 나오면 선택이 자동으로 좁혀진다 — 저비용 장기보존이면 **Tempo(오브젝트 스토리지)**, 빠른 도입·표준이면 **Jaeger v2**, 로그·메트릭 통합 UI가 필요하면 **SigNoz/ClickHouse**.
   - **Jaeger v1은 2025-12-31 EOL**이므로 신규 구축은 v2(OTel Collector 기반)로 가야 한다. 이 PoC도 v2로 검증했다.

9. **계측은 OTel로 고정하고 백엔드는 교체 가능하게 두는 것이 실질적인 헤지다.**
   - 앱 코드는 OTLP만 알고, 백엔드 전환은 Collector exporter 설정 변경으로 끝난다. PoC 내내 Jaeger v1 → v2로 갈아끼웠지만 **앱 코드는 한 줄도 안 바꿨다.**
   - 반대로 **전파 포맷과 `trace_id` 로그 필드명은 조직 전체가 합의해야 하는 계약**이다. 여긴 유연성보다 일관성이 중요하다.

---

> **재현 메모**: 이 문서와 같은 디렉터리에 포함된 최소 실행판은 [`README.md`](README.md)에 안내되어 있으며,
> PoC ①의 핵심인 `N 요청 = N trace(전파 ON)` / `N 요청 = 3N trace(전파 OFF)`, 양쪽의 동일한 span 수를 검증한다.
> 위 PoC ②~⑥의 전체 측정 스크립트는 현재 저장소에 포함되어 있지 않다.
> **PoC ①②④⑤-B는 환경과 무관하게 같은 형태**가 나오고(전파·포맷·샘플러는 결정론적),
> **PoC ③⑤-A⑥의 절대수치**(지연 ms, 로그 라인 수, 바이트)는 머신·클라이언트 환경에 따라 흔들리니 **비율과 형태**로 읽을 것.
