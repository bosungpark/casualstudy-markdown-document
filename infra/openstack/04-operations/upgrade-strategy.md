# Upgrade Strategy — OpenStack 버전 올리기

> **"올해 Caracal에서 내년 Dalmatian으로. VM 안 죽이고 어떻게?"**

OpenStack 업그레이드의 핵심은 **컨트롤 평면을 먼저 올리고, 데이터 평면(컴퓨트)은 나중에 천천히**.

---

## 한 줄 요약

```
DB 백업 → 컨트롤러(API/Scheduler) 업그레이드 → 컴퓨트 노드 롤링 업그레이드
              ↑                                       ↑
          짧은 다운타임                       VM은 살아있음 (live-migration)
```

올바르게 하면 **VM은 단 한 번도 안 꺼진다**. 잘못하면 컨트롤 평면 다운 + DB 마이그레이션 실패로 며칠을 잃음.

---

## 릴리스 모델

OpenStack은 **반기 릴리스(Spring/Fall)**, 알파벳 순 코드네임.

```
2023.1 Antelope (SLURP)  ← LTS-ish, 2년 지원
2023.2 Bobcat
2024.1 Caracal   (SLURP)  ← LTS-ish
2024.2 Dalmatian
2025.1 Epoxy     (SLURP)
2025.2 Flamingo
2026.1 (다음 SLURP)
...
```

| 모드 | 의미 |
|---|---|
| **6-month release** | 매 반기. 최신 기능, 짧은 지원 |
| **SLURP** (Skip-Level Upgrade Release Process) | 1년 단위로 **두 버전 한 번에 점프** 가능 (예: 2024.1 → 2025.1) |

> 💡 운영팀은 **SLURP 릴리스만 따라가는 것**이 일반적. 매 반기 업그레이드는 부담이 너무 크다.

---

## 업그레이드의 3대 원칙

### 1. N → N+1 만 (한 번에 한 단계)

`2024.1 → 2024.2 → 2025.1` 처럼 **한 단계씩**. SLURP를 쓰면 `2024.1 → 2025.1` 점프 가능하지만, 그것도 정의된 한 점프일 뿐 임의 점프 아님.

### 2. 컨트롤 → 컴퓨트 순서

```
[컨트롤러: API/Scheduler/Conductor]    먼저 N+1
                ↓
[컴퓨트: nova-compute/neutron-agent]   천천히 N+1
                ↓
[모두 N+1 일치 후 → DB online migration 마무리]
```

이게 가능한 이유: OpenStack은 **N과 N+1 컴퓨트의 RPC를 한 릴리스 동안 호환** 보장.

### 3. 데이터베이스는 두 단계

- **expand** (스키마 추가) — 호환되는 변경. 다운타임 없음
- **contract** (스키마 정리) — 호환 깨짐 가능. 모든 노드가 N+1 된 후 실행

```
N 운영 중 → expand 마이그레이션 (컬럼 추가)
   ↓
N+1 코드 배포 (양쪽 컬럼 다 다룸)
   ↓
모두 N+1 완료
   ↓
contract 마이그레이션 (구 컬럼 삭제)
```

---

## 표준 업그레이드 절차 (서비스 1개 기준)

```
1. ★ 백업 ★
     ├─ DB 덤프 (nova, neutron, cinder, keystone, glance, placement…)
     └─ /etc/<서비스>/ 설정 디렉토리

2. 패키지/이미지 업그레이드 준비 (운영 영향 없음)

3. 서비스 정지 (API/Scheduler/Conductor만 — 1~5분)

4. DB expand 마이그레이션
     $ <서비스>-manage db sync
     $ <서비스>-manage db expand          # 일부 서비스
     $ <서비스>-manage api_db sync

5. 새 패키지 기동 (API/Scheduler/Conductor)

6. 컴퓨트/에이전트 노드 롤링 업그레이드
     호스트 1대씩:
       a) live-migration 으로 VM 비우기
       b) nova-compute / neutron-agent 패키지 교체
       c) 다시 enable, VM 받기

7. 모두 N+1 도달 확인 후 contract
     $ <서비스>-manage db contract        # 또는 db online_data_migrations

8. 스모크 테스트 (VM 만들기, 볼륨 붙이기, FIP)
```

---

## Kolla-Ansible 업그레이드 (가장 흔한 운영 형태)

### 흐름

```bash
# 1. 새 릴리스 브랜치로 체크아웃
$ cd kolla-ansible
$ git fetch && git checkout stable/2025.1

# 2. 새 globals.yml 키 머지 (보통 minor 한두 개)
$ diff -u etc/kolla/globals.yml.sample /etc/kolla/globals.yml

# 3. 컨테이너 이미지 가져오기
$ kolla-ansible -i multinode pull

# 4. 사전 검증
$ kolla-ansible -i multinode prechecks

# 5. 업그레이드 (컨트롤 → 컴퓨트 자동 순서)
$ kolla-ansible -i multinode upgrade

# 6. 사후 점검
$ kolla-ansible -i multinode check
```

### 주의

- `pull` 단계에서 디스크 부족 자주 발생. `/var/lib/docker` 100GB+ 권장
- **VM live-migration은 자동 안 함**. `--limit` 으로 노드 단위 진행, 각 노드 비우는 건 운영자 책임
- 큰 점프(SLURP)는 **Ansible 모듈/플레이북 변수도 같이 바뀜** — release notes 필독

---

## DevStack 업그레이드?

**없다.** DevStack은 매번 새로 깐다.

```bash
$ ./unstack.sh && ./clean.sh
$ git fetch && git checkout stable/2025.1
$ ./stack.sh
```

학습 환경이니 **데이터/VM은 다 날아간다**. 보존하려면 외부 디스크에 cinder 볼륨이나 glance 이미지를 미리 export.

---

## Fast-Forward Upgrade (FFU)

여러 릴리스를 빠르게 점프하는 방법. 예: 2022.1 → 2024.1 (4단계 건너뛰기).

```
N → N+1 → N+2 → N+3 → N+4
   ↑          ↑          ↑
서비스 한 번도 안 시작
컨트롤만 패키지 갈고 DB 마이그레이션만
마지막 N+4 에서 진짜로 기동
```

장점: 컨트롤 평면 다운타임이 한 번으로 압축.
단점: **무지 위험**. 각 단계 마이그레이션이 누적, 실패하면 어느 단계인지 추적 어려움.

> 💡 가능하면 SLURP 한 점프(2단계)까지만. FFU는 정말 어쩔 수 없을 때.

---

## 의존 외부 시스템

업그레이드는 OpenStack만의 일이 아님.

| 컴포넌트 | 영향 |
|---|---|
| **MariaDB / Galera** | 메이저 버전 점프(10.4→10.6) 시 별도 절차. 보통 OS 업그레이드와 동행 |
| **RabbitMQ** | 메이저 점프(3.x→4.x)는 cluster wipe 권고 — 클러스터 형태 변경 |
| **OVN / OVS** | 데이터베이스 스키마 마이그레이션 자동, 다만 OVN 메이저 버전과 OpenStack의 호환 매트릭스 확인 |
| **Ceph** | OpenStack 호환은 보통 넓음. Ceph 자체 업그레이드 절차로 진행 |
| **OS (Ubuntu 22→24, RHEL 9→10)** | Python 버전, libvirt 버전 함께 바뀜 — OpenStack 매트릭스 재확인 필요 |

---

## 호환성 빠르게 확인하는 곳

- **Releases page**: https://releases.openstack.org/ — 각 릴리스의 지원 종료일
- **Project release notes**: 각 서비스 docs의 "Upgrade Notes" 섹션
- **Kolla-Ansible release notes**: `releasenotes/notes/` 디렉토리

> 외부 의존 매트릭스(Python/MySQL/RabbitMQ/libvirt)는 각 서비스 `setup.cfg` 와 `requirements.txt` 가 진실의 원천.

---

## 업그레이드 전 체크리스트

```
[ ] 모든 DB 백업 + 복구 테스트(중요)
[ ] /etc 디렉토리 설정 백업
[ ] 현재 알람/모니터링 정상 상태로 기준선 확보
[ ] release notes 읽기 (특히 deprecated 옵션)
[ ] custom policy.yaml 호환 확인
[ ] 외부 인증(LDAP/SAML/OIDC) 연동 호환 확인
[ ] Ceph/RabbitMQ/MariaDB 호환 매트릭스 OK
[ ] 비프로덕션(staging)에서 동일 절차 1회 성공
[ ] Maintenance window 공지
[ ] 롤백 계획 수립 (DB 복구 + 패키지 다운그레이드)
```

---

## 자주 밟는 지뢰

- **`db sync` 가 시간이 오래 걸려 운영 시간 초과** — 큰 테이블(인스턴스 수십만)은 `online_data_migrations` 가 정답. 미리 백그라운드로 돌려 데이터를 옮겨놓고, expand만 다운타임에 수행
- **노바 컴퓨트 RPC 호환 깨짐** — 한 단계 점프 규칙 어김. 또는 `[upgrade_levels] compute=N` 강제로 묶어둔 걸 안 풀고 다음 점프 시작
- **Placement 마이그레이션 누락** — Pike+에서 분리된 후 자체 DB. 함께 sync 안 해서 nova가 자원 보고 못 함
- **policy.yaml 의 default 변경** — 새 릴리스에서 기본 RBAC가 바뀌어 종전 사용자 권한이 사라짐. 업그레이드 전 `oslopolicy-policy-generator` 로 비교
- **OVN northbound 스키마 점프** — OVN 메이저 변경 시 `ovn-nbctl --version` 호환 확인. 컨테이너 배포면 보통 자동
- **Ceilometer 파이프라인** — 메트릭 이름이 바뀌어 청구 시스템에서 누락. release notes 의 "metric renames" 확인

---

## 롤백 전략

OpenStack은 **DB 마이그레이션이 비가역**인 경우가 많아 롤백이 어렵다. 실용적 전략:

```
시나리오                      현실적 롤백
-----------------------       ---------------------------
컨트롤 패키지만 올림 직후    → 패키지 다운그레이드 + DB 복구
expand 마이그 후              → 진행이 정답. 멈추면 더 망함
컴퓨트 일부만 N+1            → 그 노드만 N으로 다운그레이드 가능
contract 후                    → 롤백 사실상 불가. 백업으로 신규 환경 구축
```

→ **expand 시점이 임계점**. 거기까지 가기 전 staging에서 충분히 검증.

---

## 추천 운영 패턴

1. **연 1회 SLURP 만 따라간다** — 매 반기 업그레이드는 인력 소모 큼
2. **staging은 production과 동일 토폴로지** — Galera 3대, RabbitMQ 3대, Ceph
3. **합성 트랜잭션 모니터를 업그레이드 동안 계속** — VM 1분마다 만들고 지우기, 끊김 시점 즉시 포착
4. **VM live-migration 가능하게 준비** — 공유 스토리지(Ceph) 또는 shared instances 디렉토리

---

## 다음

- 업그레이드 직후 점검 — [troubleshooting.md](./troubleshooting.md)
- 변경 후 메트릭 베이스라인 비교 — [monitoring-telemetry.md](./monitoring-telemetry.md)
- 학습 환경 멀티노드 만들기 — [../03-installation/](../03-installation/)
