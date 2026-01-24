# Amazon EBS Deep Dive (re:Invent 2021/2022)

## 출처
- **링크**: 
  - https://d1.awsstatic.com/events/reinvent/2021/Amazon_EBS_A_tech_deep_dive_STG201.pdf
  - https://d1.awsstatic.com/events/Summits/reinvent2022/STG307-R_Amazon-EBS-A-tech-deep-dive.pdf

---

## AI 요약

### EBS 볼륨 타입

| 타입 | IOPS | 처리량 | 용도 |
|-----|------|-------|-----|
| gp3 (범용 SSD) | 3,000~16,000 | 128~1,000 MiB/s | 부팅, 일반 DB |
| io2 Block Express | 최대 256,000 | 최대 4,000 MiB/s | 고성능 DB |
| st1 (처리량 HDD) | - | 최대 500 MiB/s | 빅데이터, 순차 I/O |
| sc1 (콜드 HDD) | - | 최대 250 MiB/s | 아카이브, 백업 |

### EBS 설계 목표

- **99.999% 서비스 가용성**
- **최대 99.999% 내구성** (io2 Block Express)
- **AFR 0.1~0.2%** (Annual Failure Rate)

### 핵심 아키텍처 컴포넌트

**1. Configuration Manager**
- Host-Volume 매핑 관리
- AZ 내에 완전히 격리됨
- Paxos 기반 복제

**2. Physalia (핵심)**
- "Millions of tiny databases" 접근
- 각 EBS 볼륨마다 별도의 7-node Paxos 셀
- 네트워크/전력 토폴로지 인식 배치
- Blast radius 최소화

**3. SRD Storage Fabric**
- Native multipath 지원
- 대규모 클라우드용 congestion control
- 네트워크 장애 시 빠른 복구
- Latency jitter 최소화

**4. Nitro Card for EBS**
- NVMe 컨트롤러 (표준 드라이버 사용)
- 암호화 지원
- EBS 데이터 플레인 처리
- EBS-optimized 기본 제공

### io2 Block Express 혁신

**아키텍처 변화:**
- Disaggregated infrastructure
- Disaggregated data plane과 data services
- Nitro + SRD 조합

**성능 개선:**
- 4x 처리량 (4,000 MiB/s)
- 4x IOPS (256,000)
- 4x 볼륨 크기 (64TB)
- Sub-millisecond latency
- 더 일관된 I/O latency

### Blast Radius Reduction 전략

**AZ 독립성:**
- 각 AZ가 독립적으로 운영
- Cross-AZ 의존성 최소화

**Physalia 셀 분리:**
- 볼륨당 독립된 Paxos 셀
- 셀 간 조정 없음
- 한 셀 장애가 다른 셀에 영향 없음

**데이터 플레인 분리:**
- Fast path 코드 최소화
- 보안/정확성 추론 용이
- 명확한 API로 빠른 개발

### Snapshot 기능

- Point-in-time 복사
- 증분 백업 (변경된 블록만)
- S3에 저장 (11 nines 내구성)
- Crash consistent
- Archive tier (75% 저렴)
- Recycle Bin (삭제 복구)

---

## 내가 얻은 인사이트
