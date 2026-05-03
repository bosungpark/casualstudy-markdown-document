# Lab 01 — 첫 VM 띄우기

> **목표**: CloudStack 위에 키쌍 → 네트워크 → VM → Public IP → SSH 까지 30~45분에 손으로.

이 실습이 끝나면 [../00-overview/architecture-overview.md](../00-overview/architecture-overview.md) 의 **deployVirtualMachine 8단계**를 머릿속에서 그릴 수 있게 된다.

---

## 사전 조건

- [03-installation/multipass-allinone/setup-guide.md](../03-installation/multipass-allinone/setup-guide.md) 완료
- Zone Active, SSVM + CPVM이 Running
- Web UI 또는 cmk 작동
- 다음 명령이 비어있지 않게 결과 보임:

```bash
$ cmk list zones
$ cmk list systemvms state=Running    # SSVM, CPVM 둘 다 보여야 함
$ cmk list templates templatefilter=featured
```

---

## 1. 환경 확인

```bash
# Mac 호스트 (cmk)
$ cmk set url http://<VM-IP>:8080/client/api
$ cmk sync

# 또는 안에서 ssh
$ multipass shell cloudstack
$ source <(echo "export CMK_API=http://localhost:8080/client/api")
```

```bash
$ cmk list zones
+----+----------+-----------+--------------+
| id | name     | state     | networktype  |
+----+----------+-----------+--------------+
| .. | lab-zone | Enabled   | Advanced     |
+----+----------+-----------+--------------+

$ cmk list serviceofferings
+----+-----------+----+----+--------+
| id | name      | cpu| mhz| memory |
+----+-----------+----+----+--------+
| .. | Small     | 1  | 500| 512    |
| .. | Medium    | 1  | 1000|1024   |
+----+-----------+----+----+--------+

$ cmk list templates templatefilter=featured
+----+--------------------+----------+
| id | name               | osname   |
+----+--------------------+----------+
| .. | CentOS-Stream-9-... | ...      |
+----+--------------------+----------+
```

> 💡 ARM64라면 ARM용 template이 있어야 함. 아니면 [register template](#templates-등록) 단계 먼저.

---

## 2. SSH 키 등록

```bash
# Mac에서 키 만들기 (있으면 skip)
$ ls ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa

# CloudStack에 등록
$ cmk register sshkeypair name=mykey \
    publickey="$(cat ~/.ssh/id_rsa.pub)"

$ cmk list sshkeypairs
+--------+-------------------------------------------+
| name   | fingerprint                               |
+--------+-------------------------------------------+
| mykey  | aa:bb:cc:dd:ee:ff:...                     |
+--------+-------------------------------------------+
```

> 💡 **무슨 일이 일어났나**: VR이 cloud-init에 이 공개키를 user-data로 전달 → VM의 `~/.ssh/authorized_keys` 에 자동 주입.

---

## 3. Network 만들기

Advanced Zone 환경. Isolated Network을 만들어 VM이 들어갈 자기 사설망을 준비.

```bash
# Network Offering 확인
$ cmk list networkofferings state=Enabled \
    guestiptype=Isolated \
    forvpc=false

# 가장 일반적인 것: "DefaultIsolatedNetworkOfferingWithSourceNatService"
$ NETOFFER=$(cmk list networkofferings name=DefaultIsolatedNetworkOfferingWithSourceNatService \
    --output csv | tail -1 | cut -d, -f2)

$ cmk create network \
    name=tenant-net \
    displaytext="Lab tenant network" \
    networkofferingid=$NETOFFER \
    zoneid=<zone-id> \
    gateway=10.1.1.1 \
    netmask=255.255.255.0

# 확인
$ cmk list networks
+----+------------+----------+-----------+--------------+
| id | name       | state    | gateway   | networkdomain|
+----+------------+----------+-----------+--------------+
| .. | tenant-net | Allocated| 10.1.1.1  | cs.local     |
+----+------------+----------+-----------+--------------+
```

> 💡 **Allocated 단계**: 아직 VR은 안 떴음. 첫 VM이 들어가는 순간 VR이 자동 부팅된다.

---

## 4. VM 배포

```bash
# 필요한 ID들
$ ZONEID=$(cmk list zones --output csv | tail -1 | cut -d, -f1)
$ TPLID=$(cmk list templates templatefilter=featured \
    --output csv | tail -1 | cut -d, -f1)
$ OFFERID=$(cmk list serviceofferings name=Small \
    --output csv | tail -1 | cut -d, -f1)
$ NETID=$(cmk list networks name=tenant-net \
    --output csv | tail -1 | cut -d, -f1)

# VM 배포
$ cmk deploy virtualmachine \
    serviceofferingid=$OFFERID \
    templateid=$TPLID \
    zoneid=$ZONEID \
    networkids=$NETID \
    keypair=mykey \
    name=test-vm

{
  "jobid": "abc-123-...",
  "id": "vm-uuid"
}

# 잡 진행 확인
$ cmk query asyncjobs jobid=abc-123-...

# 완료될 때까지 (보통 1~5분, 첫 배포는 템플릿 복사로 더 오래)
```

### VM 상태 추적

```bash
$ cmk list virtualmachines name=test-vm
+----+---------+----------+----------+
| id | name    | state    | nic[0].ip|
+----+---------+----------+----------+
| .. | test-vm | Running  | 10.1.1.5 |
+----+---------+----------+----------+
```

### 만약 Error 상태라면

```bash
$ cmk list events level=ERR pagesize=10 | grep test-vm

# 또는 jobid로
$ cmk query asyncjobs jobid=<...> | jq .jobresult.errortext
```

[../04-operations/troubleshooting.md](../04-operations/troubleshooting.md) 의 진단 흐름 참고.

---

## 5. VR이 떴는지 확인

VM이 Running 되었다면 VR도 자동으로 떴다:

```bash
$ cmk list routers networkid=$NETID
+----+----------+----------+----------+----------+
| id | name     | state    | publicip | guestip  |
+----+----------+----------+----------+----------+
| .. | r-1-VM   | Running  | (할당)   | 10.1.1.1 |
+----+----------+----------+----------+----------+
```

→ "**한 게스트망 = 한 VR**" 의 실제 모습.

---

## 6. Public IP 할당 + Static NAT

VM은 사설 IP(10.1.1.5) 만 가진다. 외부에서 접속하려면 Public IP.

```bash
# Public IP 발급
$ cmk associate ipaddress \
    zoneid=$ZONEID \
    networkid=$NETID

# 결과의 ipaddressid, ipaddress 확인
$ cmk list publicipaddresses associatednetworkid=$NETID
+----+--------------+----------+
| id | ipaddress    | state    |
+----+--------------+----------+
| .. | 192.168.64.X | Allocated|
+----+--------------+----------+

$ PUBIPID=<위 id>
$ VMID=<test-vm id>

# Static NAT (1:1 매핑)
$ cmk enable staticnat \
    virtualmachineid=$VMID \
    ipaddressid=$PUBIPID
```

### Firewall 규칙 (외부 SSH 22 열기)

```bash
$ cmk create firewallrule \
    ipaddressid=$PUBIPID \
    protocol=tcp \
    startport=22 endport=22 \
    cidrlist=0.0.0.0/0
```

> 💡 **VR 안에서 일어나는 일**: iptables PREROUTING DNAT 룰이 추가됨. ICMP는 별도 firewall rule 필요.

---

## 7. SSH 접속

```bash
$ ssh -i ~/.ssh/id_rsa root@192.168.64.X
# 또는 cloud-user, ubuntu, centos (template에 따라)

# 들어가서 확인
$ uname -a
Linux test-vm 5.x.x ...

$ ip addr
# eth0: 10.1.1.5 (게스트망)

$ ip route
# default via 10.1.1.1 dev eth0   ← VR이 GW

$ curl http://169.254.169.254/latest/user-data
# (VR이 응답)

$ exit
```

🎉 **여기까지 오면 CloudStack 핵심 흐름을 한 바퀴 돈 것**.

---

## 8. UI에서 콘솔 확인 (CPVM 동작 확인)

Web UI 좌측 → Compute → Instances → test-vm → "View Console":

```
브라우저가 noVNC 화면 → CPVM 경유로 VM 콘솔 접근
```

→ "**CPVM이 살아 있고, libvirt VNC 경로가 막히지 않았다**" 의 증거.

---

## 9. AsyncJob 흐름 — 한 번 정리

```
$ cmk deploy virtualmachine ...

이 명령 뒤:
[1] ApiServer:  Signed Query 검증 (User → apiKey/HMAC)
[2] DB:         vm_instance(state=Allocated), volumes 행 작성
[3] Allocators: HostAllocator + StoragePoolAllocator → 호스트, 스토리지 결정
[4] AsyncJob:   enqueue → jobid 반환
[5] Network:    Network이 Allocated → VR 부팅 (System VM)
[6] Agent:      cloudstack-agent → libvirt:
                   ├─ SSVM이 template → primary 복사 (캐시 없으면)
                   ├─ root volume = template clone
                   └─ libvirt define + start
[7] cloud-init: VR이 169.254.169.254 통해 user-data/key 주입
[8] VM Running: state=Running 으로 update
```

→ 이 단계가 한 줄 명령어 뒤에서 일어난다. 어디서 막혔는지가 디버깅의 출발점.

---

## 10. 정리 (Cleanup)

```bash
# Static NAT 풀기
$ cmk disable staticnat ipaddressid=$PUBIPID

# Public IP 반환
$ cmk disassociate ipaddress id=$PUBIPID

# VM destroy
$ cmk destroy virtualmachine id=$VMID expunge=true

# Network 삭제 (VR 자동 정리)
$ cmk delete network id=$NETID

# 키 삭제 (선택)
$ cmk delete sshkeypair name=mykey
```

---

## 11. UI에서 같은 작업 비교

웹 UI가 더 익숙하면 같은 흐름을:

```
http://<VM-IP>:8080/client/

좌측: Compute → Instances → "Add Instance"
   → Template / Service Offering / Network 선택
   → SSH Key 선택
   → "Launch VM"
```

→ **CLI와 UI 같이 익히면 두 배로 빨리** 는다. Network Tab에서 "VR" 도 보고, SystemVM에서 SSVM/CPVM도 보기.

---

## 다음

→ [02-multi-tenant-network.md](./02-multi-tenant-network.md) — 두 Account 간 네트워크 격리 (생성 예정)
→ [../05-deep-dives/scheduler-allocator-internals.md](../05-deep-dives/scheduler-allocator-internals.md) — 위 단계 3의 내부 동작
→ [../05-deep-dives/virtual-router-internals.md](../05-deep-dives/virtual-router-internals.md) — 위 단계 5/6의 VR 동작

---

## 공식 문서 레퍼런스

- [Admin Guide — Working with Virtual Machines](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/working_with_vm.html)
- [Networking Guide — Configuring Networks](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html)
- [API: deployVirtualMachine](https://cloudstack.apache.org/api/apidocs-4.20/apis/deployVirtualMachine.html)
- [API: associateIpAddress](https://cloudstack.apache.org/api/apidocs-4.20/apis/associateIpAddress.html)
- [API: enableStaticNat](https://cloudstack.apache.org/api/apidocs-4.20/apis/enableStaticNat.html)
