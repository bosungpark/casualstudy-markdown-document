# OpenStack 아키텍처 — 질문으로 따라가는 큰 그림

> **"이건 왜 이렇게 돼있지?"** 라는 질문을 따라 OpenStack 전체 구조를 그림으로 잡는 문서.

각 컴포넌트의 사용법은 [01-core-services/](../01-core-services/) 에서, 내부 구현은 [05-deep-dives/](../05-deep-dives/) 에서. 여기는 **머릿속에 큰 그림**을 그리는 게 목적.

---

## 1. 왜 VM부터 이야기하나

OpenStack을 이해하려면 **"VM이 왜 필요한가"** 부터 잡아야 합니다.

### VM 없는 시절

```
서버1: Ubuntu + 웹앱A    (CPU 5%만 씀, 95% 놀음)
서버2: CentOS + 웹앱B    (CPU 10%, 90% 놀음)
서버3: ...               
```

문제:
- **자원 낭비**: 한 서버에 OS 하나, 앱 하나
- **격리 불가**: 한 앱 뻗으면 같이 뻗음
- **느림**: 새 서버 = 박스 사고 OS 깔고 → 며칠
- **이동 불가**: 다른 서버로 옮기려면 다시 깔기

### VM이 푸는 것

```
서버1 (물리 1대):
  ├─ VM-1: Ubuntu + 웹앱A
  ├─ VM-2: CentOS + 웹앱B
  ├─ VM-3: Ubuntu + DB
  └─ VM-4: Windows + 레거시
```

자원 효율 ↑, 격리 ↑, 30초 만에 생성, 다른 서버로 카피해 부팅 가능.

### 그럼 OpenStack은?

VM 1~2개는 KVM/libvirt로 충분. **서버 100대 × VM 1000개** 가 되면 수동 운영 불가.

```
누가 어느 서버에 띄울지 결정?      → Nova-scheduler + Placement
누가 IP 할당?                       → Neutron
누가 디스크 붙임?                   → Cinder
누가 사용자별 권한 검증?             → Keystone
누가 자원 추적?                     → Placement
누가 OS 이미지 보관?                → Glance
```

→ **OpenStack = VM 1000개를 운영하는 매니저**. 정확히는 IaaS 프레임워크.

---

## 2. OpenStack의 정체 — 세 가지 동기

### 동기 ① 멀티테넌시

여러 사용자/팀/회사가 **같은 하드웨어를 안전하게 나눠 씀**. Project/Domain으로 격리.

### 동기 ② 데이터 주권

내 데이터를 내 데이터센터에 둠. AWS에 못 올리는 규제 환경 (금융/공공/통신).

### 동기 ③ 셀프서비스

"VM 주세요" → **API 한 줄**. 운영자가 매번 손으로 안 만듦.

### 단위는 VM만이 아님

```
✅ VM (Nova) — 가장 흔함
✅ Bare Metal (Ironic) — DB·HPC·라이선스
✅ Container (Magnum/Zun) — K8s on OpenStack
```

VM은 가장 흔한 컴퓨트 단위지, 유일한 답이 아님.

### 멀티테넌시의 진짜 본체

VM 격리만으로 안 됨. **여러 층**:

| 격리 영역 | 도구 |
|---|---|
| 신원/권한 | Keystone (Project/Domain) |
| CPU/RAM | Nova + KVM |
| 네트워크 | Neutron (VLAN/VXLAN/Geneve) |
| 스토리지 | Cinder + 백엔드별 권한 |

**테넌트 A의 VM이 테넌트 B의 네트워크/디스크 못 만지게** = 진짜 멀티테넌시.

---

## 3. 서비스 지도 — 누가 누구인가

```
         [사용자 / Horizon / CLI]
                  │
   ┌──────┬──────┼──────┬──────┬──────┐
   ▼      ▼      ▼      ▼      ▼      ▼
[Keystone][Nova][Neutron][Glance][Cinder][Placement]   ← 각자 API
   ▲  ▲     ▲     ▲       ▲      ▲      ▲
   │  └─────┴─────┴───────┴──────┴──────┘
   │
   └─ 토큰 검증할 때만 호출됨
```

### 흔한 오해 — Keystone은 게이트웨이가 아님

```
❌ 사용자 → [Keystone 게이트웨이] → Nova   (트래픽 거쳐감)
✅ 사용자 → Nova/Neutron/Cinder ...        (각자 직접 받음)
              │
              └─► Keystone에 "토큰 진짜?" 물어봄
```

비유:
- ❌ **로비 안내데스크** (모두가 거쳐감)
- ✅ **신원조회소** (필요할 때 전화로 확인)

---

## 4. 통신 구조 — REST + MQ

```
[각 서비스 (Nova, Neutron, Keystone …)]
        │
        ├─► [DB]            ← 영속 데이터 (MariaDB / Galera)
        │   "nova DB", "neutron DB", "keystone DB" 각자 따로
        │
        └─► [MQ]            ← 비동기 메시지 (RabbitMQ)
            "nova-api → nova-scheduler → nova-compute"
```

### 두 종류 통신

| 통신 종류 | 도구 | 왜? |
|---|---|---|
| **같은 서비스 내부** | RabbitMQ | 비동기, 워커 분산, 재시도 |
| **서비스 간** | REST API | 느슨한 결합, 표준 인터페이스 |

```
Nova 내부:                      서비스 간:
  nova-api                        nova-compute → Glance API (HTTP)
    ⇣ RabbitMQ                    nova-compute → Neutron API (HTTP)
  nova-scheduler                  nova-compute → Keystone API (HTTP)
    ⇣ RabbitMQ
  nova-compute
```

Nova 식구들끼리는 한 가족 → MQ. Nova ↔ Glance는 남남 → REST.

### DB 분리

각 서비스 **자기 DB만 가짐**. 남의 DB에 직접 SELECT 안 함. → 마이크로서비스 패턴.

---

## 5. VM 한 개 만들 때 — 9단계 흐름

```bash
$ openstack server create --flavor m1.small --image ubuntu --network private my-vm
```

이 한 줄 뒤:

```
[1] Keystone:  토큰 검증
       ▼
[2] Nova-API:  요청 수신
       ▼
[3] Nova-Conductor:  DB에 instance 레코드 (status=BUILD)
       ▼
[4] Nova-Scheduler + Placement:  "어느 호스트?"
       ▼
[5] Nova-Compute on host-3 시작
       ├─► Glance:   OS 이미지 다운로드
       ├─► Neutron:  포트 생성, IP/MAC 할당, SG 적용
       ├─► Cinder:   (있으면) 볼륨 생성 + attach
       └─► libvirt → KVM:  실제 VM 프로세스 띄움
       ▼
[6] cloud-init:  키 주입, hostname, 네트워크 설정
       ▼
[7] ACTIVE
```

**6개 서비스가 협업** = OpenStack은 느슨한 연합체.

---

## 6. 인증/권한 — Keystone이 부하를 어떻게 견디나

### 옛날 방식의 함정

```
매 요청마다:
  Nova → Keystone: "이 토큰 진짜야?"
  Keystone → DB: SELECT * FROM tokens WHERE id=...
  Keystone → Nova: "응"

→ 초당 수천 요청 = DB 폭발
```

### 3가지 기법

#### ① Stateless 토큰 (Fernet)

토큰 자체에 user/project/expires 다 박아넣음. **AES-128-CBC + HMAC-SHA256** 으로 암호화 + 서명.

```
토큰 = AES(payload) + HMAC(payload)
검증 = HMAC 검사 → AES 복호화 → 만료 시간 체크
DB 조회 0회
```

#### ② 토큰 캐시

각 서비스가 검증 결과를 **memcached에 5~10분** 캐시. 같은 토큰은 Keystone에 재질문 안 함.

#### ③ 수평 확장

Fernet이 stateless라 **Keystone 100대 띄워도** 자유롭게 분산. 같은 Fernet 키만 공유하면 됨.

```
[LB]
  ├─► Keystone-1 (Fernet 키 동일)
  ├─► Keystone-2 (Fernet 키 동일)
  └─► Keystone-N (Fernet 키 동일)
```

### 함정

키 로테이션 시 **모든 노드에 새 키 배포** 필요. 안 그러면 노드 A에서 발급한 토큰을 노드 B가 위조로 판정.

---

## 7. 호스트 선택 — Scheduler + Placement

### Scheduler 2단계

```
① Filter: 조건 안 맞는 호스트 탈락
   - RAM/CPU 부족? → ❌
   - AZ 안 맞아? → ❌
   - GPU 요구하는데 GPU 없음? → ❌

② Weigher: 남은 후보들 점수 매겨 정렬
   - RAM 많이 남은 호스트 우선 (분산)
   - 또는 작게 남은 호스트 우선 (몰아넣기)
```

### Placement는 왜 분리됐나

원래 Nova 안에 있었음. 분리 이유:

```
옛날: Nova만 자원 추적
   ↓
요즘: Cyborg(GPU/FPGA), Neutron(대역폭), Cinder(스토리지)도 자원 추적 필요
   ↓
각자 만들면 4중 중복
   ↓
공용 "자원 가계부" 서비스로 분리 (Stein, 2019)
```

### 자원 부족 시 — 안 쫓아낸다

```
시나리오: 새 VM 띄우려는데 자원 부족
   ↓
OpenStack: "No valid host was found" → 거절
   (기존 VM 강제 종료 X)
```

이유: **멀티테넌시 신뢰 약속**. 사용자 A의 자원이 안전하다고 약속했으니 다른 사용자 때문에 못 죽임.

비교:
| 시스템 | 자원 부족 시 |
|---|---|
| OpenStack | 거절 (안 쫓아냄) |
| AWS Spot | 가격 낮은 VM 회수 (사용자 동의함) |
| Kubernetes | Priority 기반 Preemption (Pod 죽임) |

---

## 8. 네트워크 — 어떻게 두 VM이 같은 사설망인 척?

### 시나리오

```
서버1: VM-A (사설IP 10.0.0.5)
서버2: VM-B (사설IP 10.0.0.6)

VM-A → VM-B 로 ping
```

물리적으로는 다른 머신, 가상으로는 같은 사설망.

### 답 — 터널링/캡슐화 (VPN과 같은 원리)

```
원래 패킷 (VM-A):
  [eth][ip: 10.0.0.5→10.0.0.6][ICMP]
        ▼
  서버1 OVS가 봉투에 쌈:
        ▼
  [outer eth: 서버1 NIC → 서버2 NIC]
  [outer ip: 192.168.1.1 → 192.168.1.2]   ← 진짜 물리 IP
  [Geneve 헤더: VNI=42]                    ← 가상망 식별자
  [원래 패킷 그대로]
        ▼
  물리 스위치는 외부 봉투만 보고 라우팅
        ▼
  서버2 도착 → OVS 봉투 벗김 → VM-B에 전달
```

### VPN과의 차이

| 항목 | VPN | Geneve/VXLAN |
|---|---|---|
| 목적 | 보안 (암호화) | 격리 (멀티테넌시) |
| 암호화 | ✅ | ❌ (속도 우선) |
| 식별자 | 없음 | VNI 24bit (1600만 가상망) |

**VNI**가 핵심. 같은 물리 네트워크에 수천 가상망이 흘러도 라벨로 구분.

### 봉투 작업은 누가 시키나

```
[Neutron API]      ← 우체국 본사 (정책 결정)
       │
       ▼
[OVN Northbound DB]  ← 본사 정책 문서 (논리)
       │ ovn-northd 변환
       ▼
[OVN Southbound DB]  ← 각 지점 실행 매뉴얼 (구체적 OpenFlow 룰)
       │ ovn-controller가 pull
       ▼
[ovn-controller]     ← compute 노드마다 1명 (지점 매니저)
       │ OpenFlow 룰 설치
       ▼
[OVS]              ← 실제 우체부 (봉투 작업)
```

**Neutron/OVN = 무엇을 (선언)** , **OVS = 어떻게 (실행)**.

### 옛날 vs 지금

옛날 (ML2 + OVS + L3 agent):
- L3/DHCP/Metadata 에이전트가 네트워크 노드 한 곳에 몰림 → 병목

요즘 (OVN):
- 각 compute 노드에 ovn-controller
- 라우팅·DHCP·ARP 모두 분산 처리

---

## 9. 운영 관점 — VM이 BUILD에서 안 넘어갈 때

위 9단계 중 **어디든 막힐 수 있음**. Nova가 BUILD 상태를 관리하지만 진짜 원인은 협력 서비스일 가능성 큼.

### 진단 1단계: task_state

```bash
$ openstack server show my-vm
```

| task_state | 의심 영역 |
|---|---|
| `scheduling` | Scheduler/Placement (단계 4) |
| `block_device_mapping` | Cinder (단계 5) |
| `networking` | Neutron (단계 5) ⭐⭐⭐ 제일 흔함 |
| `spawning` | libvirt/KVM (단계 5) |
| ERROR + fault 메시지 | 어딘가 터짐 |

### 진단 2단계: 로그

```bash
# Nova 쪽
tail -f /opt/stack/logs/n-{api,cpu,sch}.log

# 협력 서비스
tail -f /opt/stack/logs/q-svc.log          # Neutron
tail -f /opt/stack/logs/g-api.log          # Glance
tail -f /opt/stack/logs/placement-api.log

# VM UUID 검색
grep -i "ERROR\|<my-vm-uuid>" *.log
```

### 흔한 케이스

| 증상 | 원인 | 대처 |
|---|---|---|
| "No valid host was found" | Placement 자원 부족 / allocation 누수 | `nova-manage placement heal_allocations` |
| "Image failed to download" | Glance 백엔드 (Ceph/Swift) 문제 | 백엔드 디스크/권한 |
| "Port creation failed" | Neutron IP 풀 고갈 / OVN 죽음 | subnet allocation_pool 확인 |
| spawning에서 멈춤 | libvirt/qemu 문제 | `journalctl -u libvirtd` |

### 핵심 교훈

> **OpenStack 디버깅 = "협력 서비스 중 누가 거짓말/침묵 했는지 추적".**  
> 로그를 따라가는 능력 = 운영자의 핵심 스킬.

---

## 10. 한 줄 요약

> **OpenStack = 내 데이터센터에 클라우드를 직접 구축하는 IaaS 프레임워크.**  
> **데이터 주권/규제/멀티테넌시가 핵심 동기.**  
> **여러 독립 서비스가 각자 자기 DB와 API를 갖고, 서비스 끼리는 REST로, 서비스 내부 컴포넌트끼리는 RabbitMQ로 통신.**  
> **Keystone은 게이트웨이가 아니라 모두가 신뢰하는 신원조회소.**

---

## 다음

- 각 서비스 사용법: [../01-core-services/](../01-core-services/)
- 부가 서비스 (Heat/Magnum/Octavia/Ironic): [../02-advanced-services/](../02-advanced-services/)
- 직접 깔아보기: [../03-installation/devstack/](../03-installation/devstack/)
- 운영 디테일: [../04-operations/](../04-operations/)
- 내부 구현: [../05-deep-dives/](../05-deep-dives/)
