# Server-Side Apply - `kubectl apply`를 하면 실제로 무슨 일이 벌어지는가

## 출처
- **아티클/논문**: Server-Side Apply
- **저자/출처**: Kubernetes Official Documentation
- **링크**: https://kubernetes.io/docs/reference/using-api/server-side-apply/

---

## AI 요약

### 1. 문제: `kubectl apply`는 원래 "클라이언트"가 다 했다

`kubectl apply`의 목적은 "**내가 원하는 상태를 선언하면, 나머지는 건드리지 말고 그것만 맞춰줘**"다. 그런데 이걸 어떻게 구현하느냐가 v1.22를 기점으로 완전히 바뀌었다.

| 구분 | Client-Side Apply (CSA, 구방식) | Server-Side Apply (SSA, 현재 기본) |
|------|-------------------------------|-----------------------------------|
| 병합 위치 | **클라이언트(kubectl)** | **API Server** |
| 이전 상태 저장 | `last-applied-configuration` 애노테이션 | `.metadata.managedFields` |
| 병합 방식 | 3-way merge를 로컬에서 계산 | 서버가 필드별 소유권 기반 병합 |
| 필드 소유권 | 추적 불가 (암묵적 단일 소유) | **필드별 명시적 다중 소유자 추적** |
| 충돌 감지 | 없음 | 있음 (다른 매니저 소유 필드 수정 시) |

> **3-way merge**란? CSA는 ①last-applied(과거 내가 보낸 것) ②live object(현재 서버 상태) ③desired(지금 보내는 것) 세 개를 비교해, "내가 예전에 넣었다가 이번에 뺀 필드"를 지우고 나머지는 유지했다. 이 계산을 전부 클라이언트가 했기 때문에, **누가 어떤 필드를 소유하는지** 서버는 전혀 몰랐다.

---

### 2. SSA에서 `kubectl apply` 요청의 흐름

```
kubectl apply -f config.yaml
        │
        │  HTTP PATCH
        │  Content-Type: application/apply-patch+yaml
        │  ?fieldManager=kubectl        ← 나는 누구인가(매니저 식별)
        │  Body: 내가 의견을 가진 필드들만 (부분 오브젝트)
        ▼
┌──────────────────────── API Server ────────────────────────┐
│  ① 충돌 검사: 내가 바꾸려는 필드를 다른 매니저가 소유하는가? │
│  ② managedFields 갱신: 어떤 필드를 누가 소유하는지 기록      │
│  ③ 병합: 내 의도(intent)를 live 오브젝트와 merge            │
│  ④ 저장: 갱신된 managedFields와 함께 etcd에 영속화          │
└─────────────────────────────────────────────────────────────┘
```

핵심은 **"내가 보낸 필드 = 내가 소유를 주장하는 필드"** 라는 점이다. Body에 넣지 않은 필드는 소유를 주장하지 않는다.

---

### 3. managedFields 구조 — 누가 무엇을 소유하는가

모든 오브젝트는 `.metadata.managedFields`에 필드별 소유권을 기록한다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-cm
  managedFields:
  - manager: kubectl          # 소유자(applier) 식별자
    operation: Apply          # Apply(SSA) 또는 Update(PUT/일반 PATCH)
    apiVersion: v1
    time: "2026-07-12T00:00:00Z"
    fieldsType: FieldsV1
    fieldsV1:                 # 이 매니저가 소유를 주장하는 필드 트리
      f:metadata:
        f:labels:
          f:test-label: {}
      f:data:
        f:key: {}
  labels:
    test-label: test
data:
  key: some value
```

| 필드 | 의미 |
|------|------|
| `manager` | 누가 소유하는가 (kubectl, 컨트롤러 이름 등) |
| `operation` | `Apply`(SSA) vs `Update`(전통적 PUT/PATCH) |
| `fieldsV1` | 이 매니저가 소유한 필드들의 선언적 트리 |
| `time` | 마지막 수정 시각 |

> `kubectl get`은 기본적으로 managedFields를 숨긴다. `--show-managed-fields`(json/yaml 출력 시)로 확인.

---

### 4. 충돌(Conflict)과 해결

**충돌이 발생하는 조건 (둘 다 성립할 때):**
1. 내가 적용하려는 필드의 값이 현재 값과 다르고
2. **그 필드를 다른 매니저가 소유**하고 있음

```
Manager A가 replicas=3 소유 중
        │
Manager B가 replicas=5로 apply 시도
        ▼
   HTTP 409 Conflict
   "conflicting fields: [spec.replicas]"
```

이는 **다른 사람이 설정한 값을 실수로 덮어쓰는 것을 방지**하는 안전장치다.

**해결 3가지 방법:**

| 방법 | 동작 |
|------|------|
| **① 강제(force)** | `--force-conflicts`. 값을 덮어쓰고 **소유권을 내게로 가져옴**(다른 매니저의 managedFields 항목에서 제거) |
| **② 소유 포기** | 매니페스트에서 그 필드를 **빼면** 소유권을 반납 |
| **③ 값 일치(공유)** | 현재 값과 **같은 값**으로 apply → 충돌 없이 **공유 소유(shared ownership)**. 이후 누구든 바꾸면 충돌 |

---

### 5. 병합 전략 — 리스트/맵을 어떻게 합치는가

SSA의 진가는 **리스트를 통째로 덮어쓰지 않고 키 기준으로 병합**하는 데 있다.

| listType | 동작 | 예시 |
|----------|------|------|
| **map** (associative) | 키(예: 컨테이너 `name`, env `name`) 기준 병합 | env에 VAR2 추가해도 VAR1 유지 |
| **set** | 값 기준 병합, 순서 무관 | `finalizers` — 다른 매니저가 넣은 것과 합쳐짐 |
| **atomic** | 리스트 전체를 원자적으로 교체(병합 안 함) | CRD가 atomic 지정 시 통째로 대체 |

```yaml
# 기존: env에 VAR1=old
# 내 apply: VAR1=new 로 바꾸고 VAR2 추가
spec:
  containers:
  - name: app          # ← 이 key로 매칭
    env:
    - name: VAR1
      value: new       # 갱신
    - name: VAR2
      value: added     # 추가
# 결과: VAR1 갱신 + VAR2 추가 (다른 컨테이너/env는 그대로)
```

---

### 6. Apply vs Update, 그리고 컨트롤러

| 항목 | Apply (SSA, PATCH) | Update (PUT, `kubectl replace`) |
|------|--------------------|-------------------------------|
| 충돌 감지 | 다른 매니저 소유 필드면 실패 | 절대 실패 안 함(전체 덮어씀) |
| fieldManager | 필수 쿼리 파라미터 | 선택(User-Agent에서 추론) |
| 병합 | 소유권·병합 전략 존중 | spec 전체 교체 |

**컨트롤러/오퍼레이터에서의 활용**: 컨트롤러가 SSA로 자기 이름(`fieldManager=my-operator`)을 달고 필드를 쓰면,
- managedFields에 컨트롤러 소유가 드러나 **감사(audit) 추적** 가능
- 다른 도구가 그 필드를 건드리면 충돌로 감지 → **오너십 경계**가 명확해짐

```bash
kubectl apply -f config.yaml --dry-run=server   # 서버 기준 미리보기
kubectl apply -f config.yaml --server-side=false # 옛 CSA 방식 강제
```

---

## 내가 얻은 인사이트

### 아키텍처 관점
1. **"오너십을 클라이언트에서 서버로 옮긴 것"이 본질**
   - SSA의 진짜 변화는 문법이 아니라 **진실의 원천(source of truth)의 이동**이다. 예전엔 "내가 마지막에 뭘 보냈는지"를 애노테이션에 적어 클라이언트가 기억했다. 이제는 서버가 **필드 단위로 누가 주인인지**를 안다. 이 덕분에 여러 액터(사람·CI·컨트롤러)가 **한 오브젝트를 필드별로 나눠 소유**하는 협업이 가능해졌다.

2. **원자성의 단위가 오브젝트 → 필드로 내려갔다**
   - CSA는 "이 오브젝트는 내 것"이었다면, SSA는 "이 필드는 내 것, 저 필드는 컨트롤러 것"이다. HPA가 `replicas`를 조정하는 동안 내가 이미지 태그만 바꿔도 서로 안 밟는다.

### 운영 관점
3. **`--force-conflicts`는 "덮어쓰기"가 아니라 "탈취"다**
   - 강제 적용은 값만 바꾸는 게 아니라 **소유권을 내게로 가져온다.** 무심코 CI에서 `--force-conflicts`를 쓰면, 컨트롤러가 관리하던 필드의 오너가 CI로 넘어와 이후 컨트롤러 조정과 계속 충돌할 수 있다. 강제는 "내가 이 필드의 주인이 되겠다"는 선언임을 알고 써야 한다.

4. **HPA와 replicas의 고전적 함정**
   - Deployment 매니페스트에 `replicas`를 적어두고 apply하면 내가 그 필드를 소유한다. 그런데 HPA도 `replicas`를 조정하려 한다 → **오토스케일이 apply할 때마다 되돌아가는** 문제. SSA 시대의 정석은 **매니페스트에서 `replicas`를 아예 빼서(② 소유 포기)** HPA에 소유를 넘기는 것.

### 트레이드오프 관점
5. **투명성 vs 복잡성**
   - managedFields는 "누가 무엇을 소유하는지"를 완전히 드러내지만, 그만큼 오브젝트 메타데이터가 커지고 디버깅이 복잡해진다(그래서 기본 출력에서 숨긴다). GitOps(ArgoCD/Flux)나 오퍼레이터가 많아진 환경일수록 이 필드 소유권 모델을 이해하지 못하면 **"왜 자꾸 값이 되돌아가지?"** 류의 유령 버그에 시달린다. SSA는 멀티 액터 환경을 위한 기능이고, 그 대가로 정신 모델의 복잡도를 요구한다.

---

### 참고 소스
- [Server-Side Apply | Kubernetes Docs](https://kubernetes.io/docs/reference/using-api/server-side-apply/)
- [KEP-555: Server-Side Apply | kubernetes/enhancements](https://github.com/kubernetes/enhancements/blob/master/keps/sig-api-machinery/555-server-side-apply/README.md)
- [Kubectl CSA/SSA (Client/Server Side Apply) | DEV Community](https://dev.to/cod3mason/til-kubectl-csaclient-side-apply-and-ssaserver-side-apply-20k4)
- [Kubernetes Apply: Client-Side vs. Server-Side | support.tools](https://support.tools/kubernetes-apply-client-side-vs-server-side/)
