# Nova — VM 오케스트레이터

> **"VM 만들어줘" 한 줄을 받아서 실제 서버 위에 띄워주는 지휘자.**

OpenStack에서 제일 유명한 친구. AWS의 EC2에 해당한다.

---

## 한 줄 요약

Nova는 **VM을 직접 만들지 않는다.** KVM/libvirt 같은 하이퍼바이저를 **부리는** 쪽이다. 식당 주방장이 아니라 **매니저**다.

```
사용자: "4코어 8G짜리 VM 하나"
    ▼
  Nova가 판단: "어느 서버가 한가해?"  → Placement에 질의
    ▼
  Nova가 지시: "서버 3번! libvirt로 띄워!"
    ▼
  실제 VM 탄생
```

---

## 비유: 호텔 VM 사업부

- **nova-api** = 프론트 (주문 접수)
- **nova-scheduler** = 객실 배정 담당 (어느 건물/층에 투숙객 넣을지)
- **nova-conductor** = 경리팀 (DB 접근 중앙화 — 청소부가 금고 못 열게)
- **nova-compute** = 각 건물 직원 (실제로 방 청소하고 준비)

`nova-compute`는 Compute 노드마다 한 개씩 뜬다. 나머지 셋은 컨트롤 노드에 몰려 있다.

---

## 요청 흐름 — "VM 하나 주세요"

```
[1] 사용자 → nova-api: POST /servers (flavor, image, network)
[2] nova-api → Keystone: 토큰 검증
[3] nova-api → nova-conductor → DB: "요청 기록"
[4] nova-conductor → nova-scheduler: "어디다 띄울까?"
[5] nova-scheduler → Placement: "CPU 4, RAM 8G 되는 호스트?"
    ← ["compute-01", "compute-03"]
[6] scheduler 필터링 → "compute-03 선택"
[7] nova-conductor → compute-03의 nova-compute: "띄워!"
[8] nova-compute → Glance: 이미지 다운로드
             → Neutron: 포트 생성, IP 할당
             → Cinder: 볼륨 생성 & attach
             → libvirt: "VM 시작해"
[9] VM 부팅 → ACTIVE 상태
```

한 번 VM 만드는 데 **6개 서비스**가 협업한다. OpenStack은 느슨한 연합체라는 말의 실제 모습.

---

## VM 라이프사이클

```
BUILD ──► ACTIVE ──► (SHUTOFF/PAUSED/SUSPENDED/RESIZED) ──► DELETED
                 └─► ERROR
```

- **BUILD**: 생성 중
- **ACTIVE**: 실행 중
- **SHUTOFF**: 껐음 (전원 off)
- **PAUSED**: RAM에 얼림 (빠르게 복구)
- **SUSPENDED**: 디스크에 얼림 (RAM까지 내림)
- **RESIZED**: 스펙 변경 중 (확인 대기)
- **ERROR**: 뭔가 터짐

---

## 핵심 객체

| 객체 | 설명 |
|---|---|
| **Server** (=Instance) | VM 그 자체 |
| **Flavor** | CPU/RAM/디스크 스펙 템플릿. AWS의 `m5.large` 같은 거 |
| **Image** | OS 이미지 (Glance에서 가져옴) |
| **Keypair** | SSH 공개키 |
| **Security Group** | 방화벽 규칙 (Neutron 객체지만 Nova가 자주 씀) |
| **Server Group** | 여러 VM을 "한 서버에 몰아줘" 또는 "서로 다른 서버에 나눠줘" (affinity/anti-affinity) |
| **Aggregate / AZ** | Compute 호스트 묶음 (하드웨어별 / 랙별 분리) |

---

## 스케줄러가 어떻게 호스트를 고르나

```
전체 Compute 호스트
        ▼
  [Filter] RAM 충분?  CPU 충분?  AZ 맞아?  Image 포맷 지원?
        ▼
  살아남은 후보들
        ▼
  [Weigher] RAM 여유 많은 놈한테 가중치 → 정렬
        ▼
  Top 1 선택
```

필터 & 가중치 조합은 `nova.conf`에서 설정. 대부분 기본값으로도 잘 돈다.

> 최근엔 **Placement**가 1차 필터를 먼저 친다. "CPU/RAM 숫자"만 가지고 후보 줄이기 → Nova scheduler가 더 똑똑한 필터(AZ, affinity 등)를 돌림.

---

## 손으로 해보기

```bash
# flavor 목록
$ openstack flavor list

# 이미지 목록
$ openstack image list

# VM 만들기
$ openstack server create \
    --flavor m1.small \
    --image ubuntu-22.04 \
    --network private-net \
    --key-name my-key \
    my-vm

# 상태 보기
$ openstack server list
$ openstack server show my-vm

# 콘솔 붙기
$ openstack console url show my-vm

# 삭제
$ openstack server delete my-vm
```

---

## 자주 밟는 지뢰

- **VM이 ERROR 상태** → `openstack server show <id>` 의 `fault` 필드 보기. 대부분 **이미지/네트워크/볼륨 문제**
- **"No valid host was found"** → Placement에 자원 없음. Compute 노드 죽었거나 꽉 찼거나
- **Live migration 실패** → 공유 스토리지(Ceph/NFS) 또는 block migration 설정 필요
- **cold reboot vs hard reboot** → cold는 OS에게 부탁, hard는 그냥 껐다 켜기

---

## AWS 매핑

| AWS | Nova |
|---|---|
| EC2 Instance | Server |
| Instance Type (`m5.large`) | Flavor |
| AMI | Image (Glance) |
| Key Pair | Keypair |
| AZ | Availability Zone / Host Aggregate |
| Placement Group | Server Group (affinity/anti-affinity) |

---

## 다음

→ [neutron-networking.md](./neutron-networking.md) 에서 VM이 어떻게 네트워크에 붙는지.  
→ [placement.md](./placement.md) 에서 스케줄러가 뭘 보고 배치하는지.
