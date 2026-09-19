# Ray를 활용한 분산 처리 - Task·Actor 모델과 GPU 워크로드 스케줄링

## 출처

- **아티클**: Ray v2 Architecture (공식 Ray 2.0 아키텍처 백서)
- **저자/출처**: Ray 코어 팀 / Anyscale (Stephanie Wang 외)
- **링크**: [https://docs.ray.io/en/latest/ray-contribute/whitepaper.html](https://docs.ray.io/en/latest/ray-contribute/whitepaper.html)

---

## AI 요약

### 1. Ray란?

Ray는 파이썬/자바 함수와 클래스를 **분산 환경에서 그대로 실행**하게 해주는 범용 분산 컴퓨팅 프레임워크다. 핵심 추상화는 단 두 가지 — **Task(상태 없는 원격 함수)**와 **Actor(상태를 가진 원격 객체)** — 이며, 이 둘이 하나의 동적 실행 엔진 위에서 돈다. OSDI 2018 원논문은 Ray가 **초당 180만(1.8M) 태스크** 이상으로 스케일링됨을 보고했다.

### 2. 프로그래밍 모델 — Task / Actor

**Task (`@ray.remote` 함수)**: 원격 함수를 호출하면 즉시 `ObjectRef`(future)를 반환하고, 실제 계산은 비동기로 분산 실행된다.

```python
import ray
ray.init()

@ray.remote(num_gpus=1)          # GPU 1장을 요구하는 태스크
def train_shard(data):
    import torch
    model = build_model().cuda()
    return train(model, data)    # 학습된 가중치 반환

# .remote() 호출 → 즉시 ObjectRef 반환 (논블로킹)
refs = [train_shard.remote(shard) for shard in shards]

# ray.get() → 결과가 준비될 때까지 블로킹
results = ray.get(refs)

# ray.wait() → 먼저 끝난 것부터 처리 (스트리밍 패턴)
ready, not_ready = ray.wait(refs, num_returns=1)
```

**Actor (`@ray.remote` 클래스)**: 상태를 유지하는 워커. 메서드 호출은 큐잉되어 **호출자별로 제출 순서대로(직렬)** 실행된다. 파라미터 서버, GPU 모델 서빙 인스턴스 등에 적합하다.

```python
@ray.remote(num_gpus=1)
class ParameterServer:
    def __init__(self, dim):
        self.weights = np.zeros(dim)
    def apply_gradients(self, *grads):
        self.weights += sum(grads) / len(grads)
        return self.weights

ps = ParameterServer.remote(dim=1_000_000)   # 핸들 즉시 반환
new_w = ray.get(ps.apply_gradients.remote(g1, g2))
```

| API | 의미 |
|-----|------|
| `@ray.remote` | 함수/클래스를 Task/Actor로 등록 |
| `f.remote(x)` | Task 비동기 실행, `ObjectRef` 반환 |
| `Cls.remote()` | Actor 인스턴스 생성, 핸들 반환 |
| `ray.get(ref)` | future 결과 블로킹 조회 |
| `ray.wait(refs, num_returns=k)` | 먼저 끝난 k개 반환 (논블로킹 진행) |
| `ray.put(obj)` | 객체를 object store에 저장 |
| `num_cpus / num_gpus` | 태스크·액터의 자원 요구량 명시 |

### 3. 시스템 아키텍처

```
                          ┌─────────────────────────────┐
                          │        Head Node            │
                          │  ┌───────────────────────┐  │
                          │  │  GCS (Global Control  │  │  ← 액터 위치, 노드 멤버십,
                          │  │  Service)             │  │     placement group 메타데이터
                          │  └───────────────────────┘  │
                          │   Driver (ray.init())       │
                          └──────────────┬──────────────┘
                                         │ (heartbeat / metadata)
              ┌──────────────────────────┼──────────────────────────┐
              ▼                                                      ▼
   ┌────────────────────────┐                         ┌────────────────────────┐
   │      Worker Node A      │                         │      Worker Node B      │
   │ ┌────────────────────┐ │                         │ ┌────────────────────┐ │
   │ │  Raylet            │ │  ── spillback (자원부족) ─▶ │ │  Raylet            │ │
   │ │  • Scheduler       │ │                         │ │  • Scheduler       │ │
   │ │  • Plasma Store ◀──┼─┼─── object transfer ─────┼─┼─▶ • Plasma Store    │ │
   │ └────────────────────┘ │     (zero-copy)         │ └────────────────────┘ │
   │ Worker1[ownership tbl] │                         │ Worker3[ownership tbl] │
   │ Worker2  (GPU0)        │                         │ Worker4  (GPU0)        │
   └────────────────────────┘                         └────────────────────────┘
```

- **Driver**: `ray.init()`를 실행하는 루트. 태스크를 제출하지만 직접 실행은 안 함.
- **Worker Process**: Task/Actor를 실제 실행. 각 워커는 자신이 소유한 객체의 **ownership table**과 작은 객체용 in-process store를 가짐.
- **Raylet** (노드당 1개 데몬): ① **Scheduler**(자원 할당·태스크 배치) + ② **Plasma Object Store**(큰 객체 저장·전송·스필링, 공유 메모리 zero-copy).
- **GCS (Global Control Service)**: 클러스터 수준 메타데이터(액터 위치, 노드 멤버십, placement group)를 key-value로 관리.

### 4. Ownership 모델 (Ray 2.0의 핵심 차별점)

OSDI 2018 원논문은 모든 객체 메타데이터를 중앙 GCS(Redis)에 저장했으나 병목이 되었다. Ray 1.0+ 이후 **분산 ownership 모델**을 도입:

- 각 객체에는 **owner**(보통 그 `ObjectRef`를 최초로 생성한 워커)가 있고, owner가 메타데이터·reference count·재구성용 lineage를 직접 관리한다.
- 덕분에 GCS는 객체 디렉터리 병목에서 벗어나고, **분산 가비지 컬렉션**이 자동으로 이뤄진다(모든 참조가 사라지면 데이터 자동 해제).

### 5. 분산 스케줄러 (bottom-up)

태스크는 먼저 로컬 raylet이 받고, 로컬 자원이 부족할 때만 다른 노드로 **spillback**(재배치)한다.

| 정책 | 설명 |
|---|---|
| Default Hybrid | 임계 자원 50% 전까지 packing, 이후 load-balancing |
| SPREAD | 노드 간 round-robin 분산 |
| Node Affinity | 특정 노드 hard/soft 타게팅 |
| Data Locality | 인자가 있는 raylet 우선 |
| **Placement Group** | 여러 노드에 걸쳐 bundle을 **원자적으로 예약** (분산 학습 gang scheduling 필수) |

**자원 모델**: `num_gpus`는 **논리적(logical) 자원**이다. Ray가 물리 GPU를 격리하는 게 아니라 스케줄링 회계 단위로만 쓰고 `CUDA_VISIBLE_DEVICES`를 설정해준다. 따라서 `num_gpus=0.5`처럼 **분수 GPU**도 지정 가능(여러 추론 태스크가 1장 공유).

### 6. GPU 워크로드 처리 — Ray AIR 라이브러리 군

| 라이브러리 | 용도 | GPU 활용 |
|---|---|---|
| **Ray Train** | 분산 학습 | `ScalingConfig(num_workers=N, use_gpu=True)`. 각 워커는 Actor + PyTorch DDP, 통신 백엔드 자동 **NCCL** |
| **Ray Tune** | 하이퍼파라미터 튜닝 | trial마다 `num_gpus` 할당, ASHA/PBT 조기 종료 |
| **Ray Serve** | 분산 추론 | 모델을 Actor로 배포, 분수 GPU로 1장에 여러 모델 패킹/샤딩, 오토스케일링 |
| **RLlib** | 강화학습 | parameter-server 액터 + 다수 rollout worker 액터 |

---

## 내가 얻은 인사이트

### 아키텍처 선택 관점

1. **왜 Spark/MPI가 아니라 Ray인가.**
   - Spark는 BSP(bulk-synchronous) 데이터 병렬 배치에 최적화돼 동적·비균질·상태 있는 AI 워크로드(RL rollout, 비동기 파라미터 서버, 가변 길이 LLM 추론)에는 표현력이 부족하다.
   - MPI는 빠르지만 정적 통신 패턴·수동 자원 관리·취약한 장애 내성이 단점.
   - Ray는 Task(stateless)와 Actor(stateful)를 한 모델로 통합하고 동적 태스크 그래프 + lineage 재구성을 제공해 "범용 파이썬 코드 분산화"에서 우위.

2. **`num_gpus`는 물리 격리가 아니라 논리적 회계**라는 점을 반드시 이해해야 한다.
   - Ray는 `num_gpus`에 맞춰 `CUDA_VISIBLE_DEVICES`만 설정할 뿐 GPU 메모리를 강제 격리하지 않는다.
   - `num_gpus=0.5`로 분수 할당 시 같은 GPU에 두 태스크가 올라가는데, 합산 메모리가 초과하면 OOM. 추론 패킹(Ray Serve)에서 자주 쓰지만 메모리 회계는 사용자 책임.

### 운영 관점

3. **Placement Group은 분산 학습의 숨은 필수 요소다.**
   - DDP/멀티노드 학습은 모든 워커가 동시에 떠 있어야 NCCL all-reduce가 성립한다.
   - Placement Group의 원자적 bundle 예약이 gang scheduling 역할을 해, 일부 GPU만 잡힌 채 영원히 대기하는 deadlock을 막는다. Ray Train이 내부적으로 사용.

4. **Ownership 모델 = 확장성의 비결이자 장애 내성의 함정.**
   - 메타데이터를 owner 워커로 분산시켜 GCS 병목을 없앤 것이 180만 tasks/s 확장성의 핵심.
   - 반대로 객체·태스크가 owner와 fate-share하므로 **owner(특히 driver)가 죽으면 하위 결과가 통째로 날아간다.** 장기 서비스라면 `detached` 액터나 체크포인트로 driver 의존성을 끊어야 한다.

5. **단일 head 노드(GCS)가 SPOF**라는 운영 리스크.
   - 워커 노드 장애는 견디지만 GCS를 호스팅하는 head 노드가 죽으면 클러스터가 멈춘다. 프로덕션에서는 GCS Fault Tolerance(외부 Redis 백업)와 head 노드 HA를 검토.
   - Plasma object store의 30% RAM 한도와 spilling 경로(디스크 IOPS)가 대용량 텐서 셔플 성능을 좌우하므로, spilling 디렉터리를 빠른 NVMe로 지정하는 것이 좋다.
