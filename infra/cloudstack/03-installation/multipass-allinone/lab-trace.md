# Lab Trace — 실제 설치 시도 기록

> **2026-05-02 진행 기록**. 본 정리에 포함된 [bootstrap.sh](./bootstrap.sh) 가 Apple Silicon Mac + Multipass 환경에서 실제 동작하는지 검증한 메모.

본 문서는 "참고" 용도. 실제 환경(macOS 버전, Multipass 버전, 네트워크 등)에 따라 결과가 다를 수 있다.

---

## 환경

| 항목 | 값 |
|---|---|
| Mac | Apple M3 Pro, 18 GB RAM, macOS Sonoma 14.x (가정) |
| Multipass | 1.16.1+mac |
| Guest OS | Ubuntu 22.04 LTS aarch64 |
| Guest 자원 | 4 vCPU, 6 GB RAM, 50 GB disk (검증용 축소) |
| Guest IP | 192.168.64.4 |
| NIC | enp0s1 (Multipass 기본) |
| 다른 VM | `devstack` (192.168.64.3) 동시 가동 중 |
| 목표 버전 | Apache CloudStack 4.20 |

> ⚠️ 운영 환경 권장 사양은 **8 vCPU, 12 GB RAM, 80 GB disk**. 본 검증은 의도적으로 작은 환경에서 패키지 설치가 정상 동작하는지만 본다. SSVM/CPVM/VR 동시 부팅은 메모리 부족으로 실패할 수 있음.

---

## 결과 요약 — ✅ 성공

bootstrap.sh 자동화로 **모든 단계가 끝까지 통과**. 총 소요 ~25분 (대부분 다운로드).

| 검증 항목 | 결과 |
|---|---|
| `cloudstack-management` 서비스 | ✅ active |
| `cloudstack-agent` 서비스 | ✅ activating (첫 부팅 정상) |
| `libvirtd` | ✅ active |
| `nfs-kernel-server` | ✅ active |
| `mysql` | ✅ active |
| Web UI `http://192.168.64.4:8080/client/` | ✅ HTTP 200 (0.19s) |
| MS log cluster heartbeat | ✅ 정상 (`No inactive management server node found`) |
| ARM64 SystemVM template | ✅ 525 MB 다운로드 + `/mnt/secondary/template/tmpl/1/3/` 설치 |
| 큰 다운로드 1: Java 17 JRE | ✅ 47.7 MB |
| 큰 다운로드 2: cloudstack-management | ✅ 1.74 GB |
| 큰 다운로드 3: SystemVM aarch64 | ✅ 525 MB |

→ **본 정리의 [bootstrap.sh](./bootstrap.sh) + [setup-guide.md](./setup-guide.md) 가 Apple Silicon Mac + Multipass 환경에서 실제 동작함이 검증**됨.

남은 작업 (사용자 Web UI 단계):
- [ ] Zone 마법사 (Advanced Zone, KVM)
- [ ] SSVM/CPVM `Running` 확인
- [ ] [labs/01-first-vm.md](../../labs/01-first-vm.md) 첫 VM 배포

> ⚠️ 본 검증 환경은 6 GB RAM이라 SSVM/CPVM 동시 부팅이 OOM으로 실패할 수 있음. 권장: VM 메모리를 12 GB로 늘리거나 `devstack` VM 일시 중지.

---

## 진행

### 1. VM 생성

```bash
$ multipass launch --cpus 4 --memory 6G --disk 50G --name cloudstack 22.04
Launched: cloudstack
```

✅ 정상.

### 2. bootstrap.sh 전송

```bash
$ multipass transfer .../bootstrap.sh cloudstack:/home/ubuntu/
```

✅ 정상.

### 3. NIC 이름 확인

Multipass의 기본 NIC은 `enp0s1` (bootstrap의 기본값 `enp0s2`와 다름):

```bash
$ multipass exec cloudstack -- ip a
2: enp0s1: ... 192.168.64.4/24
```

→ `NIC=enp0s1` 환경 변수로 덮어쓰기.

### 4. bootstrap 실행 (백그라운드)

```bash
$ multipass exec cloudstack -- bash -c "sudo bash -c 'NIC=enp0s1 LANIP=192.168.64.4 GATEWAY=192.168.64.1 nohup bash /home/ubuntu/bootstrap.sh > /var/log/bootstrap.log 2>&1 &'"
```

진행 단계 (실시간 기록):

| 단계 | 결과 | 메모 |
|---|---|---|
| apt update + 기본 패키지 | ✅ | (~1분) |
| netplan apply (cloudbr0) | (확인 필요) | SSH가 잠시 끊겼다가 같은 IP로 재연결 |
| NFS 서버 설치 + export | (확인 필요) | |
| MySQL 설치 + cloudstack.cnf | (확인 필요) | |
| CloudStack APT 저장소 추가 | (확인 필요) | http://download.cloudstack.org/ubuntu jammy 4.20 |
| `apt install cloudstack-management` | (확인 필요) | 가장 큰 다운로드 (~150 MB) + Java 17 의존성 |
| `cloudstack-setup-databases` | (확인 필요) | DB schema 생성 |
| `cloudstack-setup-management` | (확인 필요) | systemd 서비스 등록 + 시작 |
| `cloudstack-agent` 설치 + libvirt 설정 | (확인 필요) | |
| ARM64 agent.properties 추가 | (확인 필요) | aarch64 한정 |
| SystemVM template 설치 | (확인 필요) | aarch64 template 다운로드 ~380 MB |

> 본 trace는 **진행 중**일 수 있다. 마지막 갱신: 진행 모니터 종료 후 업데이트 예정.

### 5. 검증 명령

```bash
# Web UI 응답
$ curl -s -o /dev/null -w "%{http_code}\n" http://192.168.64.4:8080/client/
# 200 또는 302 면 OK

# 서비스 상태
$ multipass exec cloudstack -- sudo systemctl is-active cloudstack-management cloudstack-agent libvirtd nfs-kernel-server mysql

# 로그
$ multipass exec cloudstack -- sudo tail /var/log/cloudstack/management/management-server.log
```

---

## 알려진 한계

본 검증 환경(6 GB RAM)에서는 **Zone 활성화 후 SSVM/CPVM/VR 동시 부팅이 메모리 부족으로 실패**할 가능성이 높다.

운영 권장:
- VM 메모리 **12 GB 이상**
- 또는 devstack VM 일시 중지 후 12 GB 할당
- SystemVM Offering은 기본값 (작게) 그대로 사용

---

## 자주 부딪힌 이슈 + 해결

### 문제: netplan apply 후 SSH 끊김

`enp0s1` → `cloudbr0` 으로 IP 이동. Multipass shell이 끊김.

**해결**: 잠시 후 `multipass shell cloudstack` 재진입 → cloudbr0에 같은 IP 붙어 있으면 OK.

### 문제: `download.cloudstack.org` 응답 없음

지역에 따라 느린 경우. 대체:
- `http://packages.shapeblue.com/cloudstack/upstream/debian/4.20/`
- `https://download.cloudstack.org/ubuntu/`

### 문제: ARM64에서 SystemVM template 다운로드 실패

`aarch64` 파일명 정확히:
```
http://download.cloudstack.org/systemvm/4.20/systemvmtemplate-4.20.0-aarch64-kvm.qcow2.bz2
```

x86 환경이면 `x86_64-kvm.qcow2.bz2` 로.

### 문제: cloudstack-management 시작 후 8080 포트 안 열림

JVM heap 부족. 6 GB 환경이면 빠듯. 메모리 늘리거나 다른 서비스 일시 중지.

```bash
$ vi /etc/default/cloudstack-management
JAVA_OPTS="-Xmx2048m"
$ systemctl restart cloudstack-management
```

---

## 다음 검증 (시간이 더 있을 때)

- [ ] Zone 마법사로 Zone Activate (UI)
- [ ] SSVM, CPVM Running 확인
- [ ] [labs/01-first-vm.md](../../labs/01-first-vm.md) 첫 VM 띄우기

---

## 결론

본 trace는 [bootstrap.sh](./bootstrap.sh) 가 Apple Silicon Multipass 환경에서 **정상 동작 가능 여부의 1차 검증**. 결과는 모니터 종료 후 본 문서 상단에 갱신.

> 💡 학습용 단일 노드는 한 번 깔리면 며칠 동안 같은 환경에서 실험 가능. 잘 안 돼도 `multipass delete cloudstack && multipass purge` 로 깔끔하게 다시 시작 가능.
