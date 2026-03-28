# The Trend is Kubernetes (Beginner to Intermediate Edition)

## 출처
- **링크**:  https://www.inflearn.com/en/course/%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4-%EA%B8%B0%EC%B4%88

---

## Introduction

1. 서버 자원을 효율적으로 쓰기 위한 가상화 기술
2. Linux (자원 격리) -> VM (OS 기동) -> Container (OS 기동 X) -> **Container 오케스트레이터**

---

## Kubernetes Cluster Installation

1. Vagrant: VirtualBox 등 다양한 가상화 소프트웨어와 연동 가능, 명령어 한 줄로 VM 생성, 시작, 중지, 삭제 가능

---

## Pod - Container, Label, NodeSchedule

1. Container: Pod 안에는 하나의 독립적인 서비스를 구동할 수 있는 컨테이너가 있다. 컨테이너에는 하나 이상의 포트를 가질 수 있지만 중복된 포트를 가질 수는 없다. Pod 안에 컨테이너들은 하나의 호스트(기기)로 묶이게 된다. Pod 생성 시에 고유한 IP(주소)가 할당되는데 만약 Pod에 문제가 생기면 시스템이 재생성하고 이때 IP가 변경된다.
2. Label: Pod 뿐 아니라 모든 오브젝트에 달 수 있다. 목적에 따라 오브젝트를 분류하고, 오브젝트를 따로 연결하기 위한 목적이다. 키-값의 한 쌍으로 구성된다. 하나의 Pod에는 여러 Label을 달 수 있다.
3. NodeSchedule: Pod는 여러 노드들 중 하나에 올라가야 한다. 직접 선택하는 방법과 NodeSchedule을 이용하는 방법이 있다. NodeSchedule는 사용량에 따라 자동으로 스케줄 해준다.

---

## Deployment - Recreate, RollingUpdate

1. Recreate: 심플하게 삭제 후, 일정 시간의 다운 타임을 가진 후 재생성되는 방식이다. 
2. Rolling Update: 새로운 파드를 먼저 생성하여 일정 시간 신/구 버전을 이중화 하여 트래픽을 받은 이후, 안전하게 구 버전을 삭제하는 방식이다.
3. Blue/Green: Rolling Update와 유사하지만 각각의 파드에 대한 신/구 버전을 순차적으로 인전하는 Rolling Update와 달리, 서비스의 Blue/Green 플래그로 동시에 전환한다는 것이 특징이다.
4. Canary: 실험체를 통해 위험을 검증하고 배포하는 방식. 

---

## Pod - Lifecycle

Kubernetes에서 Pod는 생성부터 종료까지 여러 상태를 거친다.

1. Pending: Pod가 만들어졌지만 아직 Node에 올라가지 않았거나, 컨테이너 이미지가 받아지는 중.
2. Running: Pod가 Node에 할당되고, 컨테이너가 정상적으로 실행 중인 상태.
3. Succeeded: Pod 안의 모든 컨테이너가 정상적으로 종료(Exit Code 0)된 경우. 주로 일회성 Job에서 볼 수 있다.
4. Failed: 컨테이너 중 하나라도 비정상적으로 종료(Exit Code 0이 아님)된 경우.
5. Unknown: Pod의 상태를 알 수 없을 때(예: Node와 통신 불가 등).

컨테이너 단위로 보면 Init, Waiting, Running, Terminated 같은 상태도 있다.

Pod Lifecycle을 알면 장애 상황에서 Kubernetes가 어떻게 동작하는지, 복구는 어떻게 되는지 이해하는 데 도움이 된다.

---

## Service - Headless, Endpoint, ExternalName

1. Headless Service: 클러스터IP 없이 동작. Service 자체 IP를 할당하지 않고, DNS 쿼리 시 실제 Pod의 IP 목록을 그대로 반환. StatefulSet 등에서 개별 Pod 접근이 필요할 때 사용.
2. Endpoint: Service가 트래픽을 전달할 실제 대상(Pod, 외부 IP 등). Service와 Pod가 연결되면 자동으로 Endpoint가 생성된다. Endpoints 오브젝트를 직접 수정해서 외부 서비스로 트래픽을 보낼 수도 있다.
3. ExternalName: 클러스터 외부의 DNS 이름을 내부 Service 이름으로 매핑. 실제로는 CNAME 레코드처럼 동작하며, 외부 리소스(DB 등)에 내부에서 접근할 때 사용.

---

## StatefulSet

1. StatefulSet: 순서와 고유성을 보장해야 하는 Pod(예: DB, Zookeeper 등)에 사용. 각 Pod에 고유한 이름과 네트워크 ID, 영구 스토리지를 부여한다. Pod가 재시작돼도 이름과 볼륨이 유지된다. 주로 상태 저장 서비스에 적합.

---