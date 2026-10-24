# 스프린트 4 — 직접 바꾸고 화면으로 확인하는 실습

**처음에는 [실습.md](실습.md)를 따라간다.** 실제 Kubernetes에 ServiceMonitor를 만들고, 연결을 끊었다가 고치고, Grafana 쿼리와 파드 라벨을 바꾸며 기능을 익힌다. 준비만 자동화하며, 단계별 조작은 사용자가 직접 한다.

기존의 수치·연산 중심 PoC는 [자동 검증.md](<자동 검증.md>)로 옮겨 보조 자료로 남겼다. `run.py`도 유지한다.

## 시작

Docker Desktop/Docker Engine을 켠 뒤, 저장소 루트에서:

```bash
cd 'infra/쿠버네티스 스프린트 4'
python3 lab.py setup
python3 lab.py ui
```

`setup`은 전용 kind 클러스터와 실제 모니터링 도구를 설치한다. 처음에는 이미지 다운로드로 몇 분 걸릴 수 있다. 도구 바이너리는 공식 SHA-256과 대조해 이 폴더의 `.lab/bin/`에 받는다. 글로벌 설치는 하지 않는다.

`ui` 터미널은 켜 두고, 다른 터미널에서도 같은 폴더로 이동해 **[실습.md의 1단계](실습.md)**부터 시작한다.

- Prometheus: <http://127.0.0.1:19090>
- Grafana: <http://127.0.0.1:13000> — `admin` / `study-local-only`
- NGINX 원시 메트릭: <http://127.0.0.1:10254/metrics>

Grafana에서는 **Sprint 4 - 직접 바꾸는 모니터링**을 열어 **Save as copy** 후 사본의 패널을 수정한다. Kubernetes·Grafana의 측정값은 실행 때마다 달라지므로 고정된 CPU·메모리 숫자를 맞힐 필요가 없다.

## 내가 직접 재현할 기능

| 직접 조작 | 직접 확인할 것 |
| --- | --- |
| NGINX에 HTTP 요청 보내기 | 원시 메트릭에 값이 쌓임 |
| ServiceMonitor 생성·라벨 수정 | 객체 존재와 Prometheus job 선택의 차이 |
| port 이름·path 변경 후 복구 | 대상 없음 / DOWN·404 / UP의 차이 |
| 노드 정보 조인·Grafana 범례 변경 | IP → 노드 이름 |
| 파드 메모리에 업무 라벨 조인 | 전체 앱 → frontend 파드만 표시 |
| Deployment 라벨·레플리카 변경 | 쿼리를 그대로 두고 패널 대상이 늘어남 |
| 노드 resource 라벨 변경 | high-spec 패널의 노드 선택이 달라짐 |

## 구성 파일

| 파일 | 역할 |
| --- | --- |
| [실습.md](실습.md) | 단계별 명령·손으로 바꿀 값·화면·복구 방법 |
| [lab.py](lab.py) | 준비·UI 포워딩·전용 kubectl·요청 보내기 |
| [kind.yaml](lab/kind.yaml) | control-plane 1개 + worker 1개 |
| [monitoring-values.yaml](lab/monitoring-values.yaml) | 실제 Operator·Prometheus·Grafana·상태/노드 exporter |
| [ingress-values.yaml](lab/ingress-values.yaml) | NGINX 메트릭 노출. SM은 자동 생성하지 않음 |
| [apps.yaml](lab/apps.yaml) | 실제 frontend 2개·backend 1개와 포탈 Ingress |
| [servicemonitor.yaml](lab/servicemonitor.yaml) | 처음에 틀린 release 라벨로 만드는 실험 파일 |
| [servicemonitor-working.yaml](lab/servicemonitor-working.yaml) | 정상 상태 복구 파일 |
| [dashboard.yaml](lab/dashboard.yaml) | 사용자가 복사해 수정할 시작 대시보드 |
| [ServiceMonitor.md](ServiceMonitor.md) / [PromQL 조인.md](<PromQL 조인.md>) | 강의별 개념·근거 |
| [자동 검증.md](<자동 검증.md>) / [run.py](run.py) | 기존 29개 자동 검증. 계산을 더 확인하고 싶을 때 |
| [점검 기록.md](<점검 기록.md>) | 문서 점검 및 실습 검증 기록 |

## 고정 버전과 범위

| 도구 | 버전 |
| --- | --- |
| kind | 0.30.0 |
| Kubernetes / kubectl | 1.34.0. kind 노드 이미지는 릴리스의 SHA-256 digest 고정 |
| Helm | 3.19.0 |
| kube-prometheus-stack | 77.6.0 — Operator 0.85.0, Prometheus 3.5.0 |
| ingress-nginx 차트 | 4.14.4 — controller 1.14.4 |
| 예제 앱 | nginx:1.28.0-alpine |

기존 강의의 ingress-nginx를 로컬에서 재현하는 버전이다. 프로젝트 종료 안내와 실습 한계는 [실습.md](실습.md)에 적었다. 새 운영 환경에 배포하는 가이드가 아니다.

전용 kubeconfig는 `.lab/kubeconfig`에 보관한다. `lab.py k`는 여기에 기록한 context를 지정하며, `~/.kube/config`와 사용자의 현재 context를 바꾸지 않는다. 브라우저 포트는 127.0.0.1에만 연다. macOS·Linux arm64/amd64, Python 3.8 이상을 대상으로 한다. 실제 검증한 플랫폼은 점검 기록에 별도로 적는다.

kind 노드 두 개는 Docker VM을 공유하므로 실제 서로 다른 서버 사양·외부 방화벽·인증서 장애까지 재현하지 않는다. 실습의 `high-spec/low-spec`은 분류 라벨이다.

## 끝내기

UI 터미널에서 Ctrl+C를 누르면 접속만 닫히고 실습 데이터는 남는다. 다시 열 때는 `python3 lab.py ui`만 실행한다.

전용 클러스터와 학습 데이터를 지울 때:

```bash
python3 lab.py down
```

다른 Docker 컨테이너는 종료하지 않는다. 도구 다운로드 캐시는 `.lab/bin/`에 남는다. `setup` 재실행은 설치 values·시작 대시보드·앱 템플릿을 다시 적용하므로, 실습 도중에는 UI만 재실행한다.
