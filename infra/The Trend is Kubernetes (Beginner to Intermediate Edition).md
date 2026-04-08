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

## Component - kube-apiserver, etcd, kube-scheduler, kube-proxy, kube-controller-manager

1. kube-apiserver: Kubernetes API 서버로, 클러스터의 모든 요청을 처리하는 중앙 허브 역할을 한다. kubectl 명령어 등이 이 서버를 통해 클러스터와 상호작용한다.
2. etcd: 분산 키-값 저장소로, 클러스터의 모든 상태 정보를 저장한다. Kubernetes의 데이터베이스 역할을 한다.
3. kube-scheduler: Pod를 적절한 노드에 스케줄링하는 컴포넌트로, 리소스 요구사항과 제약사항을 고려하여 배치한다.
4. kube-proxy: 각 노드에서 실행되는 네트워크 프록시로, 서비스와 Pod 간의 트래픽을 라우팅하고 로드 밸런싱을 수행한다.
5. kube-controller-manager: 다양한 컨트롤러들을 실행하는 컴포넌트로, 클러스터의 상태를 유지하고 원하는 상태로 복구한다.

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

## K8S 실습 자료실 - 컨트롤러

### ReplicaSet

ReplicaSet은 Kubernetes에서 Pod의 복제본을 관리하는 컨트롤러입니다. 지정된 수의 Pod가 항상 실행되도록 보장하며, Pod가 실패하거나 삭제되면 자동으로 새로운 Pod를 생성합니다. ReplicationController의 후속 버전으로, 더 유연한 라벨 선택기를 지원합니다.

#### 주요 구성 요소
- **Template**: 새로운 Pod를 생성할 때 사용할 Pod 템플릿입니다. 컨테이너 이미지, 라벨, 환경 변수 등을 정의합니다.
- **Replicas**: 유지할 Pod의 수를 지정합니다.
- **Selector**: 관리할 Pod를 선택하는 라벨 선택기입니다. `matchLabels`와 `matchExpressions`를 사용하여 복잡한 조건을 지정할 수 있습니다.

#### 예제

##### 1. 기본 Pod
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod1
  labels:
    type: web
spec:
  containers:
  - name: container
    image: kubetm/app:v1
  terminationGracePeriodSeconds: 0
```

##### 2. ReplicaSet
```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: replica1
spec:
  replicas: 1
  selector:
    matchLabels:
      type: web
  template:
    metadata:
      labels:
        type: web
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
      terminationGracePeriodSeconds: 0
```

### ReplicationController에서 ReplicaSet으로 업데이트

ReplicationController는 Kubernetes의 초기 컨트롤러로, ReplicaSet의 전신입니다. 그러나 ReplicationController는 더 이상 사용되지 않으며(deprecated), ReplicaSet으로 대체되었습니다. ReplicationController에서 ReplicaSet으로 마이그레이션할 때는 주의해야 합니다.

#### 마이그레이션 예제

##### ReplicationController
```yaml
apiVersion: v1
kind: ReplicationController
metadata:
  name: replication1
spec:
  replicas: 2
  selector:
    cascade: "false"
  template:
    metadata:
      labels:
        cascade: "false"
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
```

마이그레이션 명령:
```bash
kubectl delete replicationcontrollers replication1 --cascade=false
```

##### ReplicaSet
```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: replica2
spec:
  replicas: 2
  selector:
    matchLabels:
      cascade: "false"
  template:
    metadata:
      labels:
        cascade: "false"
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
```

### Selector

Selector는 컨트롤러가 관리할 Pod를 식별하는 데 사용됩니다. ReplicaSet은 ReplicationController보다 더 강력한 선택기를 지원합니다.

- **matchLabels**: 라벨의 키-값 쌍이 정확히 일치하는 Pod를 선택합니다.
- **matchExpressions**: 더 복잡한 조건을 지정할 수 있습니다. `In`, `NotIn`, `Exists`, `DoesNotExist` 등의 연산자를 사용합니다.

#### 고급 Selector 예제

##### ReplicaSet with Advanced Selector
```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: replica1
spec:
  replicas: 1
  selector:
    matchLabels:
      type: web
      ver: v1
    matchExpressions:
    - key: type
      operator: In
      values: [web]
    - key: ver
      operator: Exists
  template:
    metadata:
      labels:
        type: web
        ver: v1
        location: dev
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
      terminationGracePeriodSeconds: 0
```

##### 관련 Pod 예제 (참고용)
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-node-affinity1
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: AZ-01
            operator: Exists
  containers:
  - name: container
    image: kubetm/init
```

**참고**: 위의 Pod 예제는 노드 어피니티를 보여주기 위한 것으로, ReplicaSet과 직접 관련이 없습니다.

### 팁
- **MatchExpressions**: `matchExpressions`를 사용하면 더 유연한 Pod 선택이 가능합니다. 예를 들어, 특정 라벨이 존재하는지 확인하거나, 값이 특정 목록에 포함되는지 등을 조건으로 지정할 수 있습니다.
- ReplicaSet은 Deployment의 일부로 더 자주 사용되며, 직접적으로 ReplicaSet을 생성하는 경우는 드뭅니다.

### 참조
- [Kubernetes ReplicaSet](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/)
- [Labels and Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)
- [ReplicationController](https://kubernetes.io/docs/concepts/workloads/controllers/replicationcontroller/)

### Deployment

Deployment는 Kubernetes에서 애플리케이션의 배포와 업데이트를 관리하는 컨트롤러입니다. ReplicaSet을 기반으로 하며, 롤링 업데이트, 롤백 등의 기능을 제공합니다. 애플리케이션의 무중단 배포를 지원합니다.

#### 배포 전략
- **Recreate**: 모든 기존 Pod를 삭제한 후 새로운 Pod를 생성합니다. 다운타임이 발생하지만, 간단합니다.
- **RollingUpdate**: 기존 Pod를 점진적으로 교체합니다. 무중단 배포가 가능합니다.

#### 예제

##### 1. Recreate 전략
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deployment-1
spec:
  selector:
    matchLabels:
      type: app
  replicas: 2
  strategy:
    type: Recreate
  revisionHistoryLimit: 1
  template:
    metadata:
      labels:
        type: app
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
      terminationGracePeriodSeconds: 10
```

##### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-1
spec:
  selector:
    type: app
  ports:
  - port: 8080
    protocol: TCP
    targetPort: 8080
```

테스트 명령:
```bash
while true; do curl 10.99.5.3:8080/version; sleep 1; done
```

롤백 명령:
```bash
kubectl rollout undo deployment deployment-1 --to-revision=2
kubectl rollout history deployment deployment-1
```

##### 2. RollingUpdate 전략
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deployment-2
spec:
  selector:
    matchLabels:
      type: app2
  replicas: 2
  strategy:
    type: RollingUpdate
  minReadySeconds: 10
  template:
    metadata:
      labels:
        type: app2
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
      terminationGracePeriodSeconds: 0
```

##### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-2
spec:
  selector:
    type: app2
  ports:
  - port: 8080
    protocol: TCP
    targetPort: 8080
```

테스트 명령:
```bash
while true; do curl 10.99.5.3:8080/version; sleep 1; done
```

##### 3. Blue/Green 배포
Blue/Green 배포는 두 개의 환경(Blue와 Green)을 유지하고, 트래픽을 한 번에 전환하는 방식입니다. Service의 selector를 변경하여 전환합니다.

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: replica1
spec:
  replicas: 2
  selector:
    matchLabels:
      ver: v1
  template:
    metadata:
      labels:
        ver: v1
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
      terminationGracePeriodSeconds: 0
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-3
spec:
  selector:
    ver: v1
  ports:
  - port: 8080
    protocol: TCP
    targetPort: 8080
```

### DaemonSet

DaemonSet은 클러스터의 모든 노드(또는 특정 노드)에 Pod를 하나씩 배포하는 컨트롤러입니다. 로그 수집, 모니터링 등 노드별로 실행해야 하는 애플리케이션에 적합합니다.

#### 주요 기능
- **HostPort**: Pod의 포트를 호스트의 특정 포트에 바인딩합니다.
- **NodeSelector**: 특정 라벨이 있는 노드에만 Pod를 배포합니다.

#### 예제

##### 1. HostPort를 사용한 DaemonSet
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: daemonset-1
spec:
  selector:
    matchLabels:
      type: app
  template:
    metadata:
      labels:
        type: app
    spec:
      containers:
      - name: container
        image: kubetm/app
        ports:
        - containerPort: 8080
          hostPort: 18080
```

테스트 명령:
```bash
curl 192.168.56.31:18080/hostname
```

##### 2. NodeSelector를 사용한 DaemonSet
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: daemonset-2
spec:
  selector:
    matchLabels:
      type: app
  template:
    metadata:
      labels:
        type: app
    spec:
      nodeSelector:
        os: centos
      containers:
      - name: container
        image: kubetm/app
        ports:
        - containerPort: 8080
```

라벨 추가:
```bash
kubectl label nodes k8s-node1 os=centos
kubectl label nodes k8s-node2 os=ubuntu
```

라벨 제거:
```bash
kubectl label nodes k8s-node2 os-
```

### Job

Job은 일회성 작업을 실행하는 컨트롤러입니다. Pod가 완료될 때까지 재시도하며, 완료되면 종료됩니다.

#### 주요 옵션
- **Completions**: 총 실행 횟수
- **Parallelism**: 동시 실행 수

#### 예제

##### 1. 기본 Job
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: job-1
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: container
        image: kubetm/init
        command: ["sh", "-c", "echo 'job start';sleep 20; echo 'job end'"]
      terminationGracePeriodSeconds: 0
```

##### 2. 병렬 Job
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: job-2
spec:
  completions: 6
  parallelism: 2
  activeDeadlineSeconds: 30
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: container
        image: kubetm/init
        command: ["sh", "-c", "echo 'job start';sleep 20; echo 'job end'"]
      terminationGracePeriodSeconds: 0
```

### CronJob

CronJob은 Job을 주기적으로 실행하는 컨트롤러입니다. Linux의 cron과 유사합니다.

#### 주요 기능
- **Schedule**: 실행 스케줄 (cron 형식)
- **ConcurrencyPolicy**: 동시 실행 정책 (Allow, Forbid, Replace)

#### 예제

##### 1. 기본 CronJob
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cron-job
spec:
  schedule: "*/1 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
          - name: container
            image: kubetm/init
            command: ["sh", "-c", "echo 'job start';sleep 20; echo 'job end'"]
          terminationGracePeriodSeconds: 0
```

수동 실행:
```bash
kubectl create job --from=cronjob/cron-job cron-job-manual-001
```

일시 중지:
```bash
kubectl patch cronjobs cron-job -p '{"spec" : {"suspend" : false }}'
```

**참고**: Kubernetes 1.19 이후, CronJob 삭제 시 수동으로 생성한 Job도 함께 삭제됩니다.

##### 2. ConcurrencyPolicy를 사용한 CronJob
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cron-job-2
spec:
  schedule: "20,21,22 * * * *"
  concurrencyPolicy: Replace
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
          - name: container
            image: kubetm/init
            command: ["sh", "-c", "echo 'job start';sleep 140; echo 'job end'"]
          terminationGracePeriodSeconds: 0
```

**참고**: Kubernetes 1.19 이후, Replace 모드에서는 기존 Job이 삭제되고 새 Job이 생성됩니다.

### 참조
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Running Automated Tasks with a CronJob](https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/)
