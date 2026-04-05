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

## Service - ClusterIP, NodePort, LoadBalancer

1. ClusterIP: 클러스터 내부에서만 접근 가능한 기본 Service 타입. Pod들 사이의 내부 통신에 사용된다. 외부에서는 접근할 수 없다.
2. NodePort: 모든 Node의 특정 포트를 열어 외부에서 접근 가능하게 한다. ClusterIP 기능을 포함하며, 추가로 각 Node의 IP와 지정된 포트를 통해 외부 트래픽을 받을 수 있다. 포트 범위는 30000~32767이다.
3. LoadBalancer: 클라우드 환경에서 외부 로드밸런서를 자동으로 프로비저닝하여 트래픽을 분산한다. NodePort와 ClusterIP 기능을 모두 포함하며, 외부에서 단일 엔드포인트로 접근할 수 있게 해준다.

---

## Volume - emptyDir, hostPath, PV/PVC

1. emptyDir: Pod가 생성될 때 함께 만들어지고, Pod가 삭제되면 함께 사라지는 임시 볼륨. Pod 내 컨테이너들끼리 데이터를 공유할 때 사용한다.
2. hostPath: Node의 실제 파일시스템 경로를 Pod에 마운트하는 방식. Pod가 재생성되어 같은 Node에 올라가면 데이터가 유지되지만, 다른 Node에 올라가면 접근할 수 없다. Node의 시스템 파일에 접근해야 할 때 사용한다.
3. PV(PersistentVolume) / PVC(PersistentVolumeClaim): PV는 클러스터 레벨에서 관리자가 미리 생성해둔 볼륨이고, PVC는 사용자가 필요한 용량과 접근 모드를 요청하는 것이다. PVC가 적절한 PV에 바인딩되면 Pod에서 사용할 수 있다. Pod와 독립적으로 존재하므로 데이터가 영속적으로 유지된다.

---

## ConfigMap, Secret - Env, Mount

1. ConfigMap: 환경 변수나 설정 파일 등 일반적인 설정 데이터를 키-값 쌍으로 저장하는 오브젝트. Pod와 분리하여 설정을 관리할 수 있어, 이미지를 다시 빌드하지 않고도 설정을 변경할 수 있다.
2. Secret: ConfigMap과 유사하지만 비밀번호, 토큰 등 민감한 데이터를 저장하기 위한 오브젝트. Base64로 인코딩되어 저장되며, 메모리에만 올려서 보안성을 높인다.
3. Env(환경 변수): ConfigMap이나 Secret의 데이터를 Pod의 환경 변수로 주입하는 방식. Pod가 생성될 때 값이 한 번 주입되며, 이후 ConfigMap/Secret이 변경되어도 Pod를 재시작해야 반영된다.
4. Mount(볼륨 마운트): ConfigMap이나 Secret을 파일로 Pod 내부에 마운트하는 방식. 마운트 방식은 원본이 변경되면 Pod 재시작 없이도 자동으로 반영될 수 있다.

---

## Namespace, ResourceQuota, LimitRange

1. Namespace: 하나의 클러스터 안에서 리소스를 논리적으로 분리하는 단위. 서로 다른 Namespace의 오브젝트들은 이름이 같아도 충돌하지 않는다. 환경별(dev, staging, prod) 또는 팀별로 분리하여 사용할 수 있다.
2. ResourceQuota: Namespace에 할당할 수 있는 리소스의 총량을 제한한다. CPU, 메모리, Pod 수, Service 수 등 다양한 리소스에 대해 최대치를 설정할 수 있어 특정 Namespace가 클러스터 자원을 독점하는 것을 방지한다.
3. LimitRange: Namespace 내 개별 Pod 또는 컨테이너 단위로 리소스 사용량의 기본값과 최소/최대값을 설정한다. ResourceQuota가 Namespace 전체의 총량을 제한한다면, LimitRange는 개별 오브젝트의 리소스를 제한한다.

---

## ReplicaSet - Template, Replicas, Selector

1. Template: ReplicaSet이 새로운 Pod를 생성할 때 사용하는 Pod의 명세(스펙). 컨테이너 이미지, 포트, 라벨 등 Pod의 설정 정보를 담고 있다. Template을 변경해도 기존 Pod에는 영향이 없고, 새로 생성되는 Pod에만 적용된다.
2. Replicas: 유지해야 할 Pod의 개수를 지정한다. ReplicaSet은 지정된 수만큼 Pod가 항상 실행 중이도록 관리한다. Pod가 삭제되거나 장애가 발생하면 자동으로 새 Pod를 생성하여 원하는 수를 유지한다.
3. Selector: ReplicaSet이 관리할 Pod를 식별하는 조건. Pod의 Label과 매칭하여 관리 대상을 결정한다. matchLabels(정확한 일치)와 matchExpressions(조건식)를 사용할 수 있어 Replication Controller보다 유연한 선택이 가능하다.

---

## Deployment - Recreate, RollingUpdate

1. Recreate: 심플하게 삭제 후, 일정 시간의 다운 타임을 가진 후 재생성되는 방식이다. 
2. Rolling Update: 새로운 파드를 먼저 생성하여 일정 시간 신/구 버전을 이중화 하여 트래픽을 받은 이후, 안전하게 구 버전을 삭제하는 방식이다.
3. Blue/Green: Rolling Update와 유사하지만 각각의 파드에 대한 신/구 버전을 순차적으로 인전하는 Rolling Update와 달리, 서비스의 Blue/Green 플래그로 동시에 전환한다는 것이 특징이다.
4. Canary: 실험체를 통해 위험을 검증하고 배포하는 방식. 

---

## DaemonSet, Job, CronJob

1. DaemonSet: 클러스터의 모든 Node(또는 특정 Node)에 Pod를 하나씩 배포하는 컨트롤러. 새로운 Node가 추가되면 자동으로 Pod가 생성되고, Node가 제거되면 Pod도 함께 삭제된다. 로그 수집기(Fluentd), 모니터링 에이전트(Prometheus Node Exporter), 네트워크 플러그인 등 모든 Node에서 실행되어야 하는 서비스에 적합하다.
2. Job: 한 번 실행되고 완료되면 종료되는 일회성 작업을 관리하는 컨트롤러. Pod가 정상적으로 완료(Succeeded)될 때까지 재시도한다. completions(총 실행 횟수)와 parallelism(동시 실행 수)을 설정하여 병렬 처리도 가능하다. 데이터 마이그레이션, 배치 처리 등에 사용된다.
3. CronJob: Job을 주기적으로 생성하고 실행하는 컨트롤러. Linux의 cron과 동일한 스케줄 형식(분 시 일 월 요일)을 사용한다. 정기적인 백업, 리포트 생성, 주기적 데이터 정리 등 반복 작업에 적합하다. concurrencyPolicy를 통해 동시 실행 정책을 제어할 수 있다.

---
