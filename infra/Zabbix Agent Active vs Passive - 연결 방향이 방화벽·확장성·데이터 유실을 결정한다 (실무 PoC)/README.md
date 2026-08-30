# Zabbix agent active vs passive PoC

Zabbix 7.0.30 한 벌과 성격이 다른 에이전트 4대를 띄워서, **연결 방향 하나가 무엇을 바꾸는지**를 실제 history 데이터로 확인한다.

```text
A. inbound 가 막힌 호스트  →  passive 0건 / active 60여 건
B. 중앙 서버 60초 부재      →  passive 구멍 70초 / active 되채움 (최대 공백 5~6초, clock 오차 0초)
C. 단절 중 에이전트 재시작  →  메모리 버퍼 소실 / 디스크 버퍼 생존, 단 재시작 이후 구간은 양쪽 다 0건
```

## 실행

필요한 것은 Docker Desktop과 Python 3뿐이다(추가 패키지 없음).

```bash
cd "infra/Zabbix Agent Active vs Passive - 연결 방향이 방화벽·확장성·데이터 유실을 결정한다 (실무 PoC)"
./run.sh
```

기동에 1~2분, 검증에 약 6분 걸린다(기준 수집 45초 + 60초 단절 시나리오 2회 + 각 65초 정착 대기).

성공하면 이렇게 끝난다.

```text
[15:52:34] 시나리오 A. inbound 차단 호스트에서 어느 쪽이 살아남는가
  [PASS] inbound 차단 시 passive 아이템: 45초 동안 수집값 0건 (기대: 0건)
  [PASS] inbound 차단 시 active 아이템: 45초 동안 수집값 7건 (기대: 5건 이상)
  [PASS] inbound 차단 호스트의 agent 인터페이스 상태: available=2 (2 = unavailable 기대)

[15:53:19] 시나리오 B. 서버가 사라진 구간을 누가 되채우는가 (재시작 없음)
  [PASS] passive: 단절 구간 수집값: 0건 (기대: 0건, 최대 공백 56초)
  [PASS] active + 메모리 버퍼: 단절 구간 되채움: 12건 / 기대 약 12건, 최대 공백 5초
  [PASS] active + 메모리 버퍼: 되채운 값의 타임스탬프: 수집시각과 저장 clock 최대 오차 0초
  [PASS] active + 디스크 버퍼: 단절 구간 되채움: 12건 / 기대 약 12건, 최대 공백 5초
  [PASS] active + 디스크 버퍼: 되채운 값의 타임스탬프: 수집시각과 저장 clock 최대 오차 0초

[15:55:25] 시나리오 C. 단절 중 에이전트가 재시작되면 버퍼는 어떻게 되는가
  [PASS] 메모리 버퍼: 재시작 전 수집분: 0건 남음
  [PASS] 디스크 영속 버퍼: 재시작 전 수집분: 5건 남음
  [PASS] 영속 버퍼가 지켜주지 않는 것: 재시작 이후 구간: 0건

===== 11/11 검증 통과 =====
```

## 구성

| 컨테이너 | 역할 | 핵심 설정 |
| --- | --- | --- |
| `zbxpoc-db` | PostgreSQL 16 | history 조회 대상 |
| `zbxpoc-server` | Zabbix server 7.0 | 단절 재현을 위해 stop/start 시킨다 |
| `zbxpoc-web` | 프론트엔드 | 호스트/아이템 API 프로비저닝용 (<http://localhost:8080>, Admin / zabbix) |
| `zbxpoc-agent-passive` | passive 전용 | `Server=` 만 설정, `ServerActive` 없음 |
| `zbxpoc-agent-active-mem` | active + 메모리 버퍼 | `EnablePersistentBuffer=0` |
| `zbxpoc-agent-active-disk` | active + 디스크 버퍼 | `EnablePersistentBuffer=1`, SQLite |
| `zbxpoc-agent-inbound-blocked` | inbound 차단 재현 | `ListenIP=127.0.0.1` (서버가 접속 불가) |

에이전트 설정은 [conf/](conf/) 안에 그대로 들어 있고, 컨테이너에 read-only로 마운트된다.

측정 아이템은 전부 `system.localtime`(`delay=5s`)이다. **값 자체가 수집 시각(epoch)** 이라, history의 `clock`과 비교하면 "언제 수집했는지"와 "언제 저장했는지"를 동시에 볼 수 있다.

> 서버 설정 중 `UnreachablePeriod=15` / `UnreachableDelay=5` / `UnavailableDelay=10` / `CacheUpdateFrequency=10` 은 실험 회전을 빠르게 하려고 기본값(45 / 15 / 60 / 10)보다 줄인 값이다. 프로덕션 권장값이 아니다.

## 직접 확인해 보기

```bash
# inbound 차단 에이전트는 10050 을 루프백에만 열어 뒀다 (0100007F = 127.0.0.1, 2742 = 10050)
docker exec zbxpoc-agent-inbound-blocked cat /proc/net/tcp

# 영속 버퍼 파일은 disk 에이전트에만 있다
docker exec zbxpoc-agent-active-disk ls -l /tmp/
docker exec zbxpoc-agent-active-mem  ls -l /tmp/

# 버퍼링/flush 로그
docker logs zbxpoc-agent-active-disk 2>&1 | grep "history upload"

# 호스트별 누적 수집값
docker exec zbxpoc-db psql -U zabbix -d zabbix -c "
SELECT h.host, i.key_, i.type, count(hu.clock) AS values
FROM items i JOIN hosts h ON h.hostid=i.hostid
LEFT JOIN history_uint hu ON hu.itemid=i.itemid
WHERE h.host LIKE 'poc-%' GROUP BY 1,2,3 ORDER BY 1;"
```

## 정리

```bash
./run.sh down
```
