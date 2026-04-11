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

**Pod란?** Kubernetes에서 서비스를 실제로 돌리는 최소 실행 단위다. 우리가 "이 앱을 Kubernetes에 띄운다"고 할 때, 실제로 뜨는 것은 Pod 안의 컨테이너다. 앞으로 나올 ReplicaSet, Deployment 같은 Controller들은 전부 이 Pod를 어떻게 관리할지 결정하는 오브젝트이므로, Pod의 기본 성질을 먼저 이해해야 한다.

### 1. Container — "Pod는 컨테이너를 담는 상자"

Pod 안에는 독립적인 서비스를 구동하는 **컨테이너가 한 개 이상** 들어간다. 한 Pod에 여러 컨테이너를 넣을 수도 있으며, 이때 몇 가지 규칙이 있다.

- **포트는 중복될 수 없다.** 한 컨테이너가 여러 포트를 노출할 수는 있지만, 같은 Pod 안의 다른 컨테이너와 포트가 겹쳐서는 안 된다.
- **같은 Pod의 컨테이너는 하나의 호스트로 묶인다.** 이 때문에 Pod 내부에서는 컨테이너끼리 `localhost:포트`로 서로 접근할 수 있다. 옆방에 있는 컨테이너를 바로 옆집 부르듯 호출할 수 있다는 뜻이다.
- **Pod에는 고유 IP가 할당된다.** 이 IP는 **Kubernetes 클러스터 내부에서만** 사용할 수 있고, 외부에서는 이 IP로 바로 접근할 수 없다. 외부 접근은 Service 오브젝트를 통해 이뤄진다.
- **Pod IP는 휘발성이다.** Pod에 문제가 생기면 시스템이 자동으로 Pod를 삭제하고 재생성하는데, 이때 **새 IP가 할당**된다. 즉 "이 Pod는 10.1.2.3이다"라고 외워놓고 쓰면 안 된다. 이게 바로 Service가 필요한 이유다.

#### YAML 예제 — 한 Pod에 두 컨테이너 담기

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-1
spec:
  containers:
  - name: container1
    image: kubetm/p8000
    ports:
    - containerPort: 8000
  - name: container2
    image: kubetm/p8080
    ports:
    - containerPort: 8080
```

### 2. Label — "해시태그로 Pod 분류하기"

Label은 Pod뿐 아니라 모든 Kubernetes 오브젝트에 붙일 수 있는 **키-값 쌍**이다. 가장 많이 쓰이는 곳이 Pod이고, 이를 쓰는 목적은 명확하다. **오브젝트를 목적별로 분류**하고, 분류된 오브젝트 중 원하는 것만 **다른 오브젝트와 연결**하기 위해서다.

SNS의 해시태그를 떠올리면 이해가 쉽다. 해시태그를 잘 붙여두면 나중에 원하는 게시물만 검색해서 볼 수 있듯이, Label을 잘 붙여두면 Service나 Controller가 "이 조건에 맞는 Pod들"만 골라서 관리할 수 있다.

- 하나의 Pod에 **여러 Label**을 동시에 달 수 있다. 예: `app=web`, `env=prod`, `version=v2`
- Service가 Pod를 찾을 때는 `selector`에 Label의 키-값을 적는다. 해당 Label을 가진 Pod들이 자동으로 Service에 연결된다.

#### YAML 예제 — Label과 Selector의 연결

```yaml
# Pod: 두 개의 Label 부착
apiVersion: v1
kind: Pod
metadata:
  name: pod-2
  labels:
    type: web
    lo: dev
spec:
  containers:
  - name: container
    image: kubetm/app
---
# Service: selector로 같은 Label을 가진 Pod 연결
apiVersion: v1
kind: Service
metadata:
  name: svc-1
spec:
  selector:
    type: web
    lo: dev
  ports:
  - port: 8080
```

### 3. NodeSchedule — "이 Pod를 어느 Node에 올릴까?"

Pod는 결국 어떤 Node(물리/가상 머신) 하나에 올라가 실행되어야 한다. "어느 Node에 올릴지"를 정하는 방법은 두 가지다.

#### 방법 1: 직접 선택 — `nodeSelector`

Node에도 Label을 붙일 수 있다. Pod를 만들 때 `nodeSelector`에 해당 Label을 지정하면 그 Label이 붙은 Node에만 Pod가 올라간다. 특정 하드웨어(SSD, GPU 등)가 있는 Node에만 Pod를 배치하고 싶을 때 유용하다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-3
spec:
  nodeSelector:
    hostname: node1
  containers:
  - name: container
    image: kubetm/app
```

#### 방법 2: Scheduler 자동 배치 — `resources.requests` / `resources.limits`

Pod를 만들 때 Node를 직접 지정하지 않으면, Kubernetes의 **Scheduler**가 현재 각 Node의 자원 상황을 보고 적절한 Node에 자동으로 배치한다. 이때 Pod가 "나는 이 정도 자원이 필요하다"고 선언해 두면 Scheduler가 그 요구사항을 만족하는 Node를 골라준다.

예를 들어 Node1에 남은 메모리가 1GB, Node2에 3.7GB가 남아 있고, Pod가 "메모리 2GB 필요"라고 선언했다면, Scheduler는 자동으로 Node2로 Pod를 보낸다.

#### requests vs limits — 꼭 구분해서 알기

| 항목 | 의미 |
|---|---|
| **requests** | Pod가 **요청**하는 최소 자원량. Scheduler가 Node를 고를 때 기준으로 삼는 값. |
| **limits** | Pod가 사용할 수 있는 **최대** 자원량. 이 선을 넘으면 제재가 가해진다. |

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-4
spec:
  containers:
  - name: container
    image: kubetm/app
    resources:
      requests:
        memory: 2Gi
      limits:
        memory: 3Gi
```

#### limits를 안 넣으면 무슨 일이 생기나?

`limits`를 지정하지 않으면, Pod 안의 앱이 부하 상황에서 Node의 자원을 **무제한으로** 가져가려 한다. 그 결과 같은 Node에 있던 다른 Pod들이 자원을 뺏겨 **다 같이 죽는 참사**가 발생할 수 있다. 실무에서는 한 Pod의 문제가 다른 Pod로 전염되지 않도록 반드시 limits를 설정한다.

#### Memory limit과 CPU limit의 동작 차이 — 자원의 성격 때문

메모리와 CPU는 limit을 넘었을 때 Kubernetes의 대응이 다르다.

- **Memory가 limit을 초과**: Pod를 **즉시 종료**시킨다. (OOMKilled)
- **CPU가 limit을 초과**: Pod를 종료시키지 않고 **속도만 느려지게** 한다(Throttling).

왜 다를까? 자원의 성격 때문이다. CPU는 여러 프로세스가 나눠 써도 서로 망가뜨리지 않고 단지 느려질 뿐이다. 파일 두 개를 동시에 복사하면 둘 다 조금 느려지는 정도다. 반면 메모리는 다르다. 두 번째 프로세스가 첫 번째 프로세스가 쓰던 메모리 영역을 침범하면 "잘못된 메모리 참조"로 프로세스가 터져 버리는 치명적 상황이 된다. 그래서 메모리는 한계를 넘는 순간 강제 종료하여 시스템을 보호한다.

> **Pod는 할 얘기가 정말 많지만 초급편에서는 여기까지**다. 위 세 가지(Container, Label, NodeSchedule)만 탄탄히 잡고 있으면 뒤에 나올 Controller들을 이해하는 데 무리가 없다.

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

**Service가 왜 필요한가?** Pod 자체에도 클러스터 내부 IP가 할당된다. 그런데 우리는 Pod IP로 직접 접근하지 않고, 굳이 그 앞에 Service를 하나 더 두고 Service의 IP로 접근한다. 이유는 하나다.

**Pod는 언제든 죽고 다시 태어날 수 있는 일회용 존재**다. 시스템 장애, 성능 문제, 업그레이드 등 여러 이유로 Pod가 재생성되면 **IP가 바뀐다.** 이 휘발성 때문에 "Pod IP 10.1.2.3으로 접근하세요"라고 알려주면 금방 무용지물이 된다. 반면 Service는 사용자가 직접 삭제하지 않는 한 사라지지 않고 IP도 고정된다. 그래서 **Service IP를 통해 접근하면 그 뒤에 붙은 Pod가 무엇이든 항상 닿을 수 있다.**

또 하나의 이점은 Service 뒤에 **여러 Pod를 붙이면 자동으로 트래픽을 분산**해 준다는 점이다. Load Balancer 역할까지 자체적으로 한다.

### 3가지 Service 타입 한눈에 비교

| 타입 | 접근 범위 | 용도 |
|---|---|---|
| **ClusterIP** (기본값) | 클러스터 내부만 | 내부 통신, 대시보드 관리, 디버깅 |
| **NodePort** | 클러스터 내부 + Node IP로 외부 | 내부망 접근, 임시 데모, 데몬셋과의 조합 |
| **LoadBalancer** | 외부 공인 IP | 실제 외부 서비스 노출 (운영 환경) |

> 기억할 점: NodePort는 ClusterIP의 기능을 포함하고, LoadBalancer는 NodePort의 기능을 포함하는 **누적 구조**다.

### 1. ClusterIP — "클러스터 내부 전용 기본형"

Service 타입을 명시하지 않으면 기본으로 설정되는 타입이다. Pod와 동일하게 클러스터 내부에서만 유효한 IP가 할당되며, 외부 네트워크에서는 이 IP로 접근할 수 없다.

- **언제 쓰나?** 외부에 노출될 필요가 없는 모든 내부 통신, Kubernetes 대시보드 접근, 특정 Pod의 상태를 디버깅할 때. 외부에서 접근이 불가능하니 자연스럽게 "클러스터 내부 접근 권한을 가진 운영자"만 쓸 수 있다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-clusterip
spec:
  selector:
    app: pod
  ports:
  - port: 9000        # Service의 포트
    targetPort: 8080  # 연결될 Pod의 포트
  # type: ClusterIP   # 생략 가능 (기본값)
```

### 2. NodePort — "모든 Node에 문을 뚫기"

NodePort 타입으로 만들면 클러스터에 속한 **모든 Node의 같은 포트**가 열리고, 어느 Node의 IP로든 그 포트에 접속하면 Service에 연결된다. **주의할 점은 "Pod가 올라가 있는 Node에만" 포트가 열리는 게 아니라는 것.** Pod가 한 Node에만 있어도 모든 Node가 그 포트를 열어 두며, 어느 Node로 들어온 트래픽이든 Service가 알아서 적절한 Pod로 전달한다.

- **포트 범위**: 30000~32767. 이 범위 내에서만 지정 가능하며, 생략하면 자동 할당된다.
- **externalTrafficPolicy: Local**: 이 옵션을 주면 동작이 달라진다. 특정 Node IP로 들어온 트래픽은 **그 Node에 올라가 있는 Pod에게만** 전달된다. 다른 Node의 Pod로 넘어가지 않는다. DaemonSet과 조합할 때 유용하다.
- **언제 쓰나?** 내부망 안에서 외부에 잠시 노출해야 할 때, 네트워크 중계기에 포트 포워딩으로 임시 데모를 보여줄 때.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-nodeport
spec:
  selector:
    app: pod
  ports:
  - port: 9000
    targetPort: 8080
    nodePort: 30000   # 30000~32767 범위
  type: NodePort
```

### 3. LoadBalancer — "외부 공인 IP로 노출"

NodePort의 기능을 포함하면서 추가로 **외부 Load Balancer**를 앞에 둔다. 이 Load Balancer가 공인 IP를 받아 외부 트래픽을 각 Node로 분산해준다.

- **주의**: 로컬에서 직접 Kubernetes를 설치했을 때는 외부 IP가 자동으로 생기지 **않는다.** 별도 플러그인(MetalLB 등)이 필요하다. 반면 **GCP, AWS, Azure 등 클라우드 Kubernetes 플랫폼**에서는 플러그인이 이미 준비되어 있어 LoadBalancer 타입을 만들면 자동으로 외부 IP가 할당된다.
- **언제 쓰나?** 실제 운영 환경에서 외부에 서비스를 노출할 때. 내부 IP가 노출되지 않으면서도 안정적인 엔드포인트를 제공한다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-loadbalancer
spec:
  selector:
    app: pod
  ports:
  - port: 9000
    targetPort: 8080
  type: LoadBalancer
```

### 사용 케이스 정리 — "상황별로 어떤 타입을 골라야 하나"

- **ClusterIP**: 내부 디버깅, 대시보드, Pod 간 내부 통신. 외부 사용자는 모르는 게 맞는 서비스.
- **NodePort**: 내부망 제한 환경이지만 외부에서 들어와야 할 때, 혹은 일시적인 데모/테스트 용도.
- **LoadBalancer**: 운영 환경에서 실제로 외부에 서비스를 공개할 때. 클라우드 환경에서 가장 많이 쓰인다.

---

## Volume - emptyDir, hostPath, PV/PVC

**Volume이 왜 필요한가?** Pod는 언제든 죽고 재생성될 수 있는 일회용 존재다. Pod 안에 데이터를 저장해 두면 Pod가 사라지는 순간 데이터도 함께 사라진다. 이 문제를 해결하기 위해 Kubernetes는 다양한 **Volume** 타입을 제공한다. 각 타입은 "데이터가 얼마나 오래 살아남아야 하는가"와 "누가 접근할 수 있는가"에 따라 구분된다.

### 3가지 Volume 타입 한눈에 비교

| 타입 | 생명 주기 | 공유 범위 | 용도 |
|---|---|---|---|
| **emptyDir** | Pod와 함께 생성/소멸 | 같은 Pod 안의 컨테이너끼리 | 임시 데이터 공유 |
| **hostPath** | Node가 살아있는 동안 | 해당 Node 위의 Pod | Node 시스템 파일 접근 |
| **PV/PVC** | Pod와 무관하게 영구 | 정의에 따라 다름 | 영속적 저장, 운영 환경 |

### 1. emptyDir — "같은 Pod 안 컨테이너들끼리 임시 공유"

**이름 그대로** 최초 생성 시 볼륨 안이 **비어 있기(empty)** 때문에 emptyDir이라 부른다. 이 볼륨은 Pod 안에 만들어지므로 **Pod가 죽으면 데이터도 함께 사라진다.** 따라서 "일시적으로 쓰는 데이터"만 넣어야 한다.

주 용도는 같은 Pod 안의 **여러 컨테이너끼리 데이터를 주고받는 것**이다. 예를 들어 한 컨테이너가 파일을 생성하고, 다른 컨테이너가 그 파일을 읽는 구조.

#### YAML 예제 — 두 컨테이너가 같은 emptyDir을 다른 경로로 마운트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-emptydir
spec:
  containers:
  - name: container1
    image: kubetm/init
    volumeMounts:
    - name: empty-dir
      mountPath: /mount1
  - name: container2
    image: kubetm/init
    volumeMounts:
    - name: empty-dir
      mountPath: /mount2
  volumes:
  - name: empty-dir
    emptyDir: {}
```

> container1은 `/mount1`, container2는 `/mount2`로 경로가 다르지만, **둘 다 같은 `empty-dir` 볼륨을 가리킨다.** 각 컨테이너는 원하는 경로로 접근할 수 있지만 실제 저장소는 동일하다.

### 2. hostPath — "Node의 실제 경로를 Pod에 마운트"

Pod가 올라가 있는 **Node의 파일 시스템 경로**를 Pod에 연결한다. emptyDir과 달리 Pod가 죽어도 Node에 있는 데이터는 남는다.

#### 치명적인 함정 — Node가 바뀌면 데이터에 접근할 수 없다

hostPath는 좋아 보이지만 큰 문제가 있다. **Pod가 재생성될 때 같은 Node에 다시 올라간다는 보장이 없다.** Scheduler가 자원 상황을 보고 다른 Node에 배치하거나, 원래 Node에 장애가 생겨서 다른 Node로 옮겨질 수 있다. 그 순간 **새 Node에는 그 경로가 없어서** Pod는 자기 데이터에 접근할 수 없게 된다.

**"방법은 있지만 추천하지 않는다"**: 운영자가 새 Node가 추가될 때마다 같은 경로를 만들고 직접 NFS 등으로 Node 간 마운트를 연결할 수는 있다. 하지만 사람의 개입이 들어가는 순간 실수 여지가 생기므로 권장되지 않는다.

- **실제 용도**: 데이터 저장이 아니라 **Node의 시스템 파일이나 로그**에 접근해야 할 때 (예: DaemonSet이 Node 로그를 수집).
- **주의**: hostPath로 지정한 경로는 Pod 생성 **이전에 Node에 미리 존재**해야 한다. 없으면 Pod 생성 시 에러가 난다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-hostpath
spec:
  containers:
  - name: container
    image: kubetm/init
    volumeMounts:
    - name: host-path
      mountPath: /mount1
  volumes:
  - name: host-path
    hostPath:
      path: /node-v
      type: DirectoryOrCreate
```

### 3. PV / PVC — "영속성 있는 진짜 저장소"

운영 환경에서는 Pod가 죽든 살든, Node가 바뀌든 말든 데이터가 **영속적으로 유지**되어야 한다. 이를 위해 Kubernetes는 **PersistentVolume(PV)**과 **PersistentVolumeClaim(PVC)** 이라는 두 단계 개념을 도입했다.

#### 왜 두 단계로 나눴나? — 관리자와 사용자의 역할 분리

Pod가 PV에 바로 연결되면 간단할 텐데, 왜 굳이 PVC를 사이에 두는가? **Kubernetes는 볼륨 사용 영역을 "Admin 영역"과 "User 영역"으로 나누었기 때문**이다.

- **Admin (클러스터 운영자)**: 실제 볼륨(AWS EBS, NFS, GlusterFS, StorageOS 등)을 PV로 정의한다. 볼륨 종류마다 연결 방법이 다 달라서 **전문 지식이 필요**하다.
- **User (서비스 개발자)**: 볼륨의 내부 구조는 몰라도 된다. "1GB 정도, 읽기/쓰기 가능한 볼륨이 필요하다"는 **요구사항만 PVC로 선언**한다.

쿠버네티스가 PVC의 요구사항을 보고 적합한 PV를 자동으로 매칭해 준다. 마지막으로 Pod는 PVC 이름만 참조하면 그 뒤에 연결된 PV를 쓸 수 있다.

```
Admin이 PV 생성
    ↓
User가 PVC 생성 (요구사항 선언)
    ↓
Kubernetes가 PVC와 PV를 자동 매칭
    ↓
Pod가 PVC를 참조하여 볼륨 사용
```

#### PV YAML 예제 (Local 볼륨 — 학습용)

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-01
spec:
  capacity:
    storage: 1G
  accessModes:
  - ReadWriteOnce
  local:
    path: /node-v
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - {key: kubernetes.io/hostname, operator: In, values: [k8s-node1]}
```

> **참고**: Local 타입 PV는 실제 현장에서는 잘 쓰지 않는다. 이 PV에 연결된 Pod는 반드시 `k8s-node1` Node 위에만 만들어진다. 학습 목적으로만 사용한다.

#### PVC YAML 예제

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-01
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1G
  storageClassName: ""
```

> `storageClassName: ""`(빈 문자열)은 "현재 만들어져 있는 PV 중에서 매칭해달라"는 의미. 생략하면 다른 동작(Dynamic Provisioning)이 발생하므로 주의. StorageClass는 중급편에서 자세히 다룬다.

#### Pod에서 PVC 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-pvc
spec:
  containers:
  - name: container
    image: kubetm/init
    volumeMounts:
    - name: pvc-pv
      mountPath: /mount3
  volumes:
  - name: pvc-pv
    persistentVolumeClaim:
      claimName: pvc-01
```

#### PV와 PVC는 어떻게 매칭되나?

Kubernetes는 **PVC의 `accessModes`와 `requests.storage`**를 보고 이를 만족하는 PV를 자동으로 연결한다. PV의 `capacity`와 `accessModes`가 PVC의 요구치보다 크거나 같으면 매칭 후보가 된다.

---

## ConfigMap, Secret - Env, Mount

**왜 필요한가? — 실전 사례로 이해하기**

서비스 A가 있다고 하자. 이 서비스는 개발 환경에서는 "보안 접근 해제" 모드로 쓰고, 상용 환경에서는 "보안 접근 + 인증 키" 모드로 써야 한다. 즉 **환경에 따라 달라져야 하는 설정값**이 있다.

만약 이 값들이 컨테이너 이미지 안에 하드코딩되어 있다면 어떻게 될까? 개발/상용 **환경마다 별도의 이미지**를 빌드해서 관리해야 한다. 설정 몇 개 때문에 수백 MB짜리 이미지를 여러 벌 관리하는 것은 부담이 크고 실수 여지도 많다.

해결책은 **환경에 따라 변하는 값들을 이미지 바깥으로 빼내는 것**이다. 이걸 도와주는 게 ConfigMap과 Secret이다.

- **ConfigMap**: 환경에 따라 달라지는 **일반 상수**를 모아둠 (URL, 모드 플래그, 버전 번호 등)
- **Secret**: 민감한 값(패스워드, 인증 키, 토큰 등)을 모아둠

이 두 오브젝트를 Pod에 연결하면 데이터가 컨테이너의 **환경 변수로 주입**되거나 **파일로 마운트**된다. 서비스 코드는 환경 변수나 파일을 읽기만 하면 되고, **이미지는 하나만 관리**하면서 ConfigMap/Secret 값만 바꿔 개발/상용을 오갈 수 있다.

### ConfigMap vs Secret — 차이점

| 항목 | ConfigMap | Secret |
|---|---|---|
| 용도 | 일반 설정값 | 민감 정보 (패스워드, 키) |
| 값 저장 형식 | 평문(plain text) | Base64 인코딩 |
| 저장 위치 | Kubernetes DB (etcd) | **메모리** |
| 크기 제한 | 상대적으로 제약 덜함 | 1MB |

> **Secret의 Base64는 "암호화"가 아니다.** Pod로 주입될 때 자동 디코딩되어 환경 변수에는 원래 값이 그대로 들어간다. Base64는 단지 Secret의 값 작성 규칙일 뿐이다.
>
> **Secret의 진짜 보안 요소**는 메모리에 저장된다는 점이다. 파일(etcd DB)에 저장되는 것보다 메모리에 있는 편이 외부 유출 위험이 낮다. 다만 메모리를 쓰므로 Secret을 남발하면 시스템 자원에 영향을 줄 수 있다.

### 3가지 주입 방식

ConfigMap/Secret의 데이터를 Pod에 넣는 방법은 세 가지다.

1. **상수 → 환경 변수**: 가장 기본. 키-값을 정의하고 Pod의 환경 변수로 주입.
2. **파일 → 환경 변수**: 파일 전체를 값으로 쓰는 특이 방식. 파일 이름이 키, 파일 내용이 값이 된다.
3. **파일 → 볼륨 마운트**: 파일을 Pod 내부 경로에 마운트. **이 방식만 변경 시 자동 반영된다.**

### 방식 1: 상수를 환경 변수로 주입

#### ConfigMap / Secret YAML

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm-dev
data:
  SSH: "false"
  User: dev
---
apiVersion: v1
kind: Secret
metadata:
  name: sec-dev
data:
  Key: MTIzNA==  # "1234"를 base64 인코딩
```

#### Pod에서 `envFrom`으로 통째로 주입

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-1
spec:
  containers:
  - name: container
    image: kubetm/init
    envFrom:
    - configMapRef:
        name: cm-dev
    - secretRef:
        name: sec-dev
```

### 방식 2: 파일을 환경 변수에 담기

파일을 통째로 ConfigMap에 넣으면 **파일 이름이 Key, 파일 내용이 Value**가 된다. 이 Key의 값을 환경 변수로 가져와 쓰는 방식이다.

#### 파일로 ConfigMap/Secret 만들기 (kubectl 명령)

대시보드에서는 지원되지 않으므로 마스터 콘솔에서 직접 실행해야 한다.

```bash
# ConfigMap
kubectl create configmap cm-file --from-file=./file.txt

# Secret (주의: 파일 내용이 자동으로 base64 인코딩됨)
kubectl create secret generic sec-file --from-file=./file.txt
```

> **Secret 주의**: 위 명령은 파일 내용을 자동으로 base64로 인코딩한다. 만약 파일 내용이 이미 base64로 인코딩된 상태라면 **두 번 인코딩**되니 주의.

#### Pod에서 해당 Key 값을 환경 변수로 읽기

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-2
spec:
  containers:
  - name: container
    image: kubetm/init
    env:
    - name: file
      valueFrom:
        configMapKeyRef:
          name: cm-file
          key: file.txt
```

### 방식 3: 파일을 볼륨으로 마운트

ConfigMap을 통째로 볼륨으로 만들어 Pod 안의 특정 경로에 마운트한다. 가장 자주 쓰는 방식 중 하나.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-3
spec:
  containers:
  - name: container
    image: kubetm/init
    volumeMounts:
    - name: file-volume
      mountPath: /mount
  volumes:
  - name: file-volume
    configMap:
      name: cm-file
```

### 환경 변수 vs 볼륨 마운트 — 숨은 차이점 (매우 중요)

이 두 방식에는 **큰 차이**가 하나 숨어 있다. **ConfigMap/Secret의 값을 수정했을 때 Pod에 반영되는 방식**이 다르다.

| 방식 | 원본(ConfigMap) 변경 시 |
|---|---|
| **환경 변수 주입** (방식 1, 2) | Pod 환경 변수에는 **반영 안 됨**. Pod를 재생성해야 새 값이 적용됨. |
| **볼륨 마운트** (방식 3) | Pod 안에 마운트된 파일 내용이 **자동으로 업데이트**됨. 재시작 불필요. |

**원리**: 환경 변수는 Pod 생성 시 한 번 "주입"되고 끝이다. 그 후 ConfigMap이 바뀌어도 이미 주입된 환경 변수는 바뀌지 않는다. 반면 마운트는 "원본과의 연결"을 유지하는 개념이라, 원본이 바뀌면 마운트된 파일도 함께 바뀐다.

> **발표 포인트**: "런타임에 설정을 동적으로 바꿔야 한다면 볼륨 마운트, 한 번 설정하고 변하지 않을 값이면 환경 변수" 식으로 상황에 맞게 선택한다.

---

## Namespace, ResourceQuota, LimitRange

**왜 필요한가? — 전체 그림부터**

Kubernetes 클러스터에는 전체 사용 가능한 메모리와 CPU가 있다. 이 안에 여러 Namespace가 있고, 각 Namespace 안에 여러 Pod가 뜬다. Pod들은 클러스터의 자원을 **공유**해서 쓴다.

여기서 문제가 시작된다.

1. **한 Namespace의 Pod가 클러스터의 남은 자원을 전부 빨아먹어 버리면?** 다른 Namespace의 Pod는 자원이 없어서 뜨지 못하거나 죽을 수 있다.
2. **한 Pod가 너무 큰 자원을 요구해서 Namespace에 들어오면?** 그 Namespace 안에 다른 Pod들이 더 이상 들어올 자리가 없어진다.

이 두 가지 문제를 해결하기 위해 **ResourceQuota**(Namespace 전체 한도)와 **LimitRange**(개별 Pod 한도)가 존재한다. Namespace는 이 두 오브젝트를 붙일 수 있는 **논리적 분리 단위**다.

### 세 오브젝트의 역할 비교

| 오브젝트 | 제한 대상 | 목적 |
|---|---|---|
| **Namespace** | — | 자원을 논리적으로 분리하는 단위 |
| **ResourceQuota** | Namespace 전체의 자원 합계 | 한 Namespace가 클러스터를 독식하지 못하게 |
| **LimitRange** | Namespace에 들어오는 개별 Pod의 자원 | 거대한 Pod 하나가 Namespace를 독차지하지 못하게 |

> ResourceQuota와 LimitRange는 Namespace뿐 아니라 **클러스터 전체**에도 붙일 수 있다.

---

### 1. Namespace — "자원을 논리적으로 격리"

Namespace는 하나의 Kubernetes 클러스터 안에서 자원을 **논리적으로 분리**하는 단위다. 환경별(dev/staging/prod)이나 팀별로 나눠 쓸 때 유용하다.

#### Namespace의 특징

1. **같은 타입의 오브젝트는 한 Namespace 안에서 이름 중복 불가.** 예: 한 Namespace에 `pod-1`이라는 Pod가 둘일 수 없다. 오브젝트마다 내부적으로 UUID가 있지만, **한 Namespace 안에서는 "이름"이 사실상 유일 키 역할**을 한다.
2. **다른 Namespace의 자원과 분리된다.** 예를 들어 A Namespace의 Pod와 B Namespace의 Service는 Label과 Selector가 일치해도 **서로 연결되지 않는다.** Namespace가 다르기 때문이다. 지금까지 배운 대부분의 오브젝트는 자기가 속한 Namespace 안에서만 작동한다.
3. **일부 오브젝트는 Namespace에 속하지 않는다.** Node, PersistentVolume 같이 클러스터 전체에서 공용으로 쓰이는 오브젝트는 Namespace 개념 바깥에 있다.
4. **Namespace를 삭제하면 그 안의 모든 자원이 함께 삭제된다.** 지울 때 매우 주의해야 한다.
5. **Pod IP로의 직접 접근은 가능**. 다만 **NetworkPolicy** 오브젝트로 제한할 수 있다.

#### YAML 예제 — Namespace 생성과 사용

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nm-1
---
apiVersion: v1
kind: Pod
metadata:
  name: pod-1
  namespace: nm-1   # 이 Namespace에 속함
  labels:
    app: pod
spec:
  containers:
  - name: container
    image: kubetm/app
---
apiVersion: v1
kind: Service
metadata:
  name: svc-1
  namespace: nm-2   # 다른 Namespace
spec:
  selector:
    app: pod       # Label은 일치하지만
  ports:
  - port: 9000
    targetPort: 8080
# → Pod와 Service의 Namespace가 달라서 연결되지 않음
```

---

### 2. ResourceQuota — "Namespace 총량 제한"

ResourceQuota는 해당 Namespace 안에 들어올 수 있는 **모든 Pod의 자원 합계**에 한계를 건다.

#### 주요 제약 항목

- **메모리/CPU**: `requests.memory`, `limits.memory`, `requests.cpu`, `limits.cpu`
- **Storage**: PVC의 용량 합계
- **오브젝트 수**: Pod, Service, ConfigMap 등의 개수

> **버전별 주의**: 제한 가능한 오브젝트 종류는 Kubernetes 버전이 올라가면서 계속 늘어난다. 사용 전 현재 버전에서 어떤 오브젝트까지 제한 가능한지 확인해야 한다.

#### 중요한 규칙 — "ResourceQuota가 있는 Namespace에 Pod를 만들 때는 반드시 resources 스펙을 명시해야 한다"

ResourceQuota가 걸린 Namespace에 들어가는 Pod는 **반드시 자신의 `resources.requests`와 `resources.limits`를 명시**해야 한다. 스펙이 없는 Pod는 애초에 Namespace에 들어오지 못한다.

#### 동작 예시

- ResourceQuota가 메모리 limits **6GB**로 설정됨.
- 이미 2GB를 쓰는 Pod가 들어와 있음 → 남은 한도 4GB.
- 새로 들어오려는 Pod가 limit 메모리 **5GB**를 요구 → **거절됨**. 한도 초과.

#### YAML 예제

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: rq-1
  namespace: nm-3
spec:
  hard:
    requests.memory: 3Gi
    limits.memory: 6Gi
```

---

### 3. LimitRange — "개별 Pod 크기 제한"

LimitRange는 Namespace에 들어오려는 **각 Pod의 자원 크기**를 검사한다. "이 Pod는 들어와도 돼" 또는 "너무 크니까 안 돼"를 판단한다.

#### 주요 제약 항목

| 항목 | 의미 |
|---|---|
| **min** | Pod의 limit이 이 값보다 **작으면 거절** (너무 작아도 안 됨) |
| **max** | Pod의 limit이 이 값을 **초과하면 거절** (너무 커도 안 됨) |
| **maxLimitRequestRatio** | `limit / request` 비율이 이 값을 초과하면 거절 |
| **defaultRequest** | Pod가 `requests`를 명시하지 않았을 때 자동 할당될 기본값 |
| **default** | Pod가 `limits`를 명시하지 않았을 때 자동 할당될 기본값 |

#### 동작 예시 (min=1Gi, max=4Gi, maxLimitRequestRatio=3)

- **Pod1**: limits 메모리 5Gi → **거절** (max 4Gi 초과)
- **Pod2**: requests 1Gi, limits 4Gi → **거절** (비율 4배, max 3배 초과)
- **Pod3**: requests 2Gi, limits 4Gi → **허용** (비율 2배)

#### maxLimitRequestRatio가 왜 있나?

requests는 "나는 최소 이 정도 자원이 필요해"의 의미이고, limits는 "최대 이 정도까지는 쓸 수 있어"의 의미다. 이 둘의 비율이 너무 벌어지면 "평소에는 거의 안 쓰면서 한 번씩 폭발적으로 자원을 쓰는" Pod가 되어 Node 자원 예측을 어렵게 만든다. 비율을 강제하면 이런 **burst 패턴을 막고 자원 예측 가능성**을 높일 수 있다.

#### YAML 예제

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: lr-1
  namespace: nm-3
spec:
  limits:
  - type: Container
    min:
      memory: 1Gi
    max:
      memory: 4Gi
    maxLimitRequestRatio:
      memory: 3
    default:
      memory: 2Gi
    defaultRequest:
      memory: 1Gi
```

> `type`으로는 `Container`, `Pod`, `PersistentVolumeClaim` 등이 있으며, 각 타입마다 지원되는 옵션이 다르다.

---

## Controller 개요

**Controller란?** Pod를 혼자 띄워두면 문제가 생겼을 때 아무도 복구해 주지 않는다. Controller는 "원하는 상태(desired state)"를 선언해 두면 현재 상태가 여기서 벗어났을 때 자동으로 맞춰주는 관리자 역할을 한다. Kubernetes 운영의 핵심을 담당하며, 대표적으로 네 가지 기능을 제공한다.

1. **Auto Healing**: Node 위에 있던 Pod가 죽거나, 해당 Node 자체가 죽으면 Controller가 이를 감지해 다른 Node에 Pod를 새로 만들어 준다. 사람이 밤중에 서버 장애를 쫓아다니지 않아도 서비스가 유지된다.
2. **Auto Scaling**: Pod의 리소스가 한계에 도달하면 Controller가 Pod를 추가 생성해 부하를 분산한다. 기존 Pod가 터지지 않도록 보호하는 역할.
3. **Rolling Upgrade / Rollback**: 여러 Pod의 버전을 한 번에 교체할 수 있고, 도중에 문제가 생기면 이전 버전으로 되돌릴 수 있다.
4. **Job 관리**: 일회성 작업이 필요할 때 그 순간에만 Pod를 띄워 작업을 수행하고, 끝나면 자원을 반환한다.

> 이 기능들을 담당하는 여러 Kubernetes 오브젝트가 존재하며, 이번 챕터에서는 **ReplicaSet, Deployment, DaemonSet, Job, CronJob**을 순서대로 살펴본다.

---

## ReplicaSet - Template, Replicas, Selector

**ReplicaSet이란?** "이 Pod를 항상 N개 띄워 두세요"를 보장해주는 Controller다. Replication Controller라는 전신이 있었으나 현재는 deprecated 되었고, 그 기능을 그대로 포함하면서 더 유연한 Selector를 지원하는 ReplicaSet이 표준이 되었다. ReplicaSet과 Pod는 Service와 Pod처럼 **Label - Selector**로 연결된다.

### 1. Template — "Pod 설계 도면"

Template은 ReplicaSet이 Pod를 새로 만들 때 참고하는 설계도다. 컨테이너 이미지, 포트, 라벨 등 Pod의 모든 스펙이 여기에 들어간다.

- **재생성 로직**: Pod가 다운되면 ReplicaSet은 항상 Template을 보고 새 Pod를 찍어낸다. 즉 "현재 돌고 있는 Pod"가 아니라 "Template의 내용"이 기준이다.
- **수동 업그레이드 트릭**: 이 성질을 이용하면 업그레이드가 가능하다. Template의 이미지를 v1 → v2로 바꾸고 기존 v1 Pod를 삭제하면, ReplicaSet은 Template(v2)을 참고해 v2 Pod를 만들어준다. (실무에서는 Deployment가 이 과정을 자동으로 해준다.)
- **Pod 이름 규칙**: Template에 `name`을 적어도 무시된다. ReplicaSet이 자기 이름 뒤에 해시 문자열을 붙여 자동으로 이름을 만들어 준다. 같은 Namespace에서 Pod 이름이 중복될 수 없기 때문이다.

### 2. Replicas — "몇 개 띄워 둘지"

유지할 Pod의 개수를 지정한다. 동작 방식은 단순하다.

- `replicas: 3`으로 설정하면 항상 3개의 Pod가 떠 있도록 유지한다.
- 누가 Pod를 삭제하거나 장애가 나서 개수가 2로 줄면, 즉시 1개를 재생성한다.
- 실행 중에 1 → 3으로 바꾸면 **Scale Out**(수평 확장), 3 → 1로 바꾸면 **Scale In**(축소)이 된다.
- 팁: 실제 현장에서는 Pod를 따로 만들지 않고, ReplicaSet의 Template과 Replicas만 정의해서 한 번에 Pod를 찍어내는 방식으로 쓴다.

### 3. Selector — "내가 관리할 Pod 고르기"

ReplicaSet이 "어떤 Label을 가진 Pod를 내 관리 대상으로 삼을지" 정하는 필터다. Replication Controller는 키-값이 완전히 일치해야 했지만, ReplicaSet은 두 가지 방식을 제공한다.

#### matchLabels — 정확 매칭

가장 자주 쓰는 방식. 지정한 키-값이 모두 같은 Pod만 연결한다. Replication Controller와 동일한 동작.

```yaml
selector:
  matchLabels:
    type: web
```

#### matchExpressions — 조건식 매칭

Operator로 더 세밀하게 고를 수 있다. 네 가지 Operator를 지원한다.

| Operator | 의미 | 예시 |
|---|---|---|
| `Exists` | 해당 키가 존재하는 모든 Pod (값은 무관) | 키가 `ver`인 Pod 모두 |
| `DoesNotExist` | 해당 키가 없는 Pod | 키에 `ver`가 없는 Pod |
| `In` | 값이 목록에 포함된 Pod | `ver`의 값이 `v2` 또는 `v3` |
| `NotIn` | 값이 목록에 포함되지 않은 Pod | `ver`의 값이 `v2`, `v3`가 아닌 것 |

```yaml
selector:
  matchLabels:
    type: web
  matchExpressions:
  - {key: ver, operator: Exists}
```

### Selector 사용 시 두 가지 주의사항

1. **Selector 조건은 반드시 Template Label에 포함되어야 한다.** 예를 들어 Selector가 `type=web, ver=v3`인데 Template Label이 `type=web`만 있다면, ReplicaSet 생성 시 "Selector와 Template Label이 매치되지 않는다"는 에러가 난다. ReplicaSet이 방금 찍어낸 Pod가 자기 관리 대상이 아닌 꼴이 되는 것을 막기 위함이다.
2. **`matchLabels`와 `matchExpressions`는 동시에 사용할 수 있고, 모든 조건이 AND로 결합된다.** 따라서 어떤 조건이든 Template Label에 전부 포함되어야 한다.

### 실무 팁

- **`matchExpressions`는 ReplicaSet 자체에서는 잘 안 쓴다.** ReplicaSet은 "내가 찍어낸 Pod를 관리"하는 용도라 조건이 단순해 `matchLabels`로 충분하다.
- `matchExpressions`의 진가는 **이미 존재하는 여러 오브젝트 중에서 원하는 것만 골라야 할 때** 드러난다. 대표적으로 Node Scheduling에서 여러 라벨이 붙은 Node 중 특정 조건에 맞는 Node만 선택할 때 쓰인다.

### ReplicaSet YAML 예제

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

> `terminationGracePeriodSeconds: 0`은 Pod 삭제 시 기본 30초 대기를 없애기 위해 사용한다. 실습 중 반복적으로 Pod를 지우고 만들 때 편하다.

### 고급 Selector 예제 (matchLabels + matchExpressions 동시 사용)

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
    - {key: type, operator: In, values: [web]}
    - {key: ver, operator: Exists}
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
```

> Selector의 모든 조건(`type=web`, `ver=v1`, `type In [web]`, `ver Exists`)은 Template Label(`type=web`, `ver=v1`, `location=dev`)에 전부 포함되므로 정상 생성된다.

### Controller만 삭제하고 Pod는 남기는 방법

ReplicaSet을 삭제하면 관리하던 Pod도 함께 삭제된다. 만약 Pod는 유지한 채 Controller만 제거하고 싶다면 `--cascade=false` 옵션을 사용한다. (대시보드에서는 지원되지 않고 `kubectl`로만 가능.)

```bash
kubectl delete replicationcontrollers replication1 --cascade=false
```

---

## Deployment - Recreate, RollingUpdate

**Deployment란?** 이미 운영 중인 서비스를 새 버전으로 업그레이드해야 할 때 사용하는 Controller다. 단순히 Pod를 몇 개 띄우는 것(ReplicaSet이 담당)에서 한 단계 나아가, "어떤 방식으로 신/구 버전을 교체할 것인지"까지 관리한다. 내부적으로는 Deployment가 ReplicaSet을 만들고, ReplicaSet이 Pod를 만드는 2단계 구조다.

### 대표적인 4가지 배포 전략

Kubernetes를 공부할 때 가장 헷갈리는 부분이 배포 전략이다. 네 가지를 비교해서 정리해 본다.

| 전략 | 다운타임 | 추가 자원 | 특징 |
|---|---|---|---|
| **Recreate** | 있음 | 필요 없음 | 기존 Pod 전체 삭제 후 새 Pod 생성. 가장 단순. |
| **Rolling Update** | 없음 | 약간 필요 | 신/구 Pod를 하나씩 교체. Deployment의 기본 방식. |
| **Blue/Green** | 없음 | 2배 | 신 버전을 완전히 띄운 후 Service Selector만 전환. 롤백이 쉬움. |
| **Canary** | 없음 | 조금 | 일부 트래픽만 신 버전에 보내 검증 후 전체 전환. |

### 1. Recreate — "다 끄고 다시 켜기"

가장 단순한 방법이다. v1 Pod들을 전부 내리고 → v2 Pod들을 새로 만든다.

1. Deployment가 Pod를 전부 삭제한다.
2. 서비스 다운타임 발생. 이 순간 사용자는 서비스에 접근할 수 없다.
3. 새 버전의 Pod들을 생성한다.

- **단점**: 다운타임이 발생한다. 일시적 중단이 허용되는 서비스에서만 쓸 수 있다.
- **장점**: 단순하고 자원이 덜 든다.

### 2. Rolling Update — "하나씩 교체하기" (기본값)

Deployment의 기본 전략이자 가장 많이 쓰이는 방식이다. 예를 들어 v1 Pod 2개가 떠 있는 상태에서 v2로 업그레이드한다고 가정해 보자.

1. Deployment가 **v2 Pod 1개**를 먼저 만든다. 이 순간 v1 2개 + v2 1개 = 총 3개 Pod. 자원이 일시적으로 늘어난다.
2. 이 상태에서 일부 트래픽은 v1에, 일부는 v2에 도달한다. (신/구 공존 구간)
3. **v1 Pod 1개를 삭제**한다. v1 1개 + v2 1개.
4. **v2 Pod를 하나 더 만든다.** v1 1개 + v2 2개.
5. 마지막 **v1 Pod를 삭제**한다. v2 2개로 전환 완료.

- **장점**: 다운타임 없음.
- **단점**: 배포 중간에 추가 자원이 필요하고, 신/구 버전이 잠시 공존한다.

### 3. Blue/Green — "완전히 새로 띄우고 스위치"

Deployment 자체 기능은 아니며, ReplicaSet과 Service의 Selector를 활용해 구현한다.

1. v1 Pod(Blue)가 Service에 연결되어 운영 중.
2. v2 Pod(Green)를 별도 ReplicaSet으로 완전히 띄운다. 이 순간 자원이 2배가 된다. Service는 아직 Blue만 가리킨다.
3. **Service의 Selector를 v1 → v2로 변경**한다. 이 한 번의 변경으로 트래픽이 즉시 Green으로 전환된다.
4. 문제가 생기면 Selector를 다시 v1로 되돌리면 된다 → **롤백이 매우 쉬움**.
5. 문제가 없으면 Blue를 삭제한다.

- **장점**: 다운타임 없음, 롤백이 간단, 안정적.
- **단점**: 자원이 잠시 2배 필요.

### 4. Canary — "실험체로 검증하고 전환"

**이름의 유래**: 카나리아는 심박수가 1초에 17회일 만큼 빠르고 유해 가스에 민감해서, 과거 광부들이 탄광에서 가스 누출을 감지하기 위해 데려갔다고 한다. 이 새가 먼저 반응하면 위험을 알 수 있었다. Canary 배포도 마찬가지로 "실험체"로 먼저 검증한 뒤 안전이 확인되면 전체에 배포하는 방식이다.

구현 방법은 두 가지가 있다.

**(a) 트래픽 일부를 무작위로 분산**: v1 Pod들(replicas=N)과 v2 Pod(replicas=1)를 같은 Label로 Service에 연결하면, 전체 트래픽 중 작은 비율이 v2로 흘러간다. 문제가 생기면 v2의 replicas만 0으로 내리면 된다.

**(b) Ingress Controller로 특정 타겟만 분기**: Ingress Controller는 유입되는 트래픽을 URL Path에 따라 다른 Service로 보내는 역할을 한다. 예컨대 글로벌 서비스에서 미국 유저만 `/en/` 경로로 들어오게 하고, 이 경로만 v2 Service로 라우팅하면 특정 지역에만 신 버전을 배포할 수 있다.

- **장점**: 불특정 다수를 대상으로 한 점진적 검증, 또는 특정 타겟 그룹에 한정된 테스트가 가능.
- **단점**: 테스트 기간과 v2 Pod 수에 따라 추가 자원이 필요.

---

### Deployment 내부 동작 — ReplicaSet을 통한 관리

Deployment 매니페스트에는 `selector`, `replicas`, `template`을 넣는다. 그런데 Deployment가 이 값으로 직접 Pod를 만드는 게 아니다. Deployment는 **ReplicaSet을 만들고**, 그 ReplicaSet에게 이 값들을 넘긴다. 실제 Pod 생성은 ReplicaSet이 담당한다.

즉 계층 구조는 다음과 같다.

```
Deployment → ReplicaSet → Pod
```

### Recreate 내부 동작 단계별 뜯어보기

1. Template이 v1에서 v2로 변경되면, Deployment는 **기존 ReplicaSet의 replicas를 0으로 내린다.**
2. 기존 ReplicaSet이 Pod를 전부 삭제한다. Service는 연결 대상이 없어 다운타임 발생.
3. Deployment가 **새 ReplicaSet(v2)을 생성**하고 replicas를 원래 값으로 설정한다.
4. 새 ReplicaSet이 v2 Pod를 생성한다. Service Label이 일치하면 자동으로 연결되어 서비스 재개.

### Rolling Update 내부 동작 단계별 뜯어보기

1. Deployment가 v2 ReplicaSet을 만들고 replicas=1로 시작. v1 ReplicaSet은 그대로.
2. v2 Pod 1개가 뜨면, Service는 v1 2개 + v2 1개에 트래픽을 분산.
3. v1 ReplicaSet의 replicas를 2 → 1로 내려 v1 Pod 하나 삭제.
4. v2 ReplicaSet의 replicas를 1 → 2로 올려 v2 Pod 추가.
5. v1 ReplicaSet의 replicas를 1 → 0으로 내려 남은 v1 Pod 삭제. 교체 완료.

> 두 전략 모두 **기존 ReplicaSet을 삭제하지 않는다.** replicas만 0으로 내려놓고 남겨둔다. 이게 곧 다음에 설명할 Rollback의 핵심이다.

### revisionHistoryLimit — "과거 ReplicaSet 몇 개까지 보관할지"

업그레이드할 때마다 replicas=0인 ReplicaSet이 하나씩 쌓인다. 기본값은 10개 보관. `revisionHistoryLimit: 1`로 설정하면 1개만 유지하고 나머지는 삭제된다. 이 "replicas=0인 ReplicaSet"은 Rollback할 때 사용된다.

### pod-template-hash — Deployment가 숨겨둔 자동 Label

Rolling Update 중에 v1 ReplicaSet과 v2 ReplicaSet이 같은 Selector(`type=app`)를 공유하면, v1 ReplicaSet이 실수로 v2 Pod를 자기 것이라 판단할 수 있다. 이를 방지하기 위해 Deployment는 각 ReplicaSet에 `pod-template-hash`라는 **해시 Label**을 추가로 붙여준다. ReplicaSet과 Pod는 이 해시 Label까지 포함해서 매칭되므로 서로 섞이지 않는다. 사용자가 직접 넣는 값이 아니며, Deployment가 자동으로 관리한다.

### Rollback — 이전 버전으로 되돌리기

replicas=0으로 남아 있는 과거 ReplicaSet을 다시 되살리는 방식으로 롤백이 이뤄진다.

```bash
# 히스토리 조회
kubectl rollout history deployment deployment-1

# 특정 revision으로 롤백
kubectl rollout undo deployment deployment-1 --to-revision=2
```

Revision 번호는 대시보드에서 해당 ReplicaSet의 `annotation`에 `deployment.kubernetes.io/revision` 값으로 확인할 수 있다.

### minReadySeconds

Rolling Update 시 각 Pod 교체 단계 사이에 일정 시간 대기하도록 하는 옵션이다. 값을 주지 않으면 교체가 거의 즉시 진행돼 시각적으로 확인하기 어렵다. `minReadySeconds: 10`을 주면 10초 간격으로 진행된다. 중급편에서 다룰 Readiness Probe와도 연관이 있다.

### Deployment YAML 예제

**Recreate 전략:**

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

**Rolling Update 전략:**

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
```

**테스트 명령 (배포 진행 과정 실시간 관찰):**

```bash
while true; do curl 10.99.5.3:8080/version; sleep 1; done
```

**Blue/Green 배포 예제 (ReplicaSet + Service Selector 변경):**

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
---
apiVersion: v1
kind: Service
metadata:
  name: svc-3
spec:
  selector:
    ver: v1   # 전환 시 이 값을 v2로 변경
  ports:
  - port: 8080
    targetPort: 8080
```

---

## DaemonSet, Job, CronJob

이 세 Controller는 모두 Pod를 만들지만, **누가 만들었느냐**에 따라 Pod의 동작이 근본적으로 다르다. 발표에서 가장 강조해야 할 부분이다.

### Controller에 따라 Pod의 성격이 달라진다

| 생성 주체 | 장애 시 동작 | 일을 안 할 때 |
|---|---|---|
| **직접 생성한 Pod** | Node가 죽으면 Pod도 소멸. 복구 없음. | 그대로 떠 있음. |
| **ReplicaSet의 Pod** | 다른 Node에 **재생성**(Recreate). 이름/IP 변경. | 강제 재기동. 서비스는 무조건 유지되어야 함. |
| **Job의 Pod** | 다른 Node에 재생성. | 작업 종료 후 Pod는 **멈춘 상태(자원 사용 X)로 남음**. 결과·로그를 확인한 뒤 수동 삭제. |

> **Recreate vs Restart 구분**: Recreate는 Pod 자체를 새로 만드는 것이라 이름과 IP가 변경된다. Restart는 Pod는 그대로 두고 **컨테이너만** 재기동하는 것으로, Pod 이름과 IP는 유지된다.

---

### 1. DaemonSet — "모든 Node에 하나씩"

**DaemonSet이란?** 이름 그대로 daemon처럼 **각 Node마다 Pod 하나를 상주**시키는 Controller다. ReplicaSet은 Node 자원 상황에 따라 Pod가 몰리거나 빠지지만, DaemonSet은 자원 상태와 무관하게 **Node 개수 = Pod 개수**를 보장한다.

#### 언제 쓰나? — 대표적인 3가지 유스케이스

1. **성능(메트릭) 수집 에이전트** — Prometheus Node Exporter처럼 각 Node의 CPU/메모리/디스크 정보를 수집하는 서비스. 모든 Node가 감시 대상이므로 Node마다 에이전트가 하나씩 필요하다.
2. **로그 수집 에이전트** — Fluentd 같은 로그 수집기. 각 Node의 로그를 중앙 시스템으로 전달해야 하므로 Node마다 설치되어야 한다.
3. **네트워크 / 스토리지 플러그인** — GlusterFS로 분산 파일 시스템을 구성하거나, Kubernetes 자체가 네트워크 관리를 위해 kube-proxy를 DaemonSet으로 띄우는 경우.

#### NodeSelector — 특정 Node만 골라서 배포

DaemonSet은 기본적으로 모든 Node에 Pod를 만들지만, `nodeSelector`를 지정하면 **해당 Label이 붙은 Node에만** Pod가 생성된다. OS가 다른 Node에는 Pod를 올리지 않는 식으로 예외 처리가 가능하다.

```bash
kubectl label nodes k8s-node1 os=centos
kubectl label nodes k8s-node2 os=ubuntu
```

> 주의: DaemonSet은 한 Node에 Pod를 **여러 개** 띄울 수는 없다. 단 "특정 Node에 Pod를 만들지 않는" 것은 가능하다.

#### hostPort — Node IP로 직접 접근

보통 Pod에 접근하려면 Service를 거친다. 하지만 DaemonSet Pod에는 `hostPort`를 설정해 **Node의 특정 포트를 Pod의 컨테이너 포트로 바로 연결**할 수 있다. 이렇게 하면 `NodeIP:hostPort`로 접근할 때 그 Node에 있는 Pod에 직접 도달한다.

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

```bash
curl 192.168.56.31:18080/hostname
```

#### nodeSelector 예제

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

---

### 2. Job — "일회성 작업"

**Job이란?** 계속 떠 있어야 하는 서비스가 아니라 **한 번만 실행되고 끝나는 작업**(데이터 마이그레이션, 배치, 일회성 계산 등)을 관리하는 Controller.

#### ReplicaSet Pod와의 결정적 차이

- ReplicaSet Pod는 내부 프로세스가 일을 멈추면 **강제로 재기동**된다. 서비스는 무조건 떠 있어야 하기 때문.
- Job Pod는 프로세스가 일을 다 하면 **종료 상태로 멈춘다.** 완전히 사라지는 게 아니라 "자원은 안 쓰지만 그대로 남아 있는" 상태다. 이 덕분에 작업이 끝난 뒤에도 `kubectl logs`로 결과를 확인할 수 있다. 필요 없어지면 직접 삭제한다.

#### 주요 옵션

- **`completions`**: 총 실행 횟수. `completions: 6`이면 Pod를 순차적으로 6개 실행하고, 6개 모두 성공해야 Job 종료.
- **`parallelism`**: 동시에 실행할 Pod 수. `parallelism: 2`면 한 번에 2개씩 병렬 실행.
- **`activeDeadlineSeconds`**: Job의 제한 시간. 이 시간을 초과하면 Job은 즉시 중단되고, 실행 중이던 Pod는 삭제된다. 아직 실행되지 못한 Pod도 앞으로 실행되지 않는다. "10초면 끝날 작업이 30초가 넘어도 안 끝나면 행이 걸렸을 확률이 크니 강제 종료"하는 안전장치.
- **`restartPolicy`**: Job에서는 `Never` 또는 `OnFailure`만 지정 가능 (Always는 사용 불가). 기본 Pod의 라이프사이클과 맞물리는 개념이라 중급편에서 자세히 다룬다. 일단은 Job에서는 이 두 값만 쓴다는 점만 기억하면 된다.

#### 예제 — 기본 Job

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
        command: ["sh", "-c", "echo 'job start'; sleep 20; echo 'job end'"]
```

#### 예제 — 병렬 + 데드라인

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
        command: ["sh", "-c", "echo 'job start'; sleep 20; echo 'job end'"]
```

> 이 예제는 총 6개의 Pod를 2개씩 병렬로 실행하려 하지만, 30초 데드라인 때문에 첫 2개(20초 소요)만 정상 완료되고, 그다음 2개는 실행 도중 삭제된다. 나머지는 아예 실행되지 않는다.

---

### 3. CronJob — "주기적으로 Job 찍어내기"

**CronJob이란?** Job을 혼자 쓰는 경우는 드물다. 대부분은 **정해진 시간에 반복**하기 위해 CronJob으로 감싸서 사용한다. Linux의 cron과 동일한 `분 시 일 월 요일` 스케줄 포맷을 쓴다.

#### 대표 유스케이스

- DB 백업: 매일 새벽마다 덤프
- 주기적 업데이트 확인
- 예약 메일·SMS 발송
- 주기적 데이터 정리

#### concurrencyPolicy — 이전 Job이 아직 돌고 있을 때 어떻게 할지

스케줄 타임이 왔는데 이전 Job이 아직 실행 중인 경우, 새 Job을 어떻게 할지 결정하는 옵션이다. 세 가지가 있다.

| 값 | 동작 |
|---|---|
| **Allow** (기본값) | 이전 Job 상태와 무관하게 스케줄 타임마다 새 Job을 생성. Job들이 동시에 여러 개 떠 있을 수 있음. |
| **Forbid** | 이전 Job이 아직 끝나지 않았으면 새 Job을 **스킵**. 이전 Job이 끝나고 나서 다음 스케줄 타임에 다시 Job 생성. |
| **Replace** | 이전 Job을 **삭제하고** 새 Job으로 교체. |

#### 일시 중지와 수동 트리거

- **일시 중지**: `spec.suspend`를 `true`로 바꾸면 CronJob이 새 Job 생성을 멈춘다. 다시 `false`로 돌리면 재개.
- **수동 실행**: 대시보드에서 Trigger 버튼을 누르거나, `kubectl create job` 명령으로 CronJob의 템플릿을 가져와 즉시 Job을 하나 만들 수 있다.

```bash
# CronJob으로부터 Job 즉시 생성
kubectl create job --from=cronjob/cron-job cron-job-manual-001

# CronJob 일시 중지 / 재개
kubectl patch cronjobs cron-job -p '{"spec":{"suspend":true}}'
kubectl patch cronjobs cron-job -p '{"spec":{"suspend":false}}'
```

#### CronJob YAML 예제

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cron-job
spec:
  schedule: "*/1 * * * *"   # 매 1분마다
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
          - name: container
            image: kubetm/init
            command: ["sh", "-c", "echo 'job start'; sleep 20; echo 'job end'"]
```

#### Forbid concurrencyPolicy 예제

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cron-job-2
spec:
  schedule: "20,21,22 * * * *"   # 20, 21, 22분에 실행
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
          - name: container
            image: kubetm/init
            command: ["sh", "-c", "echo 'job start'; sleep 140; echo 'job end'"]
```

> 이 예제에서 Pod는 140초(2분 20초) 동안 실행된다. 20분 스케줄에 Job이 생성되어 Pod가 돌기 시작하고, 21분 스케줄이 와도 이전 Pod가 끝나지 않아 **스킵**된다. 22분 스케줄이 오는 순간에는 첫 Pod가 막 종료되므로 새 Job이 생성된다.

---

## 참조

- [Kubernetes ReplicaSet](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Labels and Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)
