# Placement — 자원 가계부

> **"어느 호스트에 CPU/RAM/디스크가 얼마나 남았나"를 추적하는 인벤토리 DB.**

Nova, Cinder, Neutron이 자원 배치할 때 공통으로 물어보는 **자원 가계부**.

---

## 한 줄 요약

Nova-scheduler가 VM을 배치할 때 "CPU 4, RAM 8G 되는 호스트 있어?" 라고 물어보는 상대가 Placement다. 원래 Nova 안에 있었는데 **독립 서비스로 분리**(Stein 릴리스부터).

```
[Nova scheduler] ──► [Placement] "CPU 4, RAM 8G 호스트?"
                        │
                        ▼
                    ["compute-01", "compute-03"]
```

---

## 핵심 개념 4개

### 🏭 Resource Provider

자원을 가진 주체. 주로 **Compute 호스트**지만, 스토리지 풀, SR-IOV NIC, GPU 카드 같은 것도 Provider가 될 수 있다.

### 📊 Inventory

각 Provider가 **얼마나 가졌는지**.

```
compute-01:
  VCPU:       64
  MEMORY_MB:  256000
  DISK_GB:    2000
```

### 📝 Allocation

**누가 얼마나 썼는지**. VM이 consumer가 되고, 그 VM이 먹는 자원을 기록.

```
VM "my-vm" on compute-01:
  VCPU:       4
  MEMORY_MB:  8192
  DISK_GB:    20
```

### 🏷️ Trait

Provider의 **속성 태그**. 수량이 아니라 boolean.

```
compute-01 traits:
  HW_CPU_X86_AVX2       (AVX2 지원)
  STORAGE_DISK_SSD      (SSD 있음)
  HW_GPU_NVIDIA         (NVIDIA GPU 있음)
```

"AVX2 + SSD 조건 만족하는 호스트" 같은 질의가 가능.

---

## 질의 예시

```
요청: "VCPU=4, MEMORY_MB=8192, trait=SSD"

Placement가 하는 일:
  1. 모든 Provider 스캔
  2. Inventory - Allocation ≥ 요청량  필터
  3. Trait 조건 매칭 필터
  4. 남은 후보 리스트 반환
```

이걸 **Allocation Candidates** 라고 부름. Nova scheduler가 이 리스트에서 다시 2차 필터 + 가중치로 최종 선택.

---

## 왜 분리됐나

옛날 Nova 안에 있을 때:
- "자원 남았어?"를 물어봐야 하는 주체가 Nova 하나가 아니게 됨
- Cyborg(FPGA/GPU), Neutron(대역폭), Cinder(스토리지)도 자원 질의 필요
- → **독립 서비스로 빼서 공용 API**로 만듦 (Stein, 2019)

현재는 Nova 외에도 Neutron이 bandwidth-aware scheduling에 Placement를 쓴다.

---

## 손으로 해보기

```bash
# Resource Provider 목록 (호스트 목록)
$ openstack resource provider list

# 특정 호스트 인벤토리
$ openstack resource provider inventory list <uuid>

# 할당 현황
$ openstack resource provider show --allocations <uuid>

# Trait 목록
$ openstack resource provider trait list <uuid>

# 후보 쿼리
$ openstack allocation candidate list \
    --resource VCPU=4 --resource MEMORY_MB=8192
```

---

## 실무 용례

### 1. 이상한 스케줄링 디버깅

VM 생성이 "No valid host" 로 실패할 때, **Placement 인벤토리를 먼저** 보자.

```bash
$ openstack resource provider inventory list compute-01
# 실제 사용량 vs 예약된 양 비교
```

Placement에서 꽉 차 보이는데 실제 서버는 한가하면 → **Allocation 꼬임**이다. VM 삭제됐는데 할당이 안 지워진 경우. `nova-manage placement heal_allocations` 로 복구.

### 2. GPU 스케줄링

GPU 노드에 trait 달고, flavor에 trait 요구사항 넣으면 자동 매칭.

```bash
$ openstack flavor set gpu-flavor \
    --property resources:VGPU=1 \
    --property trait:HW_GPU_NVIDIA=required
```

---

## 자주 밟는 지뢰

- **"No allocation candidates"** → flavor가 요구하는 trait/resource를 가진 Provider 없음
- **용량 있는데 배치 실패** → **Allocation 꼬임**. `heal_allocations` 실행
- **reserved 값 누수** → `nova.conf`의 `reserved_host_memory_mb` 등 설정 확인
- **Placement DB 폭증** → 오래된 consumer(삭제된 VM) 정리 스크립트 필요

---

## 한 줄 비유

**Placement는 호텔의 객실 현황판.** 청소 끝난 방, 투숙 중인 방, 수리 중인 방을 실시간으로 기록. 프론트 데스크(Nova scheduler)가 손님 배정할 때 이 현황판만 보면 됨.

---

## AWS 매핑

**없음.** AWS는 EC2 스케줄러 내부에 숨겨져 있고 외부에 노출 안 함. OpenStack은 이걸 **외재화(externalize)** 해서 여러 서비스가 재사용하게 만든 것이 특이점.

---

## 다음

→ [nova-compute.md](./nova-compute.md): Nova scheduler가 Placement를 어떻게 쓰는지  
→ [../05-deep-dives/](../05-deep-dives/): Placement 내부 구조, Allocation API 심화
