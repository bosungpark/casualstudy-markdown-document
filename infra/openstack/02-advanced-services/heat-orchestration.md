# Heat — YAML로 인프라 찍어내기

> **"VM 3개 + 네트워크 + LB"를 한 번에 배포하는 템플릿 엔진.**

AWS CloudFormation, Terraform과 같은 계열. 클릭/CLI로 하나씩 만드는 대신 **YAML 한 장**에 다 적고 `stack create` 한 번.

---

## 왜 필요한가

Core 서비스만으로 앱 스택을 만들려면:

```bash
openstack network create ...
openstack subnet create ...
openstack router create ...
openstack server create web-1 ...
openstack server create web-2 ...
openstack server create db-1 ...
openstack volume create ...
openstack server add volume ...
# ... 20줄 더
```

- 순서 꼬이면 망함
- 중간에 실패하면 수동 롤백
- 개발/스테이징/프로덕션 환경 똑같이 만들기 어려움

Heat로 바꾸면 **한 줄**:

```bash
openstack stack create my-app -t app.yaml
```

---

## 한 줄 요약

YAML에 "원하는 상태"를 적으면 Heat가 **순서·의존성·롤백**을 알아서 처리한다. Declarative Infrastructure.

---

## 핵심 개념

| 용어 | 의미 |
|---|---|
| **Template** | YAML 파일. 리소스 정의 |
| **Stack** | 템플릿으로 만들어진 리소스 묶음 (인스턴스) |
| **Resource** | Stack 안의 개별 리소스 (Server, Network, Volume…) |
| **Parameter** | 템플릿에 주입하는 변수 (ex: flavor 이름) |
| **Output** | Stack 생성 후 알려주는 값 (ex: VM의 공인IP) |
| **HOT** | **H**eat **O**rchestration **T**emplate 포맷 |

---

## HOT 템플릿 맛보기

```yaml
heat_template_version: 2021-04-16

description: Simple web server

parameters:
  image:
    type: string
    default: ubuntu-22.04
  flavor:
    type: string
    default: m1.small

resources:
  my_network:
    type: OS::Neutron::Net

  my_subnet:
    type: OS::Neutron::Subnet
    properties:
      network: { get_resource: my_network }
      cidr: 192.168.1.0/24

  my_server:
    type: OS::Nova::Server
    properties:
      image: { get_param: image }
      flavor: { get_param: flavor }
      networks:
        - network: { get_resource: my_network }

outputs:
  server_ip:
    value: { get_attr: [my_server, first_address] }
```

- `get_resource`: 같은 템플릿의 다른 리소스 참조 → **의존성 자동 파악**
- `get_param`: 파라미터 주입
- `get_attr`: 리소스의 속성 읽기

---

## 생성/업데이트/삭제

```bash
# 생성
$ openstack stack create my-app -t app.yaml \
    --parameter flavor=m1.medium

# 상태 확인
$ openstack stack list
$ openstack stack show my-app

# 구성 리소스 보기
$ openstack stack resource list my-app

# 업데이트 (템플릿 수정 후)
$ openstack stack update my-app -t app.yaml

# 삭제 (안에 있는 리소스 전부 정리)
$ openstack stack delete my-app
```

---

## Heat가 잘하는 것

### 1. 의존성 자동 해결

```yaml
server:
  depends_on: [subnet, volume]
```

명시하지 않아도 `get_resource`로 엮여 있으면 **자동으로** 순서 잡음.

### 2. 롤백

중간에 실패하면 **이미 만든 것들을 되돌림**. `CREATE_FAILED` 상태에서 수동 정리 불필요.

### 3. Stack Update (차분 적용)

템플릿을 수정하면 Heat가 **뭐가 바뀌었는지 계산**해서 필요한 것만 수정/추가/삭제.

```
기존: VM 2대
신규: VM 3대
→ Heat가 VM 1대만 추가 (기존 2대는 그대로)
```

### 4. Nested Stack

큰 스택을 작은 스택으로 쪼개서 재사용.

```yaml
app_stack:
  type: OS::Heat::Stack
  properties:
    template: { get_file: app-tier.yaml }
```

### 5. Autoscaling Group

트래픽 따라 VM 개수 자동 조절 (Ceilometer/Aodh 연동).

---

## 자주 밟는 지뢰

- **Stack CREATE_FAILED 후 delete 안 됨** → `--force` 또는 리소스 수동 정리
- **순환 의존성** → A가 B를 참조하고 B가 A를 참조 → Heat가 거부
- **Output이 `None`** → 리소스가 아직 CREATE_IN_PROGRESS. `get_attr`는 완성 후에야 값이 나옴
- **템플릿 버전 불일치** → `heat_template_version` 의 날짜 포맷 확인 (OpenStack 릴리스별 지원 키워드 다름)

---

## AWS / Terraform 비교

| Heat | CloudFormation | Terraform |
|---|---|---|
| YAML (HOT) | JSON/YAML | HCL |
| 상태 서버에 저장 | AWS가 관리 | 로컬/S3 tfstate |
| OpenStack 전용 | AWS 전용 | 멀티 클라우드 |

> 요즘은 **Terraform + OpenStack provider** 를 쓰는 경우가 많다. 멀티 클라우드에서 도구 통일하려고. Heat는 OpenStack에만 있을 때 쓴다.

---

## 다음

→ 파라미터/Mapping/Condition 등 HOT 고급 문법은 [OpenStack 공식 문서](https://docs.openstack.org/heat/latest/template_guide/hot_spec.html)  
→ [magnum-k8s-on-openstack.md](./magnum-k8s-on-openstack.md) — Magnum은 내부적으로 Heat 템플릿으로 K8s 클러스터를 찍어냄
