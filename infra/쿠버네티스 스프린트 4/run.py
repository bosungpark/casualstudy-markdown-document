#!/usr/bin/env python3
"""강의의 조인·스크레이프 주장을 실제 Prometheus로 확인한다. Python 표준 라이브러리만 사용."""

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "3.5.0"  # 재현용 고정 버전. 최신 버전을 뜻하지 않는다.
CHECKS = 0


def binaries():
    supplied = os.environ.get("PROM_DIR")
    if supplied:
        dest = Path(supplied).expanduser().resolve()
        for name in ("prometheus", "promtool"):
            if not (dest / name).is_file():
                raise RuntimeError(f"PROM_DIR에 {name}이 없습니다: {dest}")
        return dest
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine())
    system = platform.system().lower()
    if arch is None or system not in ("darwin", "linux"):
        raise RuntimeError("macOS/Linux arm64·amd64를 지원합니다. 다른 환경은 PROM_DIR을 지정하세요.")
    package = f"prometheus-{VERSION}.{system}-{arch}"
    dest = Path(tempfile.gettempdir()) / "sprint4-prometheus" / package
    if all((dest / name).is_file() for name in ("prometheus", "promtool")):
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    base = f"https://github.com/prometheus/prometheus/releases/download/v{VERSION}"
    filename = package + ".tar.gz"
    print(f"공식 Prometheus {VERSION} 다운로드 및 SHA-256 확인", flush=True)
    with urllib.request.urlopen(base + "/sha256sums.txt", timeout=30) as response:
        sums = response.read().decode()
    expected = next(line.split()[0] for line in sums.splitlines() if line.split()[-1].lstrip("*") == filename)
    with tempfile.TemporaryDirectory(prefix="sprint4-download-") as scratch:
        archive = Path(scratch) / filename
        with urllib.request.urlopen(base + "/" + filename, timeout=180) as response, archive.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError("공식 체크섬과 다릅니다. 다운로드를 사용하지 않습니다.")
        # 경로를 따라 전체 압축을 풀지 않고 실행 파일 두 개만 복사한다.
        with tarfile.open(archive) as tar:
            for name in ("prometheus", "promtool"):
                member = tar.getmember(package + "/" + name)
                if not member.isfile():
                    raise RuntimeError(f"실행 파일이 아닙니다: {name}")
                (dest / name).write_bytes(tar.extractfile(member).read())
                (dest / name).chmod(0o755)
    return dest


def check(name, ok, detail):
    global CHECKS
    if not ok:
        raise AssertionError(f"[FAIL] {name}: {detail}")
    CHECKS += 1
    print(f"[PASS] {name}: {detail}", flush=True)


def sample(labels, value):
    return {"labels": labels, "value": value}


def rules_demo(bin_dir, work):
    """고정 입력·평가 시각을 쓰므로 발표 때 수집 타이밍에 영향을 받지 않는다."""
    disk = [
        ('disk_usage{disk="disk1",vm="vm1"}', 100),
        ('disk_usage{disk="disk2",vm="vm1"}', 200),
        ('disk_usage{disk="disk3",vm="vm2"}', 300),
        ('disk_usage{disk="disk4",vm="vm3"}', 400),
        ('vm_info{vm="vm1",os="linux"}', 1),
        ('vm_info{vm="vm2",os="windows"}', 1),
        ('vm_info_duplicate{vm="vm1",os="linux",job="ksm-a"}', 1),
        ('vm_info_duplicate{vm="vm1",os="linux",job="ksm-b"}', 1),
        ('node_memory_MemTotal_bytes{instance="10.0.0.1:9100"}', 800),
        ('node_memory_MemAvailable_bytes{instance="10.0.0.1:9100"}', 200),
        ('container_memory_working_set_bytes{namespace="team-a",pod="portal",container="app"}', 120),
        ('container_memory_working_set_bytes{namespace="team-a",pod="portal",container="sidecar"}', 30),
        ('container_memory_working_set_bytes{namespace="team-b",pod="portal",container="app"}', 70),
        ('kube_pod_labels{namespace="team-a",pod="portal",label_component="frontend-server"}', 1),
        ('kube_pod_labels{namespace="team-b",pod="portal",label_component="backend-server"}', 1),
    ]
    inputs = [{"series": label, "values": f"{value}+0x10"} for label, value in disk]
    inputs += [
        {"series": "demo_counter_total", "values": "10 20 35"},
        {"series": "demo_reset_total", "values": "100 5 15"},
        {"series": 'node_cpu_seconds_total{instance="10.0.0.1:9100",cpu="0",mode="idle"}', "values": "0+24x10"},
        {"series": 'node_uname_info{instance="10.0.0.1:9100",nodename="worker-1"}', "values": "1+0x10"},
    ]
    expected_disks = [sample(f'{{disk="disk{i}",vm="vm{1 if i < 3 else 2}",os="{"linux" if i < 3 else "windows"}"}}', i * 100) for i in (1, 2, 3)]
    cpu = '1 - avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m]))'
    pod_join = '* on(namespace,pod) group_left kube_pod_labels{label_component="frontend-server"}'
    cases = [
        ("J1 기본 라벨 집합으로는 짝이 없다", "disk_usage * vm_info", [], "5m"),
        ("J2 group_left: 디스크 3개에 OS, 값 보존", "disk_usage * on(vm) group_left(os) vm_info", expected_disks, "5m"),
        ("J3 group_right: 순서를 뒤집어도 같은 결과", "vm_info * on(vm) group_right(os) disk_usage", expected_disks, "5m"),
        ("J4 +는 실제 덧셈", "disk_usage + on(vm) group_left(os) vm_info", [dict(row, value=row["value"] + 1) for row in expected_disks], "5m"),
        ("J5 조건으로 linux 디스크만 선택", 'disk_usage * on(vm) group_left(os) vm_info{os="linux"}', expected_disks[:2], "5m"),
        ("J6 메타데이터가 없는 disk4 탐지", "disk_usage unless on(vm) vm_info", [sample('{__name__="disk_usage",disk="disk4",vm="vm3"}', 400)], "5m"),
        ("J7 오른쪽 키 중복 탐지", "count by(vm)(vm_info_duplicate) > 1", [sample('{vm="vm1"}', 2)], "5m"),
        ("J8 집계 전에 namespace·pod로 필터", f"sum by(namespace,pod)(container_memory_working_set_bytes {pod_join})", [sample('{namespace="team-a",pod="portal"}', 150)], "5m"),
        ("J9 pod를 없앤 후 조인하면 빈 결과", f"sum by(namespace)(container_memory_working_set_bytes) {pod_join}", [], "5m"),
        ("J10 CPU 사용률에 이름 부착", f"({cpu}) * on(instance) group_left(nodename) node_uname_info", [sample('{instance="10.0.0.1:9100",nodename="worker-1"}', 1 - .8)], "5m"),
        ("J11 CPU의 scalar 1 빼기는 괄호 없이도 같은 결과", f"{cpu} * on(instance) group_left(nodename) node_uname_info", [sample('{instance="10.0.0.1:9100",nodename="worker-1"}', 1 - .8)], "5m"),
        ("J12 두 벡터의 뺄셈은 괄호가 없으면 빈 결과", "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes * on(instance) group_left(nodename) node_uname_info", [], "5m"),
        ("J13 두 벡터의 뺄셈 후 이름 부착", "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) * on(instance) group_left(nodename) node_uname_info", [sample('{instance="10.0.0.1:9100",nodename="worker-1"}', 600)], "5m"),
        ("R1 60초 경계: 샘플은 3개가 아닌 2개", "count_over_time(demo_counter_total[1m])", [sample("{}", 2)], "1m"),
        ("R2 60초 창 rate", "rate(demo_counter_total[1m])", [sample("{}", .5)], "1m"),
        ("R3 61초 창 rate", "rate(demo_counter_total[61s])", [sample("{}", 25 / 60)], "1m"),
        ("R4 counter reset은 음수 증가율로 계산하지 않음", "rate(demo_reset_total[61s])", [sample("{}", .25)], "1m"),
    ]
    fixture = {"rule_files": [], "tests": [{"interval": "30s", "input_series": inputs, "promql_expr_test": [
        {"expr": expr, "eval_time": when, "exp_samples": expected} for _, expr, expected, when in cases
    ]}]}
    path = work / "promql-tests.yml"
    path.write_text(json.dumps(fixture))  # JSON은 유효한 YAML이다.
    proc = subprocess.run([str(bin_dir / "promtool"), "test", "rules", str(path)], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    for name, expr, expected, _ in cases:
        check(name, True, json.dumps(expected, ensure_ascii=False))
        print("       " + expr)
    errors = [
        ("E1 group 생략", "disk_usage * on(vm) vm_info", "multiple matches for labels"),
        ("E2 강의의 뒤집힌 group_left", "vm_info * on(vm) group_left(disk) disk_usage", "found duplicate series"),
        ("E3 오른쪽 키가 중복된 메타데이터", "disk_usage * on(vm) group_left(os) vm_info_duplicate", "found duplicate series"),
        ("E4 namespace를 빼면 동명 파드 충돌", "container_memory_working_set_bytes * on(pod) group_left(label_component) kube_pod_labels", "found duplicate series"),
    ]
    for name, expr, message in errors:
        fixture["tests"][0]["promql_expr_test"] = [{"expr": expr, "eval_time": "5m", "exp_samples": []}]
        path.write_text(json.dumps(fixture))
        proc = subprocess.run([str(bin_dir / "promtool"), "test", "rules", str(path)], capture_output=True, text=True)
        output = proc.stdout + proc.stderr
        check(name, proc.returncode != 0 and message in output, message)
        print("       " + expr)


class Metrics(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = '# TYPE demo_value gauge\ndemo_value{pod="exporter-pod"} 7\n'
        elif self.path == "/ksm":
            body = '# TYPE kube_pod_status_phase gauge\nkube_pod_status_phase{namespace="demo",pod="finished-job",phase="Failed"} 1\n'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *_):
        pass


def fetch(base, path):
    with urllib.request.urlopen(base + path, timeout=2) as response:
        return json.load(response)


def scrape_demo(bin_dir, work):
    # K8s 탐색을 흉내 내지 않고, 설정 생성 이후 relabel/scrape만 실제 엔진으로 검증한다.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Metrics)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    prom = None
    try:
        address = f"127.0.0.1:{server.server_port}"
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        jobs = []
        for name, path, honor, phase in [
            ("healthy", "/metrics", False, "Running"),
            ("honor-true", "/metrics", True, "Running"),
            ("http-error", "/missing", False, "Running"),
            ("filtered", "/metrics", False, "Failed"),
            ("ksm", "/ksm", False, "Running"),
        ]:
            labels = {"discovered_phase": phase}
            if name in ("healthy", "honor-true"):
                labels["pod"] = "discovered-pod"
            jobs.append({"job_name": name, "metrics_path": path, "honor_labels": honor,
                         "static_configs": [{"targets": [address], "labels": labels}],
                         "relabel_configs": [
                             {"source_labels": ["discovered_phase"], "regex": "Failed|Succeeded", "action": "drop"},
                             {"regex": "discovered_phase", "action": "labeldrop"},
                         ]})
        config = work / "prometheus.yml"
        config.write_text(json.dumps({"global": {"scrape_interval": "1s", "scrape_timeout": "1s"}, "scrape_configs": jobs}))
        subprocess.run([str(bin_dir / "promtool"), "check", "config", str(config)], check=True, capture_output=True, text=True)
        with (work / "prometheus.log").open("w") as log:
            prom = subprocess.Popen([str(bin_dir / "prometheus"), f"--config.file={config}",
                                     f"--storage.tsdb.path={work / 'tsdb'}", f"--web.listen-address=127.0.0.1:{port}"], stdout=log, stderr=log)

            def query(expr):
                return fetch(base, "/api/v1/query?" + urllib.parse.urlencode({"query": expr}))["data"]["result"]

            deadline = time.monotonic() + 20
            while True:
                if prom.poll() is not None:
                    raise RuntimeError((work / "prometheus.log").read_text())
                try:
                    if len(query("up")) == 4 and query('demo_value{job="healthy"}') and query('kube_pod_status_phase{phase="Failed"}'):
                        break
                except (OSError, KeyError, urllib.error.URLError):
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError("20초 안에 첫 스크레이프가 완료되지 않았습니다\n" + (work / "prometheus.log").read_text())
                time.sleep(.1)
            healthy = query('up{job="healthy"}')
            check("S1 대상에 요청 성공", len(healthy) == 1 and float(healthy[0]["value"][1]) == 1, "up=1")
            down = query('up{job="http-error"}')
            check("S2 대상은 있으나 HTTP 404", len(down) == 1 and float(down[0]["value"][1]) == 0, "up=0")
            targets = fetch(base, "/api/v1/targets?state=any")["data"]
            active = [t for t in targets["activeTargets"] if t["labels"]["job"] == "http-error"]
            check("S3 Targets 오류 원인", len(active) == 1 and "404" in active[0]["lastError"], active[0]["lastError"] if active else "missing target")
            check("S4 drop된 대상", not query('up{job="filtered"}') and len(targets["droppedTargets"]) == 1, "up 시계열 없음 / droppedTargets=1")
            check("S5 미등록 job", not query('up{job="missing"}'), "up 시계열 없음 (0이 아님)")
            failed = query('kube_pod_status_phase{phase="Failed"}')
            check("S6 Failed 상태는 별도 exporter에서 수집 가능", len(failed) == 1 and float(failed[0]["value"][1]) == 1, "filtered 대상 없음 / Failed 상태=1")
            false_row = query('demo_value{job="healthy"}')[0]
            check("S7 honor_labels=false", false_row["metric"].get("pod") == "discovered-pod" and false_row["metric"].get("exported_pod") == "exporter-pod", "pod=discovered-pod / exported_pod=exporter-pod / value=7")
            true_row = query('demo_value{job="honor-true"}')[0]
            check("S8 honor_labels=true", true_row["metric"].get("pod") == "exporter-pod" and "exported_pod" not in true_row["metric"], "pod=exporter-pod / value=7")
    finally:
        if prom is not None:
            prom.terminate()
            try:
                prom.wait(timeout=10)
            except subprocess.TimeoutExpired:
                prom.kill()
                prom.wait()
        server.shutdown()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", nargs="?", choices=["all", "promql", "scrape"], default="all")
    args = parser.parse_args()
    bin_dir = binaries()
    print(subprocess.check_output([str(bin_dir / "promtool"), "--version"], text=True).splitlines()[0], flush=True)
    with tempfile.TemporaryDirectory(prefix="sprint4-demo-") as scratch:
        work = Path(scratch)
        if args.phase in ("all", "promql"):
            rules_demo(bin_dir, work)
        if args.phase in ("all", "scrape"):
            scrape_demo(bin_dir, work)
    print(f"\n{CHECKS}/{CHECKS} checks passed. 임시 프로세스 종료·TSDB 삭제 완료.", flush=True)


if __name__ == "__main__":
    main()
