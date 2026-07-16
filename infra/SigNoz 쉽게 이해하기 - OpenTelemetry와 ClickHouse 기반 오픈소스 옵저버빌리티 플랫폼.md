# SigNoz 쉽게 이해하기 - OpenTelemetry와 ClickHouse 기반 오픈소스 옵저버빌리티 플랫폼

## 출처
- **아티클/문서**: Technical Architecture (SigNoz 공식 문서)
- **저자/출처**: SigNoz
- **링크**: https://signoz.io/docs/architecture/

> 보조 참고: [ClickHouse 블로그 - SigNoz: Open Source Metrics, Traces and Logs in a single pane](https://clickhouse.com/blog/signoz-observability-solution-with-clickhouse-and-open-telemetry)

---

## AI 요약

### 1. SigNoz란?

SigNoz는 **메트릭(Metrics) · 트레이스(Traces) · 로그(Logs)** 세 가지를 한 화면에서 보여주는 **오픈소스 옵저버빌리티(Observability) 플랫폼**이다. Datadog, New Relic 같은 상용 SaaS의 오픈소스 대안으로 자주 언급된다.

가장 큰 특징은 두 가지다.
1. **OpenTelemetry를 처음부터(natively) 기반으로** 만들어졌다 → 특정 벤더에 종속되지 않는 표준 계측.
2. **ClickHouse**라는 컬럼형 분석 DB를 단일 저장소로 사용한다 → 고카디널리티 데이터도 빠르게 조회.

| 항목 | 내용 |
|------|------|
| 분류 | 오픈소스 APM / 옵저버빌리티 플랫폼 |
| 다루는 신호 | Metrics, Traces, Logs (3대 신호 통합) |
| 계측 표준 | OpenTelemetry (OTLP) |
| 저장소 | ClickHouse (컬럼형 OLAP DB) |
| 포지셔닝 | "오픈소스 Datadog 대안" |
| 배포 | 단일 노드 ~ Kubernetes 클러스터 |

#### 옵저버빌리티의 "3대 신호"란?

```
┌───────────┬──────────────────────────────┬─────────────────────────┐
│  신호      │ 답하는 질문                    │ 예시                     │
├───────────┼──────────────────────────────┼─────────────────────────┤
│ Metrics   │ "얼마나? 몇 개? 평균은?"        │ CPU 70%, RPS 1200, p99   │
│ Traces    │ "이 요청이 어디서 느려졌나?"     │ 주문 API → DB 320ms 소요  │
│ Logs      │ "그때 정확히 무슨 일이?"         │ ERROR: null pointer ...  │
└───────────┴──────────────────────────────┴─────────────────────────┘
```

기존에는 메트릭은 Prometheus, 트레이스는 Jaeger, 로그는 ELK처럼 **따로따로** 도구를 써야 했다. SigNoz는 이 셋을 **하나의 애플리케이션**으로 묶어 신호 간 상관관계(correlation) 분석과 운영 부담을 동시에 줄인다.

---

### 2. 왜 만들어졌나? — 흩어진 도구의 문제

```
[기존 방식: 신호마다 따로]
  앱 ──► Prometheus  (메트릭)   ─┐
  앱 ──► Jaeger      (트레이스)  ─┼─► 도구 3개를 따로 운영/연결해야 함
  앱 ──► ELK         (로그)     ─┘     "느린 요청"의 로그를 찾으려면
                                        창을 여러 개 오가며 수동 대조

[SigNoz 방식: 하나로]
  앱 ──(OpenTelemetry)──► SigNoz ──► 메트릭·트레이스·로그를 한 화면에서
                                       클릭 한 번으로 서로 연결
```

- **운영 단순화**: 세 시스템을 각각 설치/스케일링/업그레이드할 필요가 없다.
- **상관관계 분석**: "p99가 튄 시점"의 느린 트레이스 → 그 트레이스의 로그로 한 번에 이동.
- **벤더 종속 탈피**: OpenTelemetry 표준이므로 계측 코드를 바꾸지 않고도 백엔드를 교체할 수 있다.

---

### 3. 아키텍처 한눈에 보기

```
 ┌──────────────────────┐
 │  계측된 애플리케이션    │  OpenTelemetry SDK로 계측
 │ (Java, Go, Python...) │
 └──────────┬───────────┘
            │ OTLP (gRPC :4317 / HTTP :4318)
            ▼
 ┌──────────────────────────────────────────┐
 │   OpenTelemetry Collector (수집 계층)       │
 │  - Jaeger/Zipkin/Kafka/OTLP 등 다양한 소스   │
 │  - signozspanmetrics 프로세서:             │
 │      트레이스 span → RED 메트릭 생성         │
 └──────────────────┬─────────────────────────┘
                    │ write
                    ▼
 ┌──────────────────────────────────────────┐
 │        ClickHouse (저장 계층)               │
 │  컬럼형 OLAP DB · traces/logs/metrics 통합   │
 │  프로덕션에선 ZooKeeper로 클러스터 구성       │
 └──────────────────┬─────────────────────────┘
                    │ query
                    ▼
 ┌──────────────────────────────────────────┐
 │   SigNoz 바이너리 ("central nervous system")│
 │  - API 서버 (쿼리/메타데이터)               │
 │  - ReactJS 프론트엔드 (대시보드)             │
 │  - OpAMP 서버 (파이프라인 동적 설정)         │
 │  - Ruler + Alertmanager (알림 평가/발송)     │
 └──────────────────┬─────────────────────────┘
                    ▼
              사용자 (브라우저 UI)
```

#### 핵심 컴포넌트 정리

| 컴포넌트 | 역할 |
|----------|------|
| **OpenTelemetry Collector** | 다양한 소스로부터 텔레메트리 수신 → 가공 → ClickHouse에 기록. 프로토콜 변환(Jaeger/Zipkin/OTLP 등) 담당 |
| **ClickHouse** | 모든 신호를 저장하는 단일 컬럼형 DB. 페타바이트급 데이터를 밀리초 단위로 조회 |
| **SigNoz 바이너리** | API 서버 + 프론트엔드 + OpAMP + Ruler + Alertmanager를 하나로 묶은 "중추 신경계" |
| **signozspanmetrics** | 트레이스 span에서 RED 메트릭(Rate·Error·Duration)을 자동 생성하는 Collector 프로세서 |

> **RED 메트릭**: Rate(요청량) · Errors(에러율) · Duration(지연 시간). 서비스 헬스를 보는 3대 지표로, 트레이스가 들어오는 것만으로 별도 계측 없이 자동 산출된다.

---

### 4. 데이터는 어떻게 흐르나 (End-to-End)

```
1) 애플리케이션이 OpenTelemetry SDK로 span/metric/log 생성
        │
2) OTLP 프로토콜로 Collector에 전송 (gRPC 4317 / HTTP 4318)
        │
3) Collector가 처리:
     - signozspanmetrics가 span → RED 메트릭 변환
     - 배치/필터링/속성 가공
        │
4) ClickHouse에 신호별 테이블로 기록
     - traces : span 1건당 1행, 30+ 컬럼 (OTel Trace 시맨틱 컨벤션)
     - logs   : OTel Logs Data Model 기반 (timestamp/severity/body/attrs)
     - metrics: 측정값 테이블 1개 + 시계열 메타 테이블 여러 개
        │
5) SigNoz API가 ClickHouse에 쿼리 → 프론트엔드가 시각화
        │
6) Ruler가 알림 규칙 평가 → Alertmanager가 Slack/PagerDuty 등으로 발송
```

---

### 5. 왜 ClickHouse인가?

SigNoz는 처음엔 **Druid**를 썼지만 ClickHouse로 옮겼다. 이유는 "작게 시작하기 쉬우면서도 크게 확장할 때 잘 동작하는" 균형 때문이다.

| 이유 | 설명 |
|------|------|
| **단일 머신부터 시작 가능** | 자원 요구량이 낮아 노트북/단일 노드에서도 구동, 이후 클러스터로 확장 |
| **컬럼형 OLAP** | 옵저버빌리티는 "분석 쿼리의 연속" → 컬럼 저장이 집계/필터에 압도적으로 유리 |
| **고카디널리티 친화** | user_id, request_id처럼 값 종류가 폭발하는 태그도 제한 없이 저장·조회 (Prometheus의 카디널리티 한계 회피) |
| **단일 저장소 통합** | 메트릭·트레이스·로그를 "그냥 또 하나의 분석 use case"로 보고 한 DB에 통합 |

#### 경쟁 도구와의 비교

| 도구 | 다루는 신호 | 특징 |
|------|------------|------|
| **Prometheus** | 메트릭 중심 | 인프라 메트릭에 강하지만 고카디널리티에 약함 |
| **Jaeger** | 트레이스 전용 | 분산 추적만 |
| **Elastic/ELK** | 로그 중심 | 로깅 강점, 메트릭은 제한적 |
| **Grafana 스택** | 3종 통합(조합) | 여러 시스템을 엮어야 해 운영 복잡 |
| **SigNoz** | 3종 통합(단일 앱) | OTel 네이티브 + ClickHouse 단일 저장소로 상관분석·운영 단순화 |

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **"단일 저장소(single backend)"가 주는 진짜 가치는 상관관계다**
   - 메트릭/트레이스/로그를 각각 다른 DB에 넣으면, "p99 스파이크 → 원인 트레이스 → 그 순간의 로그"를 잇는 데 사람이 창을 오가며 시간을 대조해야 한다.
   - 같은 ClickHouse 안에 trace_id로 묶여 있으면 클릭 한 번으로 이동 가능. **데이터 통합은 UX가 아니라 디버깅 속도의 문제**다.

2. **저장 모델이 도구의 한계를 결정한다**
   - Prometheus가 고카디널리티에 약한 건 시계열 인덱스 구조 탓이다. SigNoz가 user_id 같은 태그를 자유롭게 쓰는 건 컬럼형 OLAP을 골랐기 때문.
   - "어떤 질문을 던질 수 있는가"는 결국 "어떤 저장 엔진을 깔았는가"에서 갈린다.

### 표준/생태계 관점

3. **OpenTelemetry 네이티브 = 잠금(lock-in) 회피의 핵심**
   - 계측을 벤더 SDK가 아닌 OTel 표준으로 하면, 백엔드를 SigNoz ↔ Datadog ↔ Grafana로 바꿔도 **앱 코드는 그대로**다.
   - 옵저버빌리티 도구를 고를 때 "OTel을 얼마나 일급으로 지원하는가"가 미래 전환 비용을 좌우한다.

### 운영/도입 관점

4. **"단일 노드부터 클러스터까지" 점진적 확장 설계가 채택률을 만든다**
   - Druid → ClickHouse 전환의 핵심 동기가 "노트북에서도 돌아가야 한다"였다는 점이 인상적이다.
   - 아무리 확장성이 좋아도 시작 장벽이 높으면 도입되지 않는다. **getting-started 경험과 scale-out 성능을 동시에 잡는 것**이 인프라 제품의 승부처.

5. **트레이스만 보내면 메트릭이 공짜로 나온다 (signozspanmetrics)**
   - RED 메트릭을 별도 계측 없이 span에서 파생시키는 설계는, 계측 비용을 낮추면서 서비스 헬스 대시보드를 자동으로 채워준다.
   - "데이터 한 번 수집 → 여러 관점으로 가공"하는 Collector 파이프라인 사고방식은 다른 데이터 시스템 설계에도 응용할 만하다.
