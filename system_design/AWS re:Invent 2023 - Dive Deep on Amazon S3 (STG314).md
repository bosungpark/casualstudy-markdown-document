# AWS re:Invent 2023 - Dive Deep on Amazon S3 (STG314)

## 출처
- **링크**: https://aws.amazon.com/awstv/watch/d33eda30e60/
- **슬라이드 PDF**: https://d1.awsstatic.com/events/Summits/reinvent2023/STG314_Dive-deep-on-Amazon-S3.pdf
- **발표자**: Amy Therrien (Director, S3 Engineering), Seth Markle (Senior Principal Engineer, S3)
- **게재**: AWS re:Invent 2023

---

## AI 요약

### 1. S3의 진화: 세 가지 시대

Three epochs: Reactive → Threat modeling → Proactive

S3 팀의 성숙도는 세 단계를 거쳐 발전했다:
1. **Reactive**: 문제가 발생하면 대응
2. **Threat modeling**: 잠재적 문제를 예상하고 문서화
3. **Proactive**: 문제가 발생하기 전에 선제적으로 완화

이 접근법은 잠재적 문제를 예상하고 발생하기 전에 완화책을 구현하는 것을 포함하며, S3 팀 내에서 선제적 사고와 문제 해결 문화를 육성한다.

### 2. 핵심 원칙

There is no compression algorithm for experience

"경험에 대한 압축 알고리즘은 없다" - S3 팀이 17년간 축적한 경험과 교훈은 대체 불가능하다.

### 3. Threat Review 문화

Culture: Threat reviews - Actual written document, Interactive working meeting, Review with experienced team members, Learning opportunity for junior engineers

**Threat Review 구성 요소:**
- 실제 작성된 문서
- 인터랙티브 작업 미팅
- 경험 있는 팀 멤버와의 리뷰
- 주니어 엔지니어를 위한 학습 기회

### 4. S3 아키텍처 개요

```
┌─────────────────────────────────────┐
│             Clients                 │
├─────────────────────────────────────┤
│            Front end                │
│   Web servers, DNS, and network     │
├─────────────────────────────────────┤
│              Index                  │
│    Key/value mapping to storage     │
├─────────────────────────────────────┤
│             Storage                 │
│    Data durably stored on devices   │
└─────────────────────────────────────┘
```

350+ microservices, All AWS Regions

### 5. Front End Layer: 대규모 트래픽 처리

**규모:**
Traffic peaks at over 1PB/sec

**규모의 위협과 완화 메커니즘:**

The threat of scale and going wide - Mechanisms for mitigation: Use multipart uploads to parallelize puts, Use ranges to parallelize gets, Spread requests across many IPs in the fleet

#### 5.1 Multipart Upload (MPU)

100MB 파일을 단일 요청으로 업로드하면 X MB/s 속도지만, 5개의 20MB 파트로 나누어 병렬 업로드하면 5X MB/s 속도 달성.

**API 흐름:**
```
create-multipart-upload
    ↓
upload-part (n times, 병렬)
    ↓
complete-multipart-upload
```

#### 5.2 Range GET

다운로드도 동일 원리. `get-object-attributes`로 파트 정보 조회 후 병렬로 range GET 수행.

#### 5.3 Multi-value DNS

Spreading requests across the fleet - IT'S ALWAYS DNS

```bash
# nslookup s3.amazonaws.com
Non-authoritative answer:
Name: s3.amazonaws.com
Address: 192.0.2.1
Address: 192.0.2.4
Address: 192.0.2.5
Address: 192.0.2.9
Address: 192.0.2.2
Address: 192.0.2.6
Address: 192.0.2.8
Address: 192.0.2.7
```

다수의 IP 주소를 반환하여 클라이언트가 요청을 분산할 수 있게 함.

#### 5.4 Common Runtime (CRT)

Common Runtime (CRT) - BEST PRACTICES IMPLEMENTED IN CODE - S3AsyncClient.crtCreate(); - Open source component in the AWS SDK: Automated multipart uploads, Parallelization of range GETs for downloads, Built-in retry logic using multiple IPs, And more

### 6. Index Layer: 350조 객체 관리

**규모:**
350 trillion objects, 100+ million requests per second

#### 6.1 파티셔닝 전략

```
A - F  →  A - F
G - M      G - M
N - S      N - P  ← SPLIT
T - Z      Q - S
           T - Z
```

사용량과 용량에 따라 동적으로 파티션 분할.

#### 6.2 Prefix 개념

What's a prefix? Any string of characters after the bucket name

예시:
```
reinvent-bucket/p
reinvent-bucket/prefix
reinvent-bucket/prefix1/
reinvent-bucket/prefix2/
reinvent-bucket/prefix1/data/other
```

#### 6.3 Prefix 당 처리량 제한

3,500 PUT requests, 5,500 GET requests per prefix

#### 6.4 TPS 최대화를 위한 키 네이밍

Maximizing TPS with good key naming - Mechanisms for mitigation: Keep cardinality to the left in key names, Keep dates to the right in key names

**나쁜 예 (날짜가 왼쪽):**
```
reinvent-bucket/day1/prefix1/a  → 5,500 GETs/sec
reinvent-bucket/day1/prefix1/b  → 5,500 GETs/sec
...
Total: 22,000 TPS for day1

문제: day2로 넘어가면 day1 파티션은 미사용,
      day2 파티션을 새로 분할해야 함 → 스로틀링 발생 가능
```

**좋은 예 (날짜가 오른쪽):**
```
reinvent-bucket/prefix1/a/day1
reinvent-bucket/prefix1/a/day2  → 5,500 GETs/sec (파티션 재사용)
reinvent-bucket/prefix1/b/day1
reinvent-bucket/prefix1/b/day2  → 5,500 GETs/sec
```

날짜가 오른쪽에 있으면 기존 파티션 재사용 가능.

### 7. Storage Layer: 11 Nines Durability

**규모:**
Millions of hard drives, Exabytes of data

**내구성 목표:**
99.999999999% DATA DURABILITY

#### 7.1 위협: 디바이스 장애

Threat: Device failure - We must protect data stored on drives that can fail or corrupt bits at rest

#### 7.2 11 Nines 달성을 위한 세 가지 메커니즘

Achieving 11 9s of durability: End-to-end integrity checking of requests, Data always stored on redundant devices, Periodic durability auditing for data at rest

**1) End-to-end 무결성 검사:**
```
S3:PutObject
    ↓
Checksums taken in transit
    ↓
Data redundantly stored and checksums taken in storage
    ↓
Data stored compared to data uploaded
    ↓
200:SUCCESS
```

**2) 중복 디바이스 저장 (Erasure Coding):**
- 5개 디바이스에 각각 다른 데이터 저장
- 하나가 실패해도 나머지에서 복구 가능
- 대규모에서: 충분한 예비 용량 확보, 적극적인 장애 모니터링, 하드웨어 장애 시 중복성 유지

**3) 주기적 내구성 감사:**
휴식 중인 데이터도 지속적으로 검사하여 비트 부패 등 감지.

### 8. Multi-AZ 설계

#### 8.1 위협 모델: AZ 손실

Threat model: AZ loss - We must protect data we store against the unexpected total or partial loss of a zone. We assume that any single facility may fail at any time and that we must protect the durability of data that is stored within it.

#### 8.2 기본적으로 Multi-AZ

Multi-AZ by default - Regional storage classes span 3+ AZs

```
     AZ1          AZ2          AZ3
   ┌─────┐     ┌─────┐     ┌─────┐
   │A D B│     │A D C│     │A E C│
   │A D B│     │A D C│     │B E C│
   │     │     │A E C│     │B E D│
   └─────┘     └─────┘     └─────┘
                 ↓
            200:SUCCESS
```

데이터가 3개 AZ에 분산되어 저장된 후에야 성공 응답.

### 9. S3 Express One Zone

S3 Express One Zone - Full or partial loss of an Availability Zone may lose my data in S3 Express One Zone

99.999999999% data durability WITHIN A SINGLE AVAILABILITY ZONE

**특징:**
- 단일 AZ 내에서 11 nines 내구성
- End-to-end 무결성 검사 ✓
- 중복 디바이스 저장 ✓
- 주기적 내구성 감사 ✓
- **AZ 전체/부분 손실 시 데이터 손실 가능** ✗

S3 Express One Zone은 고성능 애플리케이션을 위해 설계된 새로운 스토리지 클래스로, 단일 가용 영역에 데이터를 로컬화하여 속도를 위해 일부 내구성을 트레이드오프한다.

### 10. 지역 격리 (Regional Isolation)

The power to touch is the power to destroy - The availability of one AWS Region can never affect the availability of another

"건드릴 수 있는 힘은 파괴할 수 있는 힘이다" - 한 리전의 가용성이 다른 리전에 절대 영향을 미쳐서는 안 된다.

Regional isolation - A LEARNED TENET - Amazon S3: 2006 - 2010

### 11. AZ 장애 시 가용성

AZ failure threat model - We must remain available through the unexpected loss of an entire zone. We assume that any single facility may fail at any time and that we must continue to serve requests when an entire zone is offline.

**DNS를 통한 장애 AZ 회피:**
```bash
# AZ1 장애 시
nslookup s3.amazonaws.com
→ AZ1 IP들은 제외하고 응답
→ 클라이언트가 자동으로 다른 AZ로 요청
```

### 12. AZ Fault Tolerance의 다른 활용

AZ fault tolerance: Not just for AZ faults! Separate fault domains: Software deployments, New hardware adoption, Configuration changes, More

AZ 분리는 단순히 AZ 장애 대응만이 아니라:
- 소프트웨어 배포
- 새 하드웨어 도입
- 구성 변경

등의 fault domain 분리에도 활용.

### 13. Defense in Depth: Guardrails

Defense in depth - Building good guardrails: Build for correctness, Threats and mitigations, But assume incorrectness, Guardrails. Examples: Shadow mode, Control plane limits

**원칙:**
- 정확성을 위해 구축하되
- 부정확성을 가정하라
- Guardrails로 보호

**예시:**
- **Shadow mode**: 변경 사항을 실제 적용 전에 시뮬레이션
- **Control plane limits**: 제어 평면 작업에 제한 설정

### 14. 우발적 삭제 방지

Accidental delete - WHEN YOU TELL US TO DELETE SOMETHING, WE DO IT - We never want accidental deletion of data in Amazon S3 buckets, especially due to bulk deletion operations

**완화 메커니즘:**
S3 Versioning, S3 Replication, S3 Object Lock, Backups

---

## 내가 얻은 인사이트
