# Scheduler / Allocator Internals — 호스트는 어떻게 결정되나

> **DeploymentPlanner + HostAllocator + StoragePoolAllocator 의 협업.**

OpenStack의 `nova-scheduler + Placement` 가 분리되어 있다면, CloudStack은 **MS 내부의 일련의 모듈** 로 한 트랜잭션 안에서 처리.

> 출처: [Developer's Guide — Allocators](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#allocators) · [소스](https://github.com/apache/cloudstack/tree/main/plugins/host-allocators).

---

## 1. 큰 그림

```
[deployVirtualMachine API 호출]
         │
         ▼
DeploymentPlanner.plan()
         │
         ├─► PlannerHostReservation: 후보 Cluster/Pod 결정
         │
         ├─► HostAllocator.allocateTo(): 그 안의 Host 후보
         │
         ├─► StoragePoolAllocator.allocateToPool(): Primary Storage 후보
         │
         ▼
DeploymentPlan 객체 (호스트 + 스토리지 결정)
         │
         ▼
AsyncJob 으로 enqueue → AgentManager → Host Agent
```

---

## 2. DeploymentPlanner — "어느 묶음?"

### Planner 종류 ([공식](https://docs.cloudstack.apache.org/en/latest/adminguide/management.html#vm-deployment-rules))

| Planner | 정책 |
|---|---|
| `FirstFitPlanner` | 자원 남는 첫 Cluster (기본) |
| `UserDispersingPlanner` | 사용자별 분산 (멀티테넌시 우선) |
| `UserConcentratedPodPlanner` | 사용자 VM을 한 Pod에 몰기 |
| `ImplicitDedicationPlanner` | 사용자 전용 호스트 우선 |
| `BareMetalPlanner` | 베어메탈 전용 |

선택은 글로벌 설정 `vm.allocation.algorithm` 또는 Service Offering 별 설정.

### FirstFitPlanner 의사 코드

```java
DeploymentPlan plan(VirtualMachineProfile vmProfile, DeploymentPlan plan) {
    // 1. Zone 후보 (보통 plan.zoneId 명시)
    List<DataCenter> zones = (plan.zoneId != null)
        ? [plan.zoneId]
        : enabledZones();

    for (Zone zone : zones) {
        // 2. Pod 후보
        List<Pod> pods = listEnabledPods(zone);

        for (Pod pod : pods) {
            // 3. Cluster 후보 (하이퍼바이저 매칭)
            List<Cluster> clusters = listMatchingClusters(pod, vmProfile.hypervisorType);

            for (Cluster cluster : clusters) {
                // 4. 그 Cluster 안에서 HostAllocator 호출
                List<Host> candidateHosts = hostAllocator.allocateTo(vmProfile, cluster);

                // 5. StoragePoolAllocator 호출
                Map<Volume, StoragePool> storage = storageAllocator.allocate(vmProfile, cluster);

                if (!candidateHosts.isEmpty() && storage != null) {
                    return new DeploymentPlan(zone, pod, cluster, candidateHosts.get(0), storage);
                }
            }
        }
    }

    throw new InsufficientCapacityException();
}
```

→ **Cluster 단위로 try → 첫 성공 → 끝**.

---

## 3. HostAllocator — "그 Cluster 안에서 누구?"

### 종류

| Allocator | 정책 |
|---|---|
| `RandomAllocator` | 무작위 |
| `FirstFitRoutingAllocator` | 첫 fit (기본) |
| `RecreateHostAllocator` | 재배포(restart from snapshot)용 |
| `TestingAllocator` | 디버그 |

기본 `FirstFitRouting` 흐름:

```java
List<Host> allocateTo(VirtualMachineProfile vm, Cluster cluster) {
    // 1. Up + Enabled 호스트만
    List<Host> hosts = listAvailableHostsInCluster(cluster);

    List<Host> matching = new ArrayList<>();

    for (Host host : hosts) {
        // 2. CPU/RAM 충분?
        if (!hasCapacity(host, vm)) continue;

        // 3. Service Offering의 hosttags 매칭?
        if (!hostTagsMatch(host, vm.getOffering().getHostTags())) continue;

        // 4. AZ/affinity 그룹 충돌?
        if (!affinityAllowed(host, vm)) continue;

        // 5. CPU model match (live migration 대비)?
        if (!cpuCompatible(host, vm)) continue;

        // 6. Reservation 침범?
        if (reservationViolates(host, vm)) continue;

        matching.add(host);
    }

    // 7. 정렬 (capacity 많이 남은 순 또는 적은 순)
    return sortByPolicy(matching);
}
```

### Capacity 체크 — `op_host_capacity` 테이블

```sql
SELECT capacity_type, used_capacity, total_capacity
FROM op_host_capacity
WHERE host_id = ?;

capacity_type:
   0 = Memory (Bytes)
   1 = CPU (MHz × cores)
   2 = Storage (Bytes, allocated)
   3 = Storage (Bytes, used)
   4 = Public IP
   5 = Private IP
   ...
```

→ "**가용 Capacity = total - used - reserved**". 한 번 reserved 잡히면 다른 잡이 못 씀.

---

## 4. StoragePoolAllocator — "어느 Primary?"

### 종류

| Allocator | 정책 |
|---|---|
| `FirstFitStoragePoolAllocator` | 첫 fit (기본) |
| `LocalStoragePoolAllocator` | Local Storage 전용 |
| `ClusterScopeStoragePoolAllocator` | Cluster scope만 |
| `ZoneWideStoragePoolAllocator` | Zone-wide pools (KVM+Ceph) |

흐름:

```java
Map<Volume, StoragePool> allocate(VM vm, Cluster cluster) {
    Map<Volume, StoragePool> result = new HashMap<>();

    for (Volume vol : vm.getVolumes()) {
        // 1. Disk Offering의 storage tag
        String tag = vol.getDiskOffering().getStorageTag();

        // 2. cluster scope 또는 zone-wide pool 후보
        List<StoragePool> pools = listPoolsForCluster(cluster, tag);

        for (StoragePool p : pools) {
            // 3. 용량 + IOPS 한계 체크
            if (canFitVolume(p, vol)) {
                result.put(vol, p);
                break;
            }
        }

        if (result.get(vol) == null) {
            throw new StorageUnavailableException();
        }
    }

    return result;
}
```

### Storage Capacity 임계

글로벌 설정:
- `pool.storage.allocated.capacity.notificationthreshold` = 0.75 (warn)
- `pool.storage.allocated.capacity.disablethreshold` = 0.85 (deny)

→ 85% 사용 시 새 볼륨 배치 거부 (Pool 자체는 살아있음, 기존 사용 중 VM은 OK).

---

## 5. 멀티 결정 트랜잭션

OpenStack의 분리된 Placement vs CloudStack의 한 곳:

```
OpenStack:
  nova-scheduler:                   "어느 호스트?" (Placement에 질의)
  cinder-scheduler (+ scheduler):   "어느 백엔드?" (또 다른 분리된 결정)
  neutron API:                      "포트 만들기"

CloudStack:
  MS의 한 트랜잭션 안에서:
     - DeploymentPlanner
     - HostAllocator
     - StoragePoolAllocator
     → 한 DB 트랜잭션, 한 잡 결과
```

**장점**: 일관성. "호스트 고른 후 스토리지 없네" 같은 race가 적다.
**단점**: 모든 결정이 한 프로세스에 모이니 부하 분산이 제한적.

---

## 6. Affinity / Anti-Affinity

> [Affinity Groups](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/affinity_groups.html).

```bash
# Anti-affinity 그룹: VM들이 다른 호스트에 배치
$ cmk create affinitygroup type=host \
    name=web-tier-aa \
    description="Web tier anti-affinity"

# VM 배포 시 그룹 지정
$ cmk deploy virtualmachine ... affinitygroupids=<aa-id>
```

Allocator가 위 단계 4에서 체크.

---

## 7. Capacity 깨짐 — heal

OpenStack의 `nova-manage placement heal_allocations` 같은 게 CloudStack에도 있다:

```bash
# capacity 재계산
$ cmk update host id=<host-id>     # 살짝 자극
$ cmk find storagepoolsformigration virtualmachineid=<vm-id>

# DB 직접 (운영 주의)
mysql> UPDATE op_host_capacity SET used_capacity = (
   SELECT SUM(...) FROM ...
) WHERE host_id = ?;
```

**보통은 MS 재시작이 capacity 재계산을 트리거**.

---

## 8. 디버깅 — 왜 이 호스트?

```
$ tail -f /var/log/cloudstack/management/management-server.log \
    | grep -i "FirstFit\|allocate\|capacity"

# 자세한 로그
[INFO ] FirstFitRoutingAllocator: Found candidate hosts: [host-1, host-3]
[DEBUG] FirstFitRouting: host-1 capacity used=4000 total=16000 → fit
[DEBUG] FirstFitRouting: host-2 SKIP (storage tag mismatch)
[INFO ] Selected host: host-1
```

→ Allocator 결정 추적 가능. 운영자는 자주 본다.

---

## 9. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| nova-scheduler (FilterScheduler) | DeploymentPlanner + HostAllocator |
| Placement (resource provider) | `op_host_capacity` 테이블 (DB) |
| Filter (RamFilter, AvailabilityZoneFilter, ...) | HostAllocator의 if 분기 |
| Weigher | sort 단계 |
| cinder-scheduler | StoragePoolAllocator |
| nova-manage placement heal | (간접: MS 재시작) |
| Server Groups (anti-affinity) | Affinity Group |

---

## 10. 한 줄 요약

```
DeploymentPlanner: 어느 묶음 (Cluster) → HostAllocator: 그 안의 누구
                                       → StoragePoolAllocator: 어느 Primary
                                       → 한 트랜잭션, 한 결정
                                       → AsyncJob → Agent 로 전달
```

**모든 결정이 MS의 한 프로세스 안**. 이게 CloudStack의 단순함이자 한계.

---

## 다음

→ [virtual-router-internals.md](./virtual-router-internals.md): 결정된 후 VR 부팅 흐름.
→ [../01-core-services/service-offerings.md](../01-core-services/service-offerings.md): hosttags 같은 메타데이터.

---

## 공식 문서 레퍼런스

- [Developer's Guide — Allocators](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#allocators)
- [Admin Guide — VM Deployment Rules](https://docs.cloudstack.apache.org/en/latest/adminguide/management.html#vm-deployment-rules)
- [Affinity Groups](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/affinity_groups.html)
- [GitHub — apache/cloudstack/plugins/host-allocators](https://github.com/apache/cloudstack/tree/main/plugins/host-allocators)
- [GitHub — apache/cloudstack/plugins/storage-allocators](https://github.com/apache/cloudstack/tree/main/plugins/storage-allocators)
