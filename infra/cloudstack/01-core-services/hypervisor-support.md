# Hypervisor Support — KVM이 1급, 나머지는 옵션

> **CloudStack은 하이퍼바이저를 만들지 않는다. KVM/XenServer/VMware/Hyper-V/LXC를 부린다.**

OpenStack과 같은 패턴이지만, **KVM은 cloudstack-agent라는 작은 Java 데몬을 Host에 깐다**는 차이가 있다.

> 출처: [Hypervisor Installation](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/) · [Concepts: Cluster](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#about-clusters).

---

## 지원 하이퍼바이저 ([공식 매트릭스](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/))

| 하이퍼바이저 | 지원 방식 | Agent 필요? | 권장도 |
|---|---|---|---|
| **KVM** (CentOS/Rocky/Ubuntu) | cloudstack-agent + libvirt | ✅ | ⭐⭐⭐ (기본 추천) |
| **XenServer / XCP-ng** | XenAPI 직접 호출 | ❌ (XenServer 자체에 Plugin 설치) | ⭐⭐ |
| **VMware vSphere** | vCenter API | ❌ (vCenter가 Agent 역할) | ⭐⭐ (라이선스 비용) |
| **Hyper-V** | WMI / WinRM | ✅ (Hyper-V 호스트에 별도 Agent) | ⭐ |
| **LXC** (실험적) | libvirt-lxc | ✅ (cloudstack-agent) | ⭐ |
| **Oracle VM** | Oracle VM Manager API | ❌ | ⭐ |

→ 운영 단순함과 ARM 호환을 함께 보면 **KVM이 사실상의 기본 선택**. 본 정리도 이후 KVM 기준.

---

## "Cluster = 같은 하이퍼바이저"

CloudStack은 한 Cluster 안에서는 **하이퍼바이저 종류와 Primary Storage가 통일**되어야 한다.

```
[Pod-1]
  ├─ Cluster-A:  KVM      Primary: Ceph-A
  │   ├─ Host-1
  │   ├─ Host-2
  │   └─ Host-3
  ├─ Cluster-B:  VMware   Primary: vSAN-B
  │   └─ Host-4
  └─ Cluster-C:  KVM      Primary: NFS-C
      └─ Host-5
```

이 제약 덕분에:
- Cluster 안 라이브 마이그레이션이 자유롭다 (스토리지 공유, 동일 하이퍼바이저)
- Allocator 로직이 단순해진다 (혼합 하이퍼바이저 매칭 X)

---

## KVM Host 구조

```
[Hypervisor Host (Linux: CentOS/Rocky/Ubuntu)]
   ├─ libvirtd               ← KVM 표준 관리 데몬
   ├─ qemu-kvm               ← 실제 VM 프로세스
   ├─ cloudstack-agent       ← MS의 손발 (Java)
   │     ├─ port 16509 → libvirt 호출
   │     └─ MS:8250 ↔ TLS RPC
   ├─ OVS or Linux bridge    ← 게스트 트래픽
   └─ iSCSI/NFS/Ceph client  ← Primary Storage 마운트
```

### cloudstack-agent의 역할

```
MS → Agent (TLS RPC 8250):
   "이 VM 시작해", "ISO 붙여", "스냅샷 만들어"
       ↓
Agent → libvirt API:
   virsh equivalent 호출
       ↓
libvirt → qemu-kvm:
   실제 VM 생성/제어
```

→ Agent는 본질적으로 **libvirt 어댑터** + **CloudStack 프로토콜 변환기**.

### 설정 파일 위치

| 경로 | 용도 |
|---|---|
| `/etc/cloudstack/agent/agent.properties` | MS 주소, 인증서 정보 |
| `/var/log/cloudstack/agent/agent.log` | Agent 로그 |
| `/etc/libvirt/qemu.conf`, `/etc/libvirt/libvirtd.conf` | libvirt TLS 설정 |
| `/etc/libvirt/qemu/*.xml` | 실제 VM의 libvirt domain XML |

### Agent 설치 한 줄

```bash
# Ubuntu Host
apt-get install cloudstack-agent
cloudstack-setup-agent  # 인증서 + MS 주소 자동 설정
```

---

## VMware vSphere 통합 — Agent 없는 경로

```
MS ──HTTPS──► vCenter ──API──► ESXi Host ──► VM
```

- Agent 없음. **vCenter API가 Agent 역할**.
- ESXi에 추가 패키지 설치 불필요.
- 단점: vCenter 라이선스 + Broadcom 인수 후 비용 상승.

---

## XenServer / XCP-ng

```
MS ──HTTPS──► XenServer Host의 XenAPI ──► dom0 ──► VMs (domU)
```

- XenServer 호스트의 dom0에 **CloudStack supplemental pack** 설치.
- KVM이 우세해진 후 신규 도입은 줄어드는 추세.

---

## 라이브 마이그레이션 — 누가 해주나

```
같은 Cluster 안 두 호스트:
   - 동일 하이퍼바이저 ✅
   - Primary Storage 공유 ✅ (같은 NFS/Ceph/iSCSI)
   ▼
KVM: virsh migrate (qemu-kvm 의 native live migration)
XenServer: XenMotion
VMware: vMotion
```

CloudStack의 역할은 **"마이그레이션 시작 신호 + 결과 추적"**, 실제 메모리 페이지 복사는 하이퍼바이저가 한다.

---

## 손으로 해보기

```bash
# MS에서 등록된 Host 확인
$ cmk list hosts

# Cluster 추가 (보통 UI로 함)
$ cmk add cluster zoneid=<...> podid=<...> \
      hypervisor=KVM \
      clustertype=CloudManaged \
      clustername=cluster-a

# Host 추가
$ cmk add host zoneid=<...> podid=<...> clusterid=<...> \
      hypervisor=KVM \
      url=http://192.168.1.20 \
      username=root password=<...>

# Maintenance 모드 (마이그레이션 후 빈집됨)
$ cmk prepare hostformaintenance id=<host-id>
$ cmk cancel hostmaintenance id=<host-id>
```

---

## 자주 밟는 지뢰

- **Agent ↔ MS TLS 인증서 mismatch** → MS의 keystore에 Agent 인증서 등록 누락. `cloudstack-setup-agent` 재실행.
- **libvirt가 8250 못 쓰겠다** → 16509(libvirt TLS) 와 8250(MS-Agent) 혼동. 둘은 별개.
- **CPU model mismatch로 마이그레이션 실패** → libvirt CPU 모델을 `host-passthrough` 대신 `Nehalem` 같은 공통 모델로 통일.
- **KVM with VHostNet** → 게스트 네트워크 성능을 위해 vhost-net 활성 필요. `/etc/libvirt/qemu.conf` 에서 `vhost_net = "on"`.

---

## ARM (Apple Silicon) 메모

> [ARM 지원 PR/이슈](https://github.com/apache/cloudstack/issues?q=ARM)

- CloudStack 4.18+ 부터 ARM64 KVM Host 지원 시도가 있었고, 4.19/4.20 부근에서 안정화 진행 중.
- Apple Silicon Mac 위 Multipass/UTM 의 Ubuntu ARM VM에서 학습 목적 단일 노드 설치 가능.
- 단, **System VM template** 이 ARM 빌드인지 확인 필수. 없으면 SSVM/CPVM/VR 부팅 실패.
- 자세한 설치 가이드: [../03-installation/multipass-allinone/setup-guide.md](../03-installation/multipass-allinone/setup-guide.md)

---

## OpenStack 매핑

| | OpenStack | CloudStack |
|---|---|---|
| Compute Host에 도는 데몬 | nova-compute | cloudstack-agent (KVM) |
| 하이퍼바이저 호출 | libvirt | libvirt |
| 스케줄러 위치 | nova-scheduler (별도) | MS 안의 Allocator |
| 다중 하이퍼바이저 | 보통 KVM 한 가지 | 1급 시민 (KVM/Xen/VMware/Hyper-V) |

---

## 다음

→ [storage-primary-secondary.md](./storage-primary-secondary.md): Host가 마운트하는 두 종류 스토리지.
→ [networking.md](./networking.md): Host에 들어가는 패킷이 어떻게 분류되는지.

---

## 공식 문서 레퍼런스

- [Hypervisor Installation Overview](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/)
- [KVM Hypervisor Host Installation](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/kvm.html)
- [VMware vSphere Installation](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/vsphere.html)
- [XenServer/XCP-ng Installation](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/xenserver.html)
