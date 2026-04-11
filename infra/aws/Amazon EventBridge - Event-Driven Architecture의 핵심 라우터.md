# Amazon EventBridge - Event-Driven Architecture의 핵심 라우터

## 출처
- **아티클**: Event bus concepts in Amazon EventBridge (AWS 공식 User Guide)
- **저자/출처**: Amazon Web Services
- **링크**: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is-how-it-works-concepts.html
- **보조 자료**: [Event Driven Architecture using Amazon EventBridge - AWS Cloud Operations Blog](https://aws.amazon.com/blogs/mt/event-driven-architecture-using-amazon-eventbridge/)

---

## AI 요약

### 1. Amazon EventBridge란?

**Amazon EventBridge**는 AWS가 제공하는 서버리스 이벤트 버스 서비스로, 이벤트 소스(AWS 서비스, SaaS 파트너, 커스텀 애플리케이션)에서 발생한 이벤트를 규칙(Rule)에 따라 다양한 타겟(Lambda, SQS, SNS, Step Functions 등)으로 라우팅한다. 내부적으로는 CloudWatch Events를 기반으로 발전한 서비스이며, 초당 수백만 건의 이벤트를 처리할 수 있도록 자동으로 스케일된다.

| 특성 | 설명 |
|------|------|
| **서비스 유형** | 서버리스 이벤트 라우터 (Managed) |
| **전달 보장** | At-least-once delivery |
| **확장성** | 자동 스케일 (초당 수백만 이벤트) |
| **결합도** | 완전한 Loose Coupling (Producer ↔ Consumer 직접 의존 없음) |
| **라우팅 기준** | JSON 기반 Event Pattern 매칭 |
| **기본 구조** | Source → Event Bus → Rule → Target(최대 5개) |

---

### 2. 전체 이벤트 흐름

EventBridge의 핵심은 "Producer는 이벤트를 던지고, Consumer는 규칙에 맞는 이벤트를 받는다"는 단방향 흐름이다. Producer는 누가 받는지 알 필요가 없다.

```
┌──────────────────────────────────────────────────────────────────────┐
│                       EVENT BRIDGE FLOW                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────┐                                                   │
│   │ AWS Services │──┐                                                │
│   └──────────────┘  │                                                │
│                     │       ┌─────────────┐                          │
│   ┌──────────────┐  │       │             │  ┌─ Rule A ──┐           │
│   │ Custom Apps  │──┼──────▶│  Event Bus  │──┼─ Rule B ──┤           │
│   └──────────────┘  │       │             │  └─ Rule C ──┘           │
│                     │       └─────────────┘         │                │
│   ┌──────────────┐  │                               │                │
│   │ SaaS Partner │──┘                               ▼                │
│   └──────────────┘                           ┌──────────────┐        │
│                                               │ Event Pattern│        │
│                                               │   Matching   │        │
│                                               └──────┬───────┘        │
│                                                      │                │
│                                                      ▼                │
│                                        ┌────┬────┬────┬────┬────┐    │
│                                        │ T1 │ T2 │ T3 │ T4 │ T5 │    │
│                                        └────┴────┴────┴────┴────┘    │
│                                        Lambda/SQS/SNS/StepFn/...     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 3. Event Bus - 라우터의 심장

Event Bus는 이벤트가 모이는 중앙 라우터이다. EventBridge는 세 종류의 Event Bus를 제공한다.

| Event Bus 종류 | 용도 | 특징 |
|---------------|------|------|
| **Default Event Bus** | AWS 서비스 이벤트 자동 수신 | 계정당 하나, EC2/S3/RDS 등 이벤트 자동 유입 |
| **Custom Event Bus** | 애플리케이션 자체 이벤트 | 도메인/워크로드별로 생성 |
| **Partner Event Bus** | SaaS 파트너 이벤트 수신 | Zendesk, Datadog, Stripe 등과 연결 |

**버스를 나누는 이유**:
- 워크로드 격리 (PII 포함 이벤트 vs 일반 이벤트)
- 도메인 분리 (주문 버스, 결제 버스, 배송 버스)
- 접근 제어 단위 (Resource Policy를 버스 단위로 부여)
- Rule 쿼터 분산 (버스당 기본 300개 Rule 제한)

---

### 4. Event - JSON으로 표현되는 상태 변화

이벤트는 "시스템 상태가 변했다"는 사실을 나타내는 JSON 객체이다. EventBridge는 이벤트의 구조를 표준화한다.

```json
{
  "version": "0",
  "id": "6a7e8feb-b491-4cf7-a9f1-bf3703467718",
  "detail-type": "EC2 Instance State-change Notification",
  "source": "aws.ec2",
  "account": "111122223333",
  "time": "2026-04-11T12:00:00Z",
  "region": "ap-northeast-2",
  "resources": [
    "arn:aws:ec2:ap-northeast-2:111122223333:instance/i-1234567890abcdef0"
  ],
  "detail": {
    "instance-id": "i-1234567890abcdef0",
    "state": "running"
  }
}
```

| 필드 | 역할 |
|------|------|
| `source` | 이벤트 발생 주체 (`aws.ec2`, `com.myapp.order` 등) |
| `detail-type` | 이벤트 타입 (사람이 읽는 라벨) |
| `detail` | 실제 페이로드 (서비스마다 구조가 다름) |
| `resources` | 관련 리소스 ARN 목록 |
| `time` | 이벤트 발생 시각 |

---

### 5. Rule - Event Pattern과 Schedule

Rule은 이벤트를 필터링하고 타겟으로 라우팅한다. Rule은 두 가지 방식으로 트리거된다.

#### 5-1. Event Pattern (이벤트 패턴 매칭)

이벤트의 구조/값과 매칭되는 JSON 패턴을 작성한다. 배열은 "OR" 의미이며, 객체는 중첩 매칭이다.

```json
// "EC2 인스턴스가 running 또는 stopped 상태로 변경됐을 때"
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["running", "stopped"]
  }
}
```

**지원되는 매처**:

| 매처 | 예시 | 설명 |
|------|------|------|
| Exact | `["running"]` | 정확히 일치 |
| Prefix | `[{"prefix": "i-"}]` | 문자열 접두사 |
| Anything-but | `[{"anything-but": "terminated"}]` | 제외 매칭 |
| Numeric | `[{"numeric": [">", 100]}]` | 숫자 비교 |
| Exists | `[{"exists": true}]` | 필드 존재 여부 |
| IP Address | `[{"cidr": "10.0.0.0/24"}]` | CIDR 매칭 |

#### 5-2. Schedule (스케줄 기반)

Cron 또는 Rate 표현식으로 정기 실행. 단, AWS는 이제 레거시인 Scheduled Rules 대신 **EventBridge Scheduler**를 권장한다. Scheduler는 유연한 시간 윈도우, 재시도 제한, 실패 보존, 훨씬 높은 확장성을 제공한다.

```
cron(0 10 * * ? *)   → 매일 UTC 10:00
rate(5 minutes)      → 5분마다
```

---

### 6. Target - 최대 5개의 목적지

Rule이 매칭되면 최대 5개의 Target에 동시에 이벤트를 전달할 수 있다. 대부분의 AWS 서비스가 Target으로 지원된다.

| 카테고리 | Target 예시 | 주 용도 |
|---------|-------------|---------|
| 컴퓨팅 | Lambda, ECS Task, Batch Job | 이벤트 처리 로직 |
| 메시징 | SQS, SNS, Kinesis Stream | 다운스트림 버퍼링/팬아웃 |
| 오케스트레이션 | Step Functions State Machine | 복잡한 워크플로우 |
| 데이터 | Firehose, Redshift, S3(Firehose 경유) | 분석/저장 |
| HTTP | API Destinations | 외부 REST API 호출 |
| 크로스 계정 | 다른 계정의 Event Bus | 멀티 계정 통합 |

**Input Transformer**를 이용해 타겟으로 전달되기 전 이벤트를 재구성할 수 있다.

```
Original                          Transformed (SNS용)
{                                 {
  "detail": {          ──────▶      "message":
    "instance-id": "i-1",             "EC2 i-1 is now running"
    "state": "running"              }
  }
}
```

---

### 7. Advanced - Archive, Replay, Schema Registry, API Destinations

#### 7-1. Archive & Replay

Event Bus를 지나가는 이벤트를 Archive에 보관하고 나중에 동일한 버스로 재전송할 수 있다.

```
┌──────────────────────────────────────────────┐
│  Event Bus ──▶ Archive (이벤트 JSON 보관)    │
│     ▲              │                          │
│     │              ▼                          │
│     └──── Replay (과거 이벤트 재주입) ───────┘│
└──────────────────────────────────────────────┘
```

**활용 사례**: 신규 서비스 Hydration, 장애 후 재처리, 재해 복구, 실제 이벤트 기반 테스트.

#### 7-2. Schema Registry

이벤트 스키마를 레지스트리에 등록해두면 Python/Java/TypeScript/Go 등으로 **코드 바인딩**을 생성할 수 있다. Schema Discovery 기능을 켜두면 버스를 흐르는 이벤트에서 스키마를 자동 추론해준다.

#### 7-3. API Destinations

EventBridge가 외부 HTTP/REST API를 Target으로 호출할 수 있게 해주는 기능. SaaS(예: Slack, Zendesk)나 자체 서비스의 API를 호출할 때 사용한다. Connection 리소스에 OAuth/API Key를 저장해 보안 있게 관리한다.

---

### 8. 실전 아키텍처 예시 - 주문 시스템

```
Producer Side                Event Bus              Consumer Side
─────────────                ─────────              ─────────────

Order Service  ──┐
                 │
Payment Service──┤──▶ custom-bus:orders ──┐
                 │                          │
Shipping Service─┘                          │
                                            │
                                            ├─▶ Rule: order.created
                                            │       ├─▶ Lambda: 재고 확인
                                            │       ├─▶ SQS: 알림 큐
                                            │       └─▶ Firehose: 분석 저장
                                            │
                                            ├─▶ Rule: payment.completed
                                            │       └─▶ StepFunctions: 배송 워크플로우
                                            │
                                            └─▶ Rule: order.cancelled
                                                    ├─▶ Lambda: 환불
                                                    └─▶ SNS: 고객 알림

별도 버스:                custom-bus:pii-events ──▶ Rule: PII 포함
                                                        └─▶ S3(KMS 암호화)
```

**포인트**: Producer는 "주문이 생성됐다"는 사실만 던진다. 알림 큐가 추가되든, 분석 파이프라인이 추가되든 Producer 코드는 바뀌지 않는다.

---

### 9. 주요 제한 및 쿼터

| 항목 | 기본값 | 조정 가능성 |
|------|--------|-------------|
| Event Bus당 Rule 수 | 300 | Service Quotas로 상향 |
| Rule당 Target 수 | 5 | 불가 (팬아웃은 SNS/다중 Rule로 해결) |
| PutEvents TPS | 리전별 기본 쿼터 | 상향 가능 |
| 이벤트 크기 | 최대 256 KB | 불가 (큰 페이로드는 S3 참조로) |
| 전달 보장 | At-least-once | 불가 (중복 가능성 내재) |

---

## 내가 얻은 인사이트

### 설계 관점

1. **"누가 받는지 모르는 것"이 확장의 핵심이다**
   - Producer가 Consumer 목록을 몰라도 되는 구조를 만드는 게 EventBridge의 본질이다. 새 Consumer가 추가돼도 Producer는 배포할 필요가 없다. 이는 마이크로서비스 간 결합도를 낮추는 가장 강력한 수단이다.

2. **Event Bus는 "도메인 경계"와 일치시키는 게 좋다**
   - Default Bus에 모든 커스텀 이벤트를 밀어넣는 것은 안티패턴에 가깝다. 주문/결제/배송 같은 도메인 단위로 Custom Bus를 분리하면 Rule 쿼터, 보안 경계, 모니터링 단위가 자연스럽게 맞아떨어진다.

3. **Rule의 5개 Target 제한은 "제약이자 힌트"다**
   - 하나의 Rule에 5개 이상을 붙이고 싶어진다면, 그건 Rule을 쪼개거나 SNS를 중간에 끼워 팬아웃해야 한다는 신호다. 5개 제한은 오히려 설계를 단순하게 유지하는 강제 장치로 작동한다.

### 운영 관점

1. **At-least-once는 곧 Idempotency 강제**
   - EventBridge는 중복 전달 가능성을 내재한다. Consumer는 반드시 멱등하게 구현되어야 하고, 이벤트에 고유 ID를 포함해 DynamoDB 등을 이용한 dedup 전략을 미리 설계해야 한다. 이 프로젝트의 `system_design/idempotency.md`와 `system_design/error_handling_in_event_driven_systems.md`가 직접적으로 연결되는 지점이다.

2. **Archive & Replay는 "무료 장애 복구 도구"다**
   - 기능 자체는 단순하지만, Consumer 버그로 한 시간치 이벤트 처리가 누락됐을 때 Archive에서 해당 시점만 Replay할 수 있다는 것은 운영 관점에서 엄청난 안전망이다. 많은 팀이 Archive를 켜두지 않아 장애 시 원본 이벤트 자체를 잃는다.

3. **Scheduled Rules 대신 EventBridge Scheduler로 일찍 갈아타라**
   - Scheduled Rules는 레거시가 되었고, Scheduler는 더 정확한 시간 윈도우, 재시도 정책, 실패 보존 등을 제공한다. 신규 프로젝트라면 처음부터 Scheduler를 쓰는 게 운영 부담을 줄인다.

### 비용 관점

1. **PutEvents 요금과 Target 호출 요금은 별개다**
   - EventBridge 자체는 발행된 이벤트 수(PutEvents 100만 건당 과금) 기준이지만, Target인 Lambda 호출/SQS 메시지/Firehose 처리 비용은 별도로 누적된다. 팬아웃이 과해지면 EventBridge 요금보다 Downstream 요금이 더 빠르게 증가한다.

2. **Schema Discovery는 켜두면 비용이 든다**
   - 편리하지만 이벤트마다 샘플링/분석이 일어나 트래픽 많은 버스에서는 무시할 수 없는 비용이 된다. 개발 단계에서만 켜고 운영에서는 끄는 전략이 현실적이다.

### Kafka / SNS와의 비교 관점

1. **EventBridge vs SNS**
   - SNS는 단순 Pub/Sub 팬아웃에 최적화되어 있고, 필터링은 메시지 속성 기반으로 제한적이다. EventBridge는 **페이로드 내용 기반의 풍부한 JSON 패턴 매칭**, Schema Registry, Archive/Replay, API Destinations까지 포함한 "라우팅 플랫폼"이다. 필터링이 복잡하거나 SaaS 통합이 필요하면 EventBridge, 단순 팬아웃이면 SNS가 맞다.

2. **EventBridge vs Kafka**
   - Kafka는 **로그 기반 재생 가능한 스트리밍 플랫폼**이고 순서 보장/파티셔닝/고처리량에 강하다. EventBridge는 순서 보장이 없고 TPS도 Kafka에 비하면 낮지만, 서버리스라 운영 부담이 0에 가깝다. "이벤트 스트리밍"이 아니라 "이벤트 라우팅"이 필요한 경우라면 EventBridge가 훨씬 가볍게 시작할 수 있다.

3. **EventBridge는 "글루(Glue)"로 쓸 때 빛난다**
   - 전체 아키텍처의 메인 스트리밍 백본으로는 한계가 있지만, AWS 서비스 간 / SaaS 간 / 마이크로서비스 간 이벤트를 "붙이는 접착제"로 쓸 때는 압도적으로 편리하다. 처음부터 메인 이벤트 버스로 삼기보다, 경계를 가로지르는 통합 레이어로 쓰는 것이 가장 합리적인 포지션이다.
