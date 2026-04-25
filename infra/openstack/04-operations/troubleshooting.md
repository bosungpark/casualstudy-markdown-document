# Troubleshooting — OpenStack/DevStack 디버깅

> **"VM이 ACTIVE인데 ping이 안 된다", "stack.sh가 또 죽었다"** 같은 흔한 장애를 어떤 순서로 따라가는지.

OpenStack은 서비스가 많아서 **로그를 어디서 봐야 하는지 아는 게 디버깅의 80%**.

---

## 한 줄 요약

```
증상 확인 → 어느 서비스의 일인가? → 그 서비스 로그 → 의존 서비스 추적
   (Horizon)        (Nova? Neutron?)      (n-cpu.log)    (Placement, Glance...)
```

OpenStack 요청은 **여러 서비스가 릴레이**하므로, 한 서비스 로그만 봐서는 답이 안 나옴. 흐름을 따라가야 함.

---

## 디버깅의 첫 3가지

### 1. 어디서 끊겼는지 좁히기

| 증상 | 1차 의심 |
|---|---|
| `openstack` CLI 토큰 에러 | Keystone, `openrc` 환경변수 |
| VM이 BUILD에서 안 넘어감 | Nova(`n-cpu`), Placement(자원 부족) |
| VM이 ACTIVE인데 ping 안 됨 | Neutron(`q-svc`, `q-agt`), Security Group |
| 볼륨 attach 실패 | Cinder(`c-vol`), iSCSI/LVM |
| 이미지 업로드 안 됨 | Glance(`g-api`), 디스크 공간 |
| Horizon 빈 화면/500 | Apache, Keystone 카탈로그 |

### 2. 로그 위치

**DevStack** — `/opt/stack/logs/` 에 모든 서비스 로그가 한곳에 모인다.

```
/opt/stack/logs/
├── stack.sh.log     ← 설치 로그 (./stack.sh 실패 시 첫 번째)
├── n-api.log        ← nova-api
├── n-cpu.log        ← nova-compute (VM 띄우는 곳)
├── n-cond.log       ← nova-conductor
├── n-sch.log        ← nova-scheduler
├── q-svc.log        ← neutron-server
├── q-agt.log        ← neutron L2 agent (OVN/OVS)
├── g-api.log        ← glance-api
├── c-api.log        ← cinder-api
├── c-vol.log        ← cinder-volume
├── keystone.log
└── placement-api.log
```

**Kolla-Ansible** — `/var/log/kolla/<서비스>/` 컨테이너별 분리. 또는 `docker logs <container>`.

**패키지 설치 (apt/dnf)** — `/var/log/<서비스>/` (예: `/var/log/nova/nova-compute.log`).

### 3. 실시간 추적

```bash
# DevStack: systemd 유닛으로 따라가기
$ sudo journalctl -u devstack@n-cpu -f
$ sudo journalctl -u devstack@q-svc -f --since "5 min ago"

# 여러 로그 동시에
$ sudo tail -f /opt/stack/logs/{n-cpu,q-agt,c-vol}.log

# ERROR/TRACE만 골라보기
$ grep -E 'ERROR|TRACE' /opt/stack/logs/n-cpu.log | tail -50
```

---

## 시나리오 1 · `./stack.sh` 가 중간에 죽음

가장 흔한 DevStack 장애. **로그 끝부분 50줄**부터 본다.

```bash
$ tail -100 /opt/stack/logs/stack.sh.log
```

| 패턴 | 원인 | 처방 |
|---|---|---|
| `Could not resolve host: opendev.org` | 네트워크/DNS | `/etc/resolv.conf` 확인, 미러 사용 |
| `pip install ... failed` | PyPI 일시 장애 | 잠시 후 재시도 |
| `Unable to determine HOST_IP` | 인터페이스 자동감지 실패 | `local.conf`에 `HOST_IP=`, `HOST_IP_IFACE=` 명시 |
| `Service n-cpu is not running` | nova-compute 기동 실패 (KVM/메모리) | 중첩 가상화, 메모리 8GB+ 확인 |
| `MySQL connection refused` | MariaDB 기동 실패 | `sudo systemctl status mariadb` |

복구 패턴:

```bash
$ ./unstack.sh   # 띄운 거 내리고
$ ./clean.sh     # 상태 초기화
$ ./stack.sh     # 다시 (수정된 local.conf로)
```

> ⚠️ `./stack.sh` 를 같은 머신에서 **수정 없이 재실행**해도 보통 깨끗하게 안 풀린다. `clean.sh` → `stack.sh` 가 정공법.

---

## 시나리오 2 · VM이 BUILD/ERROR

```bash
$ openstack server show test-vm
| status               | ERROR
| fault                | {"message": "No valid host was found...", ...}
```

### 흐름

```
Nova-API → Scheduler → Placement(자원 조회) → Conductor → Compute(KVM)
                            ↑                                ↑
                       자원 부족이면              KVM/이미지/네트워크 문제면
                       여기서 거절               여기서 죽음
```

### 체크리스트

```bash
# 1. Placement에서 자원 보고가 들어와 있나
$ openstack resource provider list
$ openstack resource provider inventory list <UUID>

# 2. Hypervisor가 살아있나
$ openstack hypervisor list
$ openstack hypervisor show <name>     # vcpus_used, memory_mb_used

# 3. 마지막 조각 — nova-compute 로그
$ sudo journalctl -u devstack@n-cpu -n 200 --no-pager
```

자주 보이는 원인:

- **No valid host**: flavor가 요구하는 vcpu/RAM > 가용량. flavor 줄이거나 호스트 늘리기
- **libvirt: Connection refused**: `sudo systemctl status libvirtd` 확인
- **Image not found in cache**: glance에서 다운로드 실패 — `g-api.log` 확인
- **Permission denied (qemu)**: `/var/lib/nova/instances` 권한 — DevStack에선 보통 stack 사용자

---

## 시나리오 3 · VM은 ACTIVE인데 통신 불가

가장 자주 헤매는 곳. **Neutron + Security Group + 라우팅** 3박자가 다 맞아야 함.

### 점검 순서

```bash
# 1. 포트가 ACTIVE 인가
$ openstack port list --server test-vm
| status | ACTIVE | fixed_ips ...

# 2. Security Group에 ICMP/SSH 허용?
$ openstack security group rule list default

# 3. 라우터가 외부망에 붙었나
$ openstack router show <router>      # external_gateway_info 확인

# 4. Floating IP 매핑
$ openstack floating ip list
| 192.168.100.50 | 10.0.0.5 | test-vm |

# 5. VM 내부에서
cirros$ ip addr           # IP 받았는지
cirros$ ping 10.0.0.1     # 게이트웨이 (router) 닿는지
cirros$ ping 8.8.8.8      # 외부 닿는지
```

### 자주 밟는 지뢰

- **Default SG에 ICMP/SSH 룰 없음** — DevStack 기본은 비어있다. 직접 추가해야 함
- **Floating IP는 붙였는데 외부에서 못 감** — 호스트의 `iptables`/`ufw`가 막음. `sudo ufw disable`
- **DHCP 못 받음** — `q-dhcp` 또는 OVN 컨트롤러 죽음. `journalctl -u devstack@q-svc`
- **Port security 켜져 있어 가짜 IP 차단** — `--allowed-address-pair` 또는 `port_security_enabled=False`

---

## 시나리오 4 · 볼륨 attach 안 됨

```bash
$ openstack server add volume test-vm vol1
# 한참 멈춤 → ERROR
```

### 체크

```bash
# Cinder가 LVM 백엔드 잘 잡았나
$ sudo vgs
| stack-volumes-default | ... |     ← DevStack 기본 VG

# c-vol 로그
$ sudo journalctl -u devstack@c-vol -n 100

# iSCSI 타깃 (DevStack 기본 백엔드는 LVM+iSCSI/tgtd)
$ sudo tgtadm --mode target --op show
```

자주 보이는 원인:

- **`No valid host was found`** — Cinder 스케줄러가 백엔드 못 찾음. `c-vol` 죽었거나 디스크 부족
- **iSCSI 로그인 실패** — `iscsid` 데몬 미기동: `sudo systemctl start iscsid`
- **Loop 디바이스 한계** — `losetup -a` 가 60+개면 한계. 사용 안 하는 볼륨 정리

---

## 시나리오 5 · Horizon 500 또는 빈 화면

```bash
# Apache 살아있나
$ sudo systemctl status apache2

# Horizon 에러 로그
$ sudo tail -f /var/log/apache2/horizon_error.log

# Keystone 카탈로그 깨짐?
$ openstack catalog list
```

원인 패턴:

- **`SESSION_ENGINE` 또는 캐시 백엔드 다운** — `memcached` 재시작
- **Keystone endpoint 잘못된 IP** — DevStack 재기동 후 IP 바뀐 경우. `openstack endpoint list` 로 확인 후 `endpoint set`
- **CSRF token mismatch** — 브라우저 캐시/쿠키 삭제

---

## 시나리오 6 · 호스트 재부팅 후 DevStack 깨짐

DevStack은 **재부팅을 가정하고 만들지 않았다**. 정공법은 다시 깔기.

```bash
$ cd ~/devstack
$ ./stack.sh         # 운 좋으면 그대로 다시 뜸
# 또는
$ ./clean.sh && ./stack.sh
```

재부팅 후 **자주 깨지는 것들**:

- `br-ex`/`br-int` 같은 OVS/OVN 브리지 사라짐
- LVM VG `stack-volumes-default` 마운트 안 됨 → `sudo losetup` 으로 백킹 파일 다시 연결 필요
- `rabbitmq-server`, `mariadb` 자동 시작 실패 → `sudo systemctl start`

> 💡 **재부팅 안 하는 게 답**. 학습 VM은 suspend/resume으로 운영.

---

## 진단용 한 줄 명령 모음

```bash
# 모든 OpenStack 서비스 상태
$ openstack service list
$ openstack endpoint list

# 모든 컴퓨트 노드 상태
$ openstack compute service list
$ openstack network agent list

# DevStack systemd 유닛 한꺼번에
$ sudo systemctl list-units 'devstack@*' --no-pager

# 죽어있는 유닛만
$ sudo systemctl list-units 'devstack@*' --state=failed

# 디스크/메모리 (자주 부족)
$ df -h /opt/stack /var/lib
$ free -h

# 가상화 지원 (KVM 가능?)
$ egrep -c '(vmx|svm)' /proc/cpuinfo
```

---

## 어떤 로그가 어떤 상황에 유용한가

| 증상 | 첫 번째 로그 | 두 번째 |
|---|---|---|
| VM 생성 실패 | `n-cpu.log` | `n-sch.log`, `placement-api.log` |
| VM 네트워크 X | `q-agt.log` | `q-svc.log`, OVN: `ovn-controller` |
| 볼륨 attach X | `c-vol.log` | `n-cpu.log` (붙이는 쪽) |
| 이미지 업로드 X | `g-api.log` | `c-api.log` (Cinder backed면) |
| 토큰 발급 X | `keystone.log` | Apache `error.log` |
| Horizon X | `horizon_error.log` | `keystone.log` |

---

## 디버깅 마인드셋

1. **요청 흐름을 그려라** — VM 만들기는 Nova 단독이 아니라 Keystone→Placement→Glance→Neutron→Cinder→Nova 합주
2. **로그는 시간순으로 합쳐서 봐라** — `multitail` 또는 `journalctl -u devstack@n-cpu -u devstack@q-svc -f`
3. **재현 가능하게 만들고 변수 하나만 바꿔라** — flavor 바꾸기, 이미지 바꾸기, 네트워크 빼기
4. **모르겠으면 ERROR/TRACE 첫 출현 시점부터 위로 200줄** — 진짜 원인은 첫 에러 직전에 있다

---

## 다음

- 흔한 패턴이 아니라 **메트릭/알림으로 자동 잡기** → [monitoring-telemetry.md](./monitoring-telemetry.md)
- 버전 올릴 때의 함정들 → [upgrade-strategy.md](./upgrade-strategy.md)
- DevStack 일상 운영(서비스 끄기/켜기, 데이터 보존) → [../03-installation/devstack/daily-ops.md](../03-installation/devstack/daily-ops.md)
