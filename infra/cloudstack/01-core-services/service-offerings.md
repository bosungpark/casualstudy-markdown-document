# Service / Disk / Network Offering — 정책의 메뉴판

> **OpenStack의 Flavor가 CPU/RAM 만이라면, CloudStack의 Offering은 거기에 HA/QoS/CPU pinning/storage tag/LB 같은 정책까지 묶은 패키지다.**

> 출처: [Admin Guide — Service Offerings](https://docs.cloudstack.apache.org/en/latest/adminguide/service_offerings.html).

---

## 1. 3종 Offering

| Offering | 무엇을 정의 | 누가 쓰나 |
|---|---|---|
| **Compute (Service) Offering** | vCPU, Memory, CPU 속도, HA, CPU pinning, NUMA, 호스트 태그 | VM 생성 시 |
| **Disk Offering** | Disk size, IOPS limit, Bytes/sec limit, storage tag | Volume 생성 시 |
| **Network Offering** | DHCP/DNS/SNAT/PF/LB/Firewall/VPN 중 어느 서비스 제공 | Network 생성 시 |

→ 운영자가 미리 정의 → 사용자가 메뉴에서 고름.

---

## 2. Compute (Service) Offering — Flavor++

### 기본 필드

| 필드 | 의미 |
|---|---|
| `cpunumber` | vCPU 개수 |
| `cpuspeed` | MHz (보통 게스트 CPU 속도 hint) |
| `memory` | MB |

### 정책 필드

| 필드 | 의미 |
|---|---|
| `offerha` | HA 활성화 (호스트 죽으면 다른 호스트로 자동 재시작) |
| `cpuPinning` | CPU 코어를 VM 전용으로 고정 |
| `numa.config` | NUMA 토폴로지 노출 |
| `hosttags` | 특정 태그 호스트에만 배치 (예: gpu, ssd-only) |
| `iopsReadRate`/`iopsWriteRate` | 디스크 IOPS QoS |
| `bytesReadRate`/`bytesWriteRate` | 디스크 BW QoS |
| `networkRate` | NIC 대역폭 (Mbps) |
| `dynamicScalingEnabled` | 라이브 리사이즈 허용 |
| `customized` | 사용자가 vCPU/Mem를 직접 입력 |

### 예시

```bash
# 표준 패키지
$ cmk create serviceoffering \
    name=m1.small \
    displaytext="1 vCPU, 1 GB" \
    cpunumber=1 \
    cpuspeed=1000 \
    memory=1024

# HA + CPU pinning 패키지
$ cmk create serviceoffering \
    name=critical-db \
    displaytext="HA + Pin" \
    cpunumber=4 \
    cpuspeed=2400 \
    memory=8192 \
    offerha=true \
    cpuPinning=true \
    hosttags=db-tier

# 사용자 정의 (customized)
$ cmk create serviceoffering \
    name=custom \
    displaytext="User-defined" \
    customized=true
```

### "Constrained / Unconstrained"

`customized=true` 시:
- **Unconstrained**: 사용자가 자유롭게 vCPU/Mem 지정
- **Constrained**: min/max 범위 안에서만

---

## 3. Disk Offering — Volume Type ++

```bash
$ cmk create diskoffering \
    name=ssd-100gb \
    displaytext="SSD 100GB" \
    disksize=100 \
    customized=false \
    iopsReadRate=3000 \
    iopsWriteRate=3000 \
    bytesReadRate=125000000 \
    bytesWriteRate=125000000 \
    storageTags=ssd
```

### 핵심 필드

| 필드 | 의미 |
|---|---|
| `disksize` | GB |
| `customized` | 사용자가 사이즈 입력 |
| `storageTags` | 매칭되는 Primary Storage 태그 |
| `iopsReadRate`, `iopsWriteRate` | IOPS 상한 |
| `bytesReadRate`, `bytesWriteRate` | BW 상한 |
| `provisioningType` | thin / sparse / fat |
| `cacheMode` | none / writeback / writethrough |

→ **Storage Tag** 매칭이 핵심. Disk Offering의 tag와 같은 tag를 가진 Primary Storage에서만 Volume이 생성됨.

```
Disk Offering: storageTags=ssd
       ▼
StoragePoolAllocator: Primary 중 storageTags=ssd 인 것만 후보
       ▼
선택 후 Volume 생성
```

---

## 4. Network Offering — 네트워크 메뉴판

> [networking.md](./networking.md) 에서 다룬 그것. 핵심만 다시.

```
Network Offering: "Default Isolated"
   └─ Services:
       ├─ DHCP (provider: VR)
       ├─ DNS (provider: VR)
       ├─ Source NAT (provider: VR)
       ├─ Static NAT (provider: VR)
       ├─ Port Forwarding (provider: VR)
       ├─ Firewall (provider: VR)
       ├─ Load Balancer (provider: VR)
       └─ User Data (provider: VR)
   └─ Properties:
       ├─ Guest Type: Isolated
       ├─ Specify VLAN: false (자동 할당)
       └─ Conserve Mode: true (Public IP 재사용)
```

### Service Provider 개념

같은 서비스(예: LB)를 다른 Provider 가 제공할 수도 있다:
- LB Provider: VR(HAProxy) / NetScaler / F5 BIG-IP
- Firewall Provider: VR / Juniper SRX

→ "**서비스 + Provider**" 매트릭스가 Network Offering의 본질.

```bash
$ cmk create networkoffering \
    name=tenant-net \
    displaytext="Default tenant net" \
    guestiptype=Isolated \
    traffictype=Guest \
    serviceProviderList[0].service=Dhcp \
    serviceProviderList[0].provider=VirtualRouter \
    serviceProviderList[1].service=Dns \
    serviceProviderList[1].provider=VirtualRouter \
    ...
```

(보통 UI에서 만든다.)

---

## 5. 시스템 Offering (System VM Offering)

내부 System VM(SSVM/CPVM/VR)도 자기만의 Offering을 가진다. 별도로 관리.

```bash
$ cmk list serviceofferings issystem=true

# SystemVM Offering 갱신 (큰 부하 환경에서 VR 메모리 늘리기 등)
$ cmk update serviceoffering id=<...> sortkey=<...>
```

---

## 6. 손으로 해보기 — 메뉴 만들고 주문하기

```bash
# 1. 메뉴 생성 (admin)
$ cmk create serviceoffering \
    name=t2.micro \
    displaytext="1 vCPU, 1 GB, no HA" \
    cpunumber=1 cpuspeed=1000 memory=1024

# 2. Disk 메뉴 생성
$ cmk create diskoffering \
    name=basic-20 displaytext="Basic 20GB" \
    disksize=20

# 3. Network 메뉴는 default 사용

# 4. 사용자가 메뉴 보고 주문
$ cmk list serviceofferings
$ cmk list diskofferings
$ cmk list networkofferings state=Enabled

$ cmk deploy virtualmachine \
    serviceofferingid=<t2-micro> \
    diskofferingid=<basic-20> \
    templateid=<...> \
    zoneid=<...> \
    networkids=<...>
```

---

## 7. 자주 밟는 지뢰

- **VM 생성이 NoAvailableHost** → Compute Offering의 hosttags 가 없는 호스트만 있음. `cmk update host hosttags=...` 또는 offering 수정.
- **Volume 생성이 NoAvailableStorage** → Disk Offering의 storageTags 와 매칭되는 Primary 없음. Primary에 tag 추가.
- **HA 옵션 켰는데 VM이 다른 호스트로 안 옮겨감** → `cluster.cpu.allocated.capacity.disablethreshold` 등 capacity 임계 초과 일 수 있음.
- **CPU pinning 활성 후 마이그레이션 실패** → 대상 호스트에 동일한 NUMA/CPU 토폴로지 필요.
- **Customized offering 사용자가 너무 큰 값 입력** → Constrained로 만들어 max 제한.

---

## 8. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Flavor | Service Offering (+ HA/QoS/Pinning 추가) |
| Volume Type | Disk Offering (+ storage tag) |
| (없음 — Neutron이 동적) | Network Offering (네트워크 정책 패키지) |
| Host Aggregate | Host Tag + Service Offering의 hosttags |
| (없음) | System VM Offering |

---

## 다음

→ [../02-advanced-services/system-vms.md](../02-advanced-services/system-vms.md): System VM에 적용되는 system offering.
→ [../labs/01-first-vm.md](../labs/01-first-vm.md): 메뉴 골라서 첫 VM 만들기.

---

## 공식 문서 레퍼런스

- [Admin Guide — Service Offerings](https://docs.cloudstack.apache.org/en/latest/adminguide/service_offerings.html)
- [Compute Offering](https://docs.cloudstack.apache.org/en/latest/adminguide/service_offerings.html#compute-and-disk-service-offerings)
- [System Service Offering](https://docs.cloudstack.apache.org/en/latest/adminguide/service_offerings.html#system-service-offerings)
- [Network Offerings](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html#about-network-offerings)
