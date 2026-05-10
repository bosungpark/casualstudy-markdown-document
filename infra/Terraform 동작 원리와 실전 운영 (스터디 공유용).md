# Terraform 동작 원리와 실전 운영 (스터디 공유용)

> HashiCorp 공식 문서(developer.hashicorp.com/terraform) 기반으로 핵심만 정리한 스터디 노트.
> 레퍼런스보다 **"왜 이런 구조인지"** 를 한 번 훑는 게 목적.

---

## 0. 한 줄 요약

> **Terraform = "선언형 IaC + State 기반 차이 계산기"**.
> 사용자는 *원하는 상태(.tf)* 만 선언, Terraform이 *현재 상태(state)* 와 *실제(refresh)* 를 비교해 최소한의 변경을 계산·실행한다.

---

## 1. Terraform 동작 원리

### 1.1 Core 워크플로

```
[Write]  .tf 파일 작성
   ▼
[Init]   backend/provider/module 준비
   ▼
[Plan]   현재 state ↔ 실제 인프라 ↔ 원하는 config 비교 → 실행 계획
   ▼
[Apply]  계획을 실제로 적용 → state 갱신
   ▼
[Destroy] 자원 회수 (선택)
```

### 1.2 `init` 내부 동작

`terraform init` 한 번에 4가지가 일어남.

| 단계 | 하는 일 | 결과물 |
|---|---|---|
| Backend 초기화 | `backend "s3" {}` 같은 원격 state 설정 검증/마이그레이션 | `.terraform/terraform.tfstate` (포인터) |
| Provider 설치 | `required_providers` 에 명시된 플러그인 다운로드 | `.terraform/providers/` |
| Module 다운로드 | `source = "..."` 모듈을 로컬 캐시 | `.terraform/modules/` |
| Lock 파일 생성 | provider 버전/해시 고정 | `.terraform.lock.hcl` |

> **포인트**: `init` 은 멱등(idempotent). 같은 디렉터리에서 여러 번 실행해도 안전. 단, backend 변경 시 `-migrate-state` 또는 `-reconfigure` 필요.

### 1.3 `plan` 내부 동작

```
1) Config 파싱        : .tf → 내부 그래프(HCL → 추상 트리)
2) State 로드         : 원격/로컬에서 terraform.tfstate
3) Refresh            : 각 리소스를 provider에 "실제 상태 줘" 호출 (READ)
4) Diff 계산          : (실제 ≠ state) → drift, (config ≠ state) → 변경
5) DAG 순서로 정렬    : depends_on / 참조 기반
6) 출력               : create / update / replace / destroy 표시
```

`-refresh=false` 로 refresh 생략 가능 (속도 ↑, 정확도 ↓).
`-out=plan.tfplan` 으로 계획 저장 → CI 에서 *plan/apply 분리* 패턴에 사용.

### 1.4 `apply` 내부 동작

- `plan` 결과(또는 즉석 plan)를 그대로 실행.
- DAG 위상 정렬을 따라 **병렬 실행** (`-parallelism=10`, 기본 10).
- 리소스 하나가 끝날 때마다 **state 즉시 갱신** (중간 실패 대비).
- 실패 시 partial state 가 남으므로 다음 plan 에서 이어서 정정.

### 1.5 Provider 구조

```
[terraform core]  ← 그래프/스케줄러/state 엔진 (Go)
       │ gRPC plugin protocol
       ▼
[provider plugin]  ← AWS/GCP/Kubernetes/Helm/... (별도 바이너리)
       │ SDK (HashiCorp plugin SDK / Plugin Framework)
       ▼
[Cloud API]        ← AWS SDK, Kubernetes API 등
```

- Core 와 Provider 는 **gRPC** 로 통신 → 언어/벤더 독립.
- Provider 는 5가지 RPC 만 구현하면 됨: `Schema / Configure / Read / Plan / Apply`.
- Public Registry: registry.terraform.io. `hashicorp/aws`, `hashicorp/google`, `hashicorp/kubernetes` 등.

### 1.6 State 파일 구조 (`terraform.tfstate`)

JSON. 핵심 필드:

```jsonc
{
  "version": 4,
  "terraform_version": "1.9.x",
  "serial": 42,                  // 변경 카운터
  "lineage": "uuid",             // state 계보
  "outputs": { ... },
  "resources": [
    {
      "mode": "managed",         // managed | data
      "type": "aws_instance",
      "name": "web",
      "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
      "instances": [
        {
          "schema_version": 1,
          "attributes": { ... },        // 실제 속성 (id, ami, ...)
          "dependencies": ["aws_vpc.main", ...],
          "sensitive_attributes": [ ... ]
        }
      ]
    }
  ]
}
```

> **주의**: state 에는 **민감 정보(비밀번호, 키)** 가 평문으로 들어갈 수 있음 → 반드시 암호화된 원격 backend.

### 1.7 Refresh 과정

- `plan` / `apply` 시 기본으로 수행.
- 각 리소스에 대해 provider 의 `Read` RPC 호출.
- 결과를 state 에 반영(메모리상) 후 diff 계산.
- 단독 실행: `terraform apply -refresh-only` (state 만 갱신).
- 옛날 `terraform refresh` 명령은 1.5+ 부터 deprecated, 위 방식 권장.

### 1.8 Dependency Graph (DAG)

- HCL 파싱 후 **방향성 비순환 그래프** 생성.
- 간선의 출처: `attribute reference`, `depends_on`, `module` 경계.
- 위상 정렬 → 같은 레벨은 병렬, 의존 관계가 있으면 직렬.
- 시각화: `terraform graph | dot -Tsvg > graph.svg`.

### 1.9 병렬 처리

- 기본 `-parallelism=10`. 한 번에 최대 10개 리소스 동시 처리.
- API rate limit 을 만나면 `-parallelism=2~5` 로 낮춤.
- DAG 의존성 때문에 실제 병렬도는 그래프 폭이 한계.

---

## 2. State 관리 — Local vs Remote

### 2.1 Local state

- `terraform.tfstate` 가 작업 디렉터리에 생김.
- 단점: 협업 불가, 분실/충돌 위험, 민감정보 평문.
- 학습/일회성 실험에만 사용.

### 2.2 Remote state — 왜 필수인가

| 문제 | Remote state 가 푸는 방식 |
|---|---|
| 동시 작업 충돌 | **Locking** (DynamoDB / GCS / Consul / TFC) |
| 분실 | 클라우드 스토리지 versioning |
| 민감정보 노출 | 서버 측 암호화 + IAM |
| 협업 | 팀 전원이 같은 state 참조 |
| 출력 공유 | `terraform_remote_state` data source |

### 2.3 S3 backend (AWS)

```hcl
terraform {
  backend "s3" {
    bucket         = "my-tfstate"
    key            = "prod/network/terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    use_lockfile   = true        # Terraform 1.10+ S3 네이티브 락 (권장)
    # dynamodb_table = "tf-locks" # 1.10 이전 또는 호환 유지 시
  }
}
```

권장 설정:
- **Bucket Versioning ON** → state rollback 가능.
- **Server-side encryption (SSE-KMS)** → 민감정보 암호화.
- **Block Public Access** + IAM 최소권한.

### 2.4 GCS backend (GCP)

```hcl
terraform {
  backend "gcs" {
    bucket = "my-tfstate"
    prefix = "prod/network"
    # GCS 는 native locking 내장 (별도 설정 불필요)
  }
}
```

- **Object Versioning** 으로 state 히스토리 보관.
- **CMEK** (Customer-Managed Encryption Key) 권장.

### 2.5 Terraform Cloud / Enterprise

- HashiCorp 의 SaaS/온프렘 솔루션.
- State 저장/락/버저닝/팀권한/실행환경(Remote runs)/Sentinel 정책 일체 제공.
- `cloud {}` 블록으로 연결, CLI/VCS/API 트리거 가능.

```hcl
terraform {
  cloud {
    organization = "acme"
    workspaces { name = "prod-network" }
  }
}
```

---

## 3. Locking — 동시 apply 방지

### 3.1 왜 락이 필요한가

같은 state 를 두 사람이 동시에 apply 하면:
- A 의 변경이 끝나기 전 B 가 옛 state 기반으로 plan → **자원 중복 생성/덮어쓰기**.
- state 파일의 `serial` 충돌 → 데이터 손실 가능.

### 3.2 백엔드별 락 방식

| Backend | 락 방식 |
|---|---|
| S3 (1.10+) | 같은 버킷에 `<key>.tflock` 객체 생성 (네이티브) |
| S3 (~1.9) | DynamoDB 테이블 (`LockID` 파티션 키) 에 conditional write |
| GCS | 객체 메타데이터 기반 네이티브 락 |
| Terraform Cloud | 워크스페이스 단위 자동 락 |
| Consul / etcd | 분산 KV 의 세션/락 사용 |

### 3.3 DynamoDB locking (legacy/호환)

```hcl
backend "s3" {
  bucket         = "my-tfstate"
  key            = "prod/terraform.tfstate"
  region         = "ap-northeast-2"
  dynamodb_table = "tf-locks"
}
```

- 테이블 스키마: `LockID` (String) 단일 PK. 빌링 모드 PAY_PER_REQUEST 충분.
- 락 타임아웃 시 `terraform force-unlock <LOCK_ID>` (위험, 정말 죽은 락만).

### 3.4 락이 죽었을 때 (작업은 끝났는데 락이 풀리지 않고 남아있는 상태)

1. 다른 사용자/CI 가 진짜 작업 중인지 확인 (Slack/PR).
2. 종료 확인되면 `force-unlock`.
3. 자주 발생하면 CI 의 timeout/cancel 핸들러 재점검.

---

## 4. State Drift

### 4.1 Drift 란

- **실제 인프라 ≠ state** 인 상태.
- 원인: 콘솔에서 수동 변경, 다른 도구가 변경, AWS Auto Scaling 같은 외부 컨트롤러.

### 4.2 탐지

```bash
terraform plan -refresh-only       # 변경 없는 척하면서 drift 만 보여줌
terraform apply -refresh-only      # state 만 실제와 맞춤 (인프라는 안 건드림)
```

자동화: TFC drift detection, driftctl, AWS Config + Lambda.

### 4.3 Import 전략

이미 존재하는 자원을 Terraform 관리로 끌어오기.

**선언형 import block (1.5+)** — 권장:

```hcl
import {
  to = aws_s3_bucket.legacy
  id = "my-existing-bucket"
}

resource "aws_s3_bucket" "legacy" {
  bucket = "my-existing-bucket"
  # ...
}
```

→ `terraform plan -generate-config-out=generated.tf` 로 config 까지 자동 생성 가능.

**기존 CLI 방식**:

```bash
terraform import aws_s3_bucket.legacy my-existing-bucket
```

> **임포트 후 반드시 `plan` 으로 diff 0 확인**. 속성이 어긋나면 다음 apply 에서 의도치 않은 변경.

### 4.4 State 조작 — 선언형(권장) vs 명령형

> **원칙**: 모듈 리팩터링·관리 중단처럼 **재현/리뷰가 필요한 작업**은 선언형 블록으로. CLI `state mv` / `state rm` 은 일회성·응급용으로 한 단계 내려서 사용.

**`moved` 블록 (1.1+)** — 리소스 주소 변경 시 권장:

```hcl
moved {
  from = aws_s3_bucket.logs
  to   = module.storage.aws_s3_bucket.logs
}
```

- 모듈 추출/이름 변경 시 단순 주소 변경이 **destroy → create** 로 잘못 잡히는 걸 방지.
- plan 에 `# ... has moved to ...` 로 표시되고 변경 0.
- 코드에 남으니 PR 리뷰·CI 재현 가능. 적용 후 정리해도 무방.

**`removed` 블록 (1.7+)** — 관리 중단(자원은 보존):

```hcl
removed {
  from = aws_s3_bucket.legacy
  lifecycle {
    destroy = false   # state 에서만 제거, 실제 자원 보존
  }
}
```

- 단순히 `resource` 블록을 지우면 자동 destroy → 의도와 반대.
- `destroy = false` 로 자원은 살리고 관리만 해제.

**CLI 명령** (응급/일회성):

| 명령 | 용도 |
|---|---|
| `terraform state list` | 관리 중인 리소스 나열 |
| `terraform state show <addr>` | 단일 리소스 상세 |
| `terraform state mv` | 주소 이동 — **응급용**, 평시는 `moved` 블록 |
| `terraform state rm` | state 에서만 제거 — **응급용**, 평시는 `removed` 블록 |
| `terraform state pull/push` | state 백업/수동 갱신 (위험) |

---

## 5. Module 설계

### 5.1 모듈이란

> 입력(variables) → 리소스 묶음 → 출력(outputs) 을 캡슐화한 재사용 단위.

```
modules/network/
  ├─ main.tf       # 리소스 정의
  ├─ variables.tf  # 입력
  ├─ outputs.tf    # 출력
  ├─ versions.tf   # provider/terraform 버전
  └─ README.md
```

### 5.2 좋은 모듈 원칙

1. **단일 책임**: "VPC + 서브넷" 까지. "VPC + EKS + RDS" 는 너무 큼.
2. **합리적 기본값**: 90% 사용자는 변수 안 건드리고 동작.
3. **출력 우선**: 다른 모듈/스택이 참조할 값(ID, ARN, endpoint) 을 빠짐없이.
4. **버전 핀**: `source = "git::...//module?ref=v1.2.0"` 또는 Registry 의 `version = "~> 1.2"`.
5. **Provider 재선언 금지**: 모듈 내부에서 `provider {}` 블록을 새로 만들지 말 것 → 호출자 측에서 주입.

### 5.3 호출 예

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.5"

  name = "prod"
  cidr = "10.0.0.0/16"
  azs  = ["ap-northeast-2a", "ap-northeast-2c"]
}
```

### 5.4 Registry 종류

- **Public Registry**: registry.terraform.io (terraform-aws-modules/vpc 등 검증된 모듈).
- **Private Registry**: TFC/TFE, GitLab, Artifactory.
- **Git source**: 가장 단순, 태그 기반 버저닝.

---

## 6. Kubernetes + Terraform

### 6.1 두 가지 Provider

| Provider | 용도 |
|---|---|
| `kubernetes` | Deployment / Service / ConfigMap / Namespace 등 K8s 객체 직접 관리 |
| `helm` | Helm 차트 install/upgrade |

```hcl
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_ca)
  token                  = data.aws_eks_cluster_auth.this.token
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_ca)
    token                  = data.aws_eks_cluster_auth.this.token
  }
}
```

### 6.2 EKS / GKE 프로비저닝

전형적인 스택 분리:

```
1) network-stack   : VPC, Subnet, NAT, Route
2) cluster-stack   : EKS/GKE control plane
3) nodepool-stack  : Managed node group / pool
4) addon-stack     : Helm 차트 (ingress-nginx, cert-manager, ArgoCD ...)
```

분리 이유:
- **변경 빈도**: 애드온은 자주, 클러스터는 거의 안 건드림.
- **권한**: 네트워크 변경은 admin 만, 애드온은 플랫폼팀.
- **장애 반경**: 애드온 plan 실수가 VPC 까지 안 망가뜨림.

### 6.3 Node pool 관리

EKS 예:
```hcl
eks_managed_node_groups = {
  general = {
    instance_types = ["m6i.large"]
    min_size  = 2
    max_size  = 10
    desired_size = 3
  }
  spot = {
    instance_types = ["m6i.large", "m5.large"]
    capacity_type  = "SPOT"
    min_size = 0
    max_size = 20
  }
}
```

> **함정**: `desired_size` 는 Cluster Autoscaler/Karpenter 가 바꿈 → drift 발생. lifecycle `ignore_changes = [desired_size]` 권장.

### 6.4 Ingress / Nginx 배포 예

```hcl
resource "helm_release" "ingress_nginx" {
  name       = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  version    = "4.10.0"
  namespace  = "ingress-nginx"
  create_namespace = true

  values = [yamlencode({
    controller = {
      service = {
        annotations = {
          "service.beta.kubernetes.io/aws-load-balancer-type" = "nlb"
        }
      }
    }
  })]
}
```

---

## 7. Workspace 전략 (dev / stage / prod 분리)

### 7.1 Terraform 내장 Workspace — 의외로 한계

```bash
terraform workspace new dev
terraform workspace new prod
```

- 같은 backend, 같은 config 를 공유. state 만 분리됨.
- 한계:
  - 환경별 backend(다른 AWS 계정, 다른 버킷) 분리 불가.
  - 권한 분리 어려움 (실수로 prod 선택해서 apply).
- 공식 문서 권장: **간단한 분기에만 사용**, 본격적인 환경 분리는 디렉터리 분리.

### 7.2 디렉터리 분리 (권장)

```
infra/
├─ modules/                 # 재사용 모듈
│  ├─ network/
│  └─ eks/
└─ envs/
   ├─ dev/
   │   ├─ main.tf           # module 호출
   │   ├─ backend.tf        # dev 전용 state
   │   └─ terraform.tfvars
   ├─ stage/
   └─ prod/
```

- 각 env 디렉터리가 **독립 root module**. 별도 backend, 별도 state, 별도 권한.
- 공통 로직은 `modules/` 에서 재사용.

### 7.3 tfvars 관리

| 파일 | 용도 |
|---|---|
| `terraform.tfvars` | 자동 로드, 환경 기본값 |
| `*.auto.tfvars` | 자동 로드 (여러 파일 가능) |
| `prod.tfvars` | 명시 로드: `terraform apply -var-file=prod.tfvars` |
| 환경 변수 `TF_VAR_xxx` | CI 비밀값 주입 |

> **민감값(비밀번호, 키)** 은 tfvars 에 평문으로 두지 말 것 → Vault, AWS SSM, GCP Secret Manager 의 data source 또는 CI secret 으로 주입.

### 7.4 Terragrunt — 흔한 보강 도구

- 디렉터리 분리 패턴의 보일러플레이트(backend 설정, common var) 제거.
- `terragrunt.hcl` 한 파일로 환경 트리 전체를 DRY 하게.
- 공식 Terraform 은 아님, gruntwork.io 의 OSS.

---

## 8. CI/CD 연동

### 8.1 GitHub Actions 기본 패턴

```yaml
# .github/workflows/terraform.yml
name: terraform
on:
  pull_request:
    paths: [ "infra/**" ]
  push:
    branches: [ main ]

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform fmt -check
      - run: terraform validate
      - run: terraform plan -out=tfplan
      - uses: actions/upload-artifact@v4
        with: { name: tfplan, path: tfplan }

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    environment: prod                      # ← Approval gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - uses: actions/download-artifact@v4
        with: { name: tfplan }
      - run: terraform apply tfplan
```

핵심 원칙:
1. **PR 에서 plan, main 머지 후 apply**.
2. **plan/apply 분리**: plan 산출물(`tfplan`) 을 apply 가 그대로 사용.
3. **환경 보호 규칙**(GitHub Environments) 으로 prod 수동 승인.
4. `OIDC` 를 통한 클라우드 인증 (long-lived AWS key 금지).

### 8.2 PR 코멘트로 plan 공유

`actions/github-script` 또는 `tfcmt`, `Atlantis` 사용.

### 8.3 대안

- **Atlantis**: 셀프호스팅, PR 코멘트 기반 (`atlantis plan`, `atlantis apply`).
- **Terraform Cloud**: VCS 연동, 자동 plan/승인/run trigger 내장.
- **Spacelift / Env0**: 정책/스택 의존성/비용까지 통합 SaaS.

---

## 9. Policy as Code

### 9.1 왜 필요한가

- "S3 버킷에 public access 허용 금지", "프로덕션은 t3.medium 이상", "태그 필수" 같은 **조직 룰** 을 plan 시점에 자동 검증.
- 사람의 코드리뷰만으로는 휴먼에러 + 일관성 부족.

### 9.2 Sentinel (HashiCorp)

- Terraform Enterprise / Cloud 에서 동작.
- `import "tfplan/v2"` 로 plan 데이터 접근.
- 정책 수준: `advisory` (경고), `soft-mandatory` (관리자 승인), `hard-mandatory` (차단).

```python
import "tfplan/v2" as tfplan

main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is "aws_instance" implies
      rc.change.after.instance_type in ["t3.medium", "t3.large"]
  }
}
```

### 9.3 OPA / Conftest

- 오픈소스, 어디서나 사용 가능.
- `terraform show -json plan.out` → JSON → Rego 정책으로 검증.

```rego
package terraform.aws

deny[msg] {
  resource := input.resource_changes[_]
  resource.type == "aws_s3_bucket"
  resource.change.after.acl == "public-read"
  msg := sprintf("S3 bucket %v cannot be public", [resource.address])
}
```

CI 통합:
```bash
terraform plan -out tfplan.binary
terraform show -json tfplan.binary > tfplan.json
conftest test tfplan.json
```

### 9.4 Sentinel vs OPA

| 항목 | Sentinel | OPA |
|---|---|---|
| 라이선스 | 상용 (TFC/TFE) | 오픈소스 |
| 통합 | Terraform 네이티브 | 다목적 (K8s, Envoy, ...) |
| 학습곡선 | Sentinel 언어 (HCL 유사) | Rego (선언형) |
| 정책 적용 | TFC run 단계 자동 | CI 단계에 직접 끼워 넣음 |

---

## 10. 참고 (공식 문서 위주)

- Terraform Docs — https://developer.hashicorp.com/terraform/docs
- State — https://developer.hashicorp.com/terraform/language/state
- Backends — https://developer.hashicorp.com/terraform/language/backend
- S3 backend & lockfile — https://developer.hashicorp.com/terraform/language/backend/s3
- Import block — https://developer.hashicorp.com/terraform/language/import
- Modules — https://developer.hashicorp.com/terraform/language/modules
- Kubernetes provider — https://registry.terraform.io/providers/hashicorp/kubernetes
- Helm provider — https://registry.terraform.io/providers/hashicorp/helm
- Sentinel — https://developer.hashicorp.com/sentinel
- Terraform Cloud — https://developer.hashicorp.com/terraform/cloud-docs
- Infracost — https://www.infracost.io/docs/
- driftctl — https://docs.driftctl.com/
