# 01 · Core Services

OpenStack을 구성하는 **필수 컴포넌트 8개**. 각 서비스는 독립 프로세스로 돌고, REST API와 RabbitMQ 메시지 버스로 서로 호출한다. "이 서비스가 없으면 뭐가 안 되는가"를 기준으로 본다.

---

## 전체 그림 — VM 한 대를 띄울 때 누가 일하는가

```
사용자: "Ubuntu VM 1개, 4 vCPU / 8GB RAM / 사설망 A / 디스크 20GB"
    │
    ▼
Horizon (웹 UI) ─────┐
                     ├──► openstack-api (REST)
openstack CLI ───────┘          │
                                 ▼
                         ┌──────────────┐
                         │  Keystone    │ "토큰 유효? 권한 OK?"
                         └──────┬───────┘
                                ▼
                         ┌──────────────┐
                         │  Nova        │ "어느 Compute 노드에 띄울까?"
                         └──┬────┬───┬──┘
                            │    │   │
                            │    │   └─► Placement : 여유 CPU/RAM 있는 호스트 찾기
                            │    └─────► Glance    : Ubuntu 이미지 다운로드
                            │             │
                            │             └─► Swift (선택): 이미지 실제 파일 저장소
                            │
                            └─► Neutron  : 사설망 A에 포트 생성, IP 부여
                            └─► Cinder   : 20GB 볼륨 생성 & VM에 attach
                                           │
                                           └─► (iSCSI/Ceph 등 백엔드)
```

Nova가 "지휘자" 역할을 하고, 나머지는 각자의 자원(인증/네트워크/이미지/디스크)을 공급하는 구조다. **Keystone 토큰이 없으면 아무도 서로 얘기하지 않는다**는 점을 먼저 붙잡고 가자.

---

## Keystone — 문지기 (Identity)

**한 줄 정의**: 사용자/서비스 인증 + 서비스 카탈로그.

- **누가 누구인지** (User, Project, Domain, Role) 저장하는 중앙 DB.
- `openstack token issue` → 토큰 발급. 이후 모든 API 호출은 헤더에 `X-Auth-Token: <토큰>`을 달고 다닌다. 다른 서비스는 그 토큰을 Keystone에 되물어 검증한다.
- **Service Catalog**: "Nova API 엔드포인트는 어디?", "Cinder API는 어디?" 를 알려주는 전화번호부. `openstack catalog list` 하면 모든 서비스의 URL이 쏟아진다.
- **Project = 테넌트 = 리소스 격리 단위**. VM도 볼륨도 네트워크도 전부 프로젝트에 소속된다. AWS의 Account/IAM이 합쳐진 느낌.

핵심 객체: **User / Group / Project / Domain / Role / Token / Endpoint**.

> Keystone이 죽으면 OpenStack 전체가 멈춘다. 토큰 검증이 안 되니까.

---

## Nova — VM 오케스트레이터 (Compute)

**한 줄 정의**: "VM 만들어줘" 요청을 받아서 적당한 Compute 노드에 배치하고 라이프사이클을 관리.

- **nova-api**: REST 요청 수신.
- **nova-scheduler**: 여러 Compute 노드 중 **어디에 띄울지** 결정. 이때 Placement에 "CPU 4, RAM 8G 가능한 호스트?" 질의.
- **nova-conductor**: DB 접근을 중앙화. Compute 노드가 DB에 직접 접근하지 않게 한다 (보안).
- **nova-compute**: 실제 노드에서 **libvirt/KVM**(또는 Xen, VMware)을 호출해 VM을 띄운다. **Nova는 하이퍼바이저가 아니다** — libvirt 같은 걸 **부리는** 쪽이다.

라이프사이클 상태 흐름:
```
BUILD → ACTIVE → (SHUTOFF / PAUSED / SUSPENDED / RESIZED / ERROR) → DELETED
```

핵심 객체: **Server(=Instance) / Flavor(= CPU/RAM 스펙 템플릿) / Keypair / Server Group / Aggregate**.

> AWS 대응: EC2. `flavor`는 `instance type`(m5.large 같은)에 해당.

---

## Neutron — 네트워크 SDN (Networking)

**한 줄 정의**: 가상 네트워크, 서브넷, 라우터, 방화벽, 플로팅 IP를 전부 관장.

- **neutron-server**: REST API.
- **L2 agent** (OVS/OVN/Linux bridge): Compute 노드 안에서 VM 포트를 어떤 VLAN/VXLAN에 붙일지 제어.
- **L3 agent**: 가상 라우터 구현 — 서로 다른 사설망끼리 통신, 외부 인터넷 연결(SNAT), 플로팅 IP(DNAT).
- **DHCP agent**: 사설망에 DHCP 서버를 자동으로 띄워줌.
- **Metadata agent**: VM이 `169.254.169.254`로 자기 정보를 조회할 때 중계.

핵심 객체: **Network / Subnet / Port / Router / Security Group / Floating IP**.

최근 트렌드는 **OVN (Open Virtual Network)** 기반. 기존 L3 agent가 하던 일을 OVN이 분산 처리해서 SPOF와 지연이 줄었다.

> AWS 대응: VPC + Subnet + Route Table + Security Group + Elastic IP. "네트워크의 모든 것"이 Neutron 하나에 몰려 있다.

---

## Glance — VM 이미지 저장소 (Image)

**한 줄 정의**: OS 디스크 이미지(Ubuntu, CentOS, Windows …)를 저장하고 배포.

- **glance-api**: 이미지 업로드/다운로드 REST API. `openstack image create --file ubuntu.qcow2 ...`
- **백엔드 스토어**: 파일을 실제 어디에 둘지 선택 가능 — `file:///`, **Swift**, **Ceph RBD**, S3 호환 스토리지 등. 프로덕션에선 보통 Ceph.
- 이미지 포맷: **qcow2** (가장 흔함), raw, vmdk, iso, ami.
- 이미지 **visibility**: private / shared / community / public.

Nova가 VM을 띄울 때 이미지 ID를 Glance에서 가져와 Compute 노드로 복사한 뒤 부트한다. "한 번 업로드 → 여러 번 부팅"의 템플릿 역할.

핵심 객체: **Image / Member / Metadef(메타데이터 스키마)**.

> AWS 대응: AMI. Glance가 이미지 저장을 Swift에 위임하듯, AWS의 AMI도 내부적으론 S3에 산다.

---

## Cinder — 블록 스토리지 (Block Storage)

**한 줄 정의**: VM에 붙였다 떼는 **영구 디스크**(볼륨)를 제공.

- **cinder-api**: REST.
- **cinder-scheduler**: 여러 스토리지 백엔드 중 어디에 볼륨을 만들지 선택 (용량/성능/타입 기준).
- **cinder-volume**: 드라이버를 통해 실제 스토리지에 LUN을 만들고 export. 드라이버는 100+개 존재 — **LVM(iSCSI)**, **Ceph RBD**, NetApp, EMC, Pure, SolidFire…

VM에 attach하면 Compute 노드에 iSCSI/NVMe-oF로 붙고, VM 안에서는 `/dev/vdb` 같은 추가 디스크로 보인다. VM을 삭제해도 볼륨은 살아남는다 — **Persistent**가 핵심.

핵심 객체: **Volume / Snapshot / Backup / Volume Type / Consistency Group**.

> AWS 대응: EBS. Snapshot → Volume 복원, Volume Type별 성능 티어도 EBS와 개념이 같다.

---

## Swift — 오브젝트 스토리지 (Object Storage)

**한 줄 정의**: HTTP로 파일을 넣고 꺼내는 **대규모 분산 오브젝트 저장소**.

- **proxy-server**: 클라이언트 요청을 받아 적절한 스토리지 노드로 라우팅.
- **account / container / object server**: 3계층 — Account(테넌트) > Container(버킷) > Object(파일).
- **Ring**: 어떤 오브젝트를 어느 디스크에 둘지 결정하는 일관된 해시 테이블. 노드 추가/제거 시 최소 이동으로 리밸런싱.
- **3x 복제** 기본(또는 Erasure Coding). 디스크/노드가 죽어도 자동 복구.
- **Eventually Consistent**: 쓴 직후 잠깐 동안은 다른 노드에서 옛 버전이 보일 수 있다.

Nova/Cinder처럼 블록 디바이스가 아니라 **HTTP GET/PUT/DELETE**로만 접근한다. 백업, 로그, 이미지, 정적 파일 서빙에 적합.

핵심 객체: **Account / Container / Object / Ring**.

> AWS 대응: S3. S3 API 호환 레이어도 있어서 s3cmd/aws-cli로도 쓸 수 있다.

---

## Horizon — 웹 대시보드

**한 줄 정의**: OpenStack 전체를 클릭으로 조작할 수 있는 **Django 기반 웹 UI**.

- 내부적으로는 각 서비스의 REST API를 호출하는 **얇은 프록시**다. Horizon만의 특별한 저장소는 없다.
- 관리자(admin) / 일반 프로젝트 사용자 뷰가 분리된다.
- **Policy**(역할 기반)로 메뉴 노출 제어.
- 플러그인 구조 — Octavia, Magnum, Designate 대시보드를 프로젝트별로 붙이고 뗀다.

> Horizon이 죽어도 CLI(`openstack ...`)와 API는 멀쩡히 작동한다. 운영자의 편의 도구이지 필수 경로가 아니다.

---

## Placement — 자원 가계부

**한 줄 정의**: "어느 호스트에 CPU/RAM/디스크가 얼마나 남았는가"를 추적하는 **인벤토리 DB**.

원래 Nova 안에 있던 기능인데, 여러 서비스가 "자원 어디 남았지?"를 물어봐야 하니 독립 서비스로 분리됐다 (Stein 릴리스부터).

- **Resource Provider**: 자원을 가진 주체 (Compute 호스트, 스토리지 풀, 네트워크 장치…).
- **Inventory**: 각 Provider의 총량 (예: VCPU=64, MEMORY_MB=256000).
- **Allocation**: 누가(= 어떤 consumer = 어떤 VM) 얼마나 썼는지.
- **Trait**: Provider의 속성 (예: `HW_CPU_X86_AVX2`, `STORAGE_DISK_SSD`).

Nova-scheduler가 VM을 배치할 때 제일 먼저 Placement에 "CPU 4, RAM 8G, SSD 속성 있는 호스트?" 쿼리한다. Cyborg(FPGA/GPU), Neutron(대역폭) 등도 Placement에 자원을 등록하는 추세.

> AWS에는 직접 대응 서비스가 없다. EC2 스케줄러가 내부적으로 하는 일을 OpenStack은 **외재화**해서 다른 서비스도 재사용하게 만든 것.

---

## 서비스 간 의존 관계 — 한눈에

```
Keystone  ← 모든 서비스가 토큰 검증 때문에 의존 (가장 아래 깔림)
    ▲
    │
Placement ← Nova-scheduler가 배치 결정에 사용
    ▲
    │
  Nova ──► Glance   (이미지)
    │  ──► Neutron  (네트워크 포트)
    │  ──► Cinder   (볼륨)
    ▼
  libvirt/KVM

Cinder, Glance ──► Swift or Ceph  (실제 파일 백엔드; 선택)
Horizon       ──► 위 모든 서비스 API 호출
```

**학습 순서 권장**: `Keystone → Glance → Neutron → Nova → Cinder → Swift → Horizon → Placement` 순서가 "직관적 → 통합적"으로 이어진다. Keystone만 먼저 잡아도 나머지 학습의 마찰이 반으로 준다.

---

## 개별 문서

각 서비스 심화 문서(작성 예정):

| 서비스 | 역할 | 문서 |
| --- | --- | --- |
| Keystone | Identity / Auth / Service Catalog | [keystone-identity.md](./keystone-identity.md) |
| Nova | Compute (VM 라이프사이클) | [nova-compute.md](./nova-compute.md) |
| Neutron | Networking (L2/L3, SDN) | [neutron-networking.md](./neutron-networking.md) |
| Glance | VM Image 저장/배포 | [glance-image.md](./glance-image.md) |
| Cinder | Block Storage | [cinder-block-storage.md](./cinder-block-storage.md) |
| Swift | Object Storage | [swift-object-storage.md](./swift-object-storage.md) |
| Horizon | Web Dashboard | [horizon-dashboard.md](./horizon-dashboard.md) |
| Placement | 리소스 인벤토리/할당 추적 | [placement.md](./placement.md) |

## 다음 단계

코어 서비스가 머리에 들어오면 → [02-advanced-services/](../02-advanced-services/) 로. Heat(오케스트레이션), Octavia(LB), Magnum(K8s), Designate(DNS), Barbican(Secrets) 등 "있으면 편한" 서비스들을 다룬다. 직접 손으로 익히려면 [03-installation/devstack/](../03-installation/devstack/)에서 단일 노드를 띄우고 위 서비스들이 실제로 어떻게 협력하는지 로그를 따라가 보는 게 가장 빠르다.
