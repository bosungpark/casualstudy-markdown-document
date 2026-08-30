#!/usr/bin/env python3
"""Zabbix agent active/passive PoC 검증 스크립트.

세 가지를 실제 데이터로 확인한다.

  A. inbound 가 막힌 호스트에서 passive 는 죽고 active 만 산다 (연결 방향)
  B. 중앙 서버가 사라진 구간에서 passive 는 구멍이 나고 active 는 되채운다 (버퍼)
  C. 그 되채움이 메모리 버퍼인지 디스크 버퍼인지에 따라 에이전트 재시작 생존이 갈린다

표준 라이브러리만 사용한다.
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "http://localhost:8080/api_jsonrpc.php"
USER = "Admin"
PASSWORD = "zabbix"

DB = "zbxpoc-db"
SERVER = "zbxpoc-server"

GROUP = "ZbxPoC"
ITEM_DELAY = "5s"
DELAY_SEC = 5

BASELINE_WAIT = 45
OUTAGE = 60
RESTART_AT = 25
SETTLE = 65

# host name -> (interface dns 또는 None, [(item key, item type)])
# item type: 0 = Zabbix agent (passive), 7 = Zabbix agent (active)
HOSTS = {
    "poc-passive": ("zbxpoc-agent-passive", [("system.localtime", 0)]),
    "poc-active-mem": (None, [("system.localtime", 7)]),
    "poc-active-disk": (None, [("system.localtime", 7)]),
    "poc-inbound-blocked": (
        "zbxpoc-agent-inbound-blocked",
        [("system.localtime[utc]", 0), ("system.localtime", 7)],
    ),
}

_token = None
_results = []


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def record(ok, title, detail):
    _results.append((ok, title, detail))
    print(f"  {'[PASS]' if ok else '[FAIL]'} {title}: {detail}", flush=True)


# --------------------------------------------------------------------------
# Zabbix API
# --------------------------------------------------------------------------
def api(method, params, auth=True):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json-rpc"},
    )
    if auth and _token:
        req.add_header("Authorization", f"Bearer {_token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if "error" in body:
        raise RuntimeError(f"{method} 실패: {body['error']}")
    return body["result"]


def wait_for_api(timeout=300):
    log("프론트엔드 API 를 기다리는 중...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            version = api("apiinfo.version", {}, auth=False)
            log(f"API 준비 완료 (Zabbix {version})")
            return version
        except (urllib.error.URLError, OSError, RuntimeError, json.JSONDecodeError):
            time.sleep(3)
    raise SystemExit("프론트엔드 API 가 시간 안에 뜨지 않았다")


def login():
    global _token
    _token = api("user.login", {"username": USER, "password": PASSWORD}, auth=False)


# --------------------------------------------------------------------------
# 프로비저닝
# --------------------------------------------------------------------------
def provision():
    log("호스트와 아이템을 API 로 생성한다")

    stale = api("host.get", {"filter": {"host": list(HOSTS)}, "output": ["hostid"]})
    if stale:
        api("host.delete", [h["hostid"] for h in stale])

    groups = api("hostgroup.get", {"filter": {"name": GROUP}, "output": ["groupid"]})
    groupid = groups[0]["groupid"] if groups else api("hostgroup.create", {"name": GROUP})["groupids"][0]

    itemids = {}
    for host, (dns, items) in HOSTS.items():
        params = {"host": host, "groups": [{"groupid": groupid}]}
        if dns:
            params["interfaces"] = [
                {"type": 1, "main": 1, "useip": 0, "ip": "", "dns": dns, "port": "10050"}
            ]
        hostid = api("host.create", params)["hostids"][0]

        interfaceid = None
        if dns:
            interfaceid = api(
                "hostinterface.get", {"hostids": hostid, "output": ["interfaceid"]}
            )[0]["interfaceid"]

        for key, itype in items:
            item = {
                "hostid": hostid,
                "name": key,
                "key_": key,
                "type": itype,
                "value_type": 3,  # numeric unsigned
                "delay": ITEM_DELAY,
                "history": "7d",
            }
            if itype == 0:
                item["interfaceid"] = interfaceid
            itemids[(host, key)] = api("item.create", item)["itemids"][0]

    docker("exec", SERVER, "zabbix_server", "-R", "config_cache_reload")
    log(f"아이템 {len(itemids)}개 생성, 서버 설정 캐시 리로드 완료")
    return itemids


# --------------------------------------------------------------------------
# docker / DB 헬퍼
# --------------------------------------------------------------------------
def docker(*args, check=True):
    proc = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=120
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)} 실패: {proc.stderr.strip()}")
    return proc.stdout.strip()


def query(sql):
    out = docker("exec", DB, "psql", "-U", "zabbix", "-d", "zabbix", "-tAF,", "-c", sql)
    return [line.split(",") for line in out.splitlines() if line]


def samples(itemid, start, end):
    """[start, end] 구간의 (clock, value) 목록. clock 오름차순."""
    rows = query(
        f"SELECT clock, value FROM history_uint "
        f"WHERE itemid={itemid} AND clock >= {int(start)} AND clock <= {int(end)} "
        f"ORDER BY clock"
    )
    return [(int(c), int(v)) for c, v in rows]


def max_gap(clocks, start, end):
    """구간 경계까지 포함한 최대 공백(초)."""
    points = [int(start), *clocks, int(end)]
    return max(b - a for a, b in zip(points, points[1:]))


# --------------------------------------------------------------------------
# 시나리오
# --------------------------------------------------------------------------
def scenario_a(itemids):
    print()
    log("시나리오 A. inbound 차단 호스트에서 어느 쪽이 살아남는가")
    start = int(time.time())
    time.sleep(BASELINE_WAIT)
    end = int(time.time())

    passive = samples(itemids[("poc-inbound-blocked", "system.localtime[utc]")], start, end)
    active = samples(itemids[("poc-inbound-blocked", "system.localtime")], start, end)

    record(
        len(passive) == 0,
        "inbound 차단 시 passive 아이템",
        f"{BASELINE_WAIT}초 동안 수집값 {len(passive)}건 (기대: 0건)",
    )
    record(
        len(active) >= BASELINE_WAIT // DELAY_SEC // 2,
        "inbound 차단 시 active 아이템",
        f"{BASELINE_WAIT}초 동안 수집값 {len(active)}건 (기대: 5건 이상)",
    )

    avail = query(
        "SELECT available FROM interface i JOIN hosts h ON h.hostid=i.hostid "
        "WHERE h.host='poc-inbound-blocked'"
    )
    # 1 = available, 2 = unavailable
    record(
        avail and avail[0][0] == "2",
        "inbound 차단 호스트의 agent 인터페이스 상태",
        f"available={avail[0][0] if avail else 'N/A'} (2 = unavailable 기대)",
    )
    return end


def outage(restart_agents):
    """중앙 서버를 OUTAGE 초 동안 내린다. 필요하면 도중에 에이전트를 재시작한다."""
    docker("stop", SERVER)
    down_at = int(time.time())
    log(f"  서버 정지 (t={down_at})")

    if restart_agents:
        time.sleep(RESTART_AT)
        for name in restart_agents:
            docker("restart", name)
        log(f"  단절 {RESTART_AT}초 시점에 {', '.join(restart_agents)} 재시작")
        time.sleep(OUTAGE - RESTART_AT)
    else:
        time.sleep(OUTAGE)

    up_at = int(time.time())
    docker("start", SERVER)
    log(f"  서버 기동 (t={up_at}), 정착 대기 {SETTLE}초")
    time.sleep(SETTLE)
    return down_at, up_at


def scenario_b(itemids):
    print()
    log("시나리오 B. 서버가 사라진 구간을 누가 되채우는가 (재시작 없음)")
    down_at, up_at = outage(restart_agents=None)
    expected = (up_at - down_at) // DELAY_SEC

    for host, label in [
        ("poc-passive", "passive"),
        ("poc-active-mem", "active + 메모리 버퍼"),
        ("poc-active-disk", "active + 디스크 버퍼"),
    ]:
        rows = samples(itemids[(host, "system.localtime")], down_at + 2, up_at - 2)
        clocks = [c for c, _ in rows]
        gap = max_gap(clocks, down_at + 2, up_at - 2)
        if host == "poc-passive":
            record(
                len(rows) == 0,
                f"{label}: 단절 구간 수집값",
                f"{len(rows)}건 (기대: 0건, 최대 공백 {gap}초)",
            )
        else:
            record(
                len(rows) >= expected * 0.7,
                f"{label}: 단절 구간 되채움",
                f"{len(rows)}건 / 기대 약 {expected}건, 최대 공백 {gap}초",
            )
            drift = [abs(v - c) for c, v in rows]
            record(
                bool(drift) and max(drift) <= 3,
                f"{label}: 되채운 값의 타임스탬프",
                f"수집시각과 저장 clock 최대 오차 {max(drift) if drift else 'N/A'}초 "
                f"(서버 도착시각이 아니라 원래 수집시각으로 저장)",
            )
    return down_at, up_at


def scenario_c(itemids):
    print()
    log("시나리오 C. 단절 중 에이전트가 재시작되면 버퍼는 어떻게 되는가")
    down_at, up_at = outage(
        restart_agents=["zbxpoc-agent-active-mem", "zbxpoc-agent-active-disk"]
    )
    # 재시작 이전에 이미 수집해 둔 값이 살아남았는가
    pre_start, pre_end = down_at + 2, down_at + RESTART_AT - 3

    mem = samples(itemids[("poc-active-mem", "system.localtime")], pre_start, pre_end)
    disk = samples(itemids[("poc-active-disk", "system.localtime")], pre_start, pre_end)

    record(
        len(mem) == 0,
        "메모리 버퍼: 재시작 전 수집분",
        f"{len(mem)}건 남음 (기대: 0건 - 프로세스와 함께 소실)",
    )
    record(
        len(disk) >= 2,
        "디스크 영속 버퍼: 재시작 전 수집분",
        f"{len(disk)}건 남음 (기대: 2건 이상 - SQLite 에서 복구)",
    )

    # 재시작 이후 구간은 양쪽 모두 비어야 한다: 설정을 못 받아 수집 자체를 못 한다
    post_start, post_end = down_at + RESTART_AT + 3, up_at - 2
    post_disk = samples(itemids[("poc-active-disk", "system.localtime")], post_start, post_end)
    record(
        len(post_disk) == 0,
        "영속 버퍼가 지켜주지 않는 것: 재시작 이후 구간",
        f"{len(post_disk)}건 (기대: 0건 - 버퍼는 수집분을 지키지 서버 없는 동안의 "
        f"설정까지 지켜주지 않는다)",
    )


# --------------------------------------------------------------------------
def main():
    wait_for_api()
    login()
    itemids = provision()

    scenario_a(itemids)
    scenario_b(itemids)
    scenario_c(itemids)

    print()
    passed = sum(1 for ok, _, _ in _results if ok)
    total = len(_results)
    print(f"===== {passed}/{total} 검증 통과 =====")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
