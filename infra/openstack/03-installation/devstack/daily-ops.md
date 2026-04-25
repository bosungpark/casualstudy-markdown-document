# DevStack 일상 운영

> **"설치는 했는데, 매일 어떻게 켜고 끄고 정리하지?"** 에 답하는 짧은 문서.

[setup-guide.md](./setup-guide.md) 로 띄운 후의 **일상 명령어 모음**. DevStack은 학습 환경이라 운영 패턴이 단순하다.

---

## 하루를 시작/끝낼 때

### 켜기 (재부팅 안 한 경우)

DevStack은 systemd 유닛으로 도니까 재부팅만 안 했다면 그냥 살아있다.

```bash
# 상태 확인
$ sudo systemctl list-units 'devstack@*' --state=failed
$ openstack service list

# 환경변수 로드
$ cd ~/devstack
$ source openrc admin admin
```

### 끄기 (잠깐 떠나기)

VM 자체를 **suspend/snapshot** 하는 게 가장 안전. DevStack 안의 OpenStack 서비스를 일일이 끄면 다시 일관성 맞추기 어렵다.

```bash
# Multipass 예시
$ multipass suspend devstack-vm

# VirtualBox/UTM
GUI에서 "Save State"
```

### 끄기 (당분간 안 쓸 때)

```bash
$ cd ~/devstack
$ ./unstack.sh   # 서비스 정지 (DB/볼륨은 살림)
```

---

## 서비스 개별 제어

DevStack의 모든 서비스는 `devstack@<이름>.service` 패턴.

```bash
$ sudo systemctl list-units 'devstack@*'
devstack@n-api.service     nova-api
devstack@n-cpu.service     nova-compute
devstack@n-cond.service    nova-conductor
devstack@n-sch.service     nova-scheduler
devstack@q-svc.service     neutron-server
devstack@g-api.service     glance-api
devstack@c-api.service     cinder-api
devstack@c-vol.service     cinder-volume
devstack@keystone.service
devstack@placement-api.service

# 재시작
$ sudo systemctl restart devstack@n-cpu

# 로그 보기
$ sudo journalctl -u devstack@n-cpu -f
```

---

## 설정 바꾸기

DevStack은 **소스 기반**이라 진짜 설정은 `/etc/<서비스>/<서비스>.conf` 에 있다.

```bash
$ ls /etc/nova/
nova.conf  policy.yaml  ...

# 디버그 로그 켜기
$ sudo vi /etc/nova/nova.conf
[DEFAULT]
debug = True

# 반영
$ sudo systemctl restart devstack@n-cpu
```

> ⚠️ `local.conf` 만 바꾸고 `./stack.sh` 재실행하면 위 변경이 **덮어써질 수 있다**. 영구 반영하려면 `local.conf` 쪽에 옵션을 넣어야 함.

---

## 자주 쓰는 명령 모음

```bash
# 클라우드 전반
$ openstack service list              # 서비스 목록
$ openstack endpoint list             # API URL
$ openstack hypervisor list           # 컴퓨트 노드
$ openstack compute service list      # nova 에이전트들
$ openstack network agent list        # neutron 에이전트들

# 자원
$ openstack server list --all-projects
$ openstack volume list --all-projects
$ openstack image list
$ openstack network list
$ openstack floating ip list

# 정리 (학습 끝나고 비우기)
$ openstack server delete $(openstack server list -f value -c ID)
$ openstack volume delete $(openstack volume list -f value -c ID)
```

---

## 디스크 정리

DevStack 학습하다 보면 디스크가 빨리 찬다.

```bash
$ df -h /opt/stack /var/lib

# Glance 이미지 캐시
$ sudo du -sh /opt/stack/data/glance/images/
$ openstack image list             # 안 쓰는 이미지 삭제

# Cinder LVM (loop 파일)
$ sudo du -sh /opt/stack/data/stack-volumes-default-backing-file
$ sudo vgs

# Nova 인스턴스 디스크
$ sudo du -sh /opt/stack/data/nova/instances/

# 로그
$ sudo du -sh /opt/stack/logs/
$ sudo find /opt/stack/logs -name '*.log.*' -delete   # 회전된 로그
```

진짜 안 되면 `./clean.sh` 가 모든 데이터를 날린다.

---

## 다시 깔기 (가장 확실한 회복)

```bash
$ cd ~/devstack
$ ./unstack.sh
$ ./clean.sh
$ ./stack.sh
```

설정 바꿀 때, 망가졌을 때, 새 릴리스 시도할 때 모두 이 흐름.

릴리스 변경:

```bash
$ git fetch
$ git checkout stable/2025.1   # 또는 master
$ ./stack.sh
```

---

## 새 사용자/프로젝트 만들기 (실습용)

```bash
$ source openrc admin admin

$ openstack project create --domain Default tenant-a
$ openstack user create --domain Default --password user-a-pass user-a
$ openstack role add --project tenant-a --user user-a member

# user-a 로 전환
$ source openrc user-a tenant-a   # 비번 입력
```

---

## 백업/이식 (학습 환경에서)

DevStack 자체는 백업을 가정하지 않는다. 그래도:

```bash
# 이미지 export
$ openstack image save --file ubuntu.qcow2 ubuntu-2204

# 인스턴스 → 이미지화 (스냅샷)
$ openstack server image create my-vm --name my-vm-snap

# DB 덤프 (학습 목적, 복구 보장 X)
$ mysqldump -u root --all-databases > /tmp/devstack-db.sql
```

운영 환경 백업은 [../../04-operations/upgrade-strategy.md](../../04-operations/upgrade-strategy.md) 의 백업 절차를 참고.

---

## 다음

- 디버깅 패턴 → [../../04-operations/troubleshooting.md](../../04-operations/troubleshooting.md)
- 메트릭/알림 붙여보기 → [../../04-operations/monitoring-telemetry.md](../../04-operations/monitoring-telemetry.md)
- 멀티노드 경험 → [../kolla-ansible/](../kolla-ansible/)
