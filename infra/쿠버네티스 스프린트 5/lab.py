#!/usr/bin/env python3
"""스프린트 5 실습: 전용 kind 클러스터와 '이전 스프린트의 Prometheus'만 준비한다. Istio 설치는 직접 한다."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
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
CLUSTER = "sprint5-istio"
CONTEXT = "kind-" + CLUSTER
KIND_VERSION = "0.30.0"
KUBE_VERSION = "1.34.0"
HELM_VERSION = "3.19.0"
STACK_VERSION = "77.6.0"
ISTIO_VERSION = "1.31.4"
GATEWAY_API_VERSION = "v1.6.0"
# Gateway API 릴리스는 체크섬 파일을 제공하지 않아, 받은 standard-install.yaml의 SHA-256을 직접 계산해 고정했다.
GATEWAY_API_SHA256 = "a557172e8348f758479e9ee4000bbbb4b4aa48302a6b73461823ea5349bad56d"
NODE_IMAGE = "kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a"
ISTIO_DIR = STATE / "istio"  # .lab/istio-<버전>을 가리키는 링크
GATEWAY_API_FILE = STATE / f"gateway-api-{GATEWAY_API_VERSION}.yaml"
PORTS = {30011: "Istio API 게이트웨이", 30012: "Gateway API 게이트웨이", 30020: "Kiali", 30090: "Prometheus"}


def run(args, capture=False, check=True, **kwargs):
    env = dict(os.environ, KUBECONFIG=str(KUBECONFIG))
    return subprocess.run([str(x) for x in args], cwd=ROOT, env=env,
                          text=True, capture_output=capture, check=check, **kwargs)


def kubectl(*args, **kwargs):
    return run([BIN / "kubectl", "--kubeconfig", KUBECONFIG, "--context", CONTEXT, *args], **kwargs)


def helm(*args, **kwargs):
    return run([BIN / "helm", "--kubeconfig", KUBECONFIG, "--kube-context", CONTEXT,
                "--repository-cache", STATE / "helm-cache", "--repository-config", STATE / "repositories.yaml", *args], **kwargs)


def istioctl(*args, **kwargs):
    return run([ISTIO_DIR / "bin" / "istioctl", "--kubeconfig", KUBECONFIG, "--context", CONTEXT, *args], **kwargs)


def download(url, dest):
    print("다운로드:", url.rsplit("/", 1)[-1], flush=True)
    with urllib.request.urlopen(url, timeout=180) as response, dest.open("wb") as output:
        shutil.copyfileobj(response, output)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def official_sha(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode().split()[0]


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
        with tempfile.TemporaryDirectory(prefix="sprint5-tools-") as scratch:
            archive = Path(scratch) / "download"
            expected = official_sha(url + suffix)
            download(url, archive)
            if sha256(archive) != expected:
                raise RuntimeError(f"{name}: 공식 SHA-256과 일치하지 않습니다.")
            if member:
                with tarfile.open(archive) as tar:
                    extracted = tar.extractfile(member)
                    if extracted is None:
                        raise RuntimeError(f"{name}: 압축 파일에 {member}가 없습니다.")
                    dest.write_bytes(extracted.read())
            else:
                shutil.copyfile(archive, dest)
            dest.chmod(0o755)

    # 강의처럼 Istio 패키지 전체(istioctl + samples/)를 받는다.
    versioned = STATE / f"istio-{ISTIO_VERSION}"
    if not (versioned / "bin" / "istioctl").exists():
        os_name = "osx" if system == "darwin" else "linux"
        url = f"https://github.com/istio/istio/releases/download/{ISTIO_VERSION}/istio-{ISTIO_VERSION}-{os_name}-{arch}.tar.gz"
        with tempfile.TemporaryDirectory(prefix="sprint5-istio-") as scratch:
            archive = Path(scratch) / "istio.tar.gz"
            expected = official_sha(url + ".sha256")
            download(url, archive)
            if sha256(archive) != expected:
                raise RuntimeError("Istio 패키지: 공식 SHA-256과 일치하지 않습니다.")
            with tarfile.open(archive) as tar:
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(STATE, filter="data")
                else:
                    for item in tar.getmembers():
                        if item.name.startswith(("/", "..")) or ".." in Path(item.name).parts:
                            raise RuntimeError("Istio 패키지 경로가 올바르지 않습니다: " + item.name)
                    tar.extractall(STATE)
    if ISTIO_DIR.is_symlink() or ISTIO_DIR.exists():
        ISTIO_DIR.unlink()
    ISTIO_DIR.symlink_to(versioned.name)

    if not GATEWAY_API_FILE.exists() or sha256(GATEWAY_API_FILE) != GATEWAY_API_SHA256:
        url = f"https://github.com/kubernetes-sigs/gateway-api/releases/download/{GATEWAY_API_VERSION}/standard-install.yaml"
        with tempfile.TemporaryDirectory(prefix="sprint5-gwapi-") as scratch:
            path = Path(scratch) / "standard-install.yaml"
            download(url, path)
            if sha256(path) != GATEWAY_API_SHA256:
                raise RuntimeError("Gateway API CRD: 고정한 SHA-256과 일치하지 않습니다.")
            shutil.copyfile(path, GATEWAY_API_FILE)


def owner_ok():
    owner = STATE / "owner.json"
    return owner.exists() and json.loads(owner.read_text()) == {"cluster": CLUSTER, "created_by": str(ROOT)}


def require_lab():
    if not KUBECONFIG.exists() or not owner_ok():
        raise RuntimeError("먼저 python3 lab.py setup으로 전용 실습 클러스터를 준비하세요.")


def setup():
    if shutil.which("docker") is None:
        raise RuntimeError("Docker가 필요합니다. Docker Desktop 또는 Docker Engine을 먼저 실행하세요.")
    if run(["docker", "info"], capture=True, check=False).returncode:
        raise RuntimeError("Docker 엔진에 연결할 수 없습니다. Docker Desktop/Docker Engine을 먼저 켜세요.")
    tools()
    clusters = run([BIN / "kind", "get", "clusters"], capture=True).stdout.split()
    if CLUSTER in clusters and not owner_ok():
        raise RuntimeError(f"이 디렉터리에서 만든 것이 아닌 클러스터가 있습니다: {CLUSTER}. 기존 클러스터를 변경하지 않습니다.")
    if CLUSTER not in clusters:
        for port, title in PORTS.items():
            with socket.socket() as sock:
                try:
                    sock.bind(("127.0.0.1", port))  # 사용 중인 포트를 빼앗지 않는다.
                except OSError:
                    raise RuntimeError(f"127.0.0.1:{port}({title})를 다른 프로그램이 쓰고 있습니다.")
        # 중간 실패 후에도 이 도구가 만들려던 클러스터임을 식별한다.
        (STATE / "owner.json").write_text(json.dumps({"cluster": CLUSTER, "created_by": str(ROOT)}, ensure_ascii=False))
        run([BIN / "kind", "create", "cluster", "--name", CLUSTER, "--image", NODE_IMAGE,
             "--config", ROOT / "lab/kind.yaml", "--kubeconfig", KUBECONFIG, "--wait", "180s"])
    elif not KUBECONFIG.exists():
        run([BIN / "kind", "export", "kubeconfig", "--name", CLUSTER, "--kubeconfig", KUBECONFIG])
    # 사용자의 ~/.kube/config와 현재 context를 변경하지 않는다.
    kubectl("wait", "--for=condition=Ready", "nodes", "--all", "--timeout=180s")
    print("\n이전 스프린트의 Prometheus 설치: 첫 실행은 이미지 다운로드로 몇 분 걸릴 수 있습니다.", flush=True)
    helm("upgrade", "--install", "monitoring", "kube-prometheus-stack", "--namespace", "monitoring", "--create-namespace",
         "--repo", "https://prometheus-community.github.io/helm-charts", "--version", STACK_VERSION,
         "-f", ROOT / "lab/monitoring-values.yaml", "--wait", "--timeout", "10m")
    deadline = time.monotonic() + 180
    while not json.loads(kubectl("-n", "monitoring", "get", "pods", "-l", "app.kubernetes.io/name=prometheus",
                                 "-o", "json", capture=True).stdout)["items"]:
        if time.monotonic() > deadline:
            raise RuntimeError("Prometheus Pod가 생성되지 않았습니다. Operator 로그를 확인하세요.")
        time.sleep(2)
    kubectl("-n", "monitoring", "wait", "--for=condition=Ready", "pod", "-l", "app.kubernetes.io/name=prometheus", "--timeout=180s")
    print("\n준비 완료. Istio는 설치하지 않았습니다. '쿠버네티스 스프린트 5.md'의 PoC 1단계에서 직접 설치합니다.")
    print("Prometheus: http://127.0.0.1:30090")


def traffic(count, target, interval):
    if count < 1 or interval < 0:
        raise RuntimeError("count는 1 이상, interval은 0 이상으로 지정하세요.")
    ports = {"istio": [30011], "gateway": [30012], "both": [30011, 30012]}[target]
    for i in range(count):
        for port in ports:
            label = PORTS[port]
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/productpage", timeout=5) as response:
                    response.read()
                    status = response.status
            except urllib.error.HTTPError as error:
                status = error.code
            except (urllib.error.URLError, OSError) as error:
                raise RuntimeError(f"{label}(:{port}) 연결 실패 ({error}). 게이트웨이 생성과 NodePort 변경을 확인하세요.")
            if i == 0 or (i + 1) % 20 == 0 or i + 1 == count:
                print(f"{label} :{port}/productpage {i + 1}/{count}: HTTP {status}", flush=True)
        time.sleep(interval)


def query(expr):
    url = "http://127.0.0.1:30090/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            rows = json.load(response)["data"]["result"]
    except urllib.error.HTTPError as error:
        raise RuntimeError(json.load(error).get("error", str(error))) from error
    if not rows:
        print("빈 결과 (시리즈 없음)")
    for row in rows:
        print(json.dumps(row["metric"], ensure_ascii=False, sort_keys=True), row["value"][1])


def rules(app):
    """파드 네트워크 네임스페이스와 노드 네임스페이스의 Istio iptables 규칙을 비교한다."""
    pods = json.loads(kubectl("get", "pods", "-n", "default", "-l", "app=" + app, "-o", "json", capture=True).stdout)["items"]
    if not pods:
        raise RuntimeError(f"default 네임스페이스에 app={app} 파드가 없습니다.")
    pod = pods[0]
    node = pod["spec"]["nodeName"]
    name = pod["metadata"]["name"]
    container = run(["docker", "exec", node, "crictl", "ps", "--name", app, "--pod",
                     run(["docker", "exec", node, "crictl", "pods", "--name", name, "-q"], capture=True).stdout.split()[0], "-q"],
                    capture=True).stdout.split()[0]
    pid = run(["docker", "exec", node, "crictl", "inspect", "--output", "go-template", "--template", "{{.info.pid}}", container],
              capture=True).stdout.strip()
    inside = run(["docker", "exec", node, "nsenter", "-t", pid, "-n", "iptables-nft-save", "-t", "nat"], capture=True).stdout
    on_node = run(["docker", "exec", node, "iptables-nft-save", "-t", "nat"], capture=True).stdout
    print(f"[{name}의 네트워크 네임스페이스] nat 테이블의 Istio 규칙")
    print("\n".join(line for line in inside.splitlines() if line.startswith("-A") and "ISTIO" in line))
    print(f"\n[노드 {node}의 기본 네임스페이스] ISTIO가 들어간 규칙 수:",
          sum("ISTIO" in line for line in on_node.splitlines()))


def status():
    kubectl("get", "nodes")
    print()
    kubectl("get", "namespace", "-L", "istio-injection")
    print()
    kubectl("get", "pods", "-A", "-o", "wide")


def reset():
    """강의의 'Istio 전체 삭제'에 해당. Prometheus만 남긴 1단계 시작 상태로 되돌린다."""
    samples = ISTIO_DIR / "samples"
    files = [
        samples / "addons/kiali.yaml",
        samples / "addons/extras/prometheus-operator.yaml",
        STATE / "my-kiali.yaml",
        STATE / "my-monitors.yaml",
        ROOT / "lab/mirror.yaml",
        samples / "bookinfo/networking/destination-rule-all.yaml",
        samples / "bookinfo/networking/bookinfo-gateway.yaml",
        samples / "bookinfo/gateway-api/bookinfo-gateway.yaml",
        samples / "bookinfo/platform/kube/bookinfo.yaml",
        samples / "httpbin/httpbin.yaml",
        samples / "curl/curl.yaml",
    ]
    for path in files:
        if path.exists():
            kubectl("delete", "-f", path, "--ignore-not-found", "--wait=false", capture=True, check=False)
    kubectl("delete", "namespace", "no-mesh", "--ignore-not-found", capture=True, check=False)
    if (ISTIO_DIR / "bin" / "istioctl").exists():
        istioctl("uninstall", "--purge", "-y", check=False)
    kubectl("delete", "namespace", "istio-system", "--ignore-not-found")
    kubectl("delete", "-f", GATEWAY_API_FILE, "--ignore-not-found", capture=True, check=False)
    kubectl("label", "namespace", "default", "istio-injection-", capture=True, check=False)
    kubectl("wait", "--for=delete", "pod", "--all", "-n", "default", "--timeout=180s", capture=True, check=False)
    # Prometheus 저장소는 emptyDir이다. 파드를 다시 만들어 이전 실습의 Istio 메트릭 이력까지 지운다.
    kubectl("delete", "pod", "-n", "monitoring", "-l", "app.kubernetes.io/name=prometheus", "--wait=true", capture=True, check=False)
    deadline = time.monotonic() + 180
    while not json.loads(kubectl("-n", "monitoring", "get", "pods", "-l", "app.kubernetes.io/name=prometheus",
                                 "-o", "json", capture=True).stdout)["items"]:
        if time.monotonic() > deadline:
            raise RuntimeError("Prometheus Pod가 다시 생성되지 않았습니다. Operator 로그를 확인하세요.")
        time.sleep(2)
    kubectl("-n", "monitoring", "wait", "--for=condition=Ready", "pod", "-l", "app.kubernetes.io/name=prometheus", "--timeout=180s")
    print("Istio·예제 앱·Gateway API CRD와 Prometheus의 이전 이력을 지웠습니다. PoC 1단계부터 다시 시작하세요.")


def main():
    # kubectl·helm·istioctl의 -n 등 옵션을 순서 그대로 전달한다.
    if len(sys.argv) > 1 and sys.argv[1] in ("k", "helm", "istioctl"):
        require_lab()
        forwarded = sys.argv[2:]
        if forwarded[:1] == ["--"]:
            forwarded = forwarded[1:]
        func = {"k": kubectl, "helm": helm, "istioctl": istioctl}[sys.argv[1]]
        raise SystemExit(func(*forwarded, check=False).returncode)
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("setup", "status", "reset", "down"):
        subs.add_parser(command)
    for command in ("k", "helm", "istioctl"):
        subs.add_parser(command)
    load = subs.add_parser("traffic")
    load.add_argument("--count", type=int, default=50)
    load.add_argument("--target", choices=["istio", "gateway", "both"], default="both")
    load.add_argument("--interval", type=float, default=0.1)
    subs.add_parser("query").add_argument("expression")
    subs.add_parser("rules").add_argument("app", nargs="?", default="productpage")
    args = parser.parse_args()
    if args.command == "setup":
        setup()
        return
    require_lab()
    if args.command == "status":
        status()
    elif args.command == "traffic":
        traffic(args.count, args.target, args.interval)
    elif args.command == "query":
        query(args.expression)
    elif args.command == "rules":
        rules(args.app)
    elif args.command == "reset":
        reset()
    elif args.command == "down":
        run([BIN / "kind", "delete", "cluster", "--name", CLUSTER])
        KUBECONFIG.unlink(missing_ok=True)
        (STATE / "owner.json").unlink()
        print("전용 실습 클러스터 삭제 완료. 받은 도구와 Istio 패키지는 .lab/에 남습니다.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"실행 중단: {error}") from error
