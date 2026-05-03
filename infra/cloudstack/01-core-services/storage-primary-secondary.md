# Storage — Primary vs Secondary, 그리고 SSVM

> **CloudStack 스토리지의 핵심 분리: 라이브 VM 디스크는 Primary, 템플릿/ISO/스냅샷은 Secondary.**

OpenStack의 "Glance(이미지) + Cinder(블록) + Swift(오브젝트)" 가 CloudStack에서는 **두 개의 스토리지 타입 + System VM 1개** 로 줄어든다.

> 출처: [Admin Guide — Storage](https://docs.cloudstack.apache.org/en/latest/adminguide/storage.html) · [Concepts: Storage](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#about-primary-storage).

---

## 1. 한 컷 비교

| | Primary | Secondary |
|---|---|---|
| 스코프 | **Cluster** (또는 Zone-wide) | **Zone** |
| 담는 것 | 라이브 VM 디스크 (root + data) | Template, ISO, Volume Snapshot |
| 프로토콜 | NFS, iSCSI, FC, **Ceph RBD**, SMB, SharedMountPoint | NFS, SMB, **S3 호환** |
| 누가 직접 마운트? | Hypervisor Host | Secondary Storage VM (SSVM) |
| 용량 특성 | 빠른 IOPS 위주 | 큰 용량, 일반 IOPS |
| 비유 | 책상 위 = 작업 중 파일 | 창고 = 보관 |

---

## 2. Primary Storage

### 누가 마운트하나

```
[Hypervisor Host (KVM)]
    │ 마운트
    ▼
[Primary Storage]
   ├─ NFS:    /mnt/<UUID>/...           (Host가 직접 mount)
   ├─ iSCSI:  /dev/disk/by-path/...     (Host가 iscsiadm)
   ├─ Ceph RBD: /dev/rbd/pool/img       (Host의 ceph client)
   └─ SharedMountPoint: 운영자가 미리 마운트한 경로
```

→ Host가 **직접** 본다. Secondary와의 결정적 차이.

### 한 Cluster = 한 Primary 그룹

```
[Cluster-A (KVM)]
   └─ Primary-A: ceph-pool-clusterA   ← Cluster-A의 모든 호스트가 마운트

[Cluster-B (KVM)]
   └─ Primary-B: nfs-clusterB
```

같은 Cluster 안에서만 Primary가 공유 → Cluster 안 라이브 마이그레이션이 자유.

### Zone-wide Primary

KVM + Ceph 조합에서는 Zone 전체에서 한 RBD pool을 공유하는 "Zone-wide Primary"도 가능. Cluster 간 이동도 가능해진다.

### Disk Offering 과의 관계

```
Disk Offering (메뉴):
  - Name: "ssd-100gb"
  - Disk size: 100 GB
  - IOPS limit: 1000
  - Storage tag: "ssd"

VM 생성 시 Disk Offering 고름
       ▼
StoragePoolAllocator: storage tag="ssd" 인 Primary 중 선택
       ▼
선택된 Primary에서 Volume 생성
```

→ "**Storage Tag**" 가 Cinder Volume Type 같은 역할.

---

## 3. Secondary Storage

### 무엇을 담나

| 항목 | 설명 |
|---|---|
| **Template** | OS 이미지. CD-ROM이 아니라 디스크 이미지 (.qcow2, .vhd, .ova) |
| **ISO** | 부팅용 CD-ROM 이미지 |
| **Volume Snapshot** | Primary의 Volume을 떠놓은 백업 |
| **System VM Templates** | SSVM/CPVM/VR 자체의 OS |

→ Secondary가 비면 **새 VM 생성 불가, 콘솔 안 됨, VR 못 띄움**. 그래서 Zone 생성 시 가장 먼저 등록한다.

### 누가 마운트? — SSVM이 매개

```
[Hypervisor Host]   ← Secondary 직접 안 봄
       │
       │ 1. "이 템플릿 줘"
       ▼
[Secondary Storage VM (SSVM)]   ← System VM
       │
       │ 2. NFS/S3 마운트
       ▼
[Secondary Storage (NFS/S3)]
       │
       │ 3. 템플릿 파일 → SSVM이 받아서 → Primary로 복사
       ▼
[Primary Storage]
       │
[Hypervisor Host가 Primary에서 사용]
```

**왜 SSVM이 매개?**
- 보안: Hypervisor Host가 Secondary에 직접 쓰면 권한 분리 어려움
- 추상화: NFS든 S3든 Host는 Primary만 알면 됨
- 처리량 격리: 큰 템플릿 다운로드가 Host 디스크 I/O를 막지 않음

---

## 4. 템플릿 흐름 (VM 생성 시)

```
[VM 생성 명령]
    │
    ▼
DB: vm_instance, volumes 레코드
    │
    ▼
TemplateManager: 이 템플릿이 선택된 Primary에 캐시되어 있나?
    │
    ├─ Yes: 캐시된 템플릿에서 클론 (qcow2 backing or RBD clone)
    │
    └─ No:
         ├─ SSVM에 "Secondary→Primary 복사 요청"
         ├─ SSVM이 Secondary에서 다운로드
         ├─ SSVM이 Primary에 업로드
         └─ template_spool_ref 테이블에 캐시 기록
    │
    ▼
[Host Agent가 클론된 disk image로 VM 부팅]
```

→ **첫 VM은 느림(템플릿 복사), 두 번째부터는 빠름(클론)**.

---

## 5. 스냅샷 흐름

> [Snapshots](https://docs.cloudstack.apache.org/en/latest/adminguide/storage.html#working-with-snapshots).

```
[Volume Snapshot 명령]
    │
    ▼
Host Agent → libvirt blockcopy / qemu-img / RBD snap create
    │
    ▼
임시 결과물 → SSVM 매개 → Secondary Storage 영구 보관
    │
    ▼
Snapshot은 Secondary에 들어가 있음
```

→ **스냅샷은 결국 Secondary로 간다**. Primary가 꽉 차도 스냅샷은 Secondary에 모인다.

자주 헷갈리는 점: **스냅샷에서 Volume 복원은 SSVM이 또 매개** (Secondary→Primary 복원).

---

## 6. 백엔드 옵션 매트릭스

### Primary Storage

| 백엔드 | KVM | XenServer | VMware | 메모 |
|---|---|---|---|---|
| NFS | ✅ | ✅ | ✅ | 가장 단순. 학습/소규모 |
| iSCSI | ✅ | ✅ | ✅ (VMFS) | 중규모 |
| FC | ✅ | ✅ | ✅ | 대규모 / 엔터프라이즈 |
| **Ceph RBD** | ✅ (권장) | ❌ | ❌ | 대규모 KVM 운영의 표준 |
| SharedMountPoint | ✅ | - | - | NFS/GFS2 등을 운영자가 직접 마운트 |
| SMB/CIFS | (제한) | - | ✅ | Hyper-V/VMware |

### Secondary Storage

| 백엔드 | 메모 |
|---|---|
| NFS | 가장 흔함. SSVM이 마운트 |
| **S3 호환** (MinIO, AWS S3, Wasabi …) | 클라우드/대규모. Object Store backed |
| SMB | Windows 환경 |

---

## 7. 손으로 해보기

```bash
# Primary Storage 추가 (NFS)
$ cmk create storagepool \
    zoneid=<...> podid=<...> clusterid=<...> \
    name=primary-nfs \
    url=nfs://192.168.1.100/exports/primary

# Secondary Storage 추가
$ cmk add imagestore \
    zoneid=<...> \
    name=secondary-nfs \
    provider=NFS \
    url=nfs://192.168.1.100/exports/secondary

# 템플릿 등록 (URL에서 다운로드)
$ cmk register template \
    zoneid=<...> \
    hypervisor=KVM \
    format=QCOW2 \
    name=ubuntu-22.04 \
    displaytext="Ubuntu 22.04" \
    url="https://cloud-images.ubuntu.com/jammy/.../jammy-server-cloudimg-arm64.img" \
    ostypeid=<...>

# 템플릿 다운로드 진행 확인
$ cmk list templates id=<id> templatefilter=self
# status: "Downloaded" 면 OK

# 볼륨 만들기
$ cmk create volume \
    name=data-disk \
    diskofferingid=<...> \
    zoneid=<...>

# 볼륨 attach
$ cmk attach volume id=<vol-id> virtualmachineid=<vm-id>
```

---

## 8. 자주 밟는 지뢰

- **템플릿이 영원히 "Downloading"** → SSVM 죽음. `cmk list systemvms` → SSVM stop 후 다시 start.
- **Secondary Storage 등록 후 SSVM 안 뜸** → SSVM template이 등록 안 됨. ARM은 ARM64 SSVM template 별도.
- **Primary 마운트 실패** → 호스트에서 `mount -t nfs ...` 직접 시도해서 NFS export 권한/네트워크 진단.
- **스냅샷 영원히 진행 중** → Secondary 디스크 가득 참. `df -h` (SSVM에서) 확인.
- **Capacity Threshold 초과** → 글로벌 설정 `pool.storage.capacity.notificationthreshold` 와 `pool.storage.allocated.capacity.disablethreshold` 조정.

---

## 9. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Glance | Secondary Storage + SSVM |
| Cinder API | StoragePoolAllocator + VolumeManager (MS) |
| Cinder backend (LVM/Ceph) | Primary Storage (Ceph/iSCSI/NFS) |
| Cinder Volume Type | Disk Offering + Storage Tag |
| Snapshot (Cinder) | Volume Snapshot (Secondary에 보관) |
| Swift | (없음. Secondary가 S3 호환이면 일부 대체) |
| nova ephemeral | (없음. CloudStack은 root volume도 Primary에 영속) |

흥미로운 차이:
- OpenStack은 root disk가 hypervisor 로컬 ephemeral 일 수 있음.
- **CloudStack은 root volume도 항상 Primary에 영속**. → 라이브 마이그레이션이 더 자연스럽다.

---

## 다음

→ [api-and-cloudmonkey.md](./api-and-cloudmonkey.md): 위 모든 명령어를 어떻게 호출하나.
→ [accounts-domains-projects.md](./accounts-domains-projects.md): 누가 어떤 스토리지를 쓸 수 있는지.
→ [../02-advanced-services/system-vms.md](../02-advanced-services/system-vms.md): SSVM의 자세한 동작.

---

## 공식 문서 레퍼런스

- [Admin Guide — Storage](https://docs.cloudstack.apache.org/en/latest/adminguide/storage.html)
- [Concepts: About Primary Storage](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#about-primary-storage)
- [Concepts: About Secondary Storage](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#about-secondary-storage)
- [Working with Templates](https://docs.cloudstack.apache.org/en/latest/adminguide/templates.html)
- [Working with Snapshots](https://docs.cloudstack.apache.org/en/latest/adminguide/storage.html#working-with-snapshots)
