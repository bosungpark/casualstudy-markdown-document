# Cinder — 붙였다 떼는 디스크

> **VM에 attach해서 쓰는 영구 디스크(볼륨)를 제공.**

AWS의 EBS. VM은 지워도 볼륨은 살아남는다 — **Persistent**가 핵심.

---

## 한 줄 요약

VM에 "외장하드 하나 더 꽂아줘" 하면 Cinder가 만들어서 붙여준다. 실제로는 iSCSI나 Ceph RBD를 통해 **원격 디스크**가 VM 안에서 `/dev/vdb`로 보이는 것.

```
  사용자: "20GB 볼륨 하나"
     ▼
  cinder-volume → 백엔드(LVM/Ceph)에 LUN 생성
     ▼
  attach → Compute 노드에 iSCSI로 연결
     ▼
  VM 안에서: $ lsblk → /dev/vdb 20G
```

---

## 내부 구성

```
[cinder-api]        REST API
     │
     ▼
[cinder-scheduler]  어느 백엔드에 만들지 선택 (용량/성능/타입 기준)
     │
     ▼
[cinder-volume]     드라이버 통해 실제 LUN 생성
     │
     ▼
[백엔드 드라이버]
   ├─ LVM (iSCSI)      — 개발용, 기본
   ├─ Ceph RBD         — 프로덕션 주류
   ├─ NetApp / Pure / EMC / SolidFire — 엔터프라이즈
   └─ NFS              — 단순하지만 느림
```

드라이버 100개 넘게 있음. **벤더가 바뀌어도 API는 동일**한 게 Cinder의 가치.

---

## 볼륨이 VM에 붙는 과정

```
[1] 사용자: openstack volume create --size 20 myvol
[2] cinder-scheduler: "어느 백엔드가 여유 있지?" → Ceph-pool-1 선택
[3] cinder-volume: Ceph에 RBD 이미지 생성 (rbd create pool1/vol-uuid --size 20G)
[4] 사용자: openstack server add volume my-vm myvol
[5] nova-compute → cinder: "이 볼륨 연결 정보 줘"
[6] cinder → nova: "rbd://pool1/vol-uuid, auth key=..."
[7] nova-compute → libvirt: VM에 디스크 추가
[8] VM 안에서 /dev/vdb 로 보임
```

---

## 핵심 객체

| 객체 | 설명 |
|---|---|
| **Volume** | 볼륨 본체 |
| **Snapshot** | 볼륨의 특정 시점 스냅샷 (같은 백엔드 내) |
| **Backup** | 볼륨을 다른 스토리지(Swift/NFS)에 백업 |
| **Volume Type** | "SSD-fast", "HDD-slow" 같은 티어 분류 |
| **Consistency Group** | 여러 볼륨을 동시에 스냅샷 (DB처럼 일관성 필요할 때) |

---

## Volume Type — 티어 분리

```
Volume Type: "ssd-gold"
 ├─ backend: ceph-ssd-pool
 └─ extra_specs: iops=10000

Volume Type: "hdd-cold"
 ├─ backend: ceph-hdd-pool
 └─ extra_specs: iops=100
```

사용자가 `--type ssd-gold`로 요청하면 scheduler가 해당 백엔드로 라우팅. AWS EBS의 gp3/io2/st1 같은 성능 티어.

---

## Snapshot vs Backup — 헷갈리는 둘

| 구분 | Snapshot | Backup |
|---|---|---|
| 저장 위치 | **같은** 스토리지 백엔드 | **다른** 스토리지 (Swift, NFS) |
| 속도 | 빠름 (Copy-on-Write) | 느림 (전체 복사) |
| 용도 | 빠른 롤백 | 재해 복구 (백엔드 자체가 죽어도 살아남음) |
| 볼륨 의존 | 원본 삭제 불가 | 독립적 |

---

## 손으로 해보기

```bash
# 볼륨 생성
$ openstack volume create --size 20 --type ssd-gold myvol

# VM에 붙이기
$ openstack server add volume my-vm myvol

# 목록
$ openstack volume list

# 스냅샷
$ openstack volume snapshot create --volume myvol snap1

# 스냅샷에서 복원
$ openstack volume create --snapshot snap1 --size 20 restored-vol

# 떼기
$ openstack server remove volume my-vm myvol

# 삭제
$ openstack volume delete myvol
```

---

## Boot from Volume

기본은 VM의 OS 디스크가 Compute 노드 로컬(ephemeral — VM 삭제시 날아감)인데, **Cinder 볼륨에서 부팅**할 수도 있다.

```
장점: VM 죽어도 OS 디스크 살아남음 → 새 VM에 다시 attach 가능
     Live migration 쉬움 (공유 스토리지라서)
단점: 느림 (네트워크 경유)
```

프로덕션은 대부분 Boot from Volume 쓴다.

---

## 자주 밟는 지뢰

- **"Volume is in use" 라 delete 안 됨** → VM에서 detach 먼저
- **attach 실패** → iSCSI 연결 문제거나, multipathd 설정 확인
- **속도 느림** → 네트워크 대역폭 / Ceph placement group 수 / 멀티패스 확인
- **snapshot 삭제가 원본 볼륨까지 영향** → 일부 드라이버는 chained snapshot을 씀. 주의

---

## AWS 매핑

| AWS EBS | Cinder |
|---|---|
| Volume | Volume |
| Snapshot | Snapshot |
| Volume Type (gp3/io2) | Volume Type (백엔드+extra_specs) |
| Backup to S3 | Backup to Swift |
| Multi-Attach (io1/io2) | Multi-Attach (일부 드라이버 지원) |

---

## 다음

→ [nova-compute.md](./nova-compute.md): VM 만들 때 볼륨이 어떻게 연결되는지  
→ [swift-object-storage.md](./swift-object-storage.md): Cinder Backup의 기본 저장소
