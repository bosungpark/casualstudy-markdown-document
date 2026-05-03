# CloudStack 단일 노드 설치 가이드 — Apple Silicon + Multipass

> **노트북 1대에 30~60분이면 CloudStack 전체가 뜨는 학습용 구성.**

프로덕션 **금지**. MS / Agent / NFS / MySQL 을 한 VM에 다 몰아넣는다. 오직 **API와 운영을 손에 익히기 위한 용도**.

> 출처: [Quick Installation Guide](https://docs.cloudstack.apache.org/en/latest/quickinstallationguide/qig.html) · [Management Server Installation (Ubuntu)](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/index.html) · [KVM Host Installation](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/kvm.html).

---

## 한 줄 요약

```
Apple Silicon Mac
    ▼
Multipass (Ubuntu 22.04 ARM64 VM)
    ▼
┌──────────────────────────────────────────┐
│  하나의 VM 안에 다 설치                   │
│   ─ MySQL                                 │
│   ─ NFS Server (Primary + Secondary)     │
│   ─ cloudstack-management (MS)            │
│   ─ cloudstack-agent (KVM)                │
│   ─ libvirt + qemu-kvm                   │
│   ─ Bridge: cloudbr0                     │
└──────────────────────────────────────────┘
    ▼
Web UI: http://<VM-IP>:8080/client (admin / password)
```

---

## 왜 Multipass + 단일 VM?

| 선택지 | 걸리는 시간 | 난이도 |
|---|---|---|
| **Multipass + 단일 VM** | 30~60분 | ⭐ |
| 베어메탈 | 1~3시간 + 하드웨어 | ⭐⭐⭐ |
| Manual Multi-Node | 2~4시간 + VM 3대 | ⭐⭐⭐⭐ |

**API와 UI/CLI를 익히는 게 목표**라면 단일 VM이 압도적으로 빠르다. 운영 흐름은 같은 컴포넌트들을 분산시키면 그대로.

---

## ⚠️ Apple Silicon 필독

### Nested 가상화

Multipass on Apple Silicon은 host의 Hypervisor.framework + QEMU를 사용한다. **VM 안에서 KVM을 사용 가능**하려면 nested virt가 필요한데, 최신 Multipass(1.13+) + macOS Sonoma + Apple Silicon M2 이상에서 지원됨.

확인:
```bash
# VM 안에서
$ ls /dev/kvm   # 있으면 OK
$ kvm-ok || lsmod | grep kvm
```

`/dev/kvm` 이 없으면 **QEMU TCG 에뮬레이션** 으로 fallback (매우 느림). 그래도 동작은 함. cirros 같은 가벼운 게스트 OS만 권장.

### ARM64 system VM template

CloudStack의 System VM(SSVM/CPVM/VR)은 아키텍처별로 별도 template. ARM64 환경에선 반드시 **aarch64용**:

```
http://download.cloudstack.org/systemvm/4.20/systemvmtemplate-4.20.0-aarch64-kvm.qcow2.bz2
```

x86용을 등록하면 SSVM/CPVM 안 뜨고 Zone 동작 안 함.

### Agent 설정

`/etc/cloudstack/agent/agent.properties` 에 ARM64 한정 설정 필요:

```ini
guest.cpu.arch=aarch64
guest.cpu.mode=host-passthrough
hypervisor.type=kvm
```

자세한 예시: [agent.properties](./agent.properties).

---

## 1. Multipass VM 만들기

```bash
# Mac 호스트에서
$ brew install --cask multipass    # 이미 있으면 skip
$ multipass version

# 8 vCPU, 12 GB RAM, 80 GB disk, Ubuntu 22.04 ARM64
$ multipass launch --cpus 8 --memory 12G --disk 80G \
    --name cloudstack 22.04

$ multipass list
+------------+---------+------------------+----------+
| Name       | State   | IPv4             | Image    |
+------------+---------+------------------+----------+
| cloudstack | Running | 192.168.64.X     | 22.04    |
| devstack   | Running | 192.168.64.3     | 22.04    |
+------------+---------+------------------+----------+

# VM에 들어가기
$ multipass shell cloudstack
ubuntu@cloudstack:~$
```

**중요**: `--cpus 8 --memory 12G` 권장. 적으면 VR/SSVM/CPVM 부팅이 OOM으로 실패.

---

## 2. 호스트 OS 준비 (VM 안에서)

```bash
# root 권한으로 진행 (대부분 sudo 필요)
$ sudo -i

# 필수 패키지
# apt update
# apt install -y vim net-tools bridge-utils chrony openssh-server

# IP 확인
# hostname -I
192.168.64.X 10.244.x.x
```

가장 큰 IP(보통 `192.168.64.X`)를 메모. 이후 `$LANIP`로 사용.

```bash
# export LANIP=<위에서 확인한 IP>
# echo $LANIP
```

### NTP

```bash
# systemctl enable --now chrony
# chronyc tracking
```

### SSH (선택, Mac에서 직접 SSH 들어오고 싶을 때)

```bash
# vim /etc/ssh/sshd_config
# PermitRootLogin yes 주석 해제
# systemctl restart ssh
```

---

## 3. 네트워크 브리지 — `cloudbr0`

KVM 게스트가 외부 통신하려면 **bridge가 필요**. Multipass의 기본 NIC을 bridge에 묶는다.

> ⚠️ Multipass의 기본 인터페이스는 보통 `enp0s2` 또는 `ens3`. `ip a` 로 확인.

```bash
# ip a | grep "state UP" -A1
# 결과 예: enp0s2
```

### netplan 으로 cloudbr0 만들기

```bash
# vim /etc/netplan/50-cloud-init.yaml
```

```yaml
network:
  version: 2
  ethernets:
    enp0s2:
      dhcp4: false
      dhcp6: false
  bridges:
    cloudbr0:
      addresses: [<위 LANIP>/24]   # 예: 192.168.64.5/24
      gateway4: 192.168.64.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
      interfaces: [enp0s2]
      parameters:
        stp: false
        forward-delay: 0
```

⚠️ **netplan apply 직후 SSH가 끊길 수 있음**. Multipass shell이면 `multipass shell cloudstack` 다시 들어가면 OK.

```bash
# chmod 600 /etc/netplan/50-cloud-init.yaml
# netplan generate
# netplan apply

# 확인
# ip a show cloudbr0
# brctl show
```

---

## 4. NFS 서버 설치 (Primary + Secondary)

```bash
# apt install -y nfs-kernel-server nfs-common

# mkdir -p /export/{primary,secondary} /mnt/{primary,secondary}
# chmod 777 /export/primary /export/secondary

# cat >> /etc/exports <<EOF
/export/primary *(rw,async,no_root_squash,no_subtree_check)
/export/secondary *(rw,async,no_root_squash,no_subtree_check)
EOF

# systemctl enable --now nfs-kernel-server
# exportfs -a
# showmount -e localhost
Export list for localhost:
/export/secondary *
/export/primary   *
```

### 자기 자신을 마운트 (Agent가 사용)

```bash
# cat >> /etc/fstab <<EOF
$LANIP:/export/primary   /mnt/primary   nfs defaults 0 0
$LANIP:/export/secondary /mnt/secondary nfs defaults 0 0
EOF

# mount -a
# df -h | grep mnt
```

---

## 5. MySQL 설치 + CloudStack 권장 설정

```bash
# apt install -y mysql-server

# cat > /etc/mysql/conf.d/cloudstack.cnf <<EOF
[mysqld]
server-id=master-01
innodb_rollback_on_timeout=1
innodb_lock_wait_timeout=600
max_connections=350
log-bin=mysql-bin
binlog-format='ROW'
EOF

# systemctl restart mysql
# systemctl enable mysql

# root 비번 설정 (학습용 password: cloudstack)
# mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'cloudstack';"

# (선택) mysql_secure_installation
```

자세한 설정 예시: [my.cnf](./my.cnf).

---

## 6. CloudStack APT 저장소 추가

```bash
# apt install -y curl gpg

# mkdir -p /etc/apt/keyrings
# wget -O- http://download.cloudstack.org/release.asc \
    | gpg --dearmor | tee /etc/apt/keyrings/cloudstack.gpg > /dev/null

# echo "deb [signed-by=/etc/apt/keyrings/cloudstack.gpg] http://download.cloudstack.org/ubuntu jammy 4.20" \
    > /etc/apt/sources.list.d/cloudstack.list

# apt update
```

---

## 7. cloudstack-management 설치

```bash
# apt install -y cloudstack-management

# 설치 확인
# dpkg -l | grep cloudstack
ii  cloudstack-common      4.20.x-1  ...
ii  cloudstack-management  4.20.x-1  ...
```

### DB 초기화

```bash
# cloudstack-setup-databases cloud:cloudstack@localhost \
    --deploy-as=root:cloudstack \
    -e file \
    -m password \
    -k password \
    -i $LANIP
```

- `cloud:cloudstack` — DB user/password 생성
- `--deploy-as=root:cloudstack` — root로 접속해서 schema 생성
- `-e file` — secret 암호화는 file mode (학습용. 운영은 web)
- `-m / -k` — management/db key (학습용 password)
- `-i` — MS의 IP

성공하면:
```
CloudStack has successfully initialized database, ...
```

### MS 시작

```bash
# cloudstack-setup-management

# 정상 부팅 확인
# systemctl status cloudstack-management
# tail -f /var/log/cloudstack/management/management-server.log
```

부팅 완료까지 약 1~3분. 다음 메시지가 나오면 Web UI 가능:
```
... INFO  ... ManagementServer started
```

---

## 8. cloudstack-agent (KVM Host) 설치

같은 VM에 Agent까지 설치 (All-in-one).

```bash
# apt install -y qemu-kvm cloudstack-agent
# systemctl enable cloudstack-agent
```

### libvirt TCP listen 활성화

```bash
# vim /etc/libvirt/qemu.conf
vnc_listen = "0.0.0.0"

# vim /etc/libvirt/libvirtd.conf
listen_tls = 0
listen_tcp = 1
tcp_port = "16509"
auth_tcp = "none"
mdns_adv = 0

# vim /etc/default/libvirtd
LIBVIRTD_ARGS="--listen"

# systemctl mask libvirtd.socket libvirtd-ro.socket libvirtd-admin.socket libvirtd-tls.socket libvirtd-tcp.socket
# systemctl restart libvirtd
```

### AppArmor 끄기 (Ubuntu 한정)

```bash
# ln -sf /etc/apparmor.d/usr.sbin.libvirtd /etc/apparmor.d/disable/
# ln -sf /etc/apparmor.d/usr.lib.libvirt.virt-aa-helper /etc/apparmor.d/disable/
# apparmor_parser -R /etc/apparmor.d/usr.sbin.libvirtd
# apparmor_parser -R /etc/apparmor.d/usr.lib.libvirt.virt-aa-helper
```

### ARM64 한정 — agent.properties

```bash
# vim /etc/cloudstack/agent/agent.properties
```

추가/확인:
```ini
hypervisor.type=kvm
guest.cpu.arch=aarch64
guest.cpu.mode=host-passthrough
network.bridge.type=native
private.bridge.name=cloudbr0
public.network.device=cloudbr0
private.network.device=cloudbr0
guest.network.device=cloudbr0
```

전체 예시: [agent.properties](./agent.properties).

```bash
# systemctl restart cloudstack-agent
# tail -f /var/log/cloudstack/agent/agent.log
```

---

## 9. SystemVM Template 설치 (★ ARM64)

Zone 활성화 전, **반드시** SystemVM template을 Secondary Storage에 등록.

```bash
# /usr/share/cloudstack-common/scripts/storage/secondary/cloud-install-sys-tmplt \
    -m /mnt/secondary \
    -u http://download.cloudstack.org/systemvm/4.20/systemvmtemplate-4.20.0-aarch64-kvm.qcow2.bz2 \
    -h kvm \
    -F
```

x86 환경이면 `aarch64` 대신 `x86_64`. **ARM64 환경에서 x86_64 template 등록은 동작 안 함**.

---

## 10. Web UI 첫 접속

```
http://$LANIP:8080/client/
ID: admin
PW: password
```

⚠️ 첫 로그인 후 **반드시 패스워드 변경** (학습용이라도 습관 들이기).

### Zone 마법사

UI의 "Add Zone" 버튼:

```
Type:           Advanced (권장) 또는 Basic
Name:           lab-zone
DNS:            8.8.8.8
Internal DNS:   8.8.8.8
Hypervisor:     KVM
```

Pod:
```
Name:           lab-pod
Reserved IP:    192.168.64.50 - 192.168.64.99   (관리망 IP 풀)
Gateway:        192.168.64.1
Netmask:        255.255.255.0
```

Cluster:
```
Hypervisor:     KVM
Name:           lab-cluster
```

Host:
```
Name:           localhost or $LANIP
Username:       root
Password:       <root password 또는 SSH key>
```

Primary Storage:
```
Name:           lab-primary
Protocol:       NFS
Server:         $LANIP
Path:           /export/primary
```

Secondary Storage:
```
Provider:       NFS
Server:         $LANIP
Path:           /export/secondary
```

마법사 끝나면 Zone Activate. **SSVM과 CPVM이 자동 부팅** (5~10분).

---

## 11. SystemVM 부팅 확인

```bash
# Mac에서 cmk 설치
$ pip3 install cloudmonkey
$ cmk set url http://$LANIP:8080/client/api
$ cmk set username admin
$ cmk set password <new-password>
$ cmk sync

$ cmk list systemvms
+----------+-------+----------+
| name     | type  | state    |
+----------+-------+----------+
| s-1-VM   | SSVM  | Running  |
| v-2-VM   | CPVM  | Running  |
+----------+-------+----------+
```

둘 다 Running이면 ✅ Zone 정상.

---

## 12. 자주 밟는 지뢰

### 🔴 SSVM/CPVM 영원히 Starting

- SystemVM template 미등록 → 9단계 다시
- ARM에 x86 template → aarch64로 다시 받기
- 메모리 부족 → VM에 12GB 이상 할당

### 🔴 Agent가 MS와 연결 안 됨

```bash
# tcpdump -i any port 8250
# tail -f /var/log/cloudstack/agent/agent.log
```

흔한 원인: 방화벽 (학습 VM은 `ufw disable`), MS IP 오타 (`/etc/cloudstack/agent/agent.properties`의 `host=`).

### 🔴 KVM 안 뜸

```bash
# kvm-ok
INFO: /dev/kvm exists
# OK

# 없으면 — Apple Silicon nested virt 미지원
# → QEMU TCG fallback (매우 느림)
```

호스트 macOS 업데이트, Multipass 업데이트로 해결되는 경우가 많다.

### 🔴 Web UI 8080 안 열림

```bash
# systemctl status cloudstack-management
# journalctl -u cloudstack-management -n 50
```

JVM heap 부족 의심: `/etc/default/cloudstack-management`의 `JAVA_OPTS`에 `-Xmx2g`.

### 🔴 NFS 마운트 실패

```bash
# showmount -e localhost
# mount -t nfs $LANIP:/export/primary /mnt/primary
```

`exports` 권한 (`no_root_squash`) 누락.

### 🔴 MySQL 비번 mismatch

```bash
# cloudstack-setup-databases ... 의 비번이 my.cnf와 안 맞음
# /etc/cloudstack/management/db.properties 의 db.cloud.password 직접 수정
# systemctl restart cloudstack-management
```

---

## 13. 중단/재시작/삭제

```bash
# 서비스 중단 (VM 살아있음)
# systemctl stop cloudstack-management cloudstack-agent

# 재시작
# systemctl start cloudstack-management cloudstack-agent

# DB 초기화 (전체 리셋)
# systemctl stop cloudstack-management
# mysql -uroot -p -e "DROP DATABASE cloud; DROP DATABASE cloud_usage;"
# cloudstack-setup-databases ... (다시)
```

VM 통째 삭제:
```bash
# Mac 호스트에서
$ multipass delete cloudstack && multipass purge
```

---

## 14. 자동화 스크립트

이 가이드의 모든 단계를 한 번에: [bootstrap.sh](./bootstrap.sh).

```bash
# Mac에서 VM에 복사
$ multipass transfer bootstrap.sh cloudstack:/home/ubuntu/

# VM 안에서
$ sudo bash bootstrap.sh
```

> ⚠️ 처음 한 번은 **각 단계 수동으로** 따라가는 것이 학습에 좋다. 자동화는 두 번째부터.

---

## 다음 단계

- [../../labs/01-first-vm.md](../../labs/01-first-vm.md) — 첫 VM 띄워보기
- [../../04-operations/troubleshooting.md](../../04-operations/troubleshooting.md) — 더 깊은 디버깅
- [../../05-deep-dives/](../../05-deep-dives/) — 내부 동작

> 💡 **최고의 학습법**: Web UI에서 VM 만들 때, 동시에 다른 터미널에서 `tail -f /var/log/cloudstack/management/management-server.log` 따라가며 **Allocator → Agent → libvirt** 가 순서대로 동작하는 걸 관찰하기.

---

## 공식 문서 레퍼런스

- [Quick Installation Guide (EL8)](https://docs.cloudstack.apache.org/en/latest/quickinstallationguide/qig.html)
- [Management Server Installation (Ubuntu)](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/index.html)
- [Configure Package Repository](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/_pkg_repo.html)
- [KVM Hypervisor Host Installation](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/kvm.html)
- [System VMs](https://docs.cloudstack.apache.org/en/latest/adminguide/systemvm.html)

비공식 (실용 참고):
- [Apache CloudStack on ARM64 with Ubuntu and KVM (ScaleNinja)](https://scaleninja.com/blog/cloudstack/)
- [CloudStack 4.20 Installation Guide (HackMD)](https://hackmd.io/@u3-iFl9kQReVWgRWl65Img/SJyjtZQQxg)
