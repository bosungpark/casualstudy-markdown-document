# Comparative Analysis of RESTful, GraphQL, and gRPC APIs - Performance Insights from Load and Stress Testing

## 출처
- **논문**: "Comparative Analysis of RESTful, GraphQL, and gRPC APIs: Performance Insight from Load and Stress Testing"
- **저자**: Steven Chandra, Ahmad Farisi
- **소속**: Faculty of Computer Science and Engineering, Universitas Multi Data Palembang, Indonesia
- **저널**: Jurnal Sisfokom (Sistem Informasi dan Komputer), Vol. 14, No. 1, January 2025
- **DOI**: https://doi.org/10.32736/sisfokom.v14i1.2315
- **키워드**: API Architecture, gRPC, GraphQL, Load Testing, Stress Testing

---

## AI 요약

### 1. 연구 배경
백엔드는 비즈니스 로직 처리, 데이터 관리, 소프트웨어 시스템 간 통신을 담당하는 디지털 인프라의 핵심 구성 요소입니다. API는 소프트웨어 상호작용을 가능하게 하는 인터페이스로서 백엔드 운영에서 중추적인 역할을 합니다. 본 연구는 세 가지 API 아키텍처(RESTful, GraphQL, gRPC)의 성능을 조사합니다.

### 2. 실험 방법론

#### 2.1 테스트 방식
- **Load Testing**: 정상 부하 조건에서의 성능 평가
- **Stress Testing**: 극한 부하 조건에서의 안정성 평가
- **실험 환경**: 실제 환경을 시뮬레이션하기 위한 전용 서버 및 클라이언트 하드웨어 사용
- **데이터셋**: 학생 관련 레코드 1,000개 행

#### 2.2 평가 지표
- **CPU Usage**: CPU 사용률
- **Memory Usage**: 메모리 사용률
- **Response Time**: 응답 시간
- **Load Time**: 로드 시간
- **Latency**: 지연 시간
- **Success Rate**: 성공률
- **Failure Rate**: 실패율

### 3. 실험 결과

#### 3.1 RESTful API
**강점:**
- **가장 높은 총 요청 처리량** (Highest Total Requests)
- 높은 처리량(throughput) 시나리오에 적합

**약점:**
- **더 큰 리소스 소비** (Greater Resource Consumption)
- **높은 실패율** (Higher Failure Rate)
- CPU 및 메모리 사용률이 높음

**적합한 사용 사례:**
- 덜 중요한 작업(less critical operations)
- 높은 처리량이 필요한 시나리오
- 실패 허용도가 높은 환경

#### 3.2 GraphQL
**강점:**
- **더 나은 CPU 및 메모리 효율성** (Better CPU and Memory Efficiency)
- **강력한 안정성** (Strong Stability)
- 리소스 효율성이 뛰어남

**약점:**
- **높은 지연 시간** (Higher Latency)
- **더 느린 응답 시간** (Slower Response Times)

**적합한 사용 사례:**
- 리소스 효율성이 중요한 환경
- 안정성이 최우선인 시스템
- 클라이언트가 필요한 데이터를 정확히 선택해야 하는 경우

#### 3.3 gRPC
**강점:**
- **중간 수준의 지연 시간과 리소스 사용** (Moderate Latency and Resource Usage)
- **균형 잡힌 성능** (Balanced Performance)
- 다양한 워크로드에서 안정적

**약점:**
- **스트레스 조건에서 약간 높은 메모리 소비** (Slightly Higher Memory Consumption Under Stress)

**적합한 사용 사례:**
- 다양한 워크로드를 처리해야 하는 환경
- 지연 시간과 리소스 사용 간 균형이 필요한 경우
- 마이크로서비스 간 내부 통신

### 4. 성능 비교 요약

| 지표 | RESTful | GraphQL | gRPC |
|------|---------|---------|------|
| **총 요청 처리량** | ⭐⭐⭐ 최고 | ⭐⭐ 중간 | ⭐⭐ 중간 |
| **CPU 효율성** | ⭐ 낮음 | ⭐⭐⭐ 높음 | ⭐⭐ 중간 |
| **메모리 효율성** | ⭐ 낮음 | ⭐⭐⭐ 높음 | ⭐⭐ 중간 (스트레스 시 주의) |
| **응답 시간** | ⭐⭐ 중간 | ⭐ 느림 | ⭐⭐⭐ 빠름 |
| **지연 시간** | ⭐⭐ 중간 | ⭐ 높음 | ⭐⭐⭐ 낮음 |
| **안정성** | ⭐ 낮음 (높은 실패율) | ⭐⭐⭐ 높음 | ⭐⭐ 중간 |
| **실패율** | ⭐ 높음 | ⭐⭐⭐ 낮음 | ⭐⭐ 중간 |

### 5. 선택 가이드라인

#### RESTful을 선택해야 하는 경우:
- 매우 높은 처리량이 필요한 시나리오
- 간헐적인 실패가 허용되는 환경
- 개발 생태계가 성숙하고 널리 사용되는 기술 필요
- 캐싱이 중요한 경우

#### GraphQL을 선택해야 하는 경우:
- 리소스(CPU/메모리) 효율성이 최우선인 환경
- 안정성과 낮은 실패율이 중요한 시스템
- 클라이언트가 필요한 데이터만 정확히 요청해야 하는 경우
- Over-fetching/Under-fetching 문제를 해결해야 할 때

#### gRPC를 선택해야 하는 경우:
- 다양한 워크로드에서 균형 잡힌 성능 필요
- 낮은 지연 시간이 중요한 마이크로서비스 간 통신
- 양방향 스트리밍이 필요한 경우
- 타입 안정성과 코드 생성의 이점이 필요한 경우

### 6. 테스트 환경 세부사항
- **데이터셋 크기**: 1,000개 행의 학생 관련 레코드
- **테스트 유형**: Load Testing + Stress Testing
- **하드웨어**: 전용 서버 및 클라이언트 시스템
- **실제 조건 시뮬레이션**: 프로덕션 환경과 유사한 조건 재현

---

## 내가 얻은 인사이트

rest는 생각보다 괜찮다. rpc는 균형잡힌 도구이다.