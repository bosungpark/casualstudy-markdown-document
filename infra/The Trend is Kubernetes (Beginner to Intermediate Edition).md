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

1. StatefulSet: 순서와 고유성을 보장해야 하는 Pod(예: DB, Zookeeper 등)에 사용. 각 Pod에 고유한 이름과 네트워크 ID, 영구 스토리지를 부여한다. Pod가 재시작돼도 이름과 볼륨이 유지된다. 주로 상태 저장 서비스에 적합. (자세한 정리는 문서 하단 [발표 정리] 참고)

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

## [중급편] Pod - Lifecycle

초급에서는 Pod의 Phase 5가지(Pending, Running, Succeeded, Failed, Unknown)만 다뤘다. 중급에서는 Pod의 `status` 구조 전체를 뜯어보고, **Phase가 어떻게 결정되는지**, **Container의 State가 어떻게 전이되는지**까지 본다. 장애 분석은 Phase가 아니라 **status.conditions**와 **containerStatuses**를 봐야 한다.

### Pod의 status 구조

Pod 오브젝트가 살아 있는 동안 `status` 필드는 다음 4가지로 구성된다.

| 필드 | 의미 |
|---|---|
| **status.phase** | Pod의 전체 단계 (Pending / Running / Succeeded / Failed / Unknown) |
| **status.conditions** | Pod가 거쳐온 마일스톤 (Initialized, ContainersReady, PodScheduled, Ready) |
| **status.containerStatuses** | 컨테이너별 상세 상태 (Waiting / Running / Terminated) |
| **status.podIP, hostIP** | 네트워크 정보 |

### Pod Conditions — "단계별 마일스톤"

Pod이 생성되는 과정에서 통과하는 4가지 마일스톤이다. 각 단계가 `True`/`False`로 표시된다.

| Condition | 의미 |
|---|---|
| **PodScheduled** | Scheduler가 Node를 골라 배치 완료 |
| **Initialized** | Init Container가 모두 정상 종료 |
| **ContainersReady** | 모든 컨테이너의 Readiness Probe가 성공 (없으면 컨테이너 기동 완료) |
| **Ready** | Pod가 Service에 트래픽을 받을 수 있는 상태 |

> Phase가 `Running`이라고 해서 트래픽을 받을 준비가 됐다는 뜻이 아니다. **Ready 컨디션이 True가 되어야** Service의 Endpoint에 등록된다.

### Init Container — "본 컨테이너 전에 돌려야 할 것들"

Pod가 Pending 상태일 때 내부적으로 일어나는 일은 크게 3가지다.

1. **Init Container 실행** — 볼륨 초기화, 보안 설정, 의존 서비스 대기 등 사전 작업. 모든 Init Container가 성공해야 `Initialized = True`
2. **Node 스케줄링** — Scheduler가 Node를 결정하면 `PodScheduled = True`
3. **이미지 Pull + 컨테이너 기동** — 이 기간 동안 컨테이너 State는 `Waiting` / reason `ContainerCreating`

Init Container를 아예 지정하지 않은 경우에도 `Initialized = True`가 된다(통과로 간주).

### Container State — "컨테이너의 일생"

Pod 안의 각 컨테이너는 다음 3가지 상태 중 하나를 가진다.

| State | 언제 발생하나 | 추가 필드 |
|---|---|---|
| **Waiting** | 이미지 Pull 중, Init Container 대기 중 등 | `reason` (예: ContainerCreating, ImagePullBackOff, CrashLoopBackOff) |
| **Running** | 정상적으로 실행 중 | `startedAt` |
| **Terminated** | 종료됨 | `exitCode`, `reason` (Completed, Error, OOMKilled), `startedAt`, `finishedAt` |

> **중요한 착각 포인트**: Pod의 Phase가 `Running`이어도 내부 컨테이너가 전부 Running은 아니다. `CrashLoopBackOff` 상태의 컨테이너는 State가 `Waiting`이지만, Kubernetes는 Pod 자체는 여전히 `Running`으로 본다. 그래서 운영에서는 `phase`만 보면 안 되고 `containerStatuses`와 `conditions.Ready`를 같이 봐야 한다.

### restartPolicy — "컨테이너가 죽었을 때 어떻게 할지"

Pod의 `spec.restartPolicy`는 컨테이너가 종료됐을 때 kubelet이 어떻게 행동할지를 정한다.

| 값 | 동작 | 사용처 |
|---|---|---|
| **Always** (기본값) | Exit Code와 무관하게 항상 재시작 | Deployment 등 상시 서비스 |
| **OnFailure** | Exit Code != 0인 경우만 재시작 | Job (실패 시 재시도) |
| **Never** | 절대 재시작하지 않음 | Job (한 번만 시도) |

> `Always`는 무한 재시작 시 **CrashLoopBackOff** 상태가 된다. 재시작 간격이 지수적으로(10s, 20s, 40s, ... 최대 5분) 늘어나 시스템을 보호한다.

### 시나리오로 보는 Phase 결정

| 시나리오 | Phase 변화 |
|---|---|
| 정상 기동 | Pending → Running |
| Job 정상 종료 (Always 외) | Running → Succeeded |
| Job 실패 종료 | Running → Failed |
| Image Pull 실패 | Pending에서 멈춤 (containerStatus는 Waiting/ImagePullBackOff) |
| Node 장애 | Running → Unknown (kubelet과 통신 두절) |

---

## [중급편] Pod - ReadinessProbe, LivenessProbe

### 두 Probe가 필요한 이유

문서 앞부분의 ["파드가 죽었다는 사실을 어떻게 아는가"](#) 흐름을 떠올려 보자. kubelet은 컨테이너 프로세스의 종료(Exit Code)는 감지하지만, **프로세스가 살아 있으면서도 응답 불능인 상태**(데드락, GC 폭주 등)는 감지하지 못한다. Probe가 이 빈틈을 메운다.

| Probe | 실패 시 동작 | 목적 |
|---|---|---|
| **ReadinessProbe** | Service Endpoint에서 **제외** (재시작 X) | 트래픽을 받을 준비 안 됨 |
| **LivenessProbe** | 컨테이너 **재시작** | 컨테이너가 죽음 (응답 불능) |

> 핵심 차이: **Readiness는 트래픽 차단, Liveness는 재시작.** 이 둘을 혼동하면 운영 사고로 이어진다.

### Probe 진단 방식 3가지

| 방식 | 동작 | 사용처 |
|---|---|---|
| **httpGet** | 지정한 path와 port로 HTTP GET 요청. 200~399면 성공 | 웹 서비스 (가장 일반적) |
| **exec** | 컨테이너 안에서 명령 실행. Exit Code 0이면 성공 | DB, 캐시 등 비-HTTP 앱 |
| **tcpSocket** | 지정한 포트로 TCP 연결 시도. 성공하면 OK | 단순 포트 오픈 확인 |

> **Tomcat 500 에러 같은 상황**이 LivenessProbe가 꼭 필요한 전형적인 케이스다. Tomcat 프로세스 자체는 살아 있어서 Pod는 `Running`으로 남지만, 위에서 돌고 있는 앱은 메모리 오버플로우로 `500 Internal Server Error`만 뿜는다. 프로세스 모니터링만으로는 이 빈틈을 못 메운다.

### 공통 옵션 — "언제, 얼마나, 몇 번 체크할지"

| 옵션 | 기본값 | 의미 |
|---|---|---|
| **initialDelaySeconds** | 0 | 컨테이너 시작 후 첫 체크까지 대기 시간 |
| **periodSeconds** | 10 | 체크 주기 |
| **timeoutSeconds** | 1 | 체크 응답 대기 시간 |
| **successThreshold** | 1 | 성공 판정에 필요한 연속 성공 횟수 |
| **failureThreshold** | 3 | 실패 판정에 필요한 연속 실패 횟수 |

### YAML 예제 — 두 Probe 동시 적용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-probe
spec:
  containers:
  - name: container
    image: kubetm/app
    ports:
    - containerPort: 8080
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 10
      failureThreshold: 3
    livenessProbe:
      httpGet:
        path: /health
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      failureThreshold: 3
```

> 두 Probe의 path를 분리하는 게 좋다. `/ready`는 의존성(DB, 캐시) 확인까지 포함하고, `/health`는 자기 프로세스 살아 있는지만 가볍게 응답하도록 설계한다.

### exec + hostPath로 수동 제어하는 전형적 예제

강의에서 자주 쓰이는 패턴으로, `ready.txt` 파일을 조건부로 만들어서 ReadinessProbe의 성공/실패를 수동으로 토글한다. 디버깅이나 데모에 유용하다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-readiness-exec
  labels:
    app: readiness
spec:
  containers:
  - name: container
    image: kubetm/app
    ports:
    - containerPort: 8080
    volumeMounts:
    - name: host-path
      mountPath: /mount1
    readinessProbe:
      exec:
        command: ["cat", "/mount1/ready.txt"]
      initialDelaySeconds: 5
      periodSeconds: 10
      successThreshold: 3
  volumes:
  - name: host-path
    hostPath:
      path: /tmp/readiness
      type: DirectoryOrCreate
```

**동작 흐름**:

1. Pod 생성 직후 `/mount1/ready.txt`가 없음 → probe 실패 → `Ready=False`
2. `kubectl describe endpoints`에서 이 Pod IP는 `notReadyAddresses`에 등록 (Service 트래픽 안 받음)
3. 호스트 Node에서 `touch /tmp/readiness/ready.txt` → probe 성공 시작
4. **3번 연속 성공**(successThreshold) 후 `Ready=True` → endpoints의 `addresses`로 이동, 트래픽 유입

### Startup Probe — "느리게 뜨는 앱을 위한 안전장치"

JVM, Spring Boot처럼 기동에 30초 이상 걸리는 앱에서 Liveness가 먼저 동작하면 무한 재시작 루프에 빠진다. Startup Probe가 성공할 때까지 Liveness/Readiness는 **유예**된다.

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30   # 최대 30 * 10s = 5분 대기
  periodSeconds: 10
```

### 실습 시나리오 — Service와 함께 동작 확인

ReadinessProbe를 가진 Pod 2개와 Service 하나를 만들어 동작을 확인한다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-readiness
spec:
  selector:
    app: readiness
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: pod-readiness-1
  labels:
    app: readiness
spec:
  containers:
  - name: container
    image: kubetm/app
    ports:
    - containerPort: 8080
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 10
```

**확인 포인트**:

```bash
# Pod의 Ready 상태 확인 (READY 컬럼)
kubectl get pods

# Service의 Endpoint 확인 — Ready=True인 Pod만 addresses에 등록됨
# Ready=False인 Pod는 notReadyAddresses로 분리되어 서비스 트래픽 대상에서 제외
kubectl describe endpoints svc-readiness

# Pod의 conditions 상세 확인
kubectl describe pod pod-readiness-1
```

`/ready`가 실패를 반환하도록 만들면 `kubectl describe endpoints`에서 해당 Pod IP가 `addresses`에서 `notReadyAddresses`로 이동하지만, **Pod 자체는 죽지 않고 Running으로 유지**된다. LivenessProbe였다면 컨테이너가 재시작되어 RESTARTS 카운트가 올라간다.

---

## [중급편] Pod - QoS Classes

### QoS가 왜 필요한가?

Node의 자원이 부족해지면 kubelet은 Pod를 강제 퇴출(Eviction)한다. **누구를 먼저 죽일지** 결정하는 우선순위가 QoS Class다. requests/limits 설정 방식에 따라 자동으로 부여된다.

### 3가지 QoS Class

| Class | 조건 | Eviction 우선순위 |
|---|---|---|
| **Guaranteed** | 모든 컨테이너가 CPU/Memory 모두 `requests == limits` | 가장 늦게 죽음 (안전) |
| **Burstable** | 하나라도 requests/limits가 설정되어 있지만 Guaranteed 조건에 미달 | 중간 |
| **BestEffort** | 어떤 컨테이너도 requests/limits를 지정하지 않음 | 가장 먼저 죽음 |

### YAML 예제 — Class별 설정

**Guaranteed** — 운영 환경의 핵심 서비스에 권장

```yaml
resources:
  requests:
    cpu: "1"
    memory: "1Gi"
  limits:
    cpu: "1"
    memory: "1Gi"
```

**Burstable** — 평소엔 적게, 부하 시 더 쓰는 일반 워크로드

```yaml
resources:
  requests:
    cpu: "0.5"
    memory: "500Mi"
  limits:
    cpu: "1"
    memory: "1Gi"
```

**BestEffort** — 죽어도 상관없는 임시/배치 작업

```yaml
# resources 자체를 지정하지 않음
```

### Eviction 시나리오

Node에 메모리가 부족해지면 kubelet은 다음 순서로 Pod를 퇴출한다.

1. **BestEffort** Pod 모두
2. **Burstable** Pod 중 requests를 초과해서 사용 중인 Pod
3. **Guaranteed** Pod (시스템 데몬 보호 차원에서만)

### 같은 Class 안에서 누가 먼저 죽나 — OOM Score

한 Class 안에 여러 Pod가 있을 때는 **OOM Score**(Out-Of-Memory Score)가 높은 쪽이 먼저 죽는다. 핵심은 **"내가 요청한 양 대비 실제로 얼마나 쓰고 있느냐"**의 비율이다.

| Pod | requests.memory | 실제 사용량 | 사용 비율 | OOM 대상 순위 |
|---|---|---|---|---|
| Pod2 | 5Gi | 4Gi | **80%** | 먼저 죽음 |
| Pod3 | 8Gi | 4Gi | 50% | 나중 |

> 같은 Burstable이라도 **requests 대비 과소비 중인 Pod**가 먼저 희생된다. 이는 "자기 몫을 더 많이 쓰는 쪽이 시스템에 더 큰 부담"이라는 kubelet의 판단 기준이다. 요청량을 실사용보다 지나치게 낮게 잡으면 Eviction 1순위가 될 수 있다는 뜻.

> 실무 팁: 결제, 인증 같은 **절대 죽으면 안 되는 서비스는 Guaranteed**, 일반 백엔드는 **Burstable**, 로그 수집 같은 부수 작업은 **BestEffort**로 두는 식의 계층 설계가 정석이다.

### QoS Class 확인

```bash
kubectl get pod pod-1 -o jsonpath='{.status.qosClass}'
```

---

## [중급편] Pod - Node Scheduling

초급에서 본 `nodeSelector`는 **단순 Label 매칭**만 가능했다. 중급에서는 더 정교한 4가지 스케줄링 메커니즘을 다룬다.

### 한눈에 보기

| 메커니즘 | 누가 결정 | 무엇을 본다 |
|---|---|---|
| **NodeName** | 사용자 | Node 이름 직접 지정 (Scheduler 우회) |
| **NodeSelector / Node Affinity** | Scheduler | Node의 Label |
| **Pod Affinity / Anti-Affinity** | Scheduler | 다른 Pod의 위치 |
| **Taint / Toleration** | Node + Pod | Node가 거부, Pod가 감내 |

### 1. NodeName — "이 Node에 무조건 올려라"

가장 단순하지만 위험한 방법. Scheduler를 거치지 않고 직접 Node를 지정한다. Node가 죽거나 자원이 없어도 그대로 시도한다. 실무에서는 거의 안 쓴다.

```yaml
spec:
  nodeName: node1
```

### 2. Node Affinity — "Label을 더 유연하게 매칭"

NodeSelector의 확장판. **연산자**(In, NotIn, Exists, DoesNotExist, Gt, Lt)를 지원하고, **Required vs Preferred**(필수 vs 선호)를 구분할 수 있다.

| 종류 | 의미 |
|---|---|
| **requiredDuringSchedulingIgnoredDuringExecution** | 반드시 만족해야 스케줄. 없으면 Pending |
| **preferredDuringSchedulingIgnoredDuringExecution** | 가급적 만족하도록 노력. 없어도 다른 Node에 스케줄 |

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: gpu
            operator: In
            values: ["true"]
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values: ["seoul"]
```

> 이름의 `IgnoredDuringExecution`은 "이미 떠 있는 Pod의 Node Label이 바뀌어도 쫓아내지 않음"을 뜻한다. 스케줄링 시점에만 평가된다.

**matchExpressions 연산자**: `In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`. 앞 `Gt`/`Lt`는 "지정한 value보다 크거나 작은 Node"를 고르는 Node Affinity 고유 연산자다 (예: 특정 CPU 용량 이상의 Node).

### Preferred의 weight — 점수 가산 방식

Scheduler는 원래 CPU 여유 등으로 Node에 기본 점수를 매기고, `preferred` 조건을 만족하는 Node에 **weight만큼 점수를 추가**해 최종 점수가 가장 높은 Node를 고른다.

예시: Node1(`zone=kr`, CPU 여유 50점), Node2(`zone=us`, CPU 여유 30점)에 `preferred` (key: `zone`, value: `kr`, weight: 50)인 Pod를 배치하면

| Node | 기본 점수 | preferred 가산 | 최종 |
|---|---|---|---|
| Node1 (kr) | 50 | +50 | **100** ← 배치 |
| Node2 (us) | 30 | 0 | 30 |

> `required`와 달리 `preferred`는 조건 미달 Node도 후보에 포함된다. weight는 0~100 정수.

### 3. Pod Affinity / Anti-Affinity — "다른 Pod와 가까이/멀리"

Node가 아니라 **다른 Pod의 위치**를 기준으로 배치한다.

| 종류 | 용도 |
|---|---|
| **podAffinity** | 같은 Node/Zone에 모으기. 캐시-앱처럼 통신이 잦은 Pod끼리 묶을 때 |
| **podAntiAffinity** | 서로 떨어뜨리기. 동일 서비스 Pod가 한 Node에 몰리지 않게 (HA) |

```yaml
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values: ["web"]
        topologyKey: "kubernetes.io/hostname"
```

> `topologyKey`가 핵심이다. `hostname`이면 같은/다른 Node 기준, `zone`이면 같은/다른 가용영역 기준이다.

**전형적 사용 시나리오**:

| 상황 | 어떤 걸 쓰나 |
|---|---|
| 웹 Pod와 서버 Pod가 **같은 hostPath PV를 공유** → 같은 Node에 있어야 데이터 접근 가능 | `podAffinity` (웹 Pod의 라벨을 매칭) |
| 마스터/슬레이브 DB처럼 **한 Node 장애 시 둘 다 죽으면 안 됨** | `podAntiAffinity` (마스터 Pod의 라벨을 매칭) |

> 먼저 스케줄링된 Pod가 기준점이 된다. 매칭 대상 라벨의 Pod가 아직 없으면 `required`인 경우 `Pending`으로 대기하고, 그 Pod가 뜨면 비로소 스케줄이 진행된다.

### 4. Taint / Toleration — "Node가 Pod를 거부하기"

지금까지는 **Pod가 Node를 골랐다**면, Taint는 반대로 **Node가 Pod를 거부**한다. Pod에 일치하는 Toleration이 있어야만 그 Node에 들어갈 수 있다.

**Taint Effect 3가지**:

| Effect | 새 Pod 스케줄 | 이미 떠 있는 Pod | 전형적 쓰임 |
|---|---|---|---|
| **NoSchedule** | 차단 | **그대로 유지** | GPU Node 격리, Master Node 보호 |
| **PreferNoSchedule** | 가급적 회피 | 유지 | "정 할당할 Node가 없으면 여기라도" |
| **NoExecute** | 차단 | **쫓아냄** (tolerationSeconds 후) | Node 장애 감지, 격리 긴급 이전 |

> **헷갈리기 쉬운 포인트**: Node Affinity, Pod Affinity, `NoSchedule` taint 모두 **최초 스케줄링 시점에만** 평가된다. 이미 배치된 Pod는 Node Label이 바뀌거나 `NoSchedule` taint가 추가돼도 **쫓겨나지 않는다**. 기존 Pod까지 건드리고 싶으면 `NoExecute`가 유일한 선택지.

```bash
# Node에 Taint 부여
kubectl taint nodes node1 gpu=true:NoSchedule

# Node에서 Taint 제거
kubectl taint nodes node1 gpu=true:NoSchedule-
```

```yaml
# Pod에 Toleration 부여
spec:
  tolerations:
  - key: "gpu"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
```

### 실습 시나리오 — Node Label + Affinity

Node에 지역 Label을 달고 `nodeAffinity`로 한쪽 Node에만 배치하는 시나리오.

```bash
# 1. Node에 라벨 부여 (여러 노드에 그룹핑 가능)
kubectl label nodes node1 kr=az1
kubectl label nodes node2 us=az1

# 2. required로 key=kr인 Node에만 Pod 배치
# 3. key가 없는 Pod는 Pending (required) / 자원 많은 Node로 배치 (preferred)
```

### 실습 시나리오 — Taint와 Toleration

GPU Node를 분리해서 GPU 워크로드만 올리는 시나리오.

```bash
# 1. node1에 GPU Taint 부여 (key=hw, value=gpu, effect=NoSchedule)
kubectl taint nodes node1 hw=gpu:NoSchedule

# 2. Toleration 없는 Pod + nodeSelector(node1) → 에러 (taint 때문에 거부)
# 3. Toleration 있는 Pod + nodeSelector(node1) → 정상 배치
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-tol
spec:
  nodeSelector:
    gpu-type: nvidia
  tolerations:
  - key: "hw"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"
  containers:
  - name: container
    image: kubetm/app
```

### 실습 시나리오 — NoExecute + tolerationSeconds

기존 Pod가 어떻게 쫓겨나는지 확인.

```bash
# 1. node2에 일반 Pod들 배치 (toleration 없음)
# 2. tolerationSeconds=30인 Pod도 node2에 배치
# 3. node2에 NoExecute taint 부여
kubectl taint nodes node2 out=service:NoExecute

# 결과:
# - 일반 Pod들 → 즉시 삭제
# - tolerationSeconds=30인 Pod → 30초 후 삭제
# - tolerationSeconds 없는 matching Toleration Pod → 계속 유지
```

> **실습 중 주의**: Master Node의 기본 `NoSchedule` taint를 지우지 않은 상태에서 Worker 전체에 `NoExecute`를 걸면, 쫓겨난 Pod들이 갈 곳이 없어 `Pending`으로 쌓인다. 노드가 2개뿐인 테스트 환경에서는 한쪽 taint를 먼저 제거한 뒤 다른 쪽에 NoExecute를 거는 순서로 진행한다.

> **주의**: Toleration은 "거부를 무시할 수 있는 권한"일 뿐, "그 Node로 배치"하는 게 아니다. 실제로 GPU Node로 보내려면 `nodeSelector`나 `nodeAffinity`를 함께 써야 한다.

### tolerationSeconds — NoExecute의 "유예 시간"

`NoExecute` taint가 붙으면 기존 Pod가 쫓겨나는데, Pod 쪽에 `tolerationSeconds`를 지정하면 **그 시간만큼 버틴 뒤 삭제**된다. 장애 Node에서 graceful shutdown을 원할 때 쓴다.

```yaml
spec:
  tolerations:
  - key: "out-of-service"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 30   # 30초 후 퇴출
```

- `tolerationSeconds` 생략: NoExecute taint가 매칭되는 한 **영원히 유지**됨
- 지정: 해당 초 경과 후 Pod 삭제

### 쿠버네티스가 자동으로 쓰는 Taint들

평소 거의 못 보지만 실제로는 Kubernetes가 내부적으로 taint를 계속 쓰고 있다.

| 언제 붙나 | Taint | Effect |
|---|---|---|
| Master Node 생성 시 (기본 제공) | `node-role.kubernetes.io/control-plane` | `NoSchedule` |
| Node 장애 감지 (kubelet 통신 두절 등) | `node.kubernetes.io/unreachable` | `NoExecute` |
| 메모리/디스크 압박 | `node.kubernetes.io/memory-pressure` 등 | `NoSchedule` |

> **Master Node에 Pod가 안 뜨는 이유** = 기본 `NoSchedule` taint. 테스트 클러스터에서 Master에도 워크로드를 올리고 싶으면 이 taint를 지우거나 Toleration을 달아야 한다.
>
> **Node 장애 시 자동 복구 흐름**: Node가 죽으면 kubelet 통신 두절 → Kubernetes가 해당 Node에 `NoExecute` taint 자동 부여 → 위에 있던 Pod들이 Eviction → ReplicaSet/Deployment가 부족분을 감지하고 다른 Node에 새 Pod 생성. 이게 "self-healing"의 실제 메커니즘이다.

### 4가지 메커니즘 조합 — 실무 패턴

| 목적 | 조합 |
|---|---|
| GPU 전용 Node 분리 | Taint(GPU Node) + Toleration + nodeSelector |
| 동일 서비스 Pod 분산 | podAntiAffinity (topologyKey: hostname) |
| 캐시-앱 인접 배치 | podAffinity (topologyKey: hostname) |
| 특정 Zone 선호 | nodeAffinity (Preferred) |

핵심은 **"누가 누구를 거부/선호하는가"**의 방향을 명확히 잡는 것이다. Pod가 Node를 고르는지, Node가 Pod를 거르는지, 다른 Pod를 기준으로 삼는지에 따라 메커니즘을 선택한다.

---

## [중급편] Service - Headless, Endpoint, ExternalName

초급에서는 사용자가 Pod에 접근하기 위한 Service(ClusterIP/NodePort/LoadBalancer)를 다뤘다. 중급에서는 **Pod 입장에서** 다른 Pod나 외부 서비스에 접근하는 방법을 본다. 핵심 문제: Pod IP는 **동적으로 바뀌기 때문에** Pod A가 Pod B의 IP를 미리 알 수가 없다.

### Cluster DNS — 이름으로 찾는 기본 메커니즘

클러스터 안에는 DNS 서버(CoreDNS)가 떠 있고, Service/Pod 생성 시 FQDN이 자동 등록된다.

| 대상 | FQDN 형식 |
|---|---|
| Service | `<service-name>.<namespace>.svc.cluster.local` |
| Pod | `<pod-ip-dashed>.<namespace>.pod.cluster.local` (기본) |

같은 네임스페이스 내에서는 서비스를 **짧은 이름**(`service-name`)으로도 부를 수 있다. Pod는 기본 FQDN의 앞부분이 IP라 실용적이지 않고, Headless Service를 통해 이름을 부여해야 쓸 만하다.

```bash
# Pod 안에서 DNS 조회
nslookup my-service                                    # 짧은 이름
nslookup my-service.default.svc.cluster.local         # FQDN
curl my-service:8080                                   # 이름으로 호출
```

### Headless Service — 개별 Pod에 직접 접근

`clusterIP: None`을 주면 Service에 IP가 할당되지 않는다. DNS 질의 시 **연결된 Pod들의 IP 목록을 그대로 반환**한다. 개별 Pod로 라우팅하고 싶을 때 쓴다(StatefulSet의 기본 패턴).

```yaml
apiVersion: v1
kind: Service
metadata:
  name: headless1
spec:
  clusterIP: None   # 핵심
  selector:
    app: pod
  ports:
  - port: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: pod-a
  labels:
    app: pod
spec:
  hostname: pod-a          # 이 값이 DNS 이름 앞자리가 됨
  subdomain: headless1     # Service 이름과 동일하게
  containers:
  - name: container
    image: kubetm/app
```

등록되는 DNS 이름:

```
# Service (여러 Pod IP 반환)
headless1.default.svc.cluster.local → [Pod-A IP, Pod-B IP, ...]

# Pod별 개별 이름
pod-a.headless1.default.svc.cluster.local → Pod-A IP
pod-b.headless1.default.svc.cluster.local → Pod-B IP
```

> `hostname` + `subdomain`을 Pod에 안 넣으면 개별 Pod 이름으로는 DNS 조회가 안 된다. StatefulSet을 쓰면 이걸 자동으로 넣어준다.

### Endpoint — Service↔Pod의 실제 연결고리

Label/Selector로 Service와 Pod를 묶는 건 사용자 편의용이다. Kubernetes는 매칭이 일어나면 **Service와 같은 이름의 Endpoint 오브젝트**를 자동 생성해서 실제 연결을 관리한다.

```bash
kubectl get endpoints                # Service와 같은 이름의 Endpoint가 있음
kubectl describe endpoints my-svc    # 연결된 Pod IP/Port 목록
```

이 규칙을 알면 **Selector 없이** 수동으로 Endpoint를 만들어 원하는 대상을 가리킬 수 있다.

```yaml
# 1. Selector 없는 Service
apiVersion: v1
kind: Service
metadata:
  name: endpoint1
spec:
  ports:
  - port: 8080
---
# 2. Service와 같은 이름의 Endpoint 직접 생성
apiVersion: v1
kind: Endpoints
metadata:
  name: endpoint1          # Service 이름과 동일해야 연결됨
subsets:
- addresses:
  - ip: 192.168.1.100      # 내부 Pod IP or 외부 IP 모두 가능
  ports:
  - port: 8080
```

IP로는 외부 서버(예: GitHub IP)도 지정 가능. 하지만 **IP는 바뀔 수 있으니** 도메인으로 지정하고 싶을 땐 ExternalName을 쓴다.

### ExternalName — 외부 도메인에 이름으로 연결

Pod가 GitHub 같은 외부 서비스를 호출할 때 Pod 코드에 외부 도메인을 박아두면, 나중에 대상이 바뀔 때 Pod 재배포가 필요해진다. ExternalName Service는 이 문제를 우회한다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: externalname1
spec:
  type: ExternalName
  externalName: github.com   # 실제 연결할 외부 도메인
```

- Pod는 항상 `externalname1`이라는 **내부 이름**으로 호출
- 대상이 `gitlab.com`으로 바뀌면 Service의 `externalName`만 수정하면 됨
- 내부적으로는 DNS CNAME 레코드로 동작

| 방법 | 대상 지정 방식 | 쓸 때 |
|---|---|---|
| Endpoint 직접 생성 | IP | 외부 시스템 IP가 고정일 때 |
| ExternalName Service | 도메인 | 도메인을 쓸 수 있을 때 (일반적으로 추천) |

---

## [중급편] Volume - Dynamic Provisioning, PV Status, ReclaimPolicy

초급에서는 PV를 관리자가 먼저 만들고 사용자가 PVC로 연결하는 정적 방식을 다뤘다. 중급에서는 **사용자가 PVC만 만들면 PV가 자동 생성**되는 Dynamic Provisioning, 그리고 **PV의 생명주기/삭제 정책**을 본다.

### Dynamic Provisioning — PVC만 만들면 PV 자동 생성

정적 방식의 번거로움(관리자가 매번 PV를 만들고, 용량/accessMode 맞춰야 함)을 해결하는 구조. 사전에 **StorageClass**가 있어야 한다.

```
사용자: PVC 생성 (storageClassName 지정)
   ↓
StorageClass가 지정된 Provisioner를 호출
   ↓
실제 볼륨(AWS EBS, StorageOS, NFS 등)이 생성됨
   ↓
PV가 자동 생성되어 PVC와 Bound
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-dynamic
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
  storageClassName: fast     # ← StorageClass 이름 지정
```

### StorageClass 동작 방식

| 경우 | 동작 |
|---|---|
| `storageClassName: "fast"` | `fast` StorageClass로 동적 생성 |
| `storageClassName: ""` (빈 문자열) | 동적 생성 비활성화 → 기존 PV와 정적 바인딩 |
| `storageClassName` 필드 생략 | **default StorageClass**로 동적 생성 (있을 경우) |

default StorageClass는 `annotation: storageclass.kubernetes.io/is-default-class: "true"`로 지정한다. 클러스터당 하나가 기본값이 된다.

> **StorageClass의 reclaimPolicy**도 정해진다. 기본 `Delete` (PVC 지우면 PV + 실제 볼륨 삭제). `Retain`으로 바꿔 두면 PVC 삭제 후에도 데이터가 남는다.

### PV Status — 5가지 상태

PV는 생성 → 연결 → 사용 → 해제의 생명주기를 거치며 `status.phase` 값이 바뀐다.

| Status | 언제 |
|---|---|
| **Available** | PV 생성 직후, 아직 어떤 PVC와도 연결 안 됨 |
| **Bound** | PVC와 연결된 상태 |
| **Released** | 연결됐던 PVC가 삭제됨 (데이터는 남아 있지만 재사용 불가) |
| **Failed** | PV와 실제 볼륨 연결 오류 |
| **Pending** | 볼륨이 아직 완전히 준비되지 않음 |

> **주의**: PV를 먼저 만들었을 때(정적)는 실제 볼륨 데이터는 Pod가 연결되는 시점에 생성된다. Dynamic Provisioning의 경우 PVC 생성 즉시 실제 볼륨이 생긴다.

### ReclaimPolicy — PVC 삭제 후 PV의 운명

PVC가 삭제되면 PV의 `spec.persistentVolumeReclaimPolicy`에 따라 동작이 달라진다.

| Policy | PVC 삭제 시 동작 | 실제 데이터 | 기본값이 되는 경우 |
|---|---|---|---|
| **Retain** | PV는 `Released` 상태로 남음, 재사용 불가 | 유지됨 (수동 삭제 필요) | **정적 PV의 기본값** |
| **Delete** | PV + 실제 볼륨까지 자동 삭제 | 볼륨 종류에 따라 삭제됨 | **Dynamic PV의 기본값** |
| **Recycle** | PV는 `Available`로 돌아옴, 재사용 가능 | 자동 삭제(`rm -rf /volume/*`) | — (Deprecated, 사용 비권장) |

```yaml
# PV에서 직접 지정
spec:
  persistentVolumeReclaimPolicy: Retain

# StorageClass에서 지정 (Dynamic PV 전체에 적용)
reclaimPolicy: Retain
```

### PVC/PV가 안 지워질 때 — Force Delete

Finalizer 등으로 PV/PVC가 Terminating 상태에 걸리면 강제 삭제가 필요하다.

```bash
# 네임스페이스 단위로 모든 자원 조회
kubectl get all -n <namespace>

# Force delete
kubectl delete pvc <name> --grace-period=0 --force
kubectl delete pv <name> --grace-period=0 --force
```

---

## [중급편] Authentication - UserAccount, ServiceAccount

Kubernetes API Server는 **모든 요청의 단일 진입점**이다. 이 서버에 접근하는 경로는 크게 "사용자가 접근"(UserAccount)과 "Pod가 접근"(ServiceAccount) 두 가지다.

### API Server 접근의 3단계

```
요청 → Authentication (누구인가?) → Authorization (뭘 할 권한?) → AdmissionControl (제약 조건 통과?)
```

- **Authentication**: 인증서/토큰 검증
- **Authorization**: 자원 권한 확인 (주로 RBAC)
- **AdmissionControl**: PV 용량 제한, 네임스페이스 정책 등

### UserAccount — 사용자가 API에 접근

`kubeconfig` 파일(보통 `~/.kube/config` 또는 `/etc/kubernetes/admin.conf`)에 인증 정보가 들어 있다.

```yaml
apiVersion: v1
kind: Config
clusters:                        # 접근할 클러스터들
- name: cluster-a
  cluster:
    server: https://10.0.0.1:6443
    certificate-authority-data: <CA-CRT-base64>
users:                           # 사용자별 인증 정보
- name: admin-a
  user:
    client-certificate-data: <client.crt-base64>
    client-key-data: <client.key-base64>
contexts:                        # 클러스터 ↔ 사용자 묶음
- name: context-a
  context:
    cluster: cluster-a
    user: admin-a
current-context: context-a
```

세 가지 접근 방식:

| 방식 | 내용 | 보안 |
|---|---|---|
| **HTTPS + 인증서** | 외부 PC가 kubeconfig의 client.crt/key로 직접 API Server 호출 | 안전 (운영) |
| **kubectl proxy** | 내부 마스터에서 `kubectl proxy --accept-hosts=.*` → 8001 포트에 HTTP 프록시 오픈 | 위험 (로컬 개발만) |
| **kubectl config** | 여러 클러스터의 kubeconfig를 합쳐놓고 `kubectl config use-context` 로 전환 | 안전 (멀티 클러스터) |

멀티 클러스터 전환 예시:

```bash
# 컨텍스트 전환
kubectl config use-context context-a
kubectl get nodes                    # cluster-a의 노드 조회

kubectl config use-context context-b
kubectl get nodes                    # cluster-b의 노드 조회

# kubectx 툴(간편 전환)
kubectx context-a
```

### ServiceAccount — Pod가 API에 접근

Namespace를 만들면 `default`라는 ServiceAccount가 자동 생성된다. Pod에 연결된 ServiceAccount의 **Secret(토큰)**으로 API Server에 인증한다.

```
Namespace 생성
  └─ ServiceAccount (default) 자동 생성
       └─ Secret(CA 인증서 + Token) 자동 연결
            └─ Pod 생성 시 자동 마운트 (/var/run/secrets/...)
```

Pod 안에서 토큰으로 API 호출:

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -k -H "Authorization: Bearer $TOKEN" \
  https://kubernetes.default.svc/api/v1/namespaces/default/pods
```

외부에서도 토큰만 있으면 쓸 수 있다:

```bash
# Secret에서 토큰 추출
kubectl get secret <sa-secret> -o jsonpath='{.data.token}' | base64 -d

# HTTP 헤더로 전달
curl -H "Authorization: Bearer <token>" https://<api-server>/api/v1/...
```

> 기본 `default` SA는 권한이 거의 없다. Pod 목록 조회도 막혀 있어 Role/RoleBinding을 붙여 줘야 실제로 쓸 수 있다 (다음 섹션).

---

## [중급편] Authorization - RBAC

Authentication을 통과했다고 자원을 다 다룰 수 있는 건 아니다. **RBAC**(Role-Based Access Control)가 "이 주체가 이 자원에 이 동작을 할 수 있는지"를 결정한다.

### 4가지 오브젝트

| 오브젝트 | 범위 | 역할 |
|---|---|---|
| **Role** | Namespace 내 | 네임스페이스 자원(Pod, Service 등)에 대한 권한 정의 |
| **RoleBinding** | Namespace 내 | Role ↔ SA 연결 |
| **ClusterRole** | 클러스터 전체 | 클러스터 자원(Node, PV 등) + 네임스페이스 자원 권한 정의 |
| **ClusterRoleBinding** | 클러스터 전체 | ClusterRole ↔ SA 연결 |

조합별 효과:

| Binding | Role 종류 | 결과 |
|---|---|---|
| RoleBinding | Role | SA는 **해당 Namespace 내 지정된 자원**만 접근 |
| RoleBinding | ClusterRole | SA는 **해당 Namespace 내에서 ClusterRole 권한**만 사용 (클러스터 자원 접근 불가) |
| ClusterRoleBinding | ClusterRole | SA는 **클러스터 전역** 자원 접근 가능 (admin 수준) |

> "RoleBinding + ClusterRole" 조합은 왜 쓰나? 여러 네임스페이스에 **동일한 권한**을 뿌려야 할 때, 매 네임스페이스마다 Role을 복사하는 대신 ClusterRole 하나를 공유하고 각 네임스페이스에서 RoleBinding으로 연결한다. 권한 변경 시 ClusterRole 하나만 고치면 된다.

### Role YAML — Pod 조회만 허용

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: namespace1
  name: role-pod-reader
rules:
- apiGroups: [""]           # "" = core API (Pod, Service, Node 등)
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
```

**apiGroups**: apiVersion이 `v1`인 core API 자원(Pod, Service, ConfigMap 등)은 `""`. `apps/v1`의 Deployment는 `"apps"`. Job은 `"batch"`.

**verbs**: `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`, `deletecollection`. 모든 동작은 `["*"]`.

### RoleBinding — SA에 Role 연결

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: rb-pod-reader
  namespace: namespace1
roleRef:
  kind: Role
  name: role-pod-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: default              # 기본 SA도 OK
  namespace: namespace1
```

### ClusterRole + ClusterRoleBinding — 모든 권한 부여

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cr-admin
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: crb-admin
roleRef:
  kind: ClusterRole
  name: cr-admin
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
  namespace: namespace2
```

이 SA의 토큰으로는 다른 네임스페이스 Pod, 클러스터 단위 Node까지 전부 조회/생성 가능.

### 실습에서 자주 쓰는 패턴 — Dashboard 보안 접근

기본 설치된 Dashboard가 "skip 로그인 + 모든 자원 접근"이 되는 이유:

```
Dashboard Pod
  └─ ServiceAccount: kubernetes-dashboard
       └─ ClusterRoleBinding: cluster-admin (내장 ClusterRole)
            → 클러스터 전 자원 접근 가능
```

**보안 강화 방법**:

1. ClusterRoleBinding을 제거하거나 제한된 ClusterRole로 교체
2. API Server 직접 접근(HTTPS + client cert)으로 변경
3. `kubectl proxy` 없이 **인증서 등록한 브라우저**에서 Dashboard 접근
4. Dashboard 로그인 시 **SA 토큰**을 입력 (skip 버튼 우회 방지)

```bash
# 클라이언트 인증서를 P12로 합쳐 브라우저에 등록
openssl pkcs12 -export -out client.p12 \
  -inkey client.key -in client.crt

# Dashboard용 SA 토큰 확인
kubectl get secret <dashboard-sa-secret> -o jsonpath='{.data.token}' | base64 -d
```

이러면 3중 보안: **IP/포트를 알아도**, **클러스터 인증서가 없으면 접근 불가**, **접근해도 토큰이 없으면 로그인 불가**.

---

# [발표 정리] StatefulSet · Ingress · AutoScaler

> 이번 주 발표용으로 강의 순서(StatefulSet 이론 → 실습 → Ingress 이론 → 실습 → AutoScaler 이론 → HPA 실습)에 맞춰 한 곳에 모은 정리. 위 본문의 짧은 1줄 정리와 일부 중복되지만, 발표 시 이 섹션만 따라가면 흐름이 끊기지 않도록 구성했다.

## [발표] 1. StatefulSet — Stateful 앱을 위한 Controller

### 1-1. Stateless vs Stateful — 왜 다른 Controller가 필요한가

| 구분 | Stateless 앱 | Stateful 앱 |
|---|---|---|
| **대표 예시** | Apache, Nginx, IIS 같은 웹서버 | MongoDB, MariaDB, Redis 같은 DB |
| **Pod 역할** | 모두 같은 역할(단순 복제) | Pod마다 고유 역할(Primary, Secondary, Arbiter 등) |
| **Pod 이름** | 바뀌어도 무방 | 이름 자체가 식별자 → 절대 바뀌면 안 됨 |
| **장애 복구** | 같은 역할의 Pod를 새로 찍어내면 끝 | 죽은 Pod와 동일한 이름·역할로 재생성되어야 함 |
| **볼륨** | 필수가 아님. 있으면 모든 Pod가 한 볼륨을 공유해도 됨 | 각 Pod가 자기 전용 볼륨을 가져야 함 |
| **네트워크** | 외부 사용자 트래픽을 분산해서 받음 | 내부 시스템이 역할에 맞는 특정 Pod에 의도적으로 접속 |
| **K8s Controller** | ReplicaSet | StatefulSet |
| **연결 Service** | 일반 Service (ClusterIP/NodePort/LoadBalancer) | Headless Service |

> **MongoDB 예시**: Primary가 메인 DB(R/W), Secondary는 읽기 전용 복제본, Arbiter는 Primary 사망을 감지해 Secondary를 Primary로 승격시키는 감시자. Arbiter Pod가 죽으면 반드시 다시 Arbiter로 복구돼야 하고, 이름이 바뀌면 다른 시스템이 누가 누구인지 알 수 없게 된다.

### 1-2. StatefulSet vs ReplicaSet 동작 차이

| 항목 | ReplicaSet | StatefulSet |
|---|---|---|
| **Pod 이름** | `replica1-xxxxx` (해시 랜덤) | `statefulset1-0`, `-1`, `-2` (0부터 순차) |
| **Pod 생성 순서** | 동시에 한꺼번에 생성 | 한 개씩 순차 생성 (앞 Pod가 Ready되어야 다음) |
| **Pod 삭제 순서** | 동시에 한꺼번에 삭제 | 인덱스 큰 것부터 (`-2` → `-1` → `-0`) 순차 삭제 |
| **재생성 시 이름** | 새로운 해시로 다른 이름 | 삭제된 것과 **동일한 이름**으로 재생성 |

이 "고정 이름 + 순차 생성"이 Stateful 앱 클러스터링에 결정적이다. "0번이 먼저 떠야 1번이 거기에 붙는" 의존성을 안전하게 처리할 수 있다.

### 1-3. 볼륨 — `volumeClaimTemplates`로 Pod마다 PVC 자동 생성

| 동작 | ReplicaSet | StatefulSet |
|---|---|---|
| PVC 생성 | 사용자가 직접 미리 생성 | `volumeClaimTemplates`로 Pod마다 자동 생성 |
| PVC ↔ Pod | N:1 (모든 Pod가 한 PVC 공유) | 1:1 (Pod마다 전용 PVC) |
| 생성된 PVC 이름 | 사용자가 정함 | `<volumeClaimTemplate.name>-<pod-name>` (예: `volume1-statefulset1-0`) |
| Pod 재생성 시 | 동일 PVC에 다시 붙음 | 같은 이름으로 재생성된 Pod가 **자기가 쓰던 PVC**에 다시 붙음 |
| `replicas: 0`으로 축소 | Pod 삭제 (PVC는 사용자 책임) | Pod는 순차 삭제, **PVC는 남는다** (데이터 보호) |

> **PVC를 자동 삭제하지 않는 이유**: 볼륨에는 운영 데이터가 있다. 사고 방지를 위해 사용자가 직접 정리해야 한다.

### 1-4. Headless Service — 특정 Pod를 콕 집어 부르기

StatefulSet 매니페스트의 `serviceName`에 Headless Service 이름을 넣고 동명의 Headless Service(`clusterIP: None`)를 만들면 각 Pod에 예측 가능한 DNS가 붙는다.

```
<pod-name>.<service-name>.<namespace>.svc.cluster.local
예: statefulset1-0.headless1.default.svc.cluster.local
```

일반 Service는 ClusterIP 한 개로 트래픽을 분산하지만, Headless Service는 IP 없이 DNS만 제공해서 내부 시스템이 도메인으로 원하는 Pod(`-0`, `-1`, `-2`)를 직접 지명해 접속할 수 있다.

### 1-5. StatefulSet YAML 예제

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: statefulset1
spec:
  replicas: 3
  serviceName: headless1          # 아래 Headless Service와 매칭
  selector:
    matchLabels:
      type: db
  template:
    metadata:
      labels:
        type: db
    spec:
      containers:
      - name: container
        image: kubetm/app:v1
        volumeMounts:
        - name: volume1            # ← volumeClaimTemplates의 name과 일치해야 함
          mountPath: /applog
      terminationGracePeriodSeconds: 10
  volumeClaimTemplates:
  - metadata:
      name: volume1                # ← volumeMounts.name과 매칭
    spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 1G
---
apiVersion: v1
kind: Service
metadata:
  name: headless1
spec:
  clusterIP: None                   # Headless 핵심 — IP를 만들지 않음
  selector:
    type: db
  ports:
  - port: 80
```

> **흔한 함정**: `volumeClaimTemplates.metadata.name`과 컨테이너의 `volumeMounts.name`이 다르면 Pod가 정상적으로 만들어지지 않는다.

### 1-6. 실습으로 검증한 핵심 동작

`terminationGracePeriodSeconds: 10`을 주면 동작 순서가 눈에 잘 들어온다.

**(a) 생성·삭제**

| 시나리오 | ReplicaSet 동작 | StatefulSet 동작 |
|---|---|---|
| `replicas: 1 → 3` | 추가 Pod 2개가 **동시에** 생성 | `-1` 생성 → Ready → `-2` 생성 (한 번에 하나씩) |
| Pod 1개 삭제 | 다른 해시 이름 새 Pod 생성 후 10초 뒤 기존 Pod 삭제 | 기존 Pod 완전 삭제 후 **동일한 이름**으로 재생성 |
| `replicas: 0` 축소 | 모든 Pod 동시에 삭제 | `-2` → `-1` → `-0` 순으로 10초 간격 순차 삭제 |

**(b) 볼륨**
- ReplicaSet은 같은 PVC를 모든 Pod가 공유 → Pod 0에서 만든 파일이 Pod 1·2에서도 보인다.
- StatefulSet은 Pod별 전용 PVC → Pod 0의 파일은 Pod 1에서 보이지 않는다.
- 어떤 Pod를 삭제해도 같은 이름으로 다시 만들어지면서 **이전 PVC에 다시 붙는다 → 데이터 보존**.
- `replicas: 0`으로 줄여도 **PVC는 그대로 남는다** (수동 정리 필요).

**(c) Headless Service로 개별 Pod 접근**

```bash
# Headless 서비스 자체에 nslookup → 연결된 모든 Pod의 IP 목록
nslookup stateful-headless

# 특정 Pod에 직접 접근 → <pod-name>.<service-name>
curl statefulset1-0.stateful-headless
curl statefulset1-1.stateful-headless
```

---

## [발표] 2. Ingress — 외부 트래픽을 도메인·Path로 라우팅

### 2-1. Ingress란? 왜 쓰나

클러스터 외부의 HTTP/HTTPS 트래픽을 도메인 이름과 URL Path 기준으로 내부 Service에 라우팅. 전통 인프라의 L4/L7 스위치 역할을 K8s 안에서 선언적으로 표현.

| 유스케이스 | 설명 |
|---|---|
| **Service Load Balancing** | 한 도메인 안에서 `/customer`, `/order` 같은 Path별로 다른 Service에 분기. 별도 L4/L7 장비 불필요. |
| **Canary 업그레이드** | 같은 도메인 트래픽 중 N%만 v2 Pod로, 또는 특정 헤더 값만 v2로 보내 점진 검증. |
| **HTTPS 종료(SSL Termination)** | Ingress에 인증서를 달아 외부 HTTPS를 받고 내부는 HTTP로 처리. Pod에서 인증서 관리가 부담될 때 유용. |

### 2-2. Ingress 동작 구조 — Rule만으로는 아무 일도 안 일어난다

**Ingress 오브젝트는 단순한 "규칙 명세"**일 뿐이다. K8s 기본 설치만으로는 룰을 실행할 주체가 없으므로 별도 **Ingress Controller**(Nginx, Kong 등)를 설치해야 한다.

```
[외부 사용자]
      ↓
[NodePort/LoadBalancer Service]   ← 외부 진입점
      ↓
[Nginx Ingress Pod]                ← Ingress Rule을 watch해 라우팅
      ↓
[svc-shopping] [svc-customer] [svc-order]
      ↓             ↓               ↓
   [shopping]   [customer]      [order] Pod
```

> Nginx Pod로 트래픽이 흘러야 하므로 외부 진입용 Service(NodePort 또는 LoadBalancer)를 Nginx Pod에 붙여야 한다.

### 2-3. Service Load Balancing — Path 기반 분기

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-service
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: svc-shopping
            port: { number: 8080 }
      - path: /customer
        pathType: Prefix
        backend:
          service:
            name: svc-customer
            port: { number: 8080 }
      - path: /order
        pathType: Prefix
        backend:
          service:
            name: svc-order
            port: { number: 8080 }
```

`http://<master-ip>:<nodeport>/` → shopping, `/customer` → 고객센터, `/order` → 주문으로 분기.

### 2-4. Canary 업그레이드 — Annotation으로 비율·헤더 제어

같은 호스트로 v1 Ingress가 운영 중일 때 **두 번째 Ingress를 같은 호스트로 추가하고 Annotation을 붙이면** Canary가 된다.

**(a) 비율 분산 — `canary-weight`**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"   # 트래픽의 10%만 v2로
spec:
  rules:
  - host: www.app.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: svc-v2
            port: { number: 8080 }
```

`while true; do curl www.app.com; sleep 1; done` 같은 식으로 트래픽을 보내면 약 10% 비율로 v2가 응답한다. 검증 후 weight를 100으로 올리거나 v1을 내려서 전환을 마무리한다.

**(b) 헤더 매칭 — 특정 타겟만 100% 분기**

```yaml
annotations:
  nginx.ingress.kubernetes.io/canary: "true"
  nginx.ingress.kubernetes.io/canary-by-header: "Accept-Language"
  nginx.ingress.kubernetes.io/canary-by-header-value: "kr"
```

`curl -H "Accept-Language: kr" www.app.com`처럼 헤더 일치 트래픽 전부가 v2로, 그 외는 v1으로. 특정 지역·디바이스 그룹만 골라 신 버전을 시험할 때 쓴다.

### 2-5. HTTPS — TLS Secret 연결

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-https
spec:
  tls:
  - hosts:
    - www.app.com
    secretName: secret-https      # 인증서를 담은 Secret
  rules:
  - host: www.app.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: svc-https
            port: { number: 8080 }
```

Secret은 `openssl`로 인증서를 생성한 뒤 `kubectl create secret tls secret-https --cert=tls.crt --key=tls.key`로 만든다. 적용 후 사용자는 반드시 `https://www.app.com`으로 접근해야 연결되고, HTTP는 차단된다.

### 2-6. 실습 시 도메인이 안 풀릴 때 — hosts 파일 매핑

`www.app.com` 같은 도메인은 공인 DNS에 없으므로 hosts 파일에 직접 매핑 등록 필요.

```bash
# Linux/Mac (Master 노드 등)
sudo sh -c 'echo "192.168.0.30  www.app.com" >> /etc/hosts'

# Windows
# C:\Windows\System32\drivers\etc\hosts 에 같은 형식으로 추가
```

### 2-7. Ingress 사용 체크리스트

1. Ingress Controller(Nginx 등)가 설치되어 있는가?
2. Ingress Controller Pod에 외부 진입용 Service(NodePort/LoadBalancer)가 붙어 있는가?
3. Ingress 룰의 호스트/Path가 백엔드 Service 이름·포트와 정확히 매칭되는가?
4. (Canary) `canary: "true"` Annotation이 두 번째 Ingress에 함께 들어가 있는가?
5. (HTTPS) TLS Secret이 같은 네임스페이스에 존재하는가?

---

## [발표] 3. AutoScaler — HPA, VPA, CA

### 3-1. 3종 AutoScaler 한눈에 비교

| 종류 | 풀네임 | 무엇을 조정하나 | 방향 | 적합한 앱 |
|---|---|---|---|---|
| **HPA** | Horizontal Pod Autoscaler | Pod **개수** | 수평 (Scale Out/In) | Stateless |
| **VPA** | Vertical Pod Autoscaler | Pod의 **CPU/Memory 자원** | 수직 (Scale Up/Down, Pod 재시작 동반) | Stateful |
| **CA** | Cluster Autoscaler | 클러스터의 **노드 수** | 노드 추가/삭제 (클라우드 프로바이더 연동) | 인프라 레벨 |

> **주의**: 한 컨트롤러에 HPA와 VPA를 동시에 달면 충돌해 작동하지 않는다.

### 3-2. HPA가 필요한 이유

ReplicaSet/Deployment로 Pod가 N개 떠 있는데 트래픽이 폭증해 자원이 한계에 닿으면 Pod가 죽을 수 있다. HPA가 자원 사용량을 감시하다가 위험 수준이면 Controller의 `replicas`를 자동 증가(**Scale Out**), 부하가 줄면 다시 감소(**Scale In**)시킨다.

**권장 조건**:
- **빠르게 기동되는 앱** (부하 급증 시 빠르게 따라잡아야 함)
- **Stateless 앱** (Stateful은 Pod마다 역할이 있어 "어떤 역할의 Pod를 늘릴지" 판단 불가 → VPA 사용)

### 3-3. HPA 메트릭 경로 — Metrics Server가 왜 필요한가

```
[Container] → [cAdvisor (kubelet 내부)] → [Metrics Server (Add-on)] → [kube-apiserver의 metrics API]
                                                                              ↑
                                                                            [HPA가 15초 주기로 조회]
```

| 컴포넌트 | 역할 |
|---|---|
| **cAdvisor** | 각 노드 kubelet 내부에서 Container의 CPU/Memory 측정 |
| **Metrics Server** | kubelet으로부터 메트릭 수집 → kube-apiserver의 `metrics.k8s.io` API로 노출. **별도 설치 필수** |
| **HPA** | kube-apiserver의 metrics API를 15초 주기로 조회 |
| (옵션) **Prometheus + Custom Adapter** | CPU/Memory 외 Pod 패킷 수, Ingress 요청 수 같은 커스텀 메트릭 제공 |

> Metrics Server가 없으면 `kubectl top pod`도, HPA도 동작하지 않는다.

### 3-4. HPA YAML과 Replica 계산 공식

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hpa-cpu
spec:
  scaleTargetRef:               # 누구를 스케일할지
    apiVersion: apps/v1
    kind: Deployment
    name: deployment-cpu
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization       # request 대비 % 기준
        averageUtilization: 50  # 평균 50% 초과 시 Scale Out
```

**target.type 3가지**:

| Type | 설명 |
|---|---|
| `Utilization` | Pod의 `requests` 대비 평균 사용률(%) — 가장 많이 쓰는 기본 |
| `AverageValue` | 절대 평균 값 (예: `100Mi`, `200m`) |
| `Value` | 단일 합산 값 |

**Replica 계산 공식**:

```
desiredReplicas = ceil( currentReplicas × (currentMetric / targetMetric) )
```

예시 (`currentReplicas=2`, target = `100m`):

| 현재 평균 CPU | 계산식 | desired |
|---|---|---|
| 100m | 2 × (100 / 100) | 2 (변화 없음) |
| 300m | 2 × (300 / 100) | 6 (Scale Out) |
| 50m  | 6 × (50 / 100)  | 3 (Scale In) |

`min/max`로 상·하한이 잡히므로 그 범위 안에서만 움직인다.

### 3-5. Metric Type 종류 — 다른 오브젝트로도 트리거 가능

| Metric Type | 데이터 출처 | 예시 |
|---|---|---|
| `Resource` | Metrics Server (cAdvisor) | Pod CPU/Memory |
| `Pods` | Custom Metrics API (Prometheus 등) | Pod로 들어오는 패킷 수 |
| `Object` | Custom Metrics API | Ingress가 받은 요청 수 |
| `External` | External Metrics API | 클라우드 큐(SQS) 길이 등 |

`Pods`/`Object`/`External`은 Prometheus + Custom Metrics Adapter 설치가 전제.

### 3-6. HPA 실습 — 부하 주입 → Scale Out → 부하 중단 → Scale In

**(a) Metrics Server 설치 및 확인**

```bash
# 설치 (공식 매니페스트)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# API 등록 확인 (AVAILABLE이 True면 정상)
kubectl get apiservices | grep metrics

# 1~2분 후 메트릭 조회 가능
kubectl top node
kubectl top pod
```

**(b) HPA 모니터링**

```bash
kubectl get hpa -w   # watch 모드: 메트릭/Replica 변화가 즉시 표시
```

`TARGETS` 컬럼은 `<현재값>/<타겟값>`, `REPLICAS`는 현재 Pod 수.

**(c) 부하 주입 → Scale Out**

```bash
# NodePort로 노출된 서비스에 짧은 간격으로 트래픽
while true; do curl -s http://<node-ip>:30001 > /dev/null; sleep 0.01; done
```

부하가 올라가면 `TARGETS`의 현재값이 50%를 넘기 시작하고, HPA가 공식대로 Replica를 **6 → 8 → 10(max)**까지 단계적으로 증가시킨다.

**(d) 부하 중단 → Scale In은 5분 지연**

부하를 끊으면 메트릭은 즉시 떨어지지만 Pod는 바로 줄지 않는다. **기본 5분(`--horizontal-pod-autoscaler-downscale-stabilization`) 안정화 시간**이 지나야 천천히 줄인다. Scale Out은 빠르게, Scale In은 신중하게 하는 정책이다.

**(e) Memory 기반 HPA — `AverageValue` 예시**

```yaml
metrics:
- type: Resource
  resource:
    name: memory
    target:
      type: AverageValue
      averageValue: 20Mi        # Pod당 평균 20Mi 초과 시 Scale Out
```

흐름은 CPU 시나리오와 동일, 트리거 기준만 메모리 절대값.

### 3-7. VPA / CA — 핵심만

- **VPA**: Stateful 앱처럼 Pod 수 증가가 어렵고 자원만 키워야 하는 경우. 자원 부족 감지 시 Pod를 **재시작**하면서 `requests/limits`를 키운다(Scale Up). 같은 컨트롤러에 HPA와 동시 사용 금지.
- **CA**: 모든 노드의 자원이 부족해 새 Pod를 어디에도 배치할 수 없을 때, 클라우드 프로바이더(AWS/GCP/Azure)에 노드 추가 요청. 반대로 노드가 한가해지면 Pod를 다른 노드로 옮기고 빈 노드를 삭제해 비용 절감.

### 3-8. AutoScaler 사용 체크리스트

1. **Stateless 앱**이면 HPA, **Stateful 앱**이면 VPA를 검토.
2. **Metrics Server**(또는 Prometheus + Adapter)가 설치되어 있는가? `kubectl top` 명령이 동작해야 HPA도 동작한다.
3. Pod에 **`resources.requests`가 설정되어 있는가?** Utilization 기반 HPA는 requests가 기준이라 없으면 동작하지 않는다.
4. 같은 컨트롤러에 HPA와 VPA를 동시에 달지 않았는가?
5. Scale In의 5분 지연을 감안해 운영·테스트 시나리오를 잡는다.

---

## [발표] 4. 마무리 — 세 주제를 관통하는 한 줄

| 주제 | 한 문장 |
|---|---|
| **StatefulSet** | "각 Pod에 고정된 이름과 전용 볼륨을 부여하는 Controller — Headless Service와 짝지어 역할 기반 접속을 가능하게 한다." |
| **Ingress** | "K8s 안에서 도메인·Path 기반 라우팅을 선언적으로 표현하는 규칙 — 동작은 별도로 설치한 Ingress Controller가 한다." |
| **AutoScaler** | "부하 변화에 맞춰 Pod 수(HPA), Pod 자원(VPA), 노드 수(CA)를 자동으로 조정 — Metrics Server가 데이터 공급선이다." |

---

# Kubernetes Architecture — Component, Networking, Storage, Logging

지금까지는 "사용자 입장에서 쓰는 Kubernetes"를 봤다면, 여기서부터는 **클러스터 내부가 어떻게 돌아가는지** — 컴포넌트, 네트워킹, 스토리지, 로깅 네 축의 아키텍처를 정리한다. 강사가 별도 강의(아키텍처 편)에서 다룬 내용으로, 운영자/플랫폼 엔지니어 관점에서는 사실상 필수.

## 전체 개요

쿠버네티스 아키텍처는 네 개 축으로 나눠 본다.

- **Components**: 마스터 노드의 **컨트롤 플레인 컴포넌트**와 워커 노드의 **워커 컴포넌트**가 어떤 역할을 하는지.
- **Networking**: Pod 네트워크(컨테이너 간, Pod 간 통신)와 Service 네트워크.
- **Storage**: PV/PVC, 볼륨 플러그인, 액세스 모드, CSI.
- **Logging & Monitoring**: Core 파이프라인 + Service 파이프라인.

쿠버네티스 클러스터는 **마스터 1대 + 워커 N대** 구조이며, 마스터는 클러스터 전체를 통제하고 워커는 실제 컨테이너를 돌린다.

---

## Components — 마스터/워커가 하는 일

### 노드 구성

```
┌─────────────────────────── Master Node ────────────────────────────┐
│  etcd  │  kube-apiserver  │  kube-scheduler  │  controller-manager │
└────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ (kubectl)
                              ▼
┌─────────────── Worker Node ───────────────┐ ┌──── Worker Node ────┐
│  kubelet  │  kube-proxy  │  Container Runtime (Docker)            │
└───────────────────────────────────────────┘ └─────────────────────┘
```

- 마스터의 주요 컴포넌트(`etcd`, `kube-apiserver`, `kube-scheduler`, `controller-manager`)는 **Static Pod 형태로 기동**된다.
- 마스터의 `/etc/kubernetes/manifests/` 폴더에 각 컴포넌트의 YAML 파일이 들어 있고, **쿠버네티스 부팅 시 kubelet이 이 파일들을 읽어서 Static Pod로 띄운다.**
- 워커 노드에는 `kubelet`과 컨테이너 런타임(예: Docker)이 OS 데몬으로 설치되어 있다.

### Pod 생성 흐름

```
사용자 (kubectl)
    │
    ▼
[kube-apiserver] ──► [etcd]      (Pod 스펙 저장)
    ▲
    │ watch
    │
[kube-scheduler] ── 노드 자원 체크 후, Pod에 노드 정보 부착
    │
    ▼
[kube-apiserver] ──► [etcd]      (Pod에 nodeName 업데이트)
    ▲
    │ watch (각 노드의 kubelet이 자기 노드 붙은 Pod를 찾음)
    ▼
[kubelet] ──► [Container Runtime]  컨테이너 생성
         └──► [kube-proxy]          네트워크 연결
```

1. **kube-apiserver**: 클러스터의 모든 요청을 받는 입구이자, 모든 컴포넌트가 거쳐가는 **중앙 허브**. 받은 요청을 etcd에 저장한다.
2. **etcd**: 쿠버네티스 모든 오브젝트 상태를 저장하는 **분산 KV DB**.
3. **kube-scheduler**: 각 노드의 자원 사용 현황을 수시로 체크하면서 apiserver에 **watch**를 걸어 "노드가 할당되지 않은 Pod"가 들어오면 적절한 노드를 골라 Pod에 `nodeName`을 붙여준다.
4. **kubelet**: 각 워커 노드에 상주하며 apiserver에 watch를 걸고 "자기 노드 이름이 붙은 Pod"가 있는지 감시한다. 발견하면 컨테이너 런타임에 컨테이너 생성 요청 + kube-proxy에 네트워크 생성 요청을 보낸다.
5. **kube-proxy**: DaemonSet으로 모든 노드에 떠 있는 Pod. 새 컨테이너에 네트워크가 통하도록 iptables/IPVS 룰을 설정.

핵심 패턴은 **apiserver를 중심으로 한 watch 기반의 느슨한 결합**이다. 컴포넌트끼리 직접 호출하지 않고, 모두 apiserver를 거쳐 상태를 주고받는다.

### Deployment 생성 흐름 — Controller Manager 체인

controller-manager 파드 안에는 Deployment, ReplicaSet, Endpoint, Node, Namespace 등 **여러 컨트롤러가 각자 스레드 형태로 돌고 있다.** 각 컨트롤러는 자기 담당 오브젝트에 watch를 걸어둔 상태.

```
kubectl create deployment --replicas=N
        │
        ▼
[kube-apiserver] ─► [etcd]                     (Deployment 저장)
        ▲
        │ watch
[Deployment Controller] ─► ReplicaSet 생성 요청
        ▼
[kube-apiserver] ─► [etcd]                     (ReplicaSet 저장)
        ▲
        │ watch
[ReplicaSet Controller] ─► replicas 수만큼 Pod 생성 요청
        ▼
[kube-apiserver] ─► [etcd]                     (Pod N개 저장)
        ▼
[kube-scheduler] → 각 Pod에 노드 할당
        ▼
[kubelet] → Docker / kube-proxy → 컨테이너 + 네트워크
```

즉, **Deployment → ReplicaSet → Pod**는 controller-manager 안의 서로 다른 컨트롤러들이 watch를 통해 **계단식으로 트리거**되는 구조다.

---

## Networking — Pod 네트워크 vs Service 네트워크

### 두 개의 네트워크 영역

쿠버네티스 설치 시 두 개의 CIDR을 설정한다.

- **Pod Network CIDR**: Pod에 부여될 IP 대역.
- **Service Network CIDR**: Service 오브젝트에 부여될 가상 IP 대역.

기본 동작은 쿠버네티스가 제공하는 `kubenet` 정도로 충분하지만, 기능이 제한적이라 실무에서는 **CNI(Container Network Interface)** 표준에 맞는 플러그인(Calico, Flannel, Cilium 등)을 설치해서 쓴다. 이 강의는 **Calico** 기준이며, **베어메탈 환경**과 클라우드(EKS/GKE)에서는 같은 Calico여도 다르게 동작한다는 점에 유의.

### Pod 내부 — pause 컨테이너와 네트워크 네임스페이스 공유

Pod를 만들면 사용자가 정의한 컨테이너 외에 **`pause` 컨테이너**가 자동으로 함께 생성된다. 이 pause 컨테이너가 Pod의 **네트워크 인터페이스와 IP**를 가지고 있고, 같은 Pod의 모든 컨테이너는 이 **네트워크 네임스페이스를 공유**한다.

- 결과적으로 한 Pod 안의 컨테이너들은 동일한 IP를 공유하고, **포트로만 서로 구분**된다.
- 같은 Pod 안에서는 `localhost:포트`로 서로 부를 수 있다.

호스트 네트워크 네임스페이스에는 Pod 하나당 **가상 인터페이스(veth)** 가 1:1로 생성되어 pause 컨테이너의 인터페이스와 연결된다. 즉 노드 ↔ Pod는 veth 페어로 이어진다.

### 같은 노드의 Pod 간 통신 — kubenet vs Calico

#### kubenet (기본, 잘 안 씀)
- 노드마다 `cbr0`라는 **컨테이너 브릿지**를 만들고 veth들을 거기에 꽂아 넣는다.
- 브릿지 CIDR은 노드 네트워크 대역을 참고해 더 작은 대역으로 잘려 들어가는데, **노드당 약 255개 Pod**까지밖에 못 만든다(주요 단점).
- 라우터 역할은 NAT가 맡는다 — Pod IP 대역이면 브릿지로 내리고, 그 외 IP면 호스트로 올린다.

#### Calico
- veth가 브릿지 없이 **라우터에 바로 꽂힌다.** 같은 노드의 Pod 간 통신은 이 라우터 레이어가 직접 라우팅.
- Pod IP CIDR이 kubenet보다 훨씬 크게 잡혀, **노드당 더 많은 Pod**를 실을 수 있다.
- 라우터 위에는 **오버레이 네트워크 레이어(IPIP 또는 VXLAN)** 가 있어서 타 노드 Pod 통신을 책임진다.

### 타 노드 Pod 간 통신 — 오버레이 네트워크

Pod A (Node B) → Pod B (Node A)로 호출했을 때의 흐름.

```
[Pod A]
  │ 목적지: Pod B IP (20.111.156.7)
  ▼
[Calico 라우터] ── 라우터에 그 IP가 없음
  │
  ▼
[오버레이 계층 (IPIP/VXLAN)]
  │ 패킷을 "노드 A의 호스트 IP"로 감싸고 (encapsulation)
  │ 원래 Pod IP는 내부에 숨김
  ▼
[Node B 호스트 인터페이스] ──► [Node A 호스트 인터페이스]
  │
  ▼
[Node A 오버레이 계층] decapsulation → 원래 Pod IP 복원
  │
  ▼
[Node A 라우터] → 해당 IP의 veth → [Pod B]
```

Calico는 클러스터의 **어느 Pod IP 대역이 어느 노드에 있는지**를 알고 있어서, 오버레이 레이어가 올바른 호스트로 패킷을 보낸다.

### Service Network와 kube-proxy

Pod에 Service를 붙이면 일어나는 일.

1. Service에 **클러스터 가상 IP**가 발급된다 (Service CIDR 범위).
2. 같은 시점에 **kube-dns**에 `service-name → service-IP` 도메인이 등록된다.
3. Pod이 정상 기동 상태라면 **Endpoint 오브젝트**가 생성돼 "이 서비스 IP는 이 Pod IP들로 연결됨"이라는 매핑을 보관한다.
4. apiserver가 Endpoint를 감시하고, 모든 노드의 **kube-proxy(DaemonSet)** 에게 매핑 정보를 전달한다.
5. kube-proxy는 그 매핑을 **NAT 룰**로 노드 커널에 설치한다.

따라서 Pod에서 `service-name`을 부르면 → kube-dns가 Service IP를 알려주고 → 노드의 NAT 룰이 그 IP를 적절한 Pod IP로 바꿔준다. **Service 오브젝트의 "실체"는 결국 노드 커널의 NAT 룰**이며, Service를 삭제하면 apiserver가 이를 감지해 kube-proxy에 룰 삭제를 지시한다.

### kube-proxy의 세 가지 Proxy Mode

| 모드 | 동작 방식 | 특징 |
|---|---|---|
| **userspace** | iptables가 Service CIDR 트래픽을 kube-proxy(유저 프로세스)로 보내고, kube-proxy가 직접 Pod IP로 NAT | 모든 트래픽이 kube-proxy를 지나가 **성능/안정성 나쁨**, 거의 안 씀 |
| **iptables** (기본) | kube-proxy가 iptables 룰에 직접 매핑을 등록, 커널이 NAT 처리 | 기본값. 성능과 안정성이 훨씬 좋음 |
| **IPVS** | 리눅스 커널의 L4 로드밸런서(IPVS)에 룰 등록 | 낮은 부하에선 iptables와 비슷, **부하가 커질수록 IPVS가 우세** |

### Calico에서의 Service 트래픽 (ClusterIP vs NodePort)

#### ClusterIP
```
Pod A ──► Service IP
            │
            ▼
       [Calico 라우터의 NAT]   서비스 IP → Pod B IP
            │
            ▼
       [오버레이] encapsulation → 타 노드 Pod B에 도달
```

#### NodePort
- 각 노드의 kube-proxy가 자기 노드의 **30000번대 포트**를 연다.
- 외부에서 `호스트IP:노드포트`로 들어오면 → iptables 룰이 트래픽을 Calico 라우터로 보냄 → ClusterIP와 같은 경로로 Pod에 도달.

---

## Storage — PV, PVC, 볼륨 플러그인, CSI

### PV를 만드는 세 가지 방법

1. **PV 직접 생성 → PVC 직접 연결.** 가장 단순한 방식.
2. **StorageClass로 그룹핑.** StorageClass를 그룹처럼 만들어 두고 PV에 소속을 지정. PVC가 그 StorageClass를 지정하면, **해당 그룹의 PV 중 스펙이 맞는 PV**와 자동 연결된다.
3. **StorageClass로 동적 프로비저닝.** StorageClass에 **provisioner**를 지정해 두면, PVC가 만들어질 때 provisioner가 **PV를 자동 생성**해서 PVC에 붙여준다.

### PV의 기본 속성

- **Capacity**: 볼륨 용량
- **AccessMode**: RWO / RWX / ROX
- **VolumeMode / Volume Plugin**: PV의 실체를 결정하는 핵심 옵션

### 대표 Volume Plugin

| 플러그인 | 설명 |
|---|---|
| **hostPath** | 워커 노드의 로컬 디렉토리를 PV의 볼륨으로 사용. 노드 종속적 |
| **NFS** | 외부 NFS 서버에 연결. **OS에 NFS 클라이언트가 설치돼 있어야 동작** |
| **클라우드 볼륨** (AWS EBS, GCP PD 등) | 클라우드 서비스의 볼륨에 연결 |
| **벤더 솔루션** (Ceph, Portworx 등) | 솔루션 회사가 만든 플러그인을 통해 직접 연결 |

쿠버네티스 공식 문서에 사용 가능한 플러그인 리스트와 **provisioner 내장 여부**가 정리돼 있다.

### CSI (Container Storage Interface)

쿠버네티스에 미리 반영되지 않은 볼륨 솔루션이나 최신 버전을 적용하려면 **CSI**를 사용한다. 쿠버네티스 표준 인터페이스에 맞춰 만든 **외부 플러그인**으로, 사용자는 솔루션 제공자가 안내하는 방식으로 클러스터에 설치만 하면 된다.

요즘은 한 발 더 나아가 **볼륨 솔루션 자체를 컨테이너로 클러스터 안에 띄우고**, CSI 플러그인까지 한 번에 설치하는 방식이 흔하다 (예: Longhorn). 사용자는 별도 외부 스토리지 없이도 PV/PVC만으로 분산 스토리지를 쓸 수 있다.

### 스토리지 타입과 AccessMode

| 솔루션 | 타입 | 지원 AccessMode |
|---|---|---|
| NFS | File | RWO + RWX (+ ROX) |
| 클라우드 (EBS 등) | Block / File / Object 모두 | 솔루션마다 다름 |
| 대부분의 서드파티 벤더 | 주로 File | RWO + RWX |
| CSI 기반 컨테이너 솔루션 | 모든 타입 가능 | 솔루션 가이드 확인 필수 |

**핵심 차이**:
- **File / Object 스토리지**는 RWX 지원 → 다른 노드의 Pod들도 동시에 연결 가능. **공유 데이터, 백업, 이미지 저장** 용도. Deployment에 PVC 붙일 때 주로 사용.
- **Block 스토리지**는 기술적으로 **단일 노드 마운트**만 가능 → 한 노드의 여러 Pod는 가능하지만, 두 노드가 동시에 같은 블록 볼륨을 못 쓴다. **RWO만 지원.** **DB 데이터처럼 빠른 R/W가 필요한 경우**에 적합. StatefulSet은 Pod마다 PVC를 새로 만들기 때문에 Block 스토리지 특성과 잘 맞는다 → 대부분의 DB 솔루션이 **Block + StatefulSet** 조합.

### CSI 내부 구조 (개념만)

CSI 플러그인을 설치하면 두 종류의 Pod가 생긴다.

- **Controller Plugin** (Deployment): CSI의 주요 기능을 담당. PVC 감시 후 PV 자동 생성(`csi-provisioner`), 볼륨 크기 변경(`csi-resizer`), 스냅샷(`csi-snapshotter`), Pod-볼륨 연결(`csi-attacher`).
- **Node Plugin** (DaemonSet): 각 노드에서 실제 볼륨 생성을 담당.

볼륨 생성 흐름 (Longhorn 예시):
1. PVC 생성 → `csi-provisioner`가 보고 PV 생성 → PVC와 연결
2. CSI 플러그인이 노드의 **볼륨 매니저 → 엔진**으로 요청을 내려 실제 볼륨을 만듦
3. Pod이 PVC를 붙이면 **VolumeAttachment** 오브젝트가 생기고, `csi-attacher`가 이를 보고 Pod와 볼륨을 연결
4. 솔루션 자체 UI는 매니저와 직접 통신해서 모니터링/제어를 제공

---

## Logging & Monitoring

### Core Pipeline (쿠버네티스 기본)

- **모니터링**: 각 노드의 kubelet에 내장된 **cAdvisor**가 CPU/메모리/디스크 사용량을 수집 → **metrics-server**로 집계 → 사용자가 `kubectl top`로 조회.
- **로깅**: kubelet이 컨테이너 로그 파일을 가리키도록 링크를 만들어 두고, 사용자가 `kubectl logs`로 그 파일을 조회.

### 노드 레벨 로깅 — 로그 파일이 만들어지는 경로

```
[App 컨테이너 stdout/stderr]
        │
        ▼
[Docker logging driver]   /etc/docker/daemon.json 설정
        │                  컨테이너당 3개 파일, 각 100MB까지
        ▼
/var/lib/docker/containers/<container-id>/<container-id>-json.log
        │
        │ (Kubernetes가 링크 생성)
        ▼
/var/log/pods/<namespace>_<pod>_<uid>/<container>/0.log
        │
        │ (또 한 번 링크 — 컨테이너 단위 이름)
        ▼
/var/log/containers/<pod>_<namespace>_<container>-<id>.log
```

**주의**: 앱이 단순히 파일에 로그를 써도 Docker가 못 본다. **반드시 stdout/stderr로 출력**해야 하며, 언어별로 stdout 로깅 방식은 다르다.

**Pod이 죽으면 이 모든 링크와 로그도 사라진다.** 그래서 `kubectl logs`는 살아 있는 Pod의 실시간 로그만 볼 수 있고, 이것이 **클러스터 레벨 로깅이 필요한 이유**다.

### Termination Message Path

기본값으로 컨테이너 안에 `/dev/termination-log` 파일이 설정돼 있다. 앱이 죽기 전 (Liveness Probe 실패 등) **여기에 에러 로그를 쓰면**, 쿠버네티스가 이를 읽어 Pod의 **status 상세 부분**에 표시해준다. 로그 파일을 뒤지지 않고도 `kubectl describe pod`로 재시작 원인을 즉시 확인할 수 있다.

### Service Pipeline (별도 플러그인)

```
[각 노드의 DaemonSet Agent] ─► [수집/분석 서버 + 저장소] ─► [Web UI]
```

- **Agent (DaemonSet)**: 노드 레벨 로그 경로 또는 Docker logging driver를 통해 로그를 읽어 수집 서버로 보냄.
- **수집/분석 서버**: 매트릭/로그를 저장. 별도 저장소 권장.
- **Web UI**: 사용자에게 시각화.

### 클러스터 레벨 로깅 패턴

1. **Node Logging Agent (DaemonSet)**: 가장 일반적. 노드 레벨 로그 파일을 에이전트가 읽어서 수집 서버로 푸시. Docker logging driver를 직접 에이전트로 보내게도 할 수 있다.
2. **Sidecar Container (Streaming)**: 메인 컨테이너가 여러 종류의 로그를 파일로 분리해 쓰면, **사이드카 컨테이너가 각 파일을 읽어 stdout으로 다시 출력**. 그러면 컨테이너 이름 단위로 로그 파일이 분리돼 수집이 깔끔해진다.
3. **Sidecar Logging Agent**: 로깅 에이전트를 **Pod 안에 사이드카로 직접** 넣음. 메인 컨테이너는 stdout 안 써도 되고, 사이드카가 직접 수집 서버로 보낸다.

### 대표 스택

| 스택 | 구성 |
|---|---|
| **ELK** | Elasticsearch + Logstash + Kibana |
| **EFK** | Elasticsearch + Fluentd/Fluent Bit + Kibana (쿠버네티스에선 Fluent Bit 선호) |
| **Prometheus + Grafana** | 매트릭 모니터링의 사실상 표준 |
| **PLG** | Promtail + Loki + Grafana (로그용 경량 스택) |

#### PLG 스택 동작
```
모든 노드(DaemonSet) ──► [Promtail]
                          │  /var/log/pods 경로 읽음 (ConfigMap으로 설정)
                          ▼
                   [Loki Service] (StatefulSet 형태)
                          │
                          ▼
                   [Grafana (Deployment)] ── UI로 LogQL 쿼리
```

---

1. **"모든 컴포넌트는 apiserver를 통해 대화한다"가 쿠버네티스 설계의 핵심이다.** scheduler → kubelet으로 직접 호출하지 않고, 둘 다 apiserver에 watch를 걸고 etcd의 상태 변화로 트리거된다. 이 덕분에 **컴포넌트가 죽었다 살아나도 상태가 깨지지 않는다** — apiserver/etcd만 살아 있으면 나머지는 재시작하면서 다시 watch를 걸어 따라잡는다.

2. **마스터 컴포넌트조차 Static Pod라는 점이 흥미롭다.** apiserver, scheduler, controller-manager가 모두 `/etc/kubernetes/manifests`의 YAML로 떠 있는 Pod라는 건, **쿠버네티스가 자기 자신을 자기 방식으로 관리**하고 있다는 의미다. kubelet은 apiserver 없이도 manifests만 보고 Static Pod를 띄울 수 있어서, 부팅 순서의 닭-달걀 문제가 해결된다.

3. **Service 오브젝트는 사실 노드 커널의 NAT 룰이다.** Service IP는 어디에도 실재하지 않는 가상 IP고, 각 노드의 iptables/IPVS 룰이 "이 IP가 호출되면 저 Pod IP로 바꿔라"는 매핑을 들고 있을 뿐이다. kube-proxy를 DaemonSet으로 깔아야 하는 이유, 그리고 Service의 **L4 동작 한계**(L7 라우팅이 안 되는 이유)가 여기서 자연스럽게 따라온다.

4. **Calico의 IPIP/VXLAN 오버레이가 "Pod IP는 어디서나 같다"는 추상화를 받쳐준다.** 노드 경계를 넘는 순간 패킷은 호스트 IP로 감싸여(encapsulation) 이동하고, 도착지에서 풀린다(decapsulation). Pod는 자기가 어느 노드에 있는지 모르고도 통신이 되며, 이게 쿠버네티스의 **노드 투명성**의 정체다. 클라우드 환경에선 오버레이 대신 클라우드 네트워크 라우팅을 쓰는 경우도 많아서, "같은 Calico여도 환경이 다르면 다르게 동작한다"는 강사의 경고는 새겨둘 만하다.

5. **Block vs File 스토리지 차이는 단순히 성능이 아니라 "동시 마운트 가능 여부"다.** Block은 기술적으로 단일 노드 마운트라 RWO만 되고, 그래서 **StatefulSet + Block**, **Deployment + File** 조합이 자연스럽다. DB가 거의 항상 StatefulSet인 건 단지 "이름이 있어서"가 아니라, **Block 스토리지의 마운트 제약**과 맞물려 있다.

6. **CSI는 "표준 인터페이스"가 얼마나 큰 차이를 만드는지를 보여준다.** 예전엔 새 스토리지 솔루션을 쓰려면 쿠버네티스 본체에 in-tree 플러그인을 머지해야 했지만, CSI 이후엔 **벤더가 컨테이너 하나로 자기 스토리지를 클러스터에 끼워 넣을 수 있다.** Longhorn처럼 솔루션 자체를 클러스터 안에 띄우는 모델은 **클라우드 종속성 없이 분산 스토리지를 운영**할 길을 열어준다.

7. **로그가 stdout/stderr로 나가야만 보인다는 제약은 12factor app 철학의 직접적 강제다.** 앱이 파일에 로그를 써도 Docker logging driver는 모른다. 컨테이너 시대의 앱은 **로그를 자기가 관리하는 게 아니라 프로세스 출력에 떠넘긴다** — 그래야 컨테이너 런타임/오케스트레이터가 일관되게 수집할 수 있다. 레거시 앱을 컨테이너화할 때 가장 먼저 손볼 부분이 이거다.

8. **노드 레벨 로깅은 "Pod가 살아 있는 동안만" 유효하다.** Pod가 죽으면 링크와 파일이 모두 사라지므로 `kubectl logs`로는 과거 죽은 Pod의 로그를 못 본다. EFK/PLG 같은 클러스터 레벨 로깅은 **선택이 아니라 운영 환경 필수 애드온**. Termination Message Path는 그 빈 틈을 메우는 작은 트릭으로, OOMKilled 같은 죽음의 원인을 적은 비용으로 남길 수 있는 유용한 장치다.

9. **watch 패턴 + DaemonSet/Sidecar 패턴이 쿠버네티스의 두 가지 핵심 아키텍처 어휘**라는 점이 이번 정리로 명확해졌다. 컨트롤 플레인은 watch로 묶이고, 데이터 플레인은 노드/Pod마다 따라붙는 에이전트(kube-proxy, CNI, 로그 에이전트, CSI Node Plugin)로 구현된다. 새 기능이 들어와도 거의 항상 이 두 패턴 중 하나로 표현된다.

---

## Helm 개요 - 왜 필요한가, 그리고 어떻게 발전했나

**Helm이 왜 필요한가?** Kubernetes에 앱 하나를 올리려면 최소한 Service, Pod, ConfigMap 같은 오브젝트 YAML을 작성하고 `kubectl`로 생성 요청을 보낸다. 처음엔 단순하지만 프로젝트가 커지면서 문제가 드러난다.

1. **앱 종류가 늘어난다.** 업무별로 앱이 쪼개지거나 기능 추가로 새 앱들이 생긴다. 보통은 A 앱의 YAML을 복사해서 이름과 일부 값만 바꾸는 식으로 만든다.
2. **환경이 분리된다.** 개발/QA/운영 환경마다 네이밍 규칙이 다르고, 환경 변수도 다르게 들어가야 한다.
3. **정적 YAML 파일이 폭증한다.** YAML은 정적 파일이라 리소스마다·환경마다·앱마다 별도로 작성해야 한다. 이름 하나 바뀌면 일일이 수정해야 한다.

해결책은 **하나의 템플릿으로 여러 YAML을 동적으로 찍어내는 것**이다. 그 툴이 Helm이고, 보통 **Kubernetes 패키지 매니저**라고 부른다.

### Helm의 짧은 역사 — v2의 복잡함에서 v3의 단순함으로

| 시점 | 사건 |
|---|---|
| 2015 | Deis 회사가 내부 프로젝트로 시작, 큐브콘에서 발표 (현재 이 회사는 마이크로소프트에 편입) |
| 2016. 1 | 구글 합류 → Helm v2 본격 개발 |
| 2016~2018 | Helm v2 꾸준한 고도화 |
| 2018. 6 | CNCF 합류 (오픈소스 공식성 인증) |
| 2019. 11 | **Helm v3 릴리즈** — 아키텍처 대폭 단순화 |
| 현재 | v2 지원 종료, **v3로 옮겨야 함** |

#### v2 아키텍처가 왜 복잡했나

Helm v2는 다음 구성요소가 모두 필요했다.

- **Tiller**: 클러스터 안에 설치되어 API Server와 REST 통신
- **Helm Client**: 사용자 PC에 설치, Tiller와 gRPC 통신
- 통신 경로: `Client → (gRPC) → Tiller → (REST) → API Server`

설치도 까다롭고 권한 관리도 골치였다. 그래도 그땐 "이거라도 있어서 다행"이라 다들 그냥 썼다.

#### v3는 어떻게 단순해졌나

**Tiller를 없앴다.** Helm Client가 직접 API Server와 통신한다.

```
[Helm Client] ──► [kube-apiserver]
```

클러스터 내부 컴포넌트가 사라지면서 설치도 권한도 단순해졌다.

> **CNCF란?** Cloud Native Computing Foundation. 클라우드 오픈소스 기술을 관리하는 단체. 심사가 까다로워서 합류 자체가 공신력을 의미한다. Kubernetes, Prometheus, Helm 등이 여기 소속이다.

---

### Helm을 쓰면 YAML이 어떻게 바뀌나 — 구체적 예시

같은 앱을 dev/QA 두 환경에 배포한다고 해보자.

#### Helm을 쓰지 않을 때 — 환경×앱마다 별도 YAML

```yaml
# dev 환경 - app1
apiVersion: v1
kind: Service
metadata:
  name: dev-app1-svc
spec:
  selector:
    app: dev-app1
  ports:
  - port: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: dev-app1-pod
  labels:
    app: dev-app1
spec:
  containers:
  - name: container
    image: app1
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: dev-app1-cm
data:
  env: dev
```

app2를 추가하고 QA 환경까지 만들면 같은 패턴의 YAML이 4배로 늘어난다. 포트 같은 세부 설정은 모두 같고 **네이밍과 환경 변수만** 다르다.

#### Helm을 쓸 때 — 템플릿 하나

```yaml
# templates/all.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Values.env }}-{{ .Values.app }}-svc
spec:
  selector:
    app: {{ .Values.env }}-{{ .Values.app }}
  ports:
  - port: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: {{ .Values.env }}-{{ .Values.app }}-pod
  labels:
    app: {{ .Values.env }}-{{ .Values.app }}
spec:
  containers:
  - name: container
    image: {{ .Values.app }}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Values.env }}-{{ .Values.app }}-cm
data:
  env: {{ .Values.env }}
```

배포할 때는 `helm install`로 값을 주입한다.

```bash
# dev/app1
helm install dev-app1 ./chart --set env=dev --set app=app1

# QA/app2
helm install qa-app2 ./chart --set env=qa --set app=app2
```

새 앱이 추가되어도 YAML을 더 만들 필요 없이 **배포 명령만 하나 더** 실행하면 끝이다.

### Helm을 쓰는 두 가지 이유

1. **내 앱 배포 관리를 편하게 하기 위해** — 환경/앱별 정적 YAML 폭증 문제를 "템플릿 + 값 분리"로 해결.
2. **오픈소스를 쉽게 설치하기 위해** — Grafana, Prometheus, Tomcat 같은 대중적인 오픈소스들이 이미 Helm Chart 형태로 배포돼 있다. 명령 한 줄로 설치 가능.

> 진입장벽은 있지만 한번 익히면 얻는 게 훨씬 많다. **오픈소스 회사 입장에서도** 자기 솔루션을 사용자 환경에 맞게 커스터마이징해서 쓸 수 있도록 모듈 분리, PV 옵션 등을 차트로 잘 만들어 두는 게 컨테이너 시장에 빨리 진입하는 길이라, 점점 Helm 차트로 배포하는 오픈소스가 늘고 있다.

---

## Helm 설치 환경과 기본 사용법

### kubectl과 똑같은 구성이라고 이해하면 쉽다

Helm의 동작 방식을 한 번에 이해하려면 **kubectl과 비교**해서 보면 된다. 두 툴은 구성이 거의 동일하다.

#### kubectl이 클러스터와 통신하는 방법

Kubernetes를 설치하면 마스터 노드의 `/etc/kubernetes/admin.conf` 파일에 API Server 접근 IP와 인증서가 들어있다. 이 파일을 `~/.kube/config`로 복사해 두면 kubectl이 이 경로의 config 파일을 읽어 자동으로 연결 대상을 인식한다.

```
[사용자] → kubectl ──► ~/.kube/config 읽음 ──► kube-apiserver
```

`kubectl`은 **원격에서도 쓸 수 있는 도구**다. 외부 PC에 kubectl을 설치하고 config 파일만 복사해 두면 그 PC에서 클러스터를 제어할 수 있다. "마스터 노드에서만 쓰는 툴"이 아니라는 점을 기억해 두자.

#### Helm도 똑같다

Helm 역시 `~/.kube/config`를 읽어 통신할 API Server를 인식한다.

```
[사용자] → helm ──► ~/.kube/config 읽음 ──► kube-apiserver
```

kubectl과 동일하게 원격 PC에서도 사용 가능하다.

> **포인트**: Helm v3는 클러스터 안에 별도 컴포넌트(v2의 Tiller 같은 것)를 설치하지 않는다. kubectl처럼 **클러스터 외부 도구**일 뿐이다.

### Helm의 외부 환경 — 어디서 차트를 찾고 어디서 다운로드받나

Helm을 처음 쓰면 헷갈리는 세 가지 개념이 있다. **공식 사이트**, **Artifact Hub**, **Helm Chart Repository**다.

| 구성요소 | 역할 |
|---|---|
| **공식 사이트** (helm.sh) | Helm 자체의 설치 가이드와 문서 |
| **Artifact Hub** | Helm 차트를 **검색**하고 사용자 가이드를 제공 (다운로드 ✗) |
| **Helm Chart Repository** | 회사/단체별 차트 **저장소** (실제 다운로드 출처) |

#### Artifact Hub — "검색 엔진이지, 다운로드처가 아니다"

내가 원하는 오픈소스의 Helm 차트가 어디 있는지 찾아주는 곳. 다만 헷갈리지 말 것은, **여기서 차트를 직접 다운로드받는 게 아니다.** 각 차트 페이지에는 "이 저장소를 등록해서 설치하세요"라는 사용자 가이드가 적혀 있고, 실제 차트는 그 저장소에 있다.

같은 소프트웨어라도 만든 곳이 다른 여러 Helm 차트가 존재할 수 있다. 예를 들어 Grafana는 Grafana 단체가 직접 만든 차트도 있고, Bitnami가 만든 차트도 있다. 사용자는 Artifact Hub에서 검색해서 입맛에 맞는 것을 고른다.

> **Bitnami란?** 타사 소프트웨어를 자기들 방식으로 Helm 차트로 만들어 가이드하는 회사. Helm 차트는 별도의 솔루션이 아니라 **"설치 스크립트"에 가까운 개념**이라, 마치 누군가 잘 쓴 블로그 글을 참고하듯 Bitnami의 차트를 쓸 수 있다.

#### Helm Chart Repository — "실제 다운로드처"

각 회사·단체가 자기 차트를 올려두는 저장소. 사용자는 `helm repo add`로 저장소를 자기 Helm에 등록해 두고, 거기서 차트를 가져와 설치한다. 개인도 자기 저장소를 만들어 Artifact Hub에 등록할 수 있다.

### Tomcat 설치 흐름 — 처음부터 끝까지

다음과 같은 단계로 진행된다.

```
[1] Artifact Hub에서 "tomcat" 검색 → Bitnami가 제공하는 차트 발견
       │
       ▼
[2] helm repo add bitnami https://...
       (내 Helm에 Bitnami 저장소 등록)
       │
       ▼
[3] helm install my-tomcat bitnami/tomcat
       (Helm이 저장소에서 차트를 가져와 분석 → API Server로 오브젝트 생성 요청)
       │
       ▼
[4] Kubernetes가 Pod 생성 → Docker Hub에서 Tomcat 컨테이너 이미지 pull
       │
       ▼
[5] Tomcat이 클러스터에서 실행됨
```

> **중요한 사실**: **Helm 차트 안에 컨테이너 이미지가 들어있는 게 아니다.** 차트는 YAML 템플릿 묶음이고, 이미지는 Docker Hub 같은 컨테이너 레지스트리에서 별도로 받아온다.

### 자주 쓰는 Helm 명령어들

#### 설치/조회/삭제

```bash
helm version                    # 설치된 Helm 버전 확인
helm install <name> <chart>     # 배포 (name은 고유 릴리스 이름)
helm list                       # 배포된 릴리스 조회
helm status <name>              # 특정 배포 상태 조회
helm uninstall <name>           # 배포 삭제
```

#### Repository 관리

```bash
helm repo add <name> <url>      # 저장소 등록
helm repo list                  # 등록한 저장소 조회
helm repo update                # 저장소 인덱스 최신화
helm repo remove <name>         # 저장소 삭제
```

#### 차트 조회 — Repository vs Hub

```bash
helm search repo <keyword>      # 내가 등록한 저장소에서만 검색
helm search hub <keyword>       # Artifact Hub 전체 검색
```

### Helm Chart를 설치하는 3가지 방법

같은 차트라도 설치 방식이 세 가지가 있다. 커스터마이징 깊이에 따라 골라 쓴다.

#### 방법 1: Repository에서 직접 install — 가장 간단

```bash
helm install my-tomcat bitnami/tomcat --version 7.1.2
```

저장소 경로의 차트를 가져와서 바로 배포. `--version`으로 특정 버전 지정 가능.

#### 방법 2: pull로 다운로드 후 install

```bash
helm pull bitnami/tomcat --version 7.1.2   # 압축 파일이 떨어짐
helm install my-tomcat ./tomcat-7.1.2.tgz
```

결과는 방법 1과 동일. 차트를 로컬에 보관해 두고 싶거나 오프라인 환경에서 쓸 때 유용.

#### 방법 3: pull → 압축 해제 → 수정 → install — 실무용

```bash
helm pull bitnami/tomcat --version 7.1.2
tar -xzf tomcat-7.1.2.tgz
# tomcat/ 디렉토리에서 values.yaml 등을 수정
helm install my-tomcat ./tomcat
```

차트 내부 값을 직접 손봐서 배포할 때 쓴다. **실무에서 환경에 맞게 커스터마이징할 때 가장 많이 쓰는 방식**.

### Helm Chart의 구조 — 압축을 풀면 뭐가 있나

```
tomcat/
├── Chart.yaml          (필수) 차트 메타데이터 (이름, 버전, 설명 등)
├── values.yaml         (필수) 변수의 기본값 모음
├── templates/          (필수) 실제 Kubernetes 오브젝트 YAML들
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ...
├── charts/             (옵션) 의존하는 다른 차트들
├── README.md           (옵션)
└── ...
```

- **templates/**: Helm이 렌더링할 YAML 템플릿들. 안에 `{{ .Values.xxx }}` 같은 변수 표현이 박혀 있다.
- **values.yaml**: templates의 변수들의 기본값. 사용자가 `--set`이나 `-f my-values.yaml`로 덮어쓸 수 있다.
- **Chart.yaml**: 차트의 정체성 정보. 이름, 버전, 의존성 등.

실무에서 차트를 커스터마이징할 때는 주로 `values.yaml`을 수정하거나 `--set`/`-f`로 값을 덮어쓴다.

### 자동완성 설정

kubectl처럼 Helm도 키워드 자동완성을 지원한다. 셸별로 한 줄 추가하면 끝.

```bash
# bash
source <(helm completion bash)

# zsh
source <(helm completion zsh)

# fish
helm completion fish | source
```

---

## Helm 설치와 Tomcat 배포 — 실전 워크플로

### 1단계: Helm 설치

Linux 기준 설치는 단순하다. 공식 사이트에서 OS에 맞는 바이너리를 다운로드받고 `/usr/local/bin/`으로 옮기면 끝.

```bash
# 1) 바이너리 다운로드 (OS/아키텍처에 맞는 URL 사용)
curl -LO https://get.helm.sh/helm-v3.x.x-linux-amd64.tar.gz

# 2) 압축 해제
tar -xzf helm-v3.x.x-linux-amd64.tar.gz

# 3) 바이너리 이동
sudo mv linux-amd64/helm /usr/local/bin/

# 4) 설치 확인
helm version
```

내 OS가 어떤 리눅스 배포판인지 모르겠다면 공식 사이트의 **자동 설치 스크립트**를 쓰면 된다. OS를 자동 감지해 최신 버전을 깔아준다.

```bash
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
```

설치 후에는 [자동완성을 셸 RC에 영구 등록](#자동완성-설정)해 두면 편하다.

### 2단계: kubeconfig 확인

Helm은 `~/.kube/config`를 통해 클러스터에 붙는다. kubectl이 정상 동작하는 환경이라면 별도 설정 없이 그대로 쓸 수 있다.

```bash
ls ~/.kube/config
kubectl get nodes   # 클러스터에 닿는지 확인
```

### 3단계: Bitnami Repository 등록과 차트 탐색

Tomcat은 Artifact Hub에서 검색해 보면 Bitnami가 제공하는 차트가 가장 유명하다. Artifact Hub의 차트 페이지에 적힌 설치 가이드대로 저장소를 등록한다.

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo list                              # 등록된 저장소 확인
helm search repo bitnami | grep tomcat      # 등록한 저장소에서 tomcat 검색
helm repo update                            # 원격 저장소의 최신 차트 인덱스 가져오기
```

> **헷갈리기 쉬운 포인트**: `helm search repo`가 보여주는 차트 목록은 **로컬에 저장된 인덱스**다. 저장소를 등록할 때 인덱스가 로컬에 저장되며, `helm repo update`를 해야 원격의 최신 버전 목록을 받아온다. 즉 `helm repo update` → `helm search repo` 순서로 써야 최신 정보를 본다.

저장소를 잘못 등록했거나 더 이상 안 쓸 거면 삭제도 가능.

```bash
helm repo remove bitnami
```

### 4단계: Tomcat 첫 배포와 LoadBalancer 함정

기본 배포 명령은 Artifact Hub의 가이드에 적힌 그대로다. 다만 **로컬 클러스터(베어메탈)에는 두 가지 함정**이 있다.

```bash
helm install my-tomcat bitnami/tomcat --version 7.1.2 \
  --set persistence.enabled=false
```

#### 함정 1: PV가 필요한 차트

Bitnami Tomcat 차트는 **기본값으로 PersistentVolume을 요구**한다. PV를 미리 만들어 두지 않았다면 Pod가 Pending 상태로 멈춘다. 학습/테스트 환경이라면 `--set persistence.enabled=false`로 비활성화하면 Pod 안에 데이터를 두고 동작한다.

#### 함정 2: LoadBalancer Pending

차트가 기본으로 Service Type을 LoadBalancer로 만든다. **로컬 클러스터엔 LoadBalancer 플러그인이 없으니 EXTERNAL-IP가 `<pending>`** 으로 남는다. 이때는 **NodePort로 우회 접속**한다.

```bash
kubectl get svc my-tomcat   # PORT(S) 칸의 8080:3xxxx/TCP 형태에서 3xxxx가 NodePort
# 마스터 노드 IP가 192.168.0.10이라면:
# http://192.168.0.10:3xxxx 로 접속
```

#### 배포 후 관리 명령

```bash
helm list                        # 배포된 릴리스 목록
helm status my-tomcat            # install 직후 나왔던 안내 노트를 다시 봄
helm uninstall my-tomcat         # 삭제
```

> **helm status가 유용한 이유**: `helm install` 직후 출력되는 접속 방법·관리자 비밀번호 확인 명령 등은 화면 위로 흘러간다. 잊었을 때 `helm status`로 그대로 다시 볼 수 있다.

### 5단계: Tomcat 관리자 페이지 활성화 — 옵션 추가하기

Tomcat의 관리자 페이지(`/manager`)는 기본적으로 비활성화돼 있다. Bitnami 차트의 **`tomcatAllowRemoteManagement` 옵션을 1로 켜야** 관리자 접속이 허용된다.

```bash
helm uninstall my-tomcat     # 기존 배포 제거
helm install my-tomcat bitnami/tomcat --version 7.1.2 \
  --set persistence.enabled=false \
  --set tomcatAllowRemoteManagement=1
```

배포 후 `kubectl get svc`로 새 NodePort를 확인하고, `helm status my-tomcat`에 안내된 명령으로 관리자 비밀번호를 추출해 로그인한다.

### 6단계: 차트를 다운로드해서 values.yaml 직접 수정하기

옵션 한두 개면 `--set`이 편하지만 **여러 값을 바꿀 때는 차트를 통째로 받아 `values.yaml`을 수정**하는 게 깔끔하다.

```bash
# 1) 차트 다운로드 (압축 파일이 떨어짐)
helm pull bitnami/tomcat --version 7.1.2

# 2) 압축 해제
tar -xzf tomcat-7.1.2.tgz

# 3) tomcat/values.yaml 편집: persistence.enabled=false, tomcatAllowRemoteManagement=1

# 4) 로컬 경로로 설치
helm install my-tomcat ./tomcat
# 또는 별도 values 파일을 만들어서 오버레이
helm install my-tomcat ./tomcat -f my-values.yaml
```

이제 `--set` 없이도 같은 결과가 나온다. 실무에서는 환경별로 `values-dev.yaml`, `values-prod.yaml`을 따로 두고 `-f`로 적용하는 패턴이 흔하다.

---

## Helm Chart 만들기 — 기본 구조와 조회 명령

### helm create — 기본 차트 골격 생성

```bash
helm create mychart
```

이 명령 하나로 다음 구조가 생성된다.

```
mychart/
├── Chart.yaml              # 차트 메타데이터
├── values.yaml             # 변수 기본값
├── charts/                 # 의존 차트 (이번 강의 범위 X)
└── templates/
    ├── _helpers.tpl        # 사용자 정의 변수 (tpl = template)
    ├── NOTES.txt           # 배포 후 화면에 표시될 안내
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── hpa.yaml
    ├── serviceaccount.yaml
    ├── tests/              # 차트 테스트용 (이번 강의 범위 X)
    └── ...
```

> **`_helpers.tpl`의 언더스코어**: 파일명이 `_`로 시작하면 Helm은 이를 **Kubernetes 오브젝트가 아닌 보조 템플릿**으로 인식해 렌더링 결과에 포함하지 않는다. 사용자 정의 변수를 모아두는 용도.

### helm show — 차트 안의 파일 들여다보기

```bash
helm show values ./mychart    # values.yaml 내용 출력 (주석 포함)
helm show chart ./mychart     # Chart.yaml 내용 출력 (주석 제외 ← cat과 차이)
helm show readme ./mychart    # README.md 내용 출력
helm show all ./mychart       # 위 세 가지를 한 번에
```

> **솔직히 `cat`과 큰 차이는 없다.** `show chart`가 Chart.yaml의 주석을 빼고 보여주는 정도가 차이다. 자주 쓰는 명령은 아니지만 **"있는데 안 쓰는 것"과 "몰라서 못 쓰는 것"은 다르므로** 알아만 두면 된다.

### helm template — 배포 전 렌더링 결과 미리보기 (중요)

이 명령은 **실제 배포 없이 변수 치환이 끝난 최종 YAML을 출력**한다. 차트를 만들 때 "내가 의도한 대로 값이 채워지는가"를 확인하는 핵심 디버깅 도구.

```bash
helm template ./mychart
helm template ./mychart -f prod-values.yaml --set image.tag=v2   # 옵션도 그대로 적용됨
```

차트를 개발하면서 함수·흐름제어·변수 처리를 짤 때 **install을 직접 하지 않고 template으로 결과만 확인**하는 패턴을 반복하게 된다.

### helm get — 배포된 릴리스(인스턴스) 정보 조회

`helm install`로 배포된 릴리스는 **인스턴스**다. 인스턴스의 정보는 `helm get`으로 조회한다.

| 명령 | 출력 |
|---|---|
| `helm get manifest <release>` | 배포된 YAML 전체 |
| `helm get notes <release>` | NOTES.txt에 정의된 안내 메시지 |
| `helm get values <release>` | install 시 **추가로 주입한** 값 (`-f`, `--set`) |
| `helm get all <release>` | 위 세 가지를 한 번에 |
| `helm status <release>` | install 직후 화면에 떴던 그 안내 |

### 템플릿 vs 인스턴스 — 자주 헷갈리는 차이

이게 핵심 개념이다.

| 구분 | 의미 | 명령 |
|---|---|---|
| **템플릿** | 차트 파일들 (변수 포함). 수정하면 즉시 반영됨 | `helm template` |
| **인스턴스** | 이미 배포된 릴리스 (불변 스냅샷) | `helm get`, `helm status` |

```
values.yaml 수정 → helm template로 보면 → 새 값 반영됨 ✓
values.yaml 수정 → helm get manifest로 보면 → 옛 값 그대로 (이미 배포된 인스턴스니까) ✗
```

새 값을 실제 클러스터에 반영하려면 **`helm upgrade`** 를 써야 한다.

```bash
helm upgrade my-release ./mychart -f prod-values.yaml
```

upgrade를 하면 `helm get manifest`의 결과도 새 내용으로 바뀌고, `.Release.IsUpgrade`는 true, `.Release.Revision`은 1 증가한다.

### `helm get values`가 비어 보이는 이유

`helm install my-release ./mychart`로 옵션 없이 배포하고 나서 `helm get values`를 치면 **아무것도 안 나온다.** "어, values.yaml 내용은 어디 갔지?" 하고 헷갈리는데, 이 명령은 **values.yaml의 기본값을 보여주는 게 아니다.**

`helm get values`가 보여주는 건 **`-f`나 `--set`으로 추가로 주입한 값**뿐이다. 옵션 없이 배포했다면 추가 주입이 없으므로 빈 결과가 정상.

```bash
# 옵션 없이 배포 → get values는 빈 결과
helm install my-release ./mychart
helm get values my-release   # (empty)

# -f로 배포 → get values에서 그 파일 내용이 나옴
helm install my-release ./mychart -f prod-values.yaml
helm get values my-release   # prod-values.yaml 내용 표시
```

---

## Helm Chart 만들기 — 빌트인 객체와 사용자 정의 변수

### 빌트인 객체 4가지

템플릿 안에서 `{{ }}` 사이에 쓸 수 있는 **내장 전역 변수**가 있다. Go template 문법을 기반으로 한다.

| 객체 | 소스 | 키 첫 글자 |
|---|---|---|
| `.Values` | `values.yaml`의 키들 | **소문자** (파일 그대로) |
| `.Chart` | `Chart.yaml`의 키들 | **대문자** (변환됨!) |
| `.Release` | `helm install` 시점의 정보 | **대문자** |
| `.Template` | 현재 렌더링 중인 템플릿 파일 정보 | **대문자** |

> **문법 해부**: `{{ .Values.replicaCount }}`
>
> - `{{ }}`: 변수 자리
> - 맨 앞의 `.`: 전체 스코프(루트)
> - `.Values`: 루트에서 Values 객체 선택
> - `.replicaCount`: Values 객체의 replicaCount 키

### .Values — values.yaml 그대로

```yaml
# values.yaml
replicaCount: 3
image:
  repository: nginx
  tag: latest
```

```yaml
# templates/deployment.yaml
spec:
  replicas: {{ .Values.replicaCount }}
  image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
```

키가 소문자면 소문자로 쓴다. **values만 대문자/소문자 변환이 없다.**

### .Chart — Chart.yaml은 대문자로

```yaml
# Chart.yaml
apiVersion: v2
name: mychart
description: A Helm chart
version: 0.1.0
type: application
```

```yaml
# templates/configmap.yaml
data:
  name: {{ .Chart.Name }}              # mychart
  version: {{ .Chart.Version }}        # 0.1.0
  type: {{ .Chart.Type }}              # application
```

> **함정**: `Chart.yaml`엔 `name: mychart`로 소문자지만, 템플릿에선 **`.Chart.Name`** 으로 대문자다. `.Release.Name`, `.Template.Name`도 마찬가지. **`.Values`만 예외**다.

### .Release — install 시점의 정보

| 키 | 의미 |
|---|---|
| `.Release.Name` | `helm install <name>`의 name |
| `.Release.Namespace` | 배포 네임스페이스 (`--namespace` 또는 default) |
| `.Release.IsInstall` | install 중이면 true |
| `.Release.IsUpgrade` | upgrade 중이면 true |
| `.Release.Revision` | install 시 1, upgrade마다 +1 |
| `.Release.Service` | 보통 `"Helm"` 고정 |

```bash
helm install my-tomcat ./mychart --namespace default
# 템플릿 안에서:
# {{ .Release.Name }}      → "my-tomcat"
# {{ .Release.Namespace }} → "default"
# {{ .Release.IsInstall }} → true
# {{ .Release.Revision }}  → 1
```

### .Template — 자신의 위치 정보

```yaml
{{ .Template.BasePath }}   # 이 차트의 templates 폴더 경로
{{ .Template.Name }}       # 현재 파일 경로 (예: mychart/templates/deployment.yaml)
```

자주 쓸 일은 없지만 오픈소스 차트를 뜯어볼 때 가끔 본다.

---

### 변수 주입 우선순위 — 마지막에 들어온 값이 이긴다

같은 변수가 여러 곳에서 정의되면 **나중에 들어온 것이 이긴다**. 우선순위는 다음과 같다.

```
낮음  ── values.yaml (기본값)
          ↓
       -f production-values.yaml (파일 오버라이드)
          ↓
       --set key=value (CLI 오버라이드)
높음
```

#### 시나리오로 보기

```yaml
# values.yaml
env: dev
log: error
path: /var/log
```

```yaml
# production-values.yaml
env: prod
log: info
# path는 미정의
```

```bash
# 1) 기본만
helm install r ./mychart
# 결과: env=dev, log=error, path=/var/log

# 2) -f 추가
helm install r ./mychart -f production-values.yaml
# 결과: env=prod, log=info, path=/var/log   ← path는 production에 없으니 기본값

# 3) -f + --set
helm install r ./mychart -f production-values.yaml --set log=debug
# 결과: env=prod, log=debug, path=/var/log  ← log는 --set이 최종 우위
```

**환경별 분기**는 `-f`로 파일을 갈아끼우고, **임시 디버깅 같은 일회성 오버라이드**는 `--set`으로 한다.

---

### 사용자 정의 변수 — `_helpers.tpl`의 define/include

빌트인 객체만으로 부족할 때 **내가 변수를 만들 수 있다.** `templates/_helpers.tpl`에 `define`으로 정의하고 다른 템플릿에서 `include`로 가져다 쓴다.

#### 정의 (`_helpers.tpl`)

```go
{{/* 단일 값 정의 */}}
{{- define "mychart.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{/* 여러 줄 값 (YAML 블록) 정의 */}}
{{- define "mychart.labels" -}}
app: {{ .Chart.Name }}
release: {{ .Release.Name }}
version: {{ .Chart.AppVersion }}
{{- end -}}
```

- `define "이름"` ... `end`: 변수 블록.
- `{{- -}}`의 `-`: 앞뒤 공백/줄바꿈 제거. (자세한 건 다음 섹션)

#### 사용 (`service.yaml`)

```yaml
metadata:
  name: {{ include "mychart.name" . }}     # 단일 값
  labels:
    {{- include "mychart.labels" . | nindent 4 }}   # 여러 줄
```

**왜 끝에 `.`이 붙나?** include의 두 번째 인자는 **스코프(scope)**다.

- `.`: 전체 스코프 (Values, Chart, Release, Template 다 접근 가능)
- `.Chart`: Chart 객체 안만 접근 가능 (Values 못 봄)

대부분 `.`을 써서 모든 객체에 접근할 수 있게 한다. **스코프 인자를 빼먹으면 컴파일 에러**가 나므로 주의.

> **왜 굳이 사용자 정의 변수를 쓰나?** 여러 템플릿에 같은 라벨/이름 규칙을 반복해서 박을 때, 한 군데서 정의해 두면 차트 전체의 일관성이 유지된다. 차트 네이밍 규칙이 바뀌어도 `_helpers.tpl` 한 곳만 고치면 끝.

---

## Helm Chart 만들기 — 함수, 파이프라인, 흐름 제어

### 함수 호출 — 인자는 공백으로 구분

Go 템플릿의 함수는 **공백을 인자 구분자**로 쓴다. 괄호가 없다.

```yaml
{{ quote .Values.env }}                       # quote(.Values.env)
{{ include "mychart.labels" . }}              # include("mychart.labels", .)
{{ printf "%s-%s" .Values.app .Values.env }}  # printf("%s-%s", app, env)
```

인자 개수가 함수마다 정해져 있고, **부족하면 컴파일 에러**. 종류는 [Helm 공식 함수 목록](https://helm.sh/docs/chart_template_guide/function_list/) 참고.

### 파이프라인 — 리눅스와 같은 개념

`|` 로 값을 다음 함수에 넘긴다. **여러 함수를 겹쳐 쓸 때 가독성이 훨씬 좋다.**

```yaml
{{ .Values.env | upper }}                     # "dev" → "DEV"
{{ .Values.env | upper | quote }}             # "dev" → "DEV" → "\"DEV\""
{{ .Values.env | repeat 2 | quote }}          # "dev" → "devdev" → "\"devdev\""
```

함수가 하나여도 파이프라인을 쓰는 케이스가 흔하다. 일관된 스타일이 보기 좋아서.

---

### 흐름 제어 1: if / else if / else

```yaml
{{- if eq .Values.env "dev" }}
log: debug
{{- else if eq .Values.env "qa" }}
log: {{ .Values.qaLog }}
{{- else }}
log: error
{{- end }}
```

자주 쓰는 비교 함수: `eq`(equal), `ne`(not equal), `and`, `or`, `not`, `lt`, `gt`, `le`, `ge`.

#### 자료형별 false 판정 — 이걸 모르면 디버깅이 어렵다

```yaml
{{ if 0 }}        # number: 0 → false
{{ if "" }}       # string: 빈 문자열 → false
{{ if "false" }}  # string: "false"는 문자열이 있으므로 → TRUE (주의!)
{{ if nil }}      # 모든 nil → false
{{ if false }}    # boolean false → false
{{ if list }}     # 빈 리스트 → false (요소가 하나라도 있으면 true)
{{ if dict }}     # 빈 맵 → false
```

> **함정**: 일반 프로그래밍 언어에선 빈 문자열을 truthy로 보는 경우도 많은데, **Helm은 빈 문자열을 false로 본다**. 또 `"false"`라는 **문자열**은 길이가 있으니 true다. 이 미묘한 차이가 자주 버그를 만든다.

---

### 흐름 제어 2: with — 스코프 좁히기

`.Values.prod.config.replicas.count` 같이 깊이가 깊은 경로를 여러 번 쓸 때, `with`로 스코프를 좁히면 가독성이 좋아진다.

```yaml
{{- with .Values.prod }}
env: {{ .env }}                   # .Values.prod.env
replicas: {{ .replicas }}         # .Values.prod.replicas
log: {{ .log }}
{{- end }}
```

- `with` 블록 안에서는 `.`이 `.Values.prod`를 의미한다.
- **블록 안에서는 `.Release.Name` 같은 바깥 객체에 접근할 수 없다.** (지역 변수로 우회 — 아래 참조)

---

### 흐름 제어 3: range — 반복문

```yaml
# values.yaml
data:
  - a
  - b
  - c
```

```yaml
# 단순 반복
items:
{{- range .Values.data }}
  - {{ . | quote }}     # . 가 각 요소 (a, b, c)
{{- end }}
```

#### range with index/value — 인덱스도 함께

```yaml
{{- range $index, $value := .Values.data }}
  - index-{{ $index }}: {{ $value }}
{{- end }}
# 출력:
#   - index-0: a
#   - index-1: b
#   - index-2: c
```

#### range over map — 맵 순회

```yaml
# values.yaml
labels:
  app: tomcat
  tier: backend
```

```yaml
{{- range $key, $value := .Values.labels }}
{{ $key }}: {{ $value | quote }}
{{- end }}
# 출력:
# app: "tomcat"
# tier: "backend"
```

> **`include` vs `range`**: include는 정의된 블록을 통째로 가져온다. range는 각 요소마다 파이프라인으로 가공할 수 있다. **요소별 변형이 필요하면 range, 통째로 끼워 넣을 거면 include.**

---

### `{{- ` 와 ` -}}` — 공백·줄바꿈 제거

흐름 제어 자체는 화면에 아무것도 출력하지 않지만, **줄을 차지하면서 빈 줄과 공백을 남긴다.** YAML은 들여쓰기에 민감하니 이 빈 자리가 파싱 에러를 만들기도 한다.

해법: `{{-` (앞 공백·줄바꿈 제거), `-}}` (뒤 공백·줄바꿈 제거).

```yaml
# 좋은 예
{{- if .Values.enabled }}
key: value
{{- end }}

# 나쁜 예 (빈 줄이 남음)
{{ if .Values.enabled }}
key: value
{{ end }}
```

대부분의 흐름 제어에는 `{{- ... -}}`을 쓴다고 보면 된다.

---

### 자주 쓰는 함수들

#### 문자열 — print, printf, quote

```yaml
{{ print "Hello " "World" }}             # "Hello World"
{{ printf "%s-%s" .Chart.Name .Values.env }}   # "mychart-dev"
{{ .Values.env | quote }}                # "dev" (양 옆에 따옴표)
```

#### ternary — 3항 연산자

```yaml
# ternary <true값> <false값> <조건>
{{ ternary "yes" "no" .Values.enabled }}
# enabled=true이면 "yes", false면 "no"
```

값에 파이프라인을 붙여 `{{ .Values.enabled | ternary "yes" "no" }}`로도 쓸 수 있다.

#### indent / nindent — 들여쓰기 추가 (필수)

리스트/맵 값을 가져와 YAML에 끼워 넣을 때 들여쓰기가 안 맞으면 컴파일 에러가 난다.

```yaml
# values.yaml
data:
  - a
  - b
  - c
```

```yaml
# 나쁜 예 — toYaml만 쓰면 첫 줄만 들여쓰기 되고 나머지는 공백 없음 → 에러
data: {{ toYaml .Values.data }}

# indent — 모든 줄에 N칸 공백을 앞에 붙임
data:
{{ toYaml .Values.data | indent 4 }}    # 좋지만 부모와 정렬이 안 보임

# nindent — 앞에 줄바꿈 + N칸 공백 추가 (실무에선 이게 더 흔함)
data:
  items:
    {{- toYaml .Values.data | nindent 4 }}
```

> **`indent`와 `nindent`의 차이**: `indent`는 그냥 N칸 공백을 앞에 붙인다. `nindent`는 **앞에 줄바꿈을 한 번 추가**해서 부모 키와 자식 값이 가독성 있게 나뉜다. 보통은 `nindent`를 쓴다.

#### default — 값이 false면 대신 쓰기

```yaml
image: {{ .Values.image | default "nginx:latest" }}
replicas: {{ .Values.replicas | default 1 }}
```

`.Values.image`가 nil/빈 문자열이면 `"nginx:latest"`가 들어간다.

#### trim — 공백·접두/접미 문자 제거

```yaml
{{ "  hello  " | trim }}              # "hello"
{{ "----hello" | trimPrefix "---" }}  # "-hello"
{{ "hello---" | trimSuffix "---" }}   # "hello"
```

#### 랜덤 문자열

| 함수 | 범위 |
|---|---|
| `randAlphaNum 8` | a-z, A-Z, 0-9에서 8자 |
| `randAlpha 8` | a-z, A-Z에서 8자 |
| `randNumeric 8` | 0-9에서 8자 |
| `randAscii 8` | 인쇄 가능 ASCII에서 8자 |

```yaml
password: {{ randAlphaNum 16 | quote }}
```

#### 기타 알아두면 좋은 함수

```yaml
{{ trunc 5 "abcdefghij" }}             # "abcde"
{{ "hello-world" | replace "-" "_" }}  # "hello_world"
{{ "catch" | contains "cat" }}         # true
{{ "1234" | b64enc }}                  # "MTIzNA==" (Secret에 자주 씀)
```

함수 전체 리스트는 공식 문서의 **Function List** 참고.

---

### 지역 변수 — `$var := value`

with 블록 안에서 바깥 객체에 접근해야 하거나, range에서 인덱스를 받을 때 **지역 변수**를 쓴다.

#### 변수 선언과 사용

```yaml
{{- $relName := .Release.Name }}

metadata:
  name: {{ $relName }}-config
```

규칙:
- `$` 접두사 필수
- `:=`로 선언, `=`로 재할당
- **선언 라인 위에서는 못 씀** (당연)
- **다른 파일에서는 못 씀** (지역이라는 이름 그대로)

#### with 내부에서 바깥 객체 접근

```yaml
{{- $relName := .Release.Name }}
{{- with .Values.prod }}
env: {{ .env }}
release: {{ $relName }}      # with 안에서도 지역 변수는 보임
{{- end }}
```

지역 변수에 미리 담아두면 with의 스코프 제약을 우회할 수 있다.

#### range에서 index/key/value 받기

이미 위에서 나왔지만 다시 정리.

```yaml
# 리스트
{{- range $index, $value := .Values.items }}
  - {{ $index }}: {{ $value }}
{{- end }}

# 맵
{{- range $key, $value := .Values.labels }}
{{ $key }}: {{ $value }}
{{- end }}
```

---

### 정리: 자동 생성된 차트 뜯어보기

`helm create mychart`로 만든 기본 차트의 `deployment.yaml`, `ingress.yaml`을 열어보면 **지금까지 배운 문법이 거의 다** 나온다.

- `include` 함수 + `_helpers.tpl`의 사용자 정의 변수
- `nindent` 로 들여쓰기 맞춤
- `if .Values.xxx` / `with .Values.xxx` 로 조건부 렌더링
- `default` 함수
- `range` 로 리스트/맵 반복

여기까지 이해됐다면, `helm template ./mychart`로 결과를 찍어보고 **각 줄의 값이 어디서 왔는지 추적할 수 있어야** 차트 작성에 무리가 없다.

---

## Helm Chart 분석 — Tomcat

`helm create`로 나오는 기본 차트는 너무 단순해서 실전 차트가 어떻게 생겼는지 감이 안 잡힌다. **Tomcat** 차트를 첫 분석 대상으로 잡는 이유는, 종속성 같은 복잡한 구조 없이 **`_helpers.tpl` → `deployment.yaml`로 이어지는 사용자 정의 변수 패턴**을 가장 깔끔하게 보여주기 때문이다. 여기서는 차트의 기능 분석이 아니라 **"이 사람들이 템플릿을 어떻게 짰는가"**에 집중한다.

### Tomcat 차트 구조 개요

```
tomcat/
├── Chart.yaml          # 패키지 정보 (.Chart.Version, .Chart.Name 으로 참조)
├── values.yaml         # 사용자가 커스터마이징하는 값 (.Values.xxx)
└── templates/
    ├── _helpers.tpl    # 사용자 정의 변수 (define 블록)
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── ...
```

`Chart.yaml`/`values.yaml`/`_helpers.tpl` 세 곳의 값이 templates/의 yaml들에 흘러 들어가 최종 매니페스트가 만들어진다.

### Tomcat에서 처음 만나는 함수들

| 함수 | 용도 | 예 |
|---|---|---|
| `dict` | 키-값을 짝수 개 받아 **딕셔너리** 생성 | `{{- $d := dict "k1" "v1" "k2" "v2" }}` |
| `get` | 딕셔너리에서 키로 값 꺼냄 | `{{ get $d "k1" }}` |
| `include` + dict | 사용자 정의 변수에 **2개 이상의 컨텍스트** 전달 | `{{ include "tplValue" (dict "value" .x "context" $) }}` |
| `typeIs` | 값의 **타입 비교** (`"string"`, `"bool"` 같은 정확한 키워드) | `{{ if typeIs "string" .value }}` |
| `tpl` | values.yaml에 **변수가 박힌 문자열**을 그 자리에서 렌더 | `{{ tpl .Values.template . }}` |
| `coalesce` | 인자 중 **첫 번째 non-null** 값을 리턴 | `{{ coalesce .a .b "default" }}` |
| `contains` | 부분 문자열 포함 여부 | `{{ if contains "tomcat" $name }}` |

#### `tpl` 함수가 진짜 필요한 순간

`values.yaml`에 **그 자체로 템플릿 문법이 박혀 있는** 문자열을 넣을 때 필요하다.

```yaml
# values.yaml
configPath: "/etc/{{ .Release.Name }}/conf"   # 변수가 박힌 문자열
```

```yaml
# 템플릿
path: {{ .Values.configPath }}                # 출력: /etc/{{ .Release.Name }}/conf (그대로)
path: {{ tpl .Values.configPath . }}          # 출력: /etc/my-release/conf  (렌더링됨)
```

#### `include`에 dict로 컨텍스트 넘기기 — 자주 쓰는 패턴

기본 `include "name" .`은 컨텍스트 하나만 넘긴다. 사용자 정의 변수에서 **여러 값을 받고 싶을 때** dict로 묶어서 한 번에 넘긴다.

```yaml
# 호출부
{{- include "tomcat.tplValue" (dict "value" .Values.nodeSelector "context" $) | nindent 8 }}
```

```yaml
# _helpers.tpl
{{- define "tomcat.tplValue" -}}
{{- if typeIs "string" .value }}
    {{- tpl .value .context }}
{{- else }}
    {{- tpl (.value | toYaml) .context }}
{{- end }}
{{- end -}}
```

> Tomcat 차트는 `nodeSelector` 값을 **문자열**로 줘도, **객체**로 줘도, 변수가 박힌 템플릿 문자열로 줘도 모두 처리되도록 이렇게 추상화했다. **다양한 입력 형태를 다 받쳐주려는 의도**다. 단, "내가 직접 차트를 만들 때 굳이 이렇게까지 할 필요는 없다"는 게 강의의 권고. 그냥 `labels: {{ include ... | nindent ... }}`처럼 쓰는 게 깔끔.

### `_helpers.tpl` 분석에서 본 관용구들

Tomcat의 `_helpers.tpl`에는 거의 모든 오픈소스 차트가 따라 쓰는 정형 패턴이 보인다.

```yaml
# 1. 차트 이름 — Override 우선, 없으면 Chart.Name. 63자 제한 + 후행 하이픈 제거.
{{- define "tomcat.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end }}

# 2. 풀네임 — Override 우선, releaseName에 chartName 포함이면 releaseName만, 아니면 합침.
{{- define "tomcat.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{ .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{ .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{ printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end -}}
{{- end -}}
{{- end }}

# 3. PVC 이름 — existingClaim 있으면 그걸, 없으면 fullname.
{{- define "tomcat.pvc" -}}
{{ coalesce .Values.persistence.existingClaim (include "tomcat.fullname" .) }}
{{- end }}
```

### `deployment.yaml`에서 `template` vs `include`

둘 다 사용자 정의 변수를 호출한다. 차이는 **결과를 파이프라인에 넘길 수 있느냐**다.

```yaml
# 단일 값을 그대로 박을 때 — template
metadata:
  name: {{ template "tomcat.fullname" . }}

# 여러 줄 결과에 indent를 먹여야 할 때 — include
metadata:
  labels:
    {{- include "tomcat.labels" . | nindent 4 }}
```

> 실무 규칙: 한 줄짜리는 `template`, 여러 줄이거나 함수 체인이 필요하면 `include`.

### `toYaml` vs 그냥 가져오기

```yaml
# values.yaml의 객체(map/slice)를 통째로 박을 때 — toYaml로 형 변환
resources:
  {{- toYaml .Values.resources | nindent 12 }}

# helpers에서 이미 yaml 텍스트로 만들어진 블록을 가져올 때 — toYaml 불필요
metadata:
  labels:
    {{- include "tomcat.labels" . | nindent 4 }}
```

소스가 **객체**면 toYaml로 직렬화하고, **이미 yaml 텍스트**면 그대로 박는다. 이 차이를 헷갈리면 들여쓰기/줄바꿈이 깨진다.

---

## Helm Chart 분석 — Prometheus

Prometheus는 컴포넌트가 많고(Alertmanager, Server, KubeStateMetrics, NodeExporter 등) **종속성 차트**라는 새 구조까지 등장한다. Tomcat이 단일 차트의 helpers 패턴이었다면, Prometheus는 **다중 컴포넌트와 종속성 관리**의 표본이다.

### 차트 종속성 (Chart Dependencies) — 차트 안에 또 차트 넣기

Prometheus 차트 안에 들어가 보면 `charts/` 폴더에 `kube-state-metrics`라는 별도 차트가 들어 있다. 하나의 헬름 차트 안에 또 하나의 완전한 헬름 차트가 종속돼 같이 배포되는 구조다.

```yaml
# Chart.yaml
dependencies:
  - name: kube-state-metrics
    version: "2.13.*"           # 와일드카드 가능 — 2.13.x 중 최신
    repository: https://prometheus-community.github.io/helm-charts
    condition: kubeStateMetrics.enabled   # values 키로 ON/OFF 제어
```

```yaml
# values.yaml
kubeStateMetrics:
  enabled: true     # false면 종속 차트 자체가 배포 대상에서 빠짐
```

명령 흐름:

```bash
helm dependency update    # repository에서 차트 풀 → charts/ 폴더에 압축으로 떨어짐
                          # Chart.lock 파일이 자동 생성 (다운로드 시점·digest 기록)
helm dependency list      # 현재 차트에 어떤 종속 차트가 묶였는지 조회
```

배포(`helm install`)하면 본 차트의 템플릿 + `charts/` 안의 종속 차트가 **같이** 클러스터로 나간다.

### 컴포넌트 폴더별 `enabled` 게이트 패턴

Prometheus 차트의 `templates/` 안에는 `alertmanager/`, `server/`, `nodeExporter/` 같은 폴더가 컴포넌트별로 나뉘어 있고, **각 폴더의 모든 yaml 파일 첫 줄**이 이 패턴으로 시작한다.

```yaml
{{- if .Values.alertmanager.enabled }}
apiVersion: v1
kind: ConfigMap
...
{{- end }}
```

`values.yaml`에서 `alertmanager.enabled: false`로만 끄면 그 폴더의 매니페스트 전체가 렌더링 결과에서 사라진다. **컴포넌트 단위 ON/OFF**의 정석.

### Prometheus에서 처음 만나는 함수들

| 함수 | 용도 | 결과 |
|---|---|---|
| `splitList "/" url` | 구분자로 잘라서 **리스트** 반환 | `["https:", "", "helm.sh", "docs"]` |
| `split "/" url` | 잘라서 **맵** 반환 (`_0`, `_1` … 키) | `{_0: "https:", _1: "", …}` |
| `first` / `last` / `rest` | 리스트의 첫 / 마지막 / "첫 제외 나머지" | `first list`, `rest list` |
| `join "," list` | 리스트를 구분자로 다시 합침 | `"a,b,c"` |
| `regexMatch <패턴> <문자열>` | 정규식 매치 → bool | true/false |
| `index <obj> <키> [<키> …]` | 다단계 키로 값 꺼냄 (`.`이 포함된 키 우회) | 값 |
| `semver "v1.2.3"` | 시멘틱 버전을 **객체**로 파싱 (Major/Minor/Patch) | 객체 |
| `semverCompare "<1.13" $v` | 시멘틱 비교 (`< > = ~ ^` 등) | bool |
| `.Capabilities.APIVersions.Has "..."` | 대상 클러스터에 해당 **API가 있는지** | bool |
| `.Capabilities.KubeVersion.GitVersion` | 클러스터 **버전 문자열** | `"v1.19.2"` 등 |

#### 키 이름에 `.`이 들어갈 때 — `index`로 우회

```yaml
# values.yaml
"grafana.ini":            # 키 자체가 "grafana.ini"
  paths:
    data: /var/lib/grafana
```

```yaml
{{ .Values.grafana.ini }}              # ❌ grafana → ini 로 파싱돼 못 찾음
{{ index .Values "grafana.ini" }}      # ✅ 통째로 키 매칭
{{ index .Values "server" "path" "prefix" "from" }}  # 다단계도 동일하게
```

#### Capabilities — "내가 배포될 클러스터"의 정보

`.Capabilities`는 **차트가 배포될 시점의 대상 클러스터** 정보를 들고 온다. 동일 차트가 K8s 버전·기능 셋에 따라 다르게 렌더되도록 만들 때 쓴다. Prometheus의 Ingress 매니페스트가 이 패턴을 쓴다.

```yaml
{{- if .Capabilities.APIVersions.Has "networking.k8s.io/v1/Ingress" }}
apiVersion: networking.k8s.io/v1
{{- else }}
apiVersion: networking.k8s.io/v1beta1
{{- end }}

{{- if semverCompare ">1.13-0" .Capabilities.KubeVersion.GitVersion }}
# 1.13 초과 버전에만 들어가는 필드
{{- end }}
```

#### `enabledServiceLinks` true OR null 패턴

Prometheus의 StatefulSet에서 본 관용구. "값이 명시적으로 true거나 아예 null이면 true로 친다"는 식의 fallback.

```yaml
{{- if or .Values.enableServiceLinks (eq (toString .Values.enableServiceLinks) "<nil>") }}
enableServiceLinks: true
{{- end }}
```

`toString`이 nil을 `"<nil>"` 문자열로 바꾸는 점을 이용한 트릭. **다소 난해하지만 오픈소스에서 종종 보인다.**

---

## Helm Chart 분석 — Grafana

Grafana는 **`templates/` 폴더 바깥에 보조 폴더(`ci/`, `tests/`, `dashboards/`)**를 적극 활용한다. 외부 파일을 차트에 임베드하는 `.Files` 객체와, 다음 챕터로 이어지는 `sha256sum` 변경 감지 관용구가 여기서 처음 나온다.

### Grafana 차트의 폴더 구조 — 보조 폴더의 역할

```
grafana/
├── Chart.yaml
├── values.yaml
├── ci/                 # 추가 values 파일 모음 — `helm install -f` 로 골라 주입
│   ├── default-values.yaml
│   └── with-ingress-values.yaml
├── templates/
│   ├── tests/          # `helm test` 명령으로만 배포되는 헬스체크용 리소스
│   ├── deployment.yaml
│   ├── statefulset.yaml
│   ├── _pod.tpl        # define 으로 Pod 스펙을 통째로 추출
│   └── ...
└── dashboards/         # ConfigMap에 박을 외부 JSON 파일 — `.Files.Get`으로 읽음
    └── sum.json
```

- **`ci/`**: `helm install -f values.yaml -f ci/with-ingress-values.yaml` 처럼 **여러 `-f`를 겹쳐서** 목적별 시나리오를 빠르게 띄울 수 있다.
- **`tests/`**: 다음에 나오는 **Hook + `helm test`** 와 짝지어진다.
- **`dashboards/`**: 차트에 동봉된 임의 파일을 ConfigMap의 데이터로 임베드.

### Grafana에서 처음 만나는 함수들

| 함수 / 객체 | 용도 |
|---|---|
| `.Files` | 차트 안 **임의 파일**을 읽음 (`.Files.Get`, `.Files.Glob` 등) |
| `sha256sum` | 문자열의 SHA256 해시 — **변경 감지용으로 자주 씀** |
| `template` vs `include` | 둘 다 사용자 정의 변수 호출. `include`는 결과를 **파이프라인으로 넘길 수 있고**, `template`은 그 자리에 출력만 함 |
| `hasKey` | 맵에 특정 키가 있는지 → bool |
| `kindIs "string" $v` | **종류 비교** (`string`, `map`, `slice` …). `typeIs`와 비슷하지만 인자가 더 유연 |
| `$.Template.BasePath` | **현재 차트의 templates/ 경로** 내장 객체 (`.Files.Get`과 짝) |

### Deployment vs StatefulSet 토글 — Pod 스펙은 한 곳에

Grafana는 `values.persistence.enabled`와 `persistence.type`에 따라 **Deployment 또는 StatefulSet** 중 하나만 배포되도록 분기한다. 그런데 두 매니페스트의 **Pod 스펙은 100% 동일**해야 한다. 그래서 `_pod.tpl`에 사용자 정의 변수로 한 번만 정의해 두고 양쪽에서 가져다 쓴다.

```yaml
# _pod.tpl
{{- define "grafana.pod" -}}
containers:
  - name: grafana
    image: ...
{{- end }}
```

```yaml
# deployment.yaml
{{- if and (not .Values.persistence.enabled) (eq .Values.persistence.type "pvc") }}
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      {{- include "grafana.pod" . | nindent 6 }}
{{- end }}
```

> **두 파일이 공통으로 들고 있어야 하는 큰 블록 → helpers로 빼라**의 모범 사례.

### `.Files` — 차트에 동봉한 파일 임베드

`templates/` 폴더 밖에 있는 파일(예: 대시보드 JSON)을 ConfigMap의 데이터로 박을 때 쓴다.

```yaml
{{- $files := .Files }}
data:
  dashboard.json: |-
    {{- $files.Get "dashboards/sum.json" | nindent 4 }}
```

```yaml
# 차트 폴더 구조 안에서 여러 파일을 한 번에
{{- range $path, $_ := .Files.Glob "dashboards/*.json" }}
  {{ base $path }}: |-
    {{- $.Files.Get $path | nindent 4 }}
{{- end }}
```

### sha256sum + `$.Template.BasePath` — ConfigMap 변경 감지 관용구

다음 챕터(개발 팁)에서 자세히 다룬다. Grafana의 Deployment에 박혀 있는 관용구를 그대로 옮기면:

```yaml
# Deployment의 pod template annotations
annotations:
  checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

- `$.Template.BasePath` = 현재 차트의 templates 경로
- `print` 로 파일 경로 합치기 → `include` 로 그 파일을 렌더한 결과를 받음
- `sha256sum`으로 해시화

ConfigMap 내용이 바뀌면 이 해시값도 바뀌고, Deployment 입장에선 spec이 변경된 것으로 보여 Pod가 재배포된다.

### 한 yaml에서 `range`로 ConfigMap 여러 개 만들기

Grafana 대시보드 ConfigMap은 `values.dashboards` 맵의 항목마다 별도 ConfigMap이 만들어진다. yaml 분리자 `---`를 range 안에 그대로 두는 방식.

```yaml
{{- range $providerName, $dashboards := .Values.dashboards }}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ $providerName }}-dashboards
data:
  {{- range $key, $value := $dashboards }}
    {{- if hasKey $value "json" }}
  {{ $key }}.json: |-
{{ index $value "json" | indent 4 }}
    {{- else if hasKey $value "file" }}
  {{ $key }}.json: |-
{{ $.Files.Get (index $value "file") | indent 4 }}
    {{- end }}
  {{- end }}
{{- end }}
```

> 같은 파일 안에 여러 리소스가 만들어지는 **Multi-document YAML** 패턴. `dashboardFound` 같은 boolean 플래그를 변수로 두고 range 안에서 갱신하는 자바스러운 패턴도 자주 보인다.

---

<!-- ============================================================ -->
<!-- 📢 내 발표 파트 시작 (강의 14~18 / 차트 개발 팁 · Helm Hook) -->
<!-- ============================================================ -->

## Helm 추가 기능 — NOTES, lint, get, rollback, package

> **🎤 발표 파트 (강의 14)** — Helm 추가 기능
>
> ⚠️ **강의 스크립트 미수신**. 강의 14의 실제 커버리지를 모르는 상태에서 **Helm 공식 문서 기준 정규 토픽으로 보강**한 섹션입니다. 발표 전 강의 영상과 대조해 가감 필요.

차트를 만드는 법(앞 챕터)과 운영 팁(다음 챕터) 사이에 들어가는 **"헬름이 추가로 제공하는 도구 / 메타 기능"** 들. 차트를 짜고 배포하는 본 흐름 외에, **사용자 가이드 메시지 / 검증 / 조회 / 롤백 / 패키지 공유** 등을 담당한다.

### 1. `NOTES.txt` — 배포 직후 보여주는 안내 메시지

`templates/NOTES.txt`를 만들어 두면 `helm install`/`helm upgrade` 직후 콘솔에 **그 내용이 렌더링되어 출력**된다. 사용자가 차트를 처음 깔았을 때 "이제 뭘 하면 되는지" 알려주는 안내문 용도.

```text
# templates/NOTES.txt
1. 다음 명령으로 애플리케이션을 확인하세요:

  kubectl get pods -n {{ .Release.Namespace }} -l app={{ include "mychart.name" . }}

2. 외부 접근 주소:
{{- if contains "NodePort" .Values.service.type }}
  export NODE_PORT=$(kubectl get svc {{ include "mychart.fullname" . }} -o jsonpath="{.spec.ports[0].nodePort}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "LoadBalancer" .Values.service.type }}
  kubectl get svc {{ include "mychart.fullname" . }} -w
{{- end }}
```

- 일반 템플릿과 똑같이 함수·변수가 다 동작한다.
- 한 번에 보여주기 좋은 길이로 압축하는 게 관례. 긴 문서는 README나 docs로.

### 2. 차트 검증 — `helm lint`, `helm template`, `--dry-run`

운영 환경에 배포하기 전에 차트가 잘 짜였는지 확인하는 3단계.

| 명령 | 검증 범위 | 클러스터 접근 |
|---|---|---|
| `helm lint ./mychart` | 차트 메타·디렉토리 구조·문법 | 없음 |
| `helm template ./mychart` | 실제 렌더링 결과(yaml) 출력 | 없음 (`--validate` 옵션 시 API 스키마 검증) |
| `helm install ... --dry-run --debug` | 실제 클러스터에 보낼 리퀘스트 시뮬레이션 | 있음 (API 서버에 dry-run 요청) |

```bash
helm lint ./mychart                              # 정적 문법 검사
helm template my-release ./mychart > out.yaml   # 렌더 결과만 보기
helm install my-release ./mychart --dry-run --debug
```

> CI 파이프라인의 첫 단계로 `helm lint`와 `helm template`를 박아두면 문법 깨진 차트가 PR에 들어오는 걸 빠르게 잡는다.

### 3. 배포 상태 조회 — `helm get`

배포된 릴리즈가 **실제로 어떤 값으로 어떻게 렌더되어 들어갔는지**를 다시 꺼내볼 때 쓴다.

```bash
helm get values   my-release   # 배포에 쓰인 values (사용자가 -f / --set으로 준 것)
helm get values   my-release --all   # 차트 기본값까지 합친 전체
helm get manifest my-release   # 실제로 클러스터에 적용된 yaml 전체
helm get notes    my-release   # NOTES.txt 렌더링 결과
helm get hooks    my-release   # 등록된 Hook 리소스
helm get all      my-release   # 위 전부
```

운영 중 "이 릴리즈에 어떤 값이 들어갔더라?"가 가장 자주 쓰는 use case.

### 4. 롤백 — `helm rollback`

[Helm 운영 팁] 챕터에서 다룬 **Secret 기반 리비전 저장소**가 여기서 빛난다. 리비전이 남아 있는 한 과거 상태로 한 번에 되돌릴 수 있다.

```bash
helm history my-release                  # 리비전 목록 확인
helm rollback my-release 3               # 리비전 3으로 되돌림
helm rollback my-release 3 --wait        # Pod 다 뜰 때까지 블록
helm rollback my-release 3 --recreate-pods   # Pod 강제 재생성
```

- 롤백 자체도 **새 리비전 번호를 만든다** (예: 5번에서 3번으로 롤백 → 6번 리비전이 "3번과 동일한 상태"로 기록).
- 그러므로 또 롤백할 수 있다.

### 5. 차트 패키지/공유 — `helm package` / `helm repo` / `helm push`

내가 만든 차트를 다른 사람·다른 클러스터에서 쓰게 하려면 차트를 **`.tgz`로 묶어 레포지토리에 올린다.**

```bash
helm package ./mychart                # mychart-0.1.0.tgz 생성
helm repo index .                     # index.yaml 갱신 (정적 호스팅용)

# OCI 레지스트리(예: GHCR, ECR)에 직접 푸시 (Helm v3.8+)
helm push mychart-0.1.0.tgz oci://ghcr.io/myorg/charts

# 다른 사람은 이렇게 받음
helm repo add my-charts https://charts.example.com
helm repo update
helm install my-app my-charts/mychart
```

- **OCI 레지스트리 사용**이 점점 표준화되는 추세. 별도 차트 호스팅 서버 없이 컨테이너 레지스트리를 그대로 차트 레포로 쓴다.
- `.helmignore`로 **패키징에서 제외할 파일**을 지정할 수 있다. (`.git`, `*.md`, `ci/` 등을 흔히 제외)

### 6. 리소스 보존 — `helm.sh/resource-policy: keep`

`helm uninstall` 시 **이 리소스만은 지우지 말아달라**고 표시하는 어노테이션. PV, PVC, Secret처럼 **데이터가 함께 사라지면 곤란한 리소스**에 자주 쓴다.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  annotations:
    "helm.sh/resource-policy": keep
spec: ...
```

- 릴리즈를 다시 install해도 이 리소스는 **헬름이 더 이상 관리하지 않는 orphan**이 된다. 직접 `kubectl delete`로만 지울 수 있음.
- 운영 데이터 보호의 최후 보루.

### 7. 서브차트 (Subchart) — 값 오버라이드 규칙

[Helm Chart 분석 — Prometheus]의 종속성 차트가 곧 서브차트다. **부모 차트의 values.yaml에서 자식 차트의 값을 덮어쓸 수 있다.**

```yaml
# 부모 values.yaml
kubeStateMetrics:    # 자식 차트의 이름과 일치하는 키
  replicaCount: 3    # 자식의 .Values.replicaCount를 3으로 덮어씀
  image:
    tag: v2.10.0
```

```yaml
# 부모 → 자식 모두에 적용하고 싶을 때 (글로벌)
global:
  imageRegistry: registry.example.com   # 모든 자식 차트의 .Values.global.imageRegistry로 접근 가능
```

- `global` 블록은 **부모와 모든 자식이 공유**하는 특별 영역.
- 자식 차트는 부모의 일반 값에는 직접 접근할 수 없고, **글로벌이나 자기 영역 키**로만 받는다.

### 8. 라이브러리 차트 (Library Chart)

`type: library`로 선언된 차트는 **그 자체로는 배포 불가**하지만, **다른 차트가 가져다 쓸 헬퍼 정의 모음**으로 쓰인다. 회사 차트들이 공통으로 쓰는 라벨/네이밍 룰을 한 곳에 묶을 때.

```yaml
# Chart.yaml
apiVersion: v2
name: common
type: library
```

```yaml
# 다른 차트가 dependencies로 끌어다 씀
dependencies:
  - name: common
    version: 1.x.x
    repository: oci://ghcr.io/myorg/charts
```

```yaml
# 그 차트의 deployment.yaml
metadata:
  labels:
    {{- include "common.labels" . | nindent 4 }}   # 라이브러리 차트의 define 사용
```

