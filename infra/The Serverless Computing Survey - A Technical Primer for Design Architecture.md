# The Serverless Computing Survey: A Technical Primer for Design Architecture

## 출처
- **저자**: Zijun Li, Linsong Guo, Jiagan Cheng, Quan Chen, Bingsheng He, Minyi Guo
- **학술지**: ACM Computing Surveys (CSUR), Vol. 54, Issue 10s, 2022
- **DOI**: https://doi.org/10.1145/3508360
- **날짜**: 2022년 1월
- **인용 횟수**: 121회 (2025년 기준)

## AI 요약

### 1. 서버리스 컴퓨팅의 등장 배경
클라우드 인프라의 발전으로 클라우드 네이티브 컴퓨팅이 등장했고, 마이크로서비스 배포를 위한 가장 유망한 아키텍처로 서버리스 컴퓨팅이 부상했다. 본질적인 확장성과 유연성 덕분에 점점 더 많은 인터넷 서비스에서 서버리스가 채택되고 있다.

### 2. 4계층 스택 아키텍처 (핵심)
논문은 서버리스 아키텍처를 **4개의 스택 계층**으로 분해하여 각 계층의 연구 도메인을 체계적으로 정리한다:

**1) Virtualization Layer (가상화 계층)**
- **역할**: 함수 실행을 위한 격리된 환경 제공
- **핵심 기술**: Containers, VMs, Unikernels, Firecracker
- **주요 이슈**: 
  - Cold start 문제 (함수 첫 실행 시 지연)
  - 보안 격리 vs 성능 트레이드오프
  - Multi-tenancy 환경의 리소스 격리
- **최신 연구**: gVisor (Google), Kata Containers, Firecracker (AWS)

**2) Encapsulation Layer (캡슐화 계층)**
- **역할**: 함수 패키징, 의존성 관리, 런타임 제공
- **핵심 기술**: Docker images, Language runtimes, Dependency bundling
- **주요 이슈**:
  - 컨테이너 이미지 크기 최적화 (빠른 배포)
  - 런타임별 성능 차이 (Python, Node.js, Java, Go 등)
  - 의존성 충돌 관리
- **트렌드**: Lazy loading, Image layering, Slim base images

**3) System Orchestration Layer (시스템 오케스트레이션 계층)**
- **역할**: 함수 라이프사이클 관리, 스케줄링, 리소스 할당
- **핵심 기술**: 
  - **Function scheduling**: 워크로드에 맞춰 함수 배치
  - **Auto-scaling**: 트래픽에 따른 자동 확장/축소
  - **Resource allocation**: CPU, 메모리, GPU 등 최적 할당
- **주요 이슈**:
  - Keep-alive 전략 (warm containers 유지)
  - Bin packing 문제 (서버 활용도 최적화)
  - QoS 보장과 비용 최적화의 균형
- **연구 방향**: ML 기반 예측 스케줄링, RL을 활용한 동적 리소스 관리

**4) System Coordination Layer (시스템 조정 계층)**
- **역할**: 분산 함수 간 통신, 워크플로 오케스트레이션, 상태 관리
- **핵심 기술**:
  - **Function composition**: DAG 기반 워크플로 실행
  - **State management**: Redis, DynamoDB 등 외부 상태 저장소 연동
  - **Data passing**: 함수 간 데이터 전달 최적화
- **주요 이슈**:
  - Stateless 제약으로 인한 복잡성
  - 네트워크 오버헤드 (함수 간 통신)
  - 분산 트랜잭션 처리
- **솔루션**: AWS Step Functions, Cloudburst (stateful FaaS), Pocket (ephemeral storage)

### 3. 서버리스의 핵심 특성
- **No server management**: 개발자는 인프라를 직접 관리하지 않음
- **Pay-per-use**: 실행 시간 기반 과금 (밀리초 단위)
- **Event-driven**: 이벤트 발생 시 함수 자동 실행
- **Automatic scaling**: 0에서 수백만까지 자동 확장

### 4. 주요 서버리스 플랫폼
- **AWS Lambda**: 시장 점유율 1위, 다양한 AWS 서비스 통합
- **Azure Functions**: Microsoft 생태계 통합
- **Google Cloud Functions**: GCP 네이티브 서비스
- **오픈소스**: OpenWhisk (Apache), Fission, Kubeless, OpenFaaS

### 5. 서버리스의 핵심 도전 과제

**Cold Start Problem**
- 함수 첫 실행 시 수백 ms ~ 수 초 지연
- 컨테이너 생성 + 런타임 초기화 + 의존성 로딩 시간
- 해결책: Pre-warming, Container reuse, Lighter runtimes (Firecracker)

**State Management**
- Stateless 제약으로 외부 저장소 필수 (Redis, S3, DynamoDB)
- 함수 간 상태 공유의 어려움
- 해결책: Cloudburst (함수 내부 상태 유지), Pocket (임시 스토리지)

**Performance Unpredictability**
- 공유 인프라로 인한 성능 변동성
- 네트워크 지연, CPU throttling
- 해결책: QoS 보장 메커니즘, Dedicated 리소스 옵션

**Security & Isolation**
- Multi-tenant 환경의 보안 위협 (Spectre, Meltdown)
- 컨테이너 탈출 공격 가능성
- 해결책: Hardware-based isolation, MicroVM (Firecracker)

**Observability**
- 분산 함수 추적의 어려움
- 디버깅 복잡성
- 해결책: X-Ray (AWS), OpenTelemetry, Distributed tracing

### 6. 서버리스 사용 사례
- **데이터 처리**: 이미지/비디오 변환, ETL 파이프라인
- **API Backend**: RESTful API, GraphQL endpoint
- **IoT 애플리케이션**: 센서 데이터 실시간 처리
- **ML Inference**: 모델 서빙 (예측 요청 처리)
- **스트림 처리**: Kinesis, Kafka 연동 실시간 분석

### 7. 서버리스 워크플로 오케스트레이션
- **AWS Step Functions**: JSON 기반 상태 머신 정의
- **Fission Workflows**: Kubernetes 네이티브
- **Triggerflow**: 이벤트 드리븐 워크플로
- **핵심 문제**: 함수 체인의 레이턴시 누적, Cascading cold starts

### 8. 미래 연구 방향
- **Stateful serverless**: 함수 내부 상태 유지 메커니즘
- **Hardware acceleration**: GPU, FPGA를 활용한 FaaS
- **Edge computing integration**: CDN 엣지에서 함수 실행
- **Serverless databases**: Aurora Serverless, DynamoDB on-demand
- **Cost optimization**: RL 기반 자동 리소스 튜닝

### 9. 보안 모델 (Security Implications)
논문은 보안 관점에서 각 계층의 핵심 한계(Limitations)와 시사점(Implications)을 강조:
- **Virtualization**: 격리 수준과 성능의 트레이드오프
- **Encapsulation**: 의존성 취약점 스캔 필요
- **Orchestration**: 멀티 테넌시 간섭 방지
- **Coordination**: 분산 시스템 공격 표면 최소화

### 10. 156개 레퍼런스 분석
논문은 Firecracker, gVisor, OpenWhisk, Pocket, Cloudburst, SAND, Wukong 등 주요 연구와 플랫폼을 망라하며, 2016-2021년 사이의 서버리스 연구 흐름을 종합적으로 정리한다.

## 내가 얻은 인사이트

람다는 많이 써봤는데, 그럼에도 깊게 공부해본적이 없어 내부 구조를 해부한 글을 읽는건 아직 낮설다. 인사이트는 아니고 그냥 구조를 한 번 보았다 정도의 감상이다.