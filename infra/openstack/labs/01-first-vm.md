# Lab 01 — 첫 VM 띄우기

> **목표**: DevStack 위에서 키페어 → 보안그룹 → 네트워크 확인 → VM 부팅 → SSH 접속까지.

전체 OpenStack의 핵심 흐름을 30분 안에 손으로 체험.

---

## 사전 조건

- DevStack 설치 완료 (Horizon 접속 가능, `openstack service list` 동작)
- `source openrc demo demo` (또는 admin) 환경
- ARM Mac + Multipass 환경이면: cirros-aarch64 이미지 사용

---

## 1. 환경 확인

```bash
$ source openrc demo demo

$ openstack service list           # 서비스 정상 동작?
$ openstack image list             # cirros 이미지 있나?
$ openstack flavor list            # 어떤 flavor가 있나?
$ openstack network list           # 기본 private/public 네트워크
```

**기대 결과**: image에 `cirros-*-disk` 가 있고, network에 `private`, `public` 둘이 보임.

---

## 2. SSH 키 등록

```bash
# 키쌍 생성 (이미 있으면 다음 단계로)
$ ls ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa

# OpenStack에 등록
$ openstack keypair create --public-key ~/.ssh/id_rsa.pub mykey

$ openstack keypair list
+-------+-------------------------------------------------+------+
| Name  | Fingerprint                                     | Type |
+-------+-------------------------------------------------+------+
| mykey | aa:bb:cc:dd:ee:ff:...                           | ssh  |
+-------+-------------------------------------------------+------+
```

> 💡 **무슨 일이 일어났나**: Nova가 VM을 만들 때 cloud-init이 이 공개키를 VM의 `~/.ssh/authorized_keys`에 자동 주입한다.

---

## 3. 보안그룹(Security Group) 열기

기본은 **모든 인바운드 차단**. SSH(22) + ICMP(ping) 만 열어보자.

```bash
$ openstack security group rule create --proto icmp default
$ openstack security group rule create --proto tcp --dst-port 22 default

# 확인
$ openstack security group rule list default
```

> 💡 **함정**: 같은 명령 두 번 실행하면 "Security group rule already exists" 나옴 → 정상.

---

## 4. VM 만들기

```bash
$ openstack server create \
    --flavor m1.tiny \
    --image cirros-0.6.2-aarch64-disk \
    --network private \
    --key-name mykey \
    --security-group default \
    test-vm

# 상태 추적
$ openstack server list
+--------+---------+--------+--------------------+------+----------+
| ID     | Name    | Status | Networks           | Image| Flavor   |
+--------+---------+--------+--------------------+------+----------+
| ...    | test-vm | BUILD  |                    | ...  | m1.tiny  |
+--------+---------+--------+--------------------+------+----------+

# 30초~수 분 대기 후 다시
$ openstack server list      # Status: ACTIVE 되면 OK
```

> 💡 **ARM/QEMU 환경**: KVM 없으면 부팅이 1~3분 걸릴 수 있음. cirros는 가벼우니 인내.

### 만약 ERROR 상태라면

```bash
$ openstack server show test-vm | grep fault -A 5
```

`fault` 메시지로 원인 추적. 흔한 케이스:
- `No valid host` → flavor가 너무 큼 / Placement에 자원 없음
- `Image not found` → cirros 이미지 이름 오타
- `Network not found` → `private` 네트워크 없음

---

## 5. Floating IP 할당

VM은 사설망 IP만 가짐. 외부에서 접속하려면 공인IP(Floating IP) 필요.

```bash
# Floating IP 발급
$ openstack floating ip create public
+---------------------+--------------------------------------+
| Field               | Value                                |
+---------------------+--------------------------------------+
| floating_ip_address | 172.24.4.10                          |
+---------------------+--------------------------------------+

# VM에 붙이기
$ openstack server add floating ip test-vm 172.24.4.10

# 확인
$ openstack server list
# Networks 컬럼에 사설IP, 172.24.4.10 (공인) 둘 다 보여야 함
```

---

## 6. SSH 접속

```bash
$ ssh cirros@172.24.4.10
# 비번: gocubsgo

cirros@test-vm:~$ uname -a
Linux test-vm 6.x.x ...

cirros@test-vm:~$ ip addr
# 사설IP 보임

cirros@test-vm:~$ exit
```

🎉 **여기까지 오면 OpenStack 핵심 흐름을 한 바퀴 돈 것**.

---

## 7. 콘솔 직접 보기 (SSH 안 될 때)

SSH가 안 되면 (보안그룹/네트워크 문제) **VNC 콘솔**로 VM에 직접 접속:

```bash
$ openstack console url show test-vm
+----------+-------------------------------------------+
| Field    | Value                                     |
+----------+-------------------------------------------+
| protocol | vnc                                       |
| type     | novnc                                     |
| url      | http://192.168.64.3/vnc_auto.html?token=… |
+----------+-------------------------------------------+
```

브라우저로 URL 열기 → cirros 콘솔 로그인 (cirros / gocubsgo)

---

## 8. Horizon에서 같은 작업 해보기

웹 UI가 더 익숙하면:

```
http://<HOST_IP>/dashboard
ID: demo / PW: secret

좌측: 프로젝트 → Compute → 인스턴스 → "인스턴스 시작"
```

같은 작업이 클릭으로 가능. **CLI와 UI를 비교하며 익히면 두 배로 빨리** 는다.

---

## 9. 정리 (Cleanup)

```bash
# Floating IP 떼기 + 풀로 반환
$ openstack server remove floating ip test-vm 172.24.4.10
$ openstack floating ip delete 172.24.4.10

# VM 삭제
$ openstack server delete test-vm

# 키쌍 삭제 (선택)
$ openstack keypair delete mykey
```

---

## 무슨 일이 일어났나 — 큰 그림

```
$ openstack server create ...
        │
        ▼
1. Keystone:    "토큰 검증 OK, demo 프로젝트의 member 권한"
2. Nova-API:    요청 수신
3. Placement:   "vcpu=1, ram=512MB 가능한 호스트?" → compute-01
4. Glance:      cirros 이미지 다운로드 → compute-01에 캐시
5. Neutron:     사설망에 포트 생성, IP 할당, Security Group 적용
6. Cinder:      (Boot from Volume이면) 볼륨 생성 + attach
7. Nova-Compute → libvirt: "VM 시작!"
8. cloud-init:  공개키 주입, hostname 설정
9. ACTIVE 상태로 전환
```

이 9단계가 한 줄 명령어 뒤에서 일어난다. 각 단계에서 실패하면 어느 서비스 로그를 봐야 할지가 OpenStack 운영의 핵심 스킬.

---

## 다음

→ [02-multi-tenant-network.md](./02-multi-tenant-network.md) — 두 프로젝트 간 네트워크 격리  
→ [03-live-migration.md](./03-live-migration.md) — VM을 멈추지 않고 다른 호스트로 이동
