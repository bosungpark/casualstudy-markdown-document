# Ironic — 베어메탈을 셀프서비스로

> **VM이 아니라 "진짜 물리 서버"를 셀프서비스로 빌려주는 서비스.**

"OpenStack인데 가상화 안 한다"는 특이한 포지션. AWS의 `i3.metal` / `m5.metal` 같은 bare-metal 인스턴스가 이 방식.

---

## 왜 필요한가

가상화가 **성능/라이선스/호환성 문제**로 곤란한 경우:

- 데이터베이스: 하이퍼바이저 오버헤드 싫음
- GPU 머신러닝: PCI Passthrough 쓰는 것보다 베어메탈이 속편함
- 레거시 앱: 특정 커널/드라이버 요구
- K8s 워커: 중첩 가상화(VM 안에 컨테이너) 피하고 싶음
- 라이선스: Oracle DB 같이 소켓 단위 과금

이럴 때 **물리 서버를 그대로** 사용자에게 넘기면서, OpenStack API로 관리할 수 있게 해준다.

---

## 한 줄 요약

사용자 입장에선 **Nova로 VM 만드는 것과 똑같이** `openstack server create`. 내부적으론 Nova가 "이건 Ironic이 처리해"라고 라우팅 → Ironic이 **PXE 부팅으로 물리 서버에 OS 설치**.

```
openstack server create --flavor baremetal ...
                            ▲
                            │
              flavor에 "baremetal" trait 박혀있음
                            │
                            ▼
              Nova scheduler: "Ironic으로 보낸다"
                            │
                            ▼
              Ironic: 물리서버 한 대 골라 OS 설치 → 전원 ON
```

---

## 물리 서버가 어떻게 제어되나

Ironic은 서버의 **관리 인터페이스**를 조종한다.

```
┌─────────────────────────────────┐
│  물리 서버                      │
│  ┌───────────┐  ┌────────────┐ │
│  │ 메인 CPU  │  │ BMC (IPMI/ │ │ ← 별도 관리 칩
│  │ (OS 실행) │  │  Redfish)  │ │
│  └───────────┘  └─────┬──────┘ │
└─────────────────────────┼──────┘
                          │
                          ▼
                    [Ironic 컨덕터]
                    "전원 켜/꺼, PXE로 부팅 해"
```

- **BMC** (Baseboard Management Controller): 메인보드에 있는 작은 컴퓨터. 서버 꺼져 있어도 살아 있음
- Ironic이 IPMI/Redfish 프로토콜로 BMC 조종 → 전원 on/off, 부팅 순서 변경

---

## 프로비저닝 흐름

```
[1] 사용자: server create (flavor=baremetal)
[2] Nova → Ironic: "서버 하나 내놔"
[3] Ironic: 대기중인 물리 서버 선택
[4] Ironic → BMC: "PXE로 부팅해"
[5] 서버 전원 ON → PXE → "deploy image" 다운로드 → RAM에서 부팅
[6] deploy image가 로컬 디스크에 진짜 OS 이미지 복사
[7] Ironic → BMC: "디스크로 부팅해" + 재부팅
[8] 서버가 설치된 OS로 부팅 → ACTIVE
```

**PXE 부팅 → 디스크 write → 재부팅** 이 핵심 시퀀스.

---

## 핵심 객체

| 객체 | 의미 |
|---|---|
| **Node** | 관리 대상 물리 서버 하나 |
| **Port** | 서버의 NIC. MAC 주소 등록 |
| **Driver** | BMC 제어 프로토콜 (ipmi, redfish, ilo, idrac…) |
| **Deploy Image** | 설치 중 잠깐 RAM에서 돌리는 소형 이미지 (IPA: Ironic Python Agent) |
| **User Image** | 사용자가 쓰고 싶은 실제 OS 이미지 (Ubuntu 등) |

---

## 노드 등록 (운영자 작업)

```bash
$ openstack baremetal node create \
    --driver ipmi \
    --driver-info ipmi_address=10.1.2.3 \
    --driver-info ipmi_username=admin \
    --driver-info ipmi_password=secret \
    --name server-01

$ openstack baremetal port create \
    aa:bb:cc:dd:ee:ff \
    --node <node-uuid>

# 인스펙션 (자동으로 하드웨어 스펙 스캔)
$ openstack baremetal node manage server-01
$ openstack baremetal node provide server-01  # 사용 가능 상태로
```

---

## 사용자는 그냥 Nova

운영자가 노드 등록 끝냈으면, 사용자는 VM 만드는 것과 **완전히 동일**:

```bash
$ openstack server create \
    --flavor baremetal-large \
    --image ubuntu-22.04 \
    --network private-net \
    my-bm-server
```

사용자는 이게 VM인지 베어메탈인지 **몰라도 된다**. Nova가 뒤에서 라우팅할 뿐.

---

## Node State Machine

```
enroll ──► manageable ──► available ──► active ──► deleted
                                          │
                                          ▼
                                       maintenance
```

- **enroll**: 막 등록됨
- **manageable**: Ironic이 제어 가능
- **available**: 임대 가능 대기
- **active**: 사용자에게 할당됨
- **maintenance**: 운영자가 점검중

---

## 자주 밟는 지뢰

- **IPMI 연결 실패** → BMC 네트워크 도달 가능한지, 비번 맞는지. BMC가 죽으면 Ironic이 손 쓸 수 없음
- **PXE 부팅 실패** → TFTP/DHCP 설정, BIOS 부팅 순서, 전용 PXE VLAN 확인
- **디스크에 흔적 남음** → 반납시 **clean step**으로 디스크 지우기 (shred / erase) 필수. 안 하면 다음 사용자에게 데이터 유출
- **IPA 이미지 못 받음** → HTTP/TFTP 서버 접근 경로 점검
- **UEFI vs Legacy BIOS** → 서버 설정과 이미지 일치해야 함

---

## Multi-tenant 네트워킹

베어메탈도 VM처럼 **테넌트별 격리**가 필요하다. Ironic은 **네트워크 스위치**와 연동해 포트를 VLAN에 자동 배치.

```
사용자 A에게 할당 → 스위치 포트를 VLAN 100(사용자 A 전용)으로 설정
사용자 B에게 할당 → VLAN 200으로 재설정
```

Neutron의 **ML2 Baremetal** 메커니즘이 이 부분을 담당.

---

## AWS 매핑

| AWS | Ironic |
|---|---|
| EC2 Bare Metal (i3.metal 등) | Ironic 노드 |
| EC2 API로 제어 | Nova API로 제어 (뒤는 Ironic) |
| Dedicated Host | 비슷한 용도, 다른 구현 |

AWS는 내부 구현을 숨기지만, 결국 **베어메탈을 API로 빌려준다는 발상**은 같다.

---

## Standalone 모드

Nova 없이 **Ironic 단독**으로도 쓸 수 있다. "OpenStack 없이 베어메탈 프로비저닝만 필요" 한 경우.

- Metal3 (K8s 오퍼레이터)가 Ironic을 단독으로 씀
- 베어메탈 K8s 클러스터 자동 구축에 활용

---

## 다음

→ [../01-core-services/nova-compute.md](../01-core-services/nova-compute.md): Nova가 Ironic을 VM처럼 통합하는 방식  
→ [../01-core-services/neutron-networking.md](../01-core-services/neutron-networking.md): 물리 스위치 연동 (ML2 Baremetal)  
→ 심화: Metal3 (K8s + Ironic) 조합 → [../05-deep-dives/](../05-deep-dives/)
