# Magnum — K8s 클러스터 셀프서비스

> **"쿠버네티스 클러스터 하나 주세요" 한 번으로 노드 VM들이 자동 생성되는 서비스.**

AWS EKS, GKE, AKS와 비슷한 **관리형 K8s**를 OpenStack 안에서 구현한 것.

---

## 왜 필요한가

K8s 직접 깔려면:
1. VM 3~5개 수동 생성
2. 각 VM에 containerd/kubelet 설치
3. `kubeadm init` 마스터 구성
4. 워커 노드 `kubeadm join`
5. CNI(Calico/Flannel) 설치
6. 스토리지 클래스 연결
7. LoadBalancer 타입 지원을 위한 Cloud Provider 설정

→ 쉬워 보이지만 **프로덕션 멱등성·HA·업그레이드까지** 가면 지옥.

Magnum은 이걸 **한 줄**로:

```bash
$ openstack coe cluster create my-k8s \
    --cluster-template k8s-template \
    --node-count 3
```

---

## 한 줄 요약

Magnum은 "K8s 클러스터를 Heat 템플릿으로 찍어내는 래퍼"다. 내부적으로 **Heat + Nova + Neutron + Cinder**를 다 부려서 완성된 클러스터를 만든다.

```
사용자: "K8s 클러스터 만들어줘"
    ▼
Magnum → Heat: (k8s 템플릿 실행)
    ▼
Heat → Nova: 마스터 VM, 워커 VM 생성
     → Neutron: 전용 네트워크, LB
     → Cinder: 볼륨
    ▼
VM들이 cloud-init으로 자기 자신 K8s로 구성
    ▼
완성된 kubeconfig 반환
```

---

## 핵심 개념

| 용어 | 의미 |
|---|---|
| **COE** | **C**ontainer **O**rchestration **E**ngine. K8s, Swarm, Mesos 중 선택 가능(사실상 K8s) |
| **Cluster Template** | 클러스터 "기종". 어떤 이미지/flavor/네트워크/버전 쓸지 |
| **Cluster** | 실제 클러스터 인스턴스 |
| **Node Group** | 마스터/워커 그룹. 그룹마다 다른 flavor 가능 |

Template이 **"설계도"**, Cluster가 **"완성품"**.

---

## 손으로 해보기

### 1. 템플릿 준비 (한 번만)

```bash
$ openstack coe cluster template create k8s-template \
    --image fedora-coreos-38 \
    --external-network public \
    --dns-nameserver 8.8.8.8 \
    --master-flavor m1.medium \
    --flavor m1.large \
    --coe kubernetes \
    --network-driver calico \
    --volume-driver cinder
```

### 2. 클러스터 생성

```bash
$ openstack coe cluster create my-k8s \
    --cluster-template k8s-template \
    --master-count 3 \
    --node-count 5 \
    --keypair my-key

# 10~15분 대기
$ openstack coe cluster list
```

### 3. kubectl 연결

```bash
$ mkdir -p ~/clusters/my-k8s
$ cd ~/clusters/my-k8s
$ $(openstack coe cluster config my-k8s)
$ kubectl get nodes
NAME         STATUS   ROLES    AGE   VERSION
master-0     Ready    master   5m    v1.28.0
worker-0     Ready    <none>   5m    v1.28.0
...
```

이제 평범한 K8s 클러스터로 쓰면 됨.

---

## OpenStack 통합이 주는 것

Magnum K8s는 자동으로 **OpenStack Cloud Provider**를 붙여준다. 그래서:

- `kubectl apply` 로 `Service type=LoadBalancer` → **Octavia LB 자동 생성**
- `PersistentVolumeClaim` → **Cinder 볼륨 자동 생성**
- `StorageClass` → Cinder 백엔드 선택 (SSD/HDD 티어)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: LoadBalancer  # ← Octavia가 자동으로 공인IP 붙은 LB 만들어줌
  ports: [{port: 80}]
  selector: {app: web}
```

K8s가 OpenStack과 얘기해서 **진짜 LB/볼륨**을 띄운다.

---

## 클러스터 스케일링/업그레이드

```bash
# 워커 추가
$ openstack coe cluster resize my-k8s 10

# 쿠버네티스 버전 업그레이드
$ openstack coe cluster upgrade my-k8s <new-template-uuid>

# 삭제
$ openstack coe cluster delete my-k8s
```

업그레이드는 **롤링 업데이트**로 노드 하나씩 교체.

---

## 자주 밟는 지뢰

- **클러스터 생성이 "CREATE_FAILED"** → Heat stack 로그부터. 대개 이미지/flavor/네트워크 설정 문제
- **kubectl 연결 안 됨** → 마스터 공인IP 접근 차단됐는지 확인 (Floating IP + Security Group)
- **이미지 선택** → Magnum은 **Fedora CoreOS / Ubuntu / Atomic** 등 특정 이미지만 지원. 그냥 Ubuntu server는 안 됨
- **Cluster API로 대체되는 추세** → CNCF의 Cluster API (CAPI) + CAPO(CAPI for OpenStack) 조합이 떠서 Magnum 신규 도입은 줄어드는 중. 기존 환경 유지에는 여전히 유효

---

## Magnum vs Cluster API (CAPO)

| 기준 | Magnum | Cluster API (CAPO) |
|---|---|---|
| 관리 주체 | OpenStack | K8s Operator |
| 배포 도구 | Heat | CRD + Controller |
| 업그레이드 | OpenStack 릴리스 따라감 | 독립적 |
| 커뮤니티 | 줄어드는 추세 | 활발 |

> 2024년 이후 새로 시작한다면 **CAPO** 검토. 기존 Magnum은 유지.

---

## AWS 매핑

| AWS | Magnum |
|---|---|
| EKS | Magnum K8s |
| EKS Managed Node Group | Node Group |
| eksctl | openstack coe cluster create |

---

## 다음

→ [heat-orchestration.md](./heat-orchestration.md): Magnum이 내부적으로 쓰는 Heat  
→ [octavia-lbaas.md](./octavia-lbaas.md): K8s Service(LoadBalancer)가 자동 호출하는 LB
