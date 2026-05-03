# Upgrade Strategy — 메이저 / 마이너 업그레이드

> **MS와 Agent의 분리된 업그레이드 + DB schema 마이그레이션 + System VM template 교체.**

CloudStack은 OpenStack의 6개월 릴리스보다 느슨한 주기. 보통 **메이저 1년에 1회, 마이너 패치 분기마다**.

> 출처: [Admin Guide — Upgrade Instructions](https://docs.cloudstack.apache.org/en/latest/upgrading/) · [Release Notes](https://docs.cloudstack.apache.org/en/latest/releasenotes/).

---

## 1. 버전 정책

| 형태 | 예 | 빈도 |
|---|---|---|
| Major | 4.18, 4.19, 4.20 | 약 1년 |
| Minor (LTS) | 4.20.0, 4.20.1, 4.20.2 | 분기 |
| Hotfix | 4.20.0.1 | 보안/긴급 |

LTS = Long Term Support. 보통 **2개의 LTS만 동시 지원** (예: 4.19 + 4.20).

---

## 2. 업그레이드 경로 정책

[Admin Guide — Upgrade Instructions](https://docs.cloudstack.apache.org/en/latest/upgrading/) 의 매트릭스를 따른다. 주요 규칙:

- **건너뛰기 금지** (4.16 → 4.20 직접 X). 단계적: 4.16 → 4.17 → 4.18 → ... → 4.20
- **MS 먼저, Agent 나중**: MS는 신/구 Agent와 호환되도록 설계됨
- **DB 마이그레이션은 자동**: `cloudstack-setup-databases` 다시 실행하지 말 것 (그건 fresh install용)

---

## 3. 절차 — 정석 8단계

### Step 1. 전체 백업

```bash
# DB
$ mysqldump -u root -p \
    --routines --triggers --single-transaction \
    cloud cloud_usage > cloudstack-backup-$(date +%F).sql

# Secondary Storage 메타 (없어도 되긴 함)
$ tar -czf secondary-meta-$(date +%F).tar.gz /export/secondary

# 설정 파일
$ tar -czf cloudstack-conf-$(date +%F).tar.gz \
    /etc/cloudstack \
    /etc/mysql/conf.d/cloudstack.cnf
```

### Step 2. Maintenance 모드 + AsyncJob 비우기

```bash
# 새 작업 차단 (UI: Global Settings 또는)
$ cmk update configuration name=management.maintenance.mode value=true

# 진행 중 잡 끝까지 대기
$ cmk list asyncjobs status=in-progress
# 0 될 때까지 기다림 (수 분 ~ 수 시간)
```

### Step 3. MS 중지

```bash
$ systemctl stop cloudstack-management
$ systemctl stop cloudstack-usage
```

### Step 4. 패키지 업그레이드 (MS 노드)

```bash
# 새 저장소로 변경
$ vi /etc/apt/sources.list.d/cloudstack.list
# 예: 4.19 → 4.20
deb [signed-by=...] http://download.cloudstack.org/ubuntu jammy 4.20

$ apt update
$ apt install --only-upgrade cloudstack-management cloudstack-common
$ apt install --only-upgrade cloudstack-usage
```

→ DEB 패키지의 **post-install hook** 이 DB schema 마이그레이션 SQL을 실행한다.

### Step 5. MS 시작

```bash
$ systemctl start cloudstack-management
$ tail -f /var/log/cloudstack/management/management-server.log

# 정상 부팅 확인 (1~5분)
# "ManagementServer started"
```

### Step 6. System VM Template 등록 (★ 메이저 업그레이드 시)

새 메이저 버전은 보통 **새 System VM Template** 동반.

```bash
$ /usr/share/cloudstack-common/scripts/storage/secondary/cloud-install-sys-tmplt \
    -m /mnt/secondary \
    -u http://download.cloudstack.org/systemvm/4.20/systemvmtemplate-4.20.0-aarch64-kvm.qcow2.bz2 \
    -h kvm \
    -F
```

UI에서 모든 System VM (SSVM/CPVM/VR) 을 **새 template으로 재기동**:

```bash
# UI: Infrastructure → System VMs → Destroy (자동 재생성)
# 또는
$ cmk destroy systemvm id=<...>     # SSVM/CPVM
$ cmk destroy router id=<...>        # 모든 VR
```

→ **VR 재기동 시 게스트망 잠깐 끊김** 주의 (Redundant VR 있으면 1~3초).

### Step 7. Agent 업그레이드 (Hypervisor Host)

```bash
# 각 KVM Host에서
$ apt update
$ apt install --only-upgrade cloudstack-agent cloudstack-common
$ systemctl restart cloudstack-agent
```

**MS는 신/구 Agent와 호환** → 한 노드씩 천천히. Agent 재시작 시 그 호스트의 VM은 영향 없음 (running VM은 libvirt가 들고 있음).

### Step 8. Maintenance 해제 + 검증

```bash
$ cmk update configuration name=management.maintenance.mode value=false

# 검증
$ cmk list zones
$ cmk list hosts state=Up
$ cmk list systemvms state=Running

# 새 VM 1개 띄워보기 (smoke test)
```

---

## 4. 흔한 함정

### 🔴 메이저 건너뛰기

```
4.16 → 4.20 직접 X
4.16 → 4.17 → 4.18 → 4.19 → 4.20  ✅
```

이유: DB schema 마이그레이션이 **단계별**로 작성됨. 건너뛰면 중간 단계 SQL을 못 만남.

### 🔴 Java 버전 mismatch

```
4.16: Java 8
4.17~4.19: Java 11
4.20+: Java 17
```

업그레이드 전 호스트의 Java 버전 확인 + 업그레이드.

```bash
$ apt install -y openjdk-17-jre-headless
$ update-alternatives --config java
```

### 🔴 System VM Template 누락

새 SystemVM template 안 등록하고 VR/SSVM 재기동 시도 → **부팅 실패 → 게스트망 마비**.

순서 엄격히: **template 등록 → 그 다음 destroy → 자동 재생성**.

### 🔴 DB schema 충돌

```
cloudstack-setup-databases 를 업그레이드 후 또 실행 → DB 깨짐
```

→ 업그레이드 시 **절대 cloudstack-setup-databases 실행 금지**. 패키지가 알아서 마이그레이션.

### 🔴 Multi-MS 환경

```
[LB] ── MS-1 (구버전) , MS-2 (신버전)
```

업그레이드 도중 양쪽이 다른 버전이면 DB 락 충돌. **모든 MS 동시 중지 → 한 곳에서 업그레이드 → 마이그레이션 끝나면 다른 노드도 업그레이드 → 동시 시작**.

---

## 5. 롤백 — 어렵다

CloudStack은 **공식 다운그레이드 미지원**. DB schema가 forward-only.

비상시 롤백:
```
1. MS 중지
2. DB 백업본으로 복원
3. 패키지 다운그레이드 (apt install cloudstack-management=4.19.x-1)
4. System VM Template 도 이전 버전으로
```

→ 운영 환경에서는 **롤백 시도 전에 베이스 스냅샷** 필수.

---

## 6. 마이너 / Hotfix 업그레이드

훨씬 간단:

```bash
# MS 노드
$ systemctl stop cloudstack-management
$ apt install --only-upgrade cloudstack-management cloudstack-common
$ systemctl start cloudstack-management

# 보통 System VM template 교체 불필요 (마이너는 호환 보장)
```

---

## 7. 권장 빈도

| | 빈도 |
|---|---|
| 마이너 LTS | 분기마다 |
| 보안 hotfix | 즉시 (CVE 발표 시) |
| 메이저 | 1~2 주기 마다 (= 1~2년) |
| Java 보안 패치 | 매월 |
| OS 패치 | 매월 |

---

## 8. OpenStack 업그레이드와 비교

| | OpenStack | CloudStack |
|---|---|---|
| 빈도 | 6개월 (Antelope, Bobcat, ...) | 1년 (4.19, 4.20, ...) |
| 컴포넌트 | 30+ 프로젝트 각자 | MS 1개 + Agent |
| DB | 서비스별 마이그레이션 | 단일 DB 마이그레이션 |
| 도구 | OSA / Kolla / TripleO | apt / yum 패키지 |
| 롤백 | 일부 가능 | 사실상 X |

→ CloudStack 업그레이드는 **단순하지만 forward-only**. OpenStack은 복잡하지만 일부 롤백 가능.

---

## 다음

→ [troubleshooting.md](./troubleshooting.md): 업그레이드 후 문제 진단.
→ [monitoring.md](./monitoring.md): 업그레이드 직후 알람 모니터링.

---

## 공식 문서 레퍼런스

- [Apache CloudStack — Upgrading Instructions](https://docs.cloudstack.apache.org/en/latest/upgrading/)
- [Release Notes](https://docs.cloudstack.apache.org/en/latest/releasenotes/)
- [Java Version Requirements](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/index.html)
- [Upgrading System VM Templates](https://docs.cloudstack.apache.org/en/latest/upgrading/upgrade/upgrade-4.20.html)
