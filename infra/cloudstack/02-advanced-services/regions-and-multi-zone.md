# Regions and Multi-Zone — 큰 그림 토폴로지

> **여러 데이터센터 / 여러 MS 인스턴스 / 사용자 페더레이션을 묶는 최상위 단위.**

> 출처: [Concepts — Cloud Infrastructure Overview](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#cloud-infrastructure-overview) · [Region](https://docs.cloudstack.apache.org/en/latest/adminguide/usage/regions.html).

---

## 1. 계층 다시

```
Region   (지리적 묶음)
  └─ Zone   (DC 1개)
       └─ Pod   (랙 1개)
            └─ Cluster   (같은 하이퍼바이저 + 스토리지)
                 └─ Host
                      └─ VM
```

각 계층의 의미는 [00-overview/architecture-overview.md](../00-overview/architecture-overview.md) 에서 다뤘다. 여기는 **Region/Zone 의 운영 시나리오**.

---

## 2. Single Zone vs Multi-Zone vs Multi-Region

### Single Zone — 입문/소규모

```
Region: rome (단일)
  └─ Zone: rome-z1
       └─ Pod-1, Pod-2, ...
```

대부분의 학습/PoC. 본 정리의 [03-installation](../03-installation/) 도 이 경우.

### Multi-Zone (한 Region 안 여러 DC)

```
Region: korea
  ├─ Zone: kr-seoul     (서울 DC)
  └─ Zone: kr-busan     (부산 DC)
```

- 한 Account가 두 Zone에 VM 띄울 수 있음
- Zone 간 **자원/네트워크는 격리** (라이브 마이그레이션 X)
- 사용자는 Zone 선택해서 deploy

```bash
$ cmk deploy virtualmachine \
    zoneid=<kr-seoul> \
    ...
```

→ AWS의 **Region 안의 AZ** 와 비슷한 의미. (CloudStack의 "Zone" 은 사실상 AZ에 가까움)

### Multi-Region (여러 지리)

```
[Region: korea]               [Region: japan]
   ├─ Zone: kr-seoul             ├─ Zone: jp-tokyo
   └─ Zone: kr-busan             └─ Zone: jp-osaka
   │                              │
   └─ MS Cluster (3대)            └─ MS Cluster (3대)
   └─ MySQL (자체)                └─ MySQL (자체)
        │                              │
        └────── Federation ────────────┘
                (사용자 SSO 페더레이션)
```

- 각 Region은 **자기 MS + MySQL** 가짐 → 데이터 주권 / 네트워크 분리
- **사용자만 페더레이션** (한 사용자가 양쪽 Region에 접근 가능)
- 자원/이벤트는 Region 단위 격리

---

## 3. Region 페더레이션 — 사용자만 공유

> [Region Configuration](https://docs.cloudstack.apache.org/en/latest/adminguide/usage/regions.html).

```
[Region: korea]                [Region: japan]
  Account "alice"                Account "alice"
   ↑ 같은 user_id                ↑ 같은 user_id
   │                              │
   └────────── Region 설정 ───────┘
              (서로의 endpoint 등록)
```

흐름:
1. 한 Region(예: korea)에서 Account 생성
2. 다른 Region(japan)에 같은 Account 페더레이션
3. 사용자는 어느 Region 엔드포인트로도 접속 가능

자원은 여전히 **Region 단위 격리**. 즉 korea의 VM이 japan에서 안 보임.

```bash
# Region 추가
$ cmk add region \
    id=2 \
    name=japan \
    endpoint=https://japan-ms.example.com:8443/client/api

$ cmk list regions
```

---

## 4. Multi-Zone 운영 패턴

### Pattern A: 각 Zone이 자급자족

```
Zone-A:
  - Secondary Storage: A 자체
  - Primary: A의 Cluster들
  - Network: A의 Public/Guest

Zone-B: 같은 식 (독립)
```

**가장 단순**. Zone 사이 자원 의존 없음.

### Pattern B: 공유 Secondary

여러 Zone이 같은 NFS/S3 Secondary 를 공유 → 템플릿 한 번만 등록.

```
Zone-A   Zone-B
  │        │
  └────┬───┘
       ▼
 [공통 Secondary (S3 또는 NFS)]
```

**대규모 운영에 유리**. 단, 네트워크 latency 주의.

### Pattern C: Zone-wide Primary (KVM + Ceph)

```
Zone-X:
  └─ Pod-1
      └─ Cluster-A (KVM)
      └─ Cluster-B (KVM)
  └─ Primary: Ceph (Zone 전체 공유)
```

KVM + Ceph RBD 조합에서만 가능. **Cluster 경계를 넘어서도 라이브 마이그레이션** 가능.

---

## 5. 사용자 시나리오

### 멀티 Zone에 VM 분산 (HA)

```bash
# Zone A에 VM
$ cmk deploy virtualmachine zoneid=<zone-A> name=app-a-1

# Zone B에 VM
$ cmk deploy virtualmachine zoneid=<zone-B> name=app-b-1

# 외부 LB(GSLB) 또는 DNS GeoLocation 으로 분산
```

CloudStack은 **GSLB** 도 자체 제공 (Network Offering의 GSLB Service).

### 백업 / DR

```
운영: Zone-A
  └─ 매일 Snapshot
        ▼
   공유 Secondary 또는 S3
        ▼
복구: Zone-B
  └─ Snapshot으로부터 Volume 복원 → VM 부팅
```

**Volume Snapshot을 다른 Zone에서 복원** 가능 (단, 같은 하이퍼바이저 type 필요).

---

## 6. 자주 밟는 지뢰

- **Zone 간 라이브 마이그레이션 시도** → ❌ 안 됨. Cluster 경계 안에서만 (또는 Zone-wide Primary).
- **Region 페더레이션 후 자원 안 보임** → 정상. Region은 격리.
- **Zone-wide Primary 만들고 Cluster마다 다른 게 나옴** → 정상. Zone-wide는 옵션, Cluster scope가 default.
- **Multi-Zone 만들었는데 Secondary 공유 안 함** → 운영자가 각 Zone에 따로 등록해야 함.
- **Zone 간 네트워크 통신** → 직접 X. Public IP 거치거나 Site-to-Site VPN으로 묶음.

---

## 7. 큰 그림 의사결정

```
Q: 사용자에게 어떤 옵션 노출?
   ├─ Single Zone:    "VM 만들 때 옵션 X (자동 선택)"
   ├─ Multi-Zone:     "VM 만들 때 Zone 선택"
   └─ Multi-Region:   "URL 다른 데로 접속 (필요 시 다른 region에서 사용)"

Q: 운영팀은 몇 명이 무엇을 보나?
   ├─ Single Zone:    한 팀이 한 곳만
   ├─ Multi-Zone:     한 팀이 여러 Zone (같은 MS)
   └─ Multi-Region:   각 Region 운영팀 + 페더레이션 운영자
```

---

## 8. OpenStack/AWS 매핑

| AWS | OpenStack | CloudStack |
|---|---|---|
| Region | Region | Region |
| AZ | Region 안 별도 endpoint or Aggregate | Zone |
| Edge / LZ | (별도) | (없음) |
| 글로벌 IAM | Federated Keystone | Region 페더레이션 |

→ "AWS의 Region/AZ" ≈ "CloudStack의 Region/Zone".

---

## 다음

→ [../03-installation/multipass-allinone/setup-guide.md](../03-installation/multipass-allinone/setup-guide.md): 단일 Zone 환경 만들기.
→ [../04-operations/upgrade-strategy.md](../04-operations/upgrade-strategy.md): Multi-Zone 환경 업그레이드.

---

## 공식 문서 레퍼런스

- [Concepts — Cloud Infrastructure Overview](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#cloud-infrastructure-overview)
- [Admin Guide — Regions](https://docs.cloudstack.apache.org/en/latest/adminguide/usage/regions.html)
- [About Zones](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#about-zones)
