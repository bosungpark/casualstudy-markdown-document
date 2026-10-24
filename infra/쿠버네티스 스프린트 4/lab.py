#!/usr/bin/env python3
"""전용 kind 클러스터를 준비하고, 사용자가 직접 조작할 UI와 kubectl을 제공한다."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
STATE = ROOT / ".lab"
BIN = STATE / "bin"
KUBECONFIG = STATE / "kubeconfig"
CLUSTER = "sprint4-monitoring"
CONTEXT = "kind-" + CLUSTER
KIND_VERSION = "0.30.0"
KUBE_VERSION = "1.34.0"
HELM_VERSION = "3.19.0"
STACK_VERSION = "77.6.0"
INGRESS_VERSION = "4.14.4"
NODE_IMAGE = "kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a"
PROM = "http://127.0.0.1:19090"


def run(args, capture=False, check=True, **kwargs):
    env = dict(os.environ, KUBECONFIG=str(KUBECONFIG))
    return subprocess.run([str(x) for x in args], cwd=ROOT, env=env,
                          text=True, capture_output=capture, check=check, **kwargs)


def kubectl(*args, **kwargs):
    return run([BIN / "kubectl", "--kubeconfig", KUBECONFIG, "--context", CONTEXT, *args], **kwargs)


def helm(*args, **kwargs):
    return run([BIN / "helm", "--kubeconfig", KUBECONFIG, "--kube-context", CONTEXT,
                "--repository-cache", STATE / "helm-cache", "--repository-config", STATE / "repositories.yaml", *args], **kwargs)


def download(url, dest):
    print("다운로드:", url.rsplit("/", 1)[-1], flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, dest.open("wb") as output:
        shutil.copyfileobj(response, output)


def tools():
    system = platform.system().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine())
    if system not in ("darwin", "linux") or arch is None:
        raise RuntimeError("macOS/Linux arm64·amd64에서 실행하세요.")
    BIN.mkdir(parents=True, exist_ok=True)
    specs = [
        ("kind", f"https://github.com/kubernetes-sigs/kind/releases/download/v{KIND_VERSION}/kind-{system}-{arch}", ".sha256sum", None),
        ("kubectl", f"https://dl.k8s.io/release/v{KUBE_VERSION}/bin/{system}/{arch}/kubectl", ".sha256", None),
        ("helm", f"https://get.helm.sh/helm-v{HELM_VERSION}-{system}-{arch}.tar.gz", ".sha256sum", f"{system}-{arch}/helm"),
    ]
    for name, url, suffix, member in specs:
        dest = BIN / name
        if dest.exists():
            continue
        with tempfile.TemporaryDirectory(prefix="sprint4-tools-") as scratch:
            archive = Path(scratch) / "download"
            with urllib.request.urlopen(url + suffix, timeout=30) as response:
                expected = response.read().decode().split()[0]
            download(url, archive)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"{name}: 공식 SHA-256과 일치하지 않습니다.")
            if member:
                with tarfile.open(archive) as tar:
                    dest.write_bytes(tar.extractfile(member).read())
            else:
                shutil.copyfile(archive, dest)
            dest.chmod(0o755)


def require_lab():
    if not KUBECONFIG.exists() or not (STATE / "owner.json").exists():
        raise RuntimeError("먼저 python3 lab.py setup으로 전용 실습 클러스터를 준비하세요.")


def setup():
    if shutil.which("docker") is None:
        raise RuntimeError("Docker가 필요합니다. Docker Desktop 또는 Docker Engine을 먼저 실행하세요.")
    docker = run(["docker", "info"], capture=True, check=False)
    if docker.returncode:
        raise RuntimeError("Docker 엔진에 연결할 수 없습니다. Docker Desktop/Docker Engine을 먼저 켜세요.")
    tools()
    clusters = run([BIN / "kind", "get", "clusters"], capture=True).stdout.split()
    owner = STATE / "owner.json"
    if CLUSTER in clusters and not owner.exists():
        raise RuntimeError(f"동일한 이름의 다른 클러스터가 있습니다: {CLUSTER}. 기존 클러스터를 변경하지 않습니다.")
    if CLUSTER in clusters and json.loads(owner.read_text()) != {"cluster": CLUSTER, "created_by": str(ROOT)}:
        raise RuntimeError("이 디렉터리에서 생성한 클러스터인지 확인할 수 없어 변경하지 않습니다.")
    if CLUSTER not in clusters:
        # 중간 실패 후에도 이 도구가 생성하려던 클러스터임을 식별한다.
        owner.write_text(json.dumps({"cluster": CLUSTER, "created_by": str(ROOT)}, ensure_ascii=False))
        run([BIN / "kind", "create", "cluster", "--name", CLUSTER, "--image", NODE_IMAGE,
             "--config", ROOT / "lab/kind.yaml", "--kubeconfig", KUBECONFIG, "--wait", "180s"])
    elif not KUBECONFIG.exists():
        run([BIN / "kind", "export", "kubeconfig", "--name", CLUSTER, "--kubeconfig", KUBECONFIG])
    # 사용자의 ~/.kube/config와 현재 context를 변경하지 않는다.
    kubectl("wait", "--for=condition=Ready", "nodes", "--all", "--timeout=180s")
    kubectl("create", "namespace", "monitoring", check=False)
    print("\n모니터링 스택 설치: 첫 실행은 이미지 다운로드로 몇 분 걸릴 수 있습니다.", flush=True)
    helm("upgrade", "--install", "monitoring", "kube-prometheus-stack", "--namespace", "monitoring",
         "--repo", "https://prometheus-community.github.io/helm-charts", "--version", STACK_VERSION,
         "-f", ROOT / "lab/monitoring-values.yaml", "--wait", "--timeout", "12m")
    helm("upgrade", "--install", "ingress-nginx", "ingress-nginx", "--namespace", "ingress-nginx", "--create-namespace",
         "--repo", "https://kubernetes.github.io/ingress-nginx", "--version", INGRESS_VERSION,
         "-f", ROOT / "lab/ingress-values.yaml", "--wait", "--timeout", "8m")
    kubectl("apply", "-f", ROOT / "lab/apps.yaml")
    for name in ("portal", "api"):
        kubectl("-n", "apps", "rollout", "status", "deployment/" + name, "--timeout=240s")
    deadline = time.monotonic() + 180
    while True:
        pods = kubectl("-n", "monitoring", "get", "pods", "-l", "app.kubernetes.io/name=prometheus", "-o", "json", capture=True)
        if json.loads(pods.stdout)["items"]:
            break
        if time.monotonic() > deadline:
            raise RuntimeError("Prometheus Pod가 생성되지 않았습니다. status와 Operator 로그를 확인하세요.")
        time.sleep(2)
    kubectl("-n", "monitoring", "wait", "--for=condition=Ready", "pod", "-l", "app.kubernetes.io/name=prometheus", "--timeout=180s")
    kubectl("apply", "-f", ROOT / "lab/dashboard.yaml")
    print("\n준비 완료. ServiceMonitor는 직접 만들어 볼 수 있도록 생성하지 않았습니다.")
    print("터미널 1: python3 lab.py ui")
    print("터미널 2: 실습.md의 1단계부터 진행하세요.")


def ui():
    require_lab()
    forwards = [
        ("monitoring", "prometheus-operated", 19090, 9090, "Prometheus"),
        ("monitoring", "monitoring-grafana", 13000, 80, "Grafana"),
        ("ingress-nginx", "ingress-nginx-controller", 18080, 80, "포탈 요청"),
        ("ingress-nginx", "ingress-nginx-controller-metrics", 10254, 10254, "NGINX 원시 메트릭"),
    ]
    for _, _, port, _, _ in forwards:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))  # 사용 중인 포트를 빼앗지 않는다.
    processes = []
    log_path = STATE / "port-forward.log"
    old_handler = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        with log_path.open("w") as log:
            for namespace, service, port, target, title in forwards:
                cmd = [BIN / "kubectl", "--kubeconfig", KUBECONFIG, "--context", CONTEXT, "-n", namespace,
                       "port-forward", "--address=127.0.0.1", "svc/" + service, f"{port}:{target}"]
                processes.append(subprocess.Popen([str(x) for x in cmd], stdout=log, stderr=log))
                print(f"{title}: http://127.0.0.1:{port}", flush=True)
            print("Grafana: admin / study-local-only → Dashboards → Sprint 4 - 직접 바꾸는 모니터링", flush=True)
            print("이 터미널은 켜 두세요. Ctrl+C는 포워딩만 종료하며 클러스터·데이터는 유지합니다.", flush=True)
            while True:
                if any(proc.poll() is not None for proc in processes):
                    raise RuntimeError("포워딩이 종료됐습니다. " + str(log_path) + " 확인 후 ui를 다시 실행하세요.")
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nUI 포워딩 종료. 클러스터는 유지됩니다.")
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        signal.signal(signal.SIGTERM, old_handler)


def fetch(path):
    with urllib.request.urlopen(PROM + path, timeout=10) as response:
        return json.load(response)


def query(expr):
    try:
        body = fetch("/api/v1/query?" + urllib.parse.urlencode({"query": expr}))
    except urllib.error.HTTPError as error:
        raise RuntimeError(json.load(error).get("error", str(error))) from error
    rows = body["data"]["result"]
    if not rows:
        print("빈 결과 (시리즈 없음)")
    for row in rows:
        print(json.dumps(row["metric"], ensure_ascii=False, sort_keys=True), row["value"][1])


def traffic(count, interval):
    if count < 1 or interval < 0:
        raise RuntimeError("count는 1 이상, interval은 0 이상으로 지정하세요.")
    for i in range(count):
        request = urllib.request.Request("http://127.0.0.1:18080/", headers={"Host": "portal.study.local"})
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
            if i == 0 or (i + 1) % 20 == 0 or i + 1 == count:
                print(f"포탈에 실제 요청 {i + 1}/{count}: HTTP {response.status}", flush=True)
        time.sleep(interval)


def main():
    # kubectl/Helm의 -n 등 옵션을 순서 그대로 전달한다.
    if len(sys.argv) > 1 and sys.argv[1] in ("k", "helm"):
        require_lab()
        forwarded = sys.argv[2:]
        if forwarded[:1] == ["--"]:
            forwarded = forwarded[1:]
        func = kubectl if sys.argv[1] == "k" else helm
        raise SystemExit(func(*forwarded, check=False).returncode)
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("setup", "ui", "status", "targets", "config", "down"):
        subs.add_parser(command)
    for command in ("k", "helm"):
        subs.add_parser(command).add_argument("args", nargs=argparse.REMAINDER)
    subs.add_parser("query").add_argument("expression")
    load = subs.add_parser("traffic")
    load.add_argument("--count", type=int, default=100)
    load.add_argument("--interval", type=float, default=.05)
    args = parser.parse_args()
    if args.command == "setup":
        setup()
        return
    require_lab()
    if args.command == "ui":
        ui()
    elif args.command in ("k", "helm"):
        func = kubectl if args.command == "k" else helm
        result = func(*args.args, check=False)
        raise SystemExit(result.returncode)
    elif args.command == "status":
        kubectl("get", "nodes", "-L", "resource")
        kubectl("get", "pods", "-A")
    elif args.command == "query":
        query(args.expression)
    elif args.command == "traffic":
        traffic(args.count, args.interval)
    elif args.command == "config":
        config = fetch("/api/v1/status/config")["data"]["yaml"]
        selected = [line.strip() for line in config.splitlines() if "job_name:" in line and "nginx-metrics" in line]
        print("\n".join(selected) if selected else "nginx-metrics job 없음: ServiceMonitor 선택 조건부터 확인하세요.")
    elif args.command == "targets":
        data = fetch("/api/v1/targets?state=any")["data"]
        rows = [x for x in data["activeTargets"] if "nginx-metrics" in x.get("scrapePool", "")]
        print("NGINX 활성 대상:", len(rows))
        for target in rows:
            print(target["health"], target["scrapeUrl"], target["lastError"] or "오류 없음")
        dropped = [x for x in data["droppedTargets"] if x["discoveredLabels"].get("__meta_kubernetes_namespace") == "ingress-nginx"]
        print("ingress-nginx namespace의 dropped 후보:", len(dropped), "(다른 job에서 제외한 후보도 포함)")
    elif args.command == "down":
        owner = json.loads((STATE / "owner.json").read_text())
        if owner != {"cluster": CLUSTER, "created_by": str(ROOT)}:
            raise RuntimeError("이 디렉터리에서 생성한 클러스터인지 확인할 수 없어 삭제하지 않습니다.")
        run([BIN / "kind", "delete", "cluster", "--name", CLUSTER])
        KUBECONFIG.unlink(missing_ok=True)
        (STATE / "owner.json").unlink()
        print("전용 실습 클러스터 삭제 완료. 다운로드한 도구 캐시는 유지됩니다.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"실행 중단: {error}") from error
