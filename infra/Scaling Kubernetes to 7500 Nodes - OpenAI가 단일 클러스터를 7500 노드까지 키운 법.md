# Scaling Kubernetes to 7,500 Nodes - OpenAI가 단일 클러스터를 7,500 노드까지 키운 법

## 출처
- **아티클/논문**: Scaling Kubernetes to 7,500 nodes
- **저자/출처**: OpenAI Engineering Blog
- **링크**: https://openai.com/index/scaling-kubernetes-to-7500-nodes/

---

## AI 요약

### 1. 배경: 왜 "거대한 단일 클러스터"인가?

OpenAI는 GPT, DALL·E 같은 대규모 모델 학습을 위해 Kubernetes를 **연구 인프라의 기반**으로 사용한다. 앞선 글("Scaling to 2,500 nodes")에 이어, 이번에는 **7,500 노드** 규모까지 확장한 경험을 다룬다.

핵심 철학은 "**작은 클러스터 여러 개보다 큰 클러스터 하나**"다.

| 관점 | 큰 단일 클러스터의 이점 |
|------|------------------------|
| 연구 속도 | 연구팀이 코드를 바꾸지 않고도 규모를 키울 수 있음 |
| 자원 이동 | 실험 간 자원 재배치가 매끄러움(파편화 최소화) |
| 운영 단순성 | 관리해야 할 컨트롤 플레인 수가 적음 |
| MPI 통신 | 한 작업의 모든 파드가 같은 클러스터·같은 저지연 네트워크에 위치 |

> 워크로드 특성: 전형적인 웹 서비스(수많은 작은 stateless 파드)와 정반대다. **하나의 거대한 배치 학습 작업**이 수천 개 GPU를 gang scheduling으로 한꺼번에 점유한다. CPU 사용량은 낮지만 **GPU·네트워크(InfiniBand)** 를 극한까지 쓴다.

---

### 2. 네트워킹: Flannel → 네이티브 파드 네트워킹

노드가 수천 대로 늘자 Flannel의 오버레이(VXLAN) 방식이 처리량 병목이 되었다.

```
[ Flannel / VXLAN 방식 ]
  파드 → 노드에서 패킷 캡슐화(encapsulation) → 가상 라우트 → 목적지 노드에서 디캡슐화 → 파드
        └ 오버헤드: 캡슐화 + 가상 라우팅 테이블

[ Azure CNI / 네이티브 직접 라우팅 ]
  파드 IP ──────── 직접 라우팅 ──────── 파드 IP
        └ 노드와 파드가 같은 IP 대역, 캡슐화 없음
```

- Azure(AKS)에서 **Azure VMSS + 커스텀 CNI**를 사용해 직접 라우팅 채택
- 패킷 캡슐화·가상 라우트가 사라져 **파드↔파드 통신이 노드 내부 통신만큼 빠름**
- IP 주소 관리를 위해 CIDR(예: `10.0.0.0/8`) 기반으로 트래픽을 표시하고 `iptables-exporter`로 대역별 사용량을 관측
- 외부 트래픽은 **전용 NAT 호스트**를 통해 나가도록 분리(hub-and-spoke 격리)
- 모델 학습의 all-reduce 등 집합 통신은 Kubernetes 네트워크가 아니라 **InfiniBand** 위에서 직접 이루어진다

---

### 3. 컨트롤 플레인: API Server & etcd

7,500 노드 규모에서 가장 큰 부담을 받는 곳은 컨트롤 플레인이다.

```
        ┌──────────────── 클러스터 외부 (전용 노드) ────────────────┐
        │   API Server × 5              etcd × 5                    │
        │   (heap 최대 ~70GB/서버)      (events는 별도 디스크로 분리) │
        └───────────────────────────────────────────────────────────┘
                         ▲                    ▲
                         │ watch/list         │
             ┌───────────┴─────────┐          │
          Kubelet(수천)      Controller/Scheduler
```

| 항목 | 설정/수치 |
|------|-----------|
| API Server 수 | 최대 **5대** (전용 노드) |
| etcd 노드 수 | **5대** (전용 노드) |
| API Server 힙 | 서버당 최대 **~70GB** |
| etcd 이벤트 | Kubernetes **Events를 별도 etcd·별도 디스크**에 저장해 메인 상태 저장소 부하 분리 |
| 부하 원인 | `List`/`Watch`가 가장 비쌈. 특히 대량 `WATCH`가 API Server 메모리를 밀어올림 |

**EndpointSlices의 위력**: Kubernetes 1.17에서 도입된 EndpointSlices는 기존 Endpoints 오브젝트가 서비스마다 전체 파드 목록을 한 덩어리로 관리하던 방식을 조각내어, **네트워크 관련 부하를 약 1000배 감소**시켰다.

또한 각 노드의 kubelet이 모든 서비스 변경을 감시하지 않도록 하고, 비싼 `LIST` 대신 캐시된 조회를 쓰도록 클라이언트 동작을 튜닝했다.

---

### 4. 스케줄링: Gang Scheduling · Taints · Balloon

#### Gang Scheduling
분산 학습 작업은 "**전부 켜지거나, 전부 안 켜지거나**"여야 한다. 파드 절반만 스케줄되면 나머지를 기다리며 GPU만 낭비된다.
- Kubernetes 1.18+ **Coscheduling 플러그인**으로 한 작업의 파드들을 한꺼번에(gang) 배치

#### Team Taints & Tolerations
- `team-resource-manager`가 노드에 팀별 taint를 부여 → 팀이 확보한 자원을 다른 팀이 침범하지 못하게 함
- toleration으로 팀 경계를 넘는 유연한 스케줄링도 허용

#### Balloon(풍선) Deployment — 스케일다운 방지
```
빈 노드 ──> 낮은 우선순위 "balloon" 파드가 미리 채워둠(anti-affinity로 골고루 분산)
   │
   └─ 진짜 작업이 오면 balloon 파드는 preempt(밀려남) → 즉시 자리 확보
   └─ cluster-autoscaler가 노드를 성급히 축소하지 못하게 완충
```
- cluster-autoscaler: **min size = 0, max size = 가용 용량**으로 설정
- 한 번에 너무 많은 노드가 join하면 API Server가 과부하 → **노드 추가를 점진적으로(smoothing)** 진행

---

### 5. 관측성(Observability)과 헬스체크

| 영역 | 방식 |
|------|------|
| 메트릭 | **Prometheus + Grafana** (시계열) |
| DNS | CoreDNS. 수천 노드에서 DNS 쿼리 폭증 → 캐싱/노드로컬 DNS로 완화 |
| Passive 헬스체크 | 네트워크·디스크·GPU 상태를 상시 모니터링 |
| Active GPU 테스트 | 부팅 시 및 주기적으로 GPU 유효성 검증 |
| 불량 노드 처리 | 자동 감지 후 cordon/drain → 교체 |

**아직 못 푼 숙제(글 기준)**:
- Prometheus TSDB 컴팩션이 느려 재시작 시간이 길어짐(WAL 재생 병목)
- 파드 네트워크 트래픽 셰이핑(대역폭 관리)
- 외부 의존성에 대한 인터넷 대역폭 제약

---

## 내가 얻은 인사이트

### 아키텍처 관점
1. **"확장은 워크로드 특성에서 출발한다"**
   - OpenAI의 결론이 "큰 단일 클러스터"인 이유는 그들의 작업이 *하나의 거대한 gang job*이기 때문이다. 마이크로서비스 트래픽이라면 오히려 클러스터를 쪼개는 게 정답이었을 수 있다. 남의 스케일 전략을 복붙하지 말고 **내 워크로드의 통신·자원 패턴**부터 봐야 한다.

2. **컨트롤 플레인이 진짜 병목**
   - 노드가 아니라 **API Server의 List/Watch와 etcd**가 먼저 무너진다. EndpointSlices(1000x), Events 분리, 클라이언트 LIST 최소화 같은 처방이 전부 "**컨트롤 플레인으로 가는 트래픽을 어떻게 줄일까**"에 수렴한다.

### 운영 관점
3. **오버레이 네트워크의 비용은 스케일에서 폭발한다**
   - 소규모에선 무시되던 VXLAN 캡슐화 오버헤드가 수천 노드·GPU 통신에선 치명적. 가능하면 **직접 라우팅(no-encapsulation) CNI**를 택하는 게 대규모의 정석.

4. **Balloon 파드 — "미리 낭비해서 나중에 아낀다"**
   - 낮은 우선순위 파드로 노드를 미리 채워두는 발상이 인상적이다. autoscaler의 성급한 스케일다운과 노드 join 폭주를 동시에 막는 **완충 장치**. preemption을 자원 관리 도구로 쓰는 좋은 예.

### 트레이드오프 관점
5. **단일 거대 클러스터 = 단순함 vs 폭발 반경(blast radius)**
   - 하나로 묶으면 연구 속도와 운영 단순성을 얻지만, **컨트롤 플레인 하나가 죽으면 전부 멈춘다**. OpenAI는 API Server/etcd를 워크로드 노드에서 물리적으로 분리하고 5중화하는 것으로 이 리스크를 상쇄했다. 즉 "단일 클러스터의 단순함"은 **컨트롤 플레인을 강하게 격리·다중화**해야 성립한다.

---

### 참고 소스
- [Scaling Kubernetes to 7,500 nodes | OpenAI](https://openai.com/index/scaling-kubernetes-to-7500-nodes/)
- [Scaling Kubernetes to 2,500 nodes | OpenAI](https://openai.com/index/scaling-kubernetes-to-2500-nodes/)
- [How OpenAI Scaled Kubernetes to 7500 Nodes | Better Stack](https://newsletter.betterstack.com/p/how-openai-scaled-kubernetes-to-7500)
- [Scaling Kubernetes to 7500 nodes | 01cloud Engineering](https://engineering.01cloud.com/2024/02/07/scaling-kubernetes-to-7500-nodes/)
