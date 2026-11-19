#!/usr/bin/env python3
"""'쿠버네티스 스프린트 5.md' PoC의 단계를 처음 상태부터 그대로 실행하고 관찰값을 판정한다.

주의: 시작할 때와 끝날 때 `lab.py reset`을 실행한다. 직접 실습하던 상태는 지워지고 Prometheus만 남는다.
결과는 lab/검증 결과.json에 저장한다.
"""

import importlib.util
import json
from pathlib import Path
import platform
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
# lab/ 폴더와 이름이 겹치지 않도록 lab.py를 파일 경로로 불러온다.
_spec = importlib.util.spec_from_file_location("sprint5_lab", ROOT / "lab.py")
assert _spec and _spec.loader
lab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab)

SAMPLES = lab.ISTIO_DIR / "samples"
RESULTS = []


def k(*args, check=True):
    return lab.kubectl(*args, capture=True, check=check).stdout


def kj(*args):
    return json.loads(k(*args, "-o", "json"))


def wait_until(fn, timeout=180, interval=3):
    deadline = time.monotonic() + timeout
    while True:
        value = fn()
        if value or time.monotonic() > deadline:
            return value
        time.sleep(interval)


def http(port, path="/productpage"):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, ""
    except (urllib.error.URLError, OSError):
        return 0, ""


def prom(expr):
    url = "http://127.0.0.1:30090/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)["data"]["result"]


def reviews_counts():
    rows = prom('sum by (destination_workload) (istio_requests_total{reporter="destination", destination_service_name="reviews"})')
    return {r["metric"]["destination_workload"]: float(r["value"][1]) for r in rows}


def kiali_edges():
    url = "http://127.0.0.1:30020/kiali/api/namespaces/graph?namespaces=default,istio-system&graphType=versionedApp&duration=600s"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            elements = json.load(response)["elements"]
    except (urllib.error.URLError, OSError):
        return set()
    names = {n["data"]["id"]: n["data"].get("workload") or n["data"].get("app") or n["data"].get("service")
             for n in elements["nodes"]}
    return {(names[e["data"]["source"]], names[e["data"]["target"]]) for e in elements["edges"]}


def record(step, action, expected, observed, passed):
    RESULTS.append({"step": step, "action": action, "expected": expected, "observed": observed, "passed": bool(passed)})
    print(("통과" if passed else "실패"), step, "-", observed, flush=True)


def pod_spec(app):
    return kj("get", "pod", "-l", "app=" + app)["items"][0]["spec"]


def istio_rules(app):
    pod = kj("get", "pod", "-l", "app=" + app)["items"][0]
    node, name = pod["spec"]["nodeName"], pod["metadata"]["name"]
    sandbox = lab.run(["docker", "exec", node, "crictl", "pods", "--name", name, "-q"], capture=True).stdout.split()[0]
    container = lab.run(["docker", "exec", node, "crictl", "ps", "--name", app, "--pod", sandbox, "-q"], capture=True).stdout.split()[0]
    pid = lab.run(["docker", "exec", node, "crictl", "inspect", "--output", "go-template", "--template", "{{.info.pid}}", container],
                  capture=True).stdout.strip()
    inside = lab.run(["docker", "exec", node, "nsenter", "-t", pid, "-n", "iptables-nft-save", "-t", "nat"], capture=True).stdout
    on_node = lab.run(["docker", "exec", node, "iptables-nft-save", "-t", "nat"], capture=True).stdout
    return ({line for line in inside.splitlines() if line.startswith("-A") and "ISTIO" in line},
            sum("ISTIO" in line for line in on_node.splitlines()))


def deploy_bookinfo():
    k("apply", "-f", SAMPLES / "bookinfo/platform/kube/bookinfo.yaml")
    k("wait", "--for=condition=Ready", "pod", "-l", "app in (productpage,details,ratings,reviews)", "--timeout=600s")


def main():
    lab.require_lab()
    started = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    print("시작 상태로 초기화합니다.", flush=True)
    lab.reset()
    nodes = len(kj("get", "nodes")["items"])

    # 1단계: Istio 기본 설치
    lab.istioctl("install", "--set", "profile=default", "-y", capture=True)
    deployments = sorted(d["metadata"]["name"] for d in kj("get", "deploy", "-n", "istio-system")["items"])
    crds = [c for c in k("get", "crd", "-o", "name").split() if c.endswith(".istio.io")]
    record("1 기본 설치", "istioctl install --set profile=default", "istiod·istio-ingressgateway, Istio CRD",
           f"Deployment {deployments}, *.istio.io CRD {len(crds)}개",
           deployments == ["istio-ingressgateway", "istiod"] and len(crds) >= 10)

    # 2단계: 라벨과 데모 앱
    k("label", "namespace", "default", "istio-injection=enabled", "--overwrite")
    deploy_bookinfo()
    pods = kj("get", "pods", "-l", "app in (productpage,details,ratings,reviews)")["items"]
    spec = pod_spec("productpage")
    init = {c["name"]: c for c in spec["initContainers"]}
    sec = init["istio-init"]["securityContext"]
    proxy_req = init["istio-proxy"]["resources"]["requests"]
    record("2 사이드카 주입", "라벨 후 Bookinfo 배포", "파드 6개, istio-init·istio-proxy·앱 컨테이너",
           f"파드 {len(pods)}개, initContainers {list(init)}, containers {[c['name'] for c in spec['containers']]}, "
           f"istio-proxy restartPolicy={init['istio-proxy'].get('restartPolicy')}",
           len(pods) == 6 and list(init) == ["istio-init", "istio-proxy"] and init["istio-proxy"].get("restartPolicy") == "Always")
    record("2 istio-init 권한", "productpage의 istio-init securityContext 조회", "NET_ADMIN·NET_RAW, root, 쓰기 가능",
           f"add={sec['capabilities'].get('add')}, runAsUser={sec.get('runAsUser')}, privileged={sec.get('privileged')}, "
           f"readOnlyRootFilesystem={sec.get('readOnlyRootFilesystem')}; istio-proxy requests={proxy_req}",
           sec["capabilities"].get("add") == ["NET_ADMIN", "NET_RAW"] and sec.get("runAsUser") == 0 and not sec.get("readOnlyRootFilesystem"))
    init_rules, node_count = istio_rules("productpage")
    record("2 iptables 위치", "lab.py rules productpage", "파드 네임스페이스에만 15001·15006 REDIRECT",
           f"파드 안 ISTIO 규칙 {len(init_rules)}개 (15001:{any('--to-ports 15001' in r for r in init_rules)}, "
           f"15006:{any('--to-ports 15006' in r for r in init_rules)}), 노드 {node_count}개",
           any("--to-ports 15001" in r for r in init_rules) and any("--to-ports 15006" in r for r in init_rules) and node_count == 0)

    # 3단계: Istio API 게이트웨이
    k("apply", "-f", SAMPLES / "bookinfo/networking/bookinfo-gateway.yaml")
    before, _ = http(30011)
    k("patch", "svc", "istio-ingressgateway", "-n", "istio-system", "-p", '{"spec":{"ports":[{"port":80,"nodePort":30011}]}}')
    after, body = wait_until(lambda: (lambda r: r if r[0] == 200 else None)(http(30011)), 60) or (0, "")
    root, _ = http(30011, "/")
    record("3 Istio API 접속", "Gateway·VirtualService 적용 후 NodePort 30011로 변경", "변경 전 실패, 후 200, match 밖 404",
           f"변경 전 {before}, 변경 후 {after} ({'Simple Bookstore App' in body}), / {root}",
           before == 0 and after == 200 and "Simple Bookstore App" in body and root == 404)

    # 3단계: Gateway API
    missing = lab.kubectl("get", "gatewayclass", capture=True, check=False).returncode != 0
    k("apply", "--server-side", "-f", lab.GATEWAY_API_FILE)
    classes = wait_until(lambda: {c["metadata"]["name"]: c["spec"]["controllerName"]
                                  for c in kj("get", "gatewayclass")["items"]} or None, 60)
    record("3 GatewayClass 자동 생성", "Gateway API CRD 설치", "CRD 전 리소스 없음, 후 istio·istio-remote",
           f"CRD 전 없음={missing}, 후 {classes}", missing and set(classes or {}) == {"istio", "istio-remote"})
    k("apply", "-f", SAMPLES / "bookinfo/gateway-api/bookinfo-gateway.yaml")
    k("rollout", "status", "deploy/bookinfo-gateway-istio", "--timeout=180s")
    gw_pod = kj("get", "deploy", "bookinfo-gateway-istio")["spec"]["template"]["spec"]["containers"][0]["name"]
    programmed = wait_until(lambda: next((c for c in kj("get", "gtw", "bookinfo-gateway").get("status", {}).get("conditions", [])
                                          if c["type"] == "Programmed"), None), 60)
    k("patch", "svc", "bookinfo-gateway-istio", "-p", '{"spec":{"ports":[{"port":80,"nodePort":30012}]}}')
    gw_status, _ = wait_until(lambda: (lambda r: r if r[0] == 200 else None)(http(30012)), 60) or (0, "")
    short = k("get", "gateway", "-o", "jsonpath={.items[0].apiVersion}")
    record("3 Gateway API 접속", "Gateway·HTTPRoute 적용 후 NodePort 30012로 변경",
           "게이트웨이 파드 자동 생성, 200", f"Deployment bookinfo-gateway-istio({gw_pod}), Programmed={programmed and programmed['status']} "
           f"({programmed and programmed['reason']}), 30012 {gw_status}, kubectl get gateway → {short}",
           gw_pod == "istio-proxy" and gw_status == 200 and short.startswith("gateway.networking.k8s.io"))
    k("annotate", "gtw", "bookinfo-gateway", "networking.istio.io/service-type=NodePort", "--overwrite")
    fixed = wait_until(lambda: next((c["status"] == "True" for c in kj("get", "gtw", "bookinfo-gateway")["status"]["conditions"]
                                     if c["type"] == "Programmed"), False), 60)
    port = kj("get", "svc", "bookinfo-gateway-istio")["spec"]["ports"]
    record("3 Programmed 상태", "Gateway에 service-type=NodePort 주석", "Programmed=True, NodePort 유지",
           f"Programmed={fixed}, ports={[(p['port'], p.get('nodePort')) for p in port]}, 30012 {http(30012)[0]}",
           fixed and any(p["port"] == 80 and p.get("nodePort") == 30012 for p in port) and http(30012)[0] == 200)

    # 4·5단계: Kiali와 Prometheus 연동
    k("apply", "-f", SAMPLES / "addons/kiali.yaml")
    k("patch", "svc", "kiali", "-n", "istio-system", "-p", '{"spec":{"type":"NodePort","ports":[{"port":20001,"nodePort":30020}]}}')
    k("rollout", "status", "deploy/kiali", "-n", "istio-system", "--timeout=300s")
    lab.traffic(10, "both", 0.1)
    no_host = wait_until(lambda: "no such host" in k("logs", "deploy/kiali", "-n", "istio-system", "--tail=200"), 90)
    record("4 Kiali 원본", "samples/addons/kiali.yaml 그대로 설치", "기본 주소의 Prometheus를 찾지 못함",
           f"로그 'prometheus.istio-system … no such host'={no_host}, 그래프 엣지 {len(kiali_edges())}개",
           no_host and not kiali_edges())
    original = (SAMPLES / "addons/kiali.yaml").read_text()
    anchor = "      prometheus:\n        enabled: true\n"
    mine = lab.STATE / "my-kiali.yaml"
    mine.write_text(original.replace(anchor, anchor + "        url: http://monitoring-prometheus.monitoring:9090\n"))
    k("apply", "-f", mine)
    k("rollout", "restart", "deploy/kiali", "-n", "istio-system")
    k("rollout", "status", "deploy/kiali", "-n", "istio-system", "--timeout=300s")
    connected = wait_until(lambda: "Prometheus connected" in k("logs", "deploy/kiali", "-n", "istio-system", "--tail=200")
                           or "prometheus" not in k("logs", "deploy/kiali", "-n", "istio-system", "--tail=200").lower(), 90)
    record("4 Kiali 주소 수정", "사본에 url 한 줄 추가 후 재적용", "연결되지만 Istio 메트릭이 없어 그래프 빔",
           f"연결={connected}, 그래프 엣지 {len(kiali_edges())}개", connected and not kiali_edges())
    k("apply", "-f", SAMPLES / "addons/extras/prometheus-operator.yaml")
    time.sleep(30)
    envoy = [t for t in lab_targets() if "envoy-stats" in t["scrapePool"]]
    record("5 샘플 모니터 원본", "prometheus-operator.yaml 그대로 적용(release: istio)", "Prometheus가 선택하지 않음",
           f"envoy-stats 대상 {len(envoy)}개", not envoy)
    monitors = lab.STATE / "my-monitors.yaml"
    monitors.write_text((SAMPLES / "addons/extras/prometheus-operator.yaml").read_text().replace("release: istio", "release: monitoring"))
    k("apply", "-f", monitors)
    up = wait_until(lambda: (lambda ts: ts if len([t for t in ts if "envoy-stats" in t["scrapePool"] and t["health"] == "up"]) >= 8
                             and any("istio-component" in t["scrapePool"] and t["health"] == "up" for t in ts) else None)(lab_targets()), 180, 5)
    record("5 모니터 라벨 수정", "release: monitoring으로 수정", "사이드카 8개·istiod 수집",
           f"envoy-stats UP {len([t for t in up or [] if 'envoy-stats' in t['scrapePool'] and t['health'] == 'up'])}개, "
           f"istiod UP {any('istio-component' in t['scrapePool'] and t['health'] == 'up' for t in up or [])}", bool(up))
    expected = {("istio-ingressgateway", "productpage-v1"), ("bookinfo-gateway-istio", "productpage-v1"),
                ("productpage-v1", "details-v1"), ("productpage-v1", "reviews-v1"), ("productpage-v1", "reviews-v2"),
                ("productpage-v1", "reviews-v3"), ("reviews-v2", "ratings-v1"), ("reviews-v3", "ratings-v1")}

    def graph_ready():
        lab.traffic(20, "both", 0.1)
        return kiali_edges() if expected <= kiali_edges() else None
    edges = wait_until(graph_ready, 240, 10) or kiali_edges()
    record("5 Kiali 그래프", "두 게이트웨이로 트래픽 전송", "게이트웨이 2개 → productpage → details·reviews → ratings",
           f"엣지 {len(edges)}개, 기대 엣지 포함={expected <= edges}", expected <= edges)

    # 6단계: Istio CNI로 전환
    k("delete", "-f", SAMPLES / "bookinfo/platform/kube/bookinfo.yaml")
    k("wait", "--for=delete", "pod", "-l", "app in (productpage,details,ratings,reviews)", "--timeout=180s")
    lab.istioctl("install", "-f", ROOT / "lab/istio-cni.yaml", "-y", capture=True)
    ds = kj("get", "ds", "istio-cni-node", "-n", "istio-system")["status"]
    ingress_port = [p.get("nodePort") for p in kj("get", "svc", "istio-ingressgateway", "-n", "istio-system")["spec"]["ports"] if p["port"] == 80]
    record("6 CNI 설치", "istioctl install -f lab/istio-cni.yaml", "노드마다 istio-cni-node 1개",
           f"DaemonSet ready {ds.get('numberReady')}/{ds.get('desiredNumberScheduled')} (노드 {nodes}개), 30011 유지={ingress_port == [30011]}",
           ds.get("numberReady") == nodes and ingress_port == [30011])
    deploy_bookinfo()
    spec = pod_spec("productpage")
    init = {c["name"]: c for c in spec["initContainers"]}
    sec = init.get("istio-validation", {}).get("securityContext", {})
    record("6 init 컨테이너 교체", "Bookinfo 재배포 후 조회", "istio-validation, 추가 권한 없음, root 아님, 읽기 전용",
           f"initContainers {list(init)}, add={sec.get('capabilities', {}).get('add')}, runAsUser={sec.get('runAsUser')}, "
           f"readOnlyRootFilesystem={sec.get('readOnlyRootFilesystem')}, 30011 {http(30011)[0]} / 30012 {http(30012)[0]}",
           list(init) == ["istio-validation", "istio-proxy"] and not sec.get("capabilities", {}).get("add")
           and sec.get("runAsNonRoot") and sec.get("readOnlyRootFilesystem") and http(30011)[0] == 200 and http(30012)[0] == 200)
    cni_rules, node_count = istio_rules("productpage")
    extra = sorted(cni_rules - init_rules)
    record("6 같은 핵심 규칙, 다른 설치자", "lab.py rules productpage (CNI 방식)", "init 방식의 규칙이 모두 있음, 노드에는 없음",
           f"init {len(init_rules)}개 → CNI {len(cni_rules)}개, 빠진 규칙 {len(init_rules - cni_rules)}개, 추가 {extra}, 노드 {node_count}개",
           init_rules <= cni_rules and node_count == 0)

    # 더 해보기: 받는 앱이 보는 주소
    k("create", "namespace", "no-mesh")
    for args in (["-f", SAMPLES / "curl/curl.yaml"], ["-f", SAMPLES / "httpbin/httpbin.yaml"],
                 ["-n", "no-mesh", "-f", SAMPLES / "httpbin/httpbin.yaml"]):
        k("apply", *args)
    k("wait", "--for=condition=Ready", "pod", "-l", "app in (curl,httpbin)", "-A", "--timeout=300s")
    curl_ip = kj("get", "pod", "-l", "app=curl")["items"][0]["status"]["podIP"]
    mesh = json.loads(k("exec", "deploy/curl", "--", "curl", "-s", "httpbin.default:8000/ip"))["origin"]
    plain = json.loads(k("exec", "deploy/curl", "--", "curl", "-s", "httpbin.no-mesh:8000/ip"))["origin"]
    xfcc = json.loads(k("exec", "deploy/curl", "--", "curl", "-s", "httpbin.default:8000/headers"))["headers"].get("X-Forwarded-Client-Cert", [""])[0]
    record("더 해보기 호출자 주소", "curl 파드에서 사이드카 있는/없는 httpbin 호출", "사이드카 쪽은 127.0.0.6, 신원은 XFCC",
           f"curl IP {curl_ip}, 메시 httpbin이 본 주소 {mesh}, 비메시 {plain}, XFCC URI=…{xfcc.split('URI=')[-1]}",
           mesh.startswith("127.0.0.6:") and plain.startswith(curl_ip + ":") and xfcc.endswith("URI=spiffe://cluster.local/ns/default/sa/curl"))

    # 더 해보기: 미러링
    k("apply", "-f", ROOT / "lab/mirror.yaml")
    time.sleep(10)
    lab.traffic(3, "istio", 0.2)
    time.sleep(35)
    before_counts = reviews_counts()
    stars = 0
    for _ in range(20):
        stars += http(30011)[1].count("glyphicon-star")
        time.sleep(0.2)
    after_counts = wait_until(lambda: (lambda c: c if c.get("reviews-v1", 0) - before_counts.get("reviews-v1", 0) >= 20
                                       and c.get("reviews-v2", 0) - before_counts.get("reviews-v2", 0) >= 20 else None)(reviews_counts()), 90, 5) \
        or reviews_counts()
    delta = {w: after_counts.get(w, 0) - before_counts.get(w, 0) for w in ("reviews-v1", "reviews-v2", "reviews-v3")}
    record("더 해보기 미러링", "lab/mirror.yaml 적용 후 페이지 20회", "사용자는 v1만(별점 0), v2에도 같은 수의 요청",
           f"별점 아이콘 {stars}개, 요청 증가 {delta}", stars == 0 and delta["reviews-v1"] == 20 and delta["reviews-v2"] >= 20 and delta["reviews-v3"] == 0)

    # 정리: 처음 상태로
    lab.reset()
    left = [c for c in k("get", "crd", "-o", "name").split() if c.endswith(".istio.io") or "gateway.networking.k8s.io" in c]
    ns = [n["metadata"]["name"] for n in kj("get", "ns")["items"]]
    label = kj("get", "ns", "default")["metadata"]["labels"].get("istio-injection")
    prom_ready = http(30090, "/-/ready")[0]
    record("정리 reset", "python3 lab.py reset", "Istio·CRD·라벨 제거, Prometheus 유지",
           f"남은 CRD {len(left)}개, istio-system 존재={'istio-system' in ns}, 라벨={label}, Prometheus {prom_ready}",
           not left and "istio-system" not in ns and label is None and prom_ready == 200)

    passed = sum(r["passed"] for r in RESULTS)
    summary = {
        "started": started, "finished": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "platform": f"{platform.system()} {platform.machine()}",
        "docker": lab.run(["docker", "version", "--format", "{{.Server.Version}}"], capture=True).stdout.strip(),
        "versions": {"kind": lab.KIND_VERSION, "kubernetes": lab.KUBE_VERSION, "istio": lab.ISTIO_VERSION,
                     "gateway_api": lab.GATEWAY_API_VERSION, "kube_prometheus_stack": lab.STACK_VERSION},
        "passed": passed, "total": len(RESULTS), "results": RESULTS,
    }
    (ROOT / "lab/검증 결과.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"\n{passed}/{len(RESULTS)} 통과. lab/검증 결과.json에 저장했습니다.")
    raise SystemExit(0 if passed == len(RESULTS) else 1)


def lab_targets():
    with urllib.request.urlopen("http://127.0.0.1:30090/api/v1/targets?state=active", timeout=10) as response:
        return json.load(response)["data"]["activeTargets"]


if __name__ == "__main__":
    main()
