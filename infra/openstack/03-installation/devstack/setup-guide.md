# DevStack 설치 가이드

> **노트북/VM 1대에 15~30분이면 OpenStack 전체가 뜨는 학습용 도구.**

프로덕션 **금지**. 재부팅하면 날아가고, HA도 없고, 보안도 허술. 오직 **배우기 위한 용도**.

---

## 한 줄 요약

`stack.sh` 스크립트 하나가 **Keystone/Nova/Neutron/Glance/Cinder/Horizon/Placement**를 전부 소스에서 받아 설치해준다. `local.conf` 파일로 설정만 주면 끝.

```
  git clone devstack
      ▼
  local.conf 편집
      ▼
  ./stack.sh   ← 커피 한 잔 마시고 오면 완료
      ▼
  Horizon 접속 → 놀기
```

---

## 왜 DevStack으로 시작?

| 선택지 | 걸리는 시간 | 난이도 |
|---|---|---|
| **DevStack** | 15~30분 | ⭐ |
| Kolla-Ansible | 1~2시간 | ⭐⭐⭐ |
| 수동 설치 | 며칠 | ⭐⭐⭐⭐⭐ |

OpenStack **API와 CLI를 익히는 게 목표**라면 DevStack이 압도적으로 빠르다. 서비스 간 협업을 눈으로 보고 싶을 때도 `/opt/stack/logs/` 가 다 열려 있어서 디버깅하기 좋음.

---

## 환경 준비

### 최소 사양

| 항목 | 최소 | 권장 |
|---|---|---|
| CPU | 4 vCPU | 6+ vCPU |
| RAM | 8 GB | 12 GB |
| Disk | 50 GB | 80 GB+ |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

> 💡 **M1/M2 Mac** 은 ARM 이슈로 고생함. **AMD64 Linux VM** 을 권장. UTM으로 에뮬하면 느려서 비추.

### VM으로 돌릴 때 추천 조합

- **macOS**: Multipass (`multipass launch --cpus 4 --memory 8G --disk 50G 22.04`) 가 가장 편함
- **Windows/Linux**: VirtualBox, VMware Workstation, KVM 아무거나
- **클라우드**: EC2 `t3.xlarge` 이상 / GCP `e2-standard-4`

> ⚠️ **중첩 가상화(Nested Virt)** 활성화. DevStack이 VM을 띄워야 하니 CPU 가상화 extension(`vmx`/`svm`)이 보여야 함. `egrep -c '(vmx|svm)' /proc/cpuinfo` → 0이면 안 됨.

---

## 설치 단계

### 1. stack 사용자 만들기

DevStack은 **반드시 전용 사용자**에서 돌려야 한다. root 금지.

```bash
sudo useradd -s /bin/bash -d /opt/stack -m stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/stack
sudo -u stack -i    # stack 사용자로 전환
```

### 2. DevStack 소스 받기

```bash
git clone https://opendev.org/openstack/devstack
cd devstack
```

### 3. `local.conf` 작성

이 디렉토리의 [local.conf](./local.conf) 를 복사해서 **HOST_IP만 본인 IP**로 바꾸면 된다.

```bash
cp /path/to/this-repo/local.conf .
vi local.conf    # HOST_IP=... 수정
```

### 4. 설치 실행

```bash
./stack.sh
```

로그가 엄청나게 찍히면서 15~30분 돈다. 끝나면 이런 메시지:

```
=========================
DevStack Component Timing
=========================
...
This is your host IP address: 192.168.1.10
This is your host IPv6 address: ...
Horizon is now available at http://192.168.1.10/dashboard
Keystone is serving at http://192.168.1.10/identity/
...
```

---

## 설치 후 첫 확인

### Horizon 웹 접속

```
http://<HOST_IP>/dashboard
아이디: admin 또는 demo
비번: local.conf 의 ADMIN_PASSWORD (기본 "secret")
```

### CLI 환경변수 설정

```bash
source openrc admin admin     # admin 계정으로
# 또는
source openrc demo demo       # 일반 사용자로
```

### 잘 떴나 확인

```bash
$ openstack service list
+----+------------+----------+
| ID | Name       | Type     |
+----+------------+----------+
| .. | keystone   | identity |
| .. | nova       | compute  |
| .. | neutron    | network  |
| .. | glance     | image    |
| .. | cinder     | volumev3 |
| .. | placement  | placement|
+----+------------+----------+

$ openstack image list   # cirros 같은 테스트 이미지가 기본 포함
$ openstack flavor list
$ openstack network list
```

---

## 첫 VM 띄워보기 (5분 코스)

```bash
# 1. 키쌍 생성
$ openstack keypair create --public-key ~/.ssh/id_rsa.pub mykey

# 2. 기본 Security Group에 SSH/ICMP 허용
$ openstack security group rule create --proto icmp default
$ openstack security group rule create --proto tcp --dst-port 22 default

# 3. VM 생성 (cirros 이미지는 기본 제공)
$ openstack server create \
    --flavor m1.tiny \
    --image cirros-0.6.2-x86_64-disk \
    --network private \
    --key-name mykey \
    test-vm

# 4. 공인 IP 할당
$ openstack floating ip create public
$ openstack server add floating ip test-vm <floating-ip>

# 5. 접속
$ ssh cirros@<floating-ip>     # 비번: gocubsgo
```

이 5줄 흐름이 돌아가면 **OpenStack 사용법의 절반은 익힌 것**.

---

## 중단/재시작/삭제

```bash
# 서비스 중단 (VM/데이터는 살아있음 — 하지만 불안정)
./unstack.sh

# 재시작 (unstack 후)
./stack.sh   # 일반적으로 재실행은 깨끗한 clean.sh 후 권장

# 완전 초기화 (DB/로그/VM 다 날림)
./clean.sh
```

> ⚠️ **호스트 재부팅하면 DevStack은 깨진다**. `./stack.sh` 재실행이 권장 방식. 재부팅 후 복구 스크립트 `./rejoin-stack.sh` 가 있지만 버전에 따라 불안정.

---

## 자주 밟는 지뢰

### 🔴 설치 중 `git clone` 실패

opendev.org 속도 느림. `GIT_BASE=https://github.com` 로 GitHub 미러 사용 가능.

```bash
# local.conf 에 추가
GIT_BASE=https://github.com
```

### 🔴 "HOST_IP를 결정할 수 없음"

인터페이스가 여러 개면 자동 감지 실패. `local.conf`에 명시.

```bash
HOST_IP=192.168.1.10
HOST_IP_IFACE=eth0
```

### 🔴 VM이 BUILD에서 안 넘어감

- 중첩 가상화 비활성 → KVM 못 뜸 → QEMU로 fallback(엄청 느림)
- 메모리 부족 → `free -h` 확인, swap 추가
- `tail -f /opt/stack/logs/n-cpu.log` 로 nova-compute 로그 확인

### 🔴 Horizon 접속 안 됨

- Apache 상태: `sudo systemctl status apache2`
- 방화벽: `sudo ufw disable` (학습 VM이니 편하게)

### 🔴 디스크 부족

cinder 볼륨, glance 이미지가 loop 파일로 저장됨. 50GB는 빠듯함. **80GB 이상 권장**.

### 🔴 `./stack.sh` 중간에 실패

대부분 네트워크/패키지 문제. 로그 끝부분 확인 후:

```bash
./unstack.sh
./clean.sh
./stack.sh    # 재시도
```

---

## 서비스 추가하기

기본 설치는 **Keystone / Nova / Neutron / Glance / Cinder / Horizon / Placement** 만 깔린다. 더 필요하면 `local.conf` 에 플러그인 활성화:

```bash
# Heat (오케스트레이션)
enable_plugin heat https://opendev.org/openstack/heat

# Octavia (로드밸런서)
enable_plugin octavia https://opendev.org/openstack/octavia
enable_plugin octavia-dashboard https://opendev.org/openstack/octavia-dashboard

# Magnum (K8s 클러스터)
enable_plugin magnum https://opendev.org/openstack/magnum
enable_plugin magnum-ui https://opendev.org/openstack/magnum-ui

# Ironic (베어메탈)
enable_plugin ironic https://opendev.org/openstack/ironic
```

추가 후 `./stack.sh` 재실행하면 새 서비스가 설치됨.

---

## 디버깅 요점

### 로그 위치

```
/opt/stack/logs/                  ← 모든 서비스 로그
├── stack.sh.log                  ← 설치 로그
├── n-cpu.log                     ← nova-compute
├── n-api.log                     ← nova-api
├── q-svc.log                     ← neutron-server
├── c-vol.log                     ← cinder-volume
├── g-api.log                     ← glance-api
└── ...
```

### 서비스 재시작

DevStack 서비스는 **systemd 유닛**으로 돈다. `devstack@*` 패턴.

```bash
$ sudo systemctl list-units 'devstack@*'
devstack@n-api.service       nova-api
devstack@n-cpu.service       nova-compute
devstack@q-svc.service       neutron-server
...

# 재시작
$ sudo systemctl restart devstack@n-cpu
```

### 실시간 로그 따라가기

```bash
$ sudo journalctl -u devstack@n-cpu -f
```

---

## 다음 단계

- 기본 서비스 확인 끝났으면 → [../../01-core-services/](../../01-core-services/) 각 서비스 문서 읽으며 실제 명령어 쳐보기
- Advanced 서비스 붙여보고 싶으면 → 위 "서비스 추가하기" 섹션
- 멀티노드 / 프로덕션 구조 경험하고 싶으면 → [../kolla-ansible/setup-guide.md](../kolla-ansible/setup-guide.md)

> 💡 **최고의 학습법**: DevStack 띄운 뒤 Horizon에서 VM 하나 만들 때, 동시에 다른 터미널에서 `tail -f /opt/stack/logs/*.log` 로 **어느 서비스가 언제 일하는지** 관찰하기. Keystone → Nova → Placement → Glance → Neutron → Cinder 순서로 로그가 튀는 게 눈으로 보인다.
