# Accounts, Domains, Projects — 멀티테넌시 모델

> **CloudStack의 멀티테넌시는 OpenStack과 다르게 "Domain 트리"가 N단으로 깊어진다.**

OpenStack의 "Domain → Project" 가 평면이라면, CloudStack은 **계층형 Domain + Account + (선택) Project**.

> 출처: [Admin Guide — Accounts](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html) · [Concepts: Accounts](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#account-and-domain).

---

## 1. 객체 4개

| 객체 | 한 줄 설명 |
|---|---|
| **Domain** | 회사/조직 단위. 트리 구조. 루트는 `ROOT` |
| **Account** | Domain 안의 빌링/소유 단위. 1 Account = 1+ User |
| **User** | 실제 로그인하는 사람. apiKey/secretKey 발급 단위 |
| **Project** | (선택) Account 간 협업 단위. 여러 Account가 같은 Project에 참여 |

```
Domain Tree (계층형)
ROOT
 ├─ acme-corp                    (Domain)
 │   ├─ acme-eng                 (Sub-Domain)
 │   │   └─ Account: dev-team
 │   │       ├─ User: alice (apiKey-A)
 │   │       └─ User: bob   (apiKey-B)
 │   └─ acme-finance
 │       └─ Account: finance
 │           └─ User: carol
 └─ partner-corp
     └─ Account: partner-default
         └─ User: dave
```

---

## 2. Domain 트리 — Reseller 모델

OpenStack과 가장 다른 점. CloudStack의 Domain은 **N단으로 깊어진다**.

### 시나리오: 클라우드 리셀러

```
ROOT (운영자: 우리 회사)
 ├─ reseller-A (도메인 관리자: 리셀러A 사장)
 │   ├─ customer-A1
 │   ├─ customer-A2
 │   └─ customer-A3
 └─ reseller-B
     ├─ customer-B1
     └─ customer-B2
```

→ Reseller A의 Domain Admin은 자기 하위(customer-A1/A2/A3)를 모두 관리할 수 있지만 reseller-B는 못 본다.

### Domain Admin 권한 범위

| Role | 권한 |
|---|---|
| **Root Admin** | 전체 (ROOT Domain의 admin) |
| **Domain Admin** | 자기 Domain + 하위 Domain의 모든 객체 |
| **Resource Admin** | (제한된) Domain 운영, 사용자/리소스 관리 |
| **User** | 자기 Account 안의 리소스만 |

→ "**Domain 트리 + Domain Admin**" 이 SaaS/호스팅에 천연 적합.

---

## 3. Account — 빌링/소유 단위

```
Account: dev-team
   ├─ User: alice
   ├─ User: bob
   ├─ Resources: VM-1, VM-2, Volume-X, Network-Y
   └─ Limits: max VMs = 50, max CPU = 100, ...
```

- **모든 리소스는 Account 소유**. User가 만든 게 아니라 Account가 소유.
- Account 안의 모든 User는 같은 리소스를 본다.
- Account 단위로 **Resource Limit** 설정 가능.

### Account Type ([공식](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html#accounts))

| Type | 의미 |
|---|---|
| 0 | User Account (일반) |
| 1 | Root Admin |
| 2 | Domain Admin |
| 3 | Resource Admin |

---

## 4. User — 로그인 + apiKey 단위

```
User: alice
   ├─ login: alice / password
   ├─ apiKey/secretKey: (apiKey-A, secretKey-A)
   ├─ 2FA: (옵션)
   └─ Account: dev-team
```

- User 단위로 apiKey/secretKey가 발급됨
- **삭제 시 그 User만 사라짐**, Account의 다른 User/리소스는 살아 있음
- 같은 Account의 다른 User가 만든 VM도 보고 조작 가능

---

## 5. Project — 여러 Account의 협업

OpenStack의 Project와 의미가 다르다. CloudStack에서 Project는 **선택적인 협업 컨테이너**.

```
Project: "shared-infra"
   ├─ Owner: alice (dev-team Account)
   ├─ Member: bob (dev-team Account)
   ├─ Member: carol (finance Account)   ← 다른 Account에서 합류!
   └─ Resources: 공유 VM-X, Volume-Y
```

→ "**여러 Account를 모은 협업 공간**". Account 경계를 가로지른다.

### Project vs Account 차이

| | Account | Project |
|---|---|---|
| 자동 생성? | User 만들면 자동 | 수동 생성 |
| 다른 Account에서 합류? | ❌ | ✅ |
| 빌링 | Account 단위 | Project 단위 (추가) |
| Resource 소유권 | Account | Project (Project 모드 시) |

UI/cmk에서 작업 시 "Account context" vs "Project context" 를 토글해서 사용.

---

## 6. RBAC — Dynamic Roles (4.9+)

> [Dynamic Roles](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html#using-dynamic-roles).

기본 4개 Role 외에 **커스텀 Role** 정의 가능.

```bash
# 새 Role 생성
$ cmk create role name=ReadOnly type=User \
    description="Can only list resources"

# Role에 API 권한 추가/제거
$ cmk create rolepermission roleid=<...> \
    rule=list* permission=allow
$ cmk create rolepermission roleid=<...> \
    rule=create* permission=deny

# Account 생성 시 Role 지정
$ cmk create account ... roleid=<readonly-role-id>
```

→ "**API 단위로 allow/deny**" 가능. OpenStack의 policy.yaml과 비슷.

---

## 7. Resource Limit / Quota

> [Setting Resource Limits](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html#setting-resource-limits).

Domain/Account/Project 단위로 양적 제한.

| 리소스 | 단위 |
|---|---|
| User VMs | 개 |
| Public IPs | 개 |
| Volumes | 개 |
| Snapshots | 개 |
| Networks | 개 |
| VPCs | 개 |
| CPUs (총합) | 개 |
| Memory (총합) | MB |
| Primary Storage | GB |
| Secondary Storage | GB |

```bash
$ cmk update resourcelimit \
    account=dev-team \
    domainid=<...> \
    resourcetype=0 \
    max=20

# resourcetype:
# 0=Instance, 1=PublicIP, 2=Volume, 3=Snapshot, 4=Template,
# 6=Network, 7=VPC, 8=CPU, 9=Memory, 10=PrimaryStorage, 11=SecondaryStorage
```

→ 멀티테넌시 환경에서 한 테넌트가 자원을 독점하지 못하도록.

---

## 8. 손으로 해보기

```bash
# Domain 트리
$ cmk create domain name=acme parentdomainid=<root-id>
$ cmk create domain name=acme-eng parentdomainid=<acme-id>

# Account
$ cmk create account \
    accounttype=0 \
    domainid=<acme-eng-id> \
    username=alice \
    email=alice@example.com \
    firstname=Alice \
    lastname=A \
    password=secret123 \
    account=dev-team

# 추가 User
$ cmk create user account=dev-team \
    domainid=<acme-eng-id> \
    username=bob \
    email=bob@example.com \
    firstname=Bob \
    lastname=B \
    password=secret123

# apiKey 발급
$ cmk register userkeys id=<bob-user-id>

# Project
$ cmk create project name=shared-infra \
    displaytext="Cross-team infra" \
    domainid=<acme-id>

# Project 멤버 추가
$ cmk add accounttoproject projectid=<...> account=finance

# Project context로 전환 (UI에서 토글)
$ cmk -p alice list virtualmachines projectid=<...>
```

---

## 9. 자주 밟는 지뢰

- **다른 Domain 의 리소스가 안 보임** → 정상. Domain 격리. Root admin으로 보거나 Domain Admin 권한 확인.
- **Project 안에 VM 만들었는데 Account에서 안 보임** → 정상. Project 컨텍스트로 봐야.
- **User 삭제했는데 VM 살아있음** → 정상. 리소스 소유권은 Account. User는 Account의 멤버.
- **Resource Limit 변경했는데 적용 안 됨** → `cmk update resourcecount` 로 카운트 다시 동기화 필요할 수 있음.
- **Domain Admin 인데 자식 Domain 못 봄** → API 호출 시 `domainid` 명시. 또는 `cmk set domain` 으로 컨텍스트 전환.

---

## 10. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Domain | Domain (CloudStack은 트리, OpenStack은 평면) |
| Project | Account (소유 단위) |
| User | User |
| Role | Role (Dynamic Role) |
| Application Credential | apiKey/secretKey 추가 발급 |
| (없음) | **CloudStack Project** = 여러 Account의 협업 공간 |

가장 다른 점:
- **CloudStack의 Domain 은 N단 트리** → 리셀러 모델 천연 지원
- **CloudStack의 Project 는 OpenStack Project와 의미가 다름** (= 여러 Account 협업)

---

## 다음

→ [service-offerings.md](./service-offerings.md): Account가 고를 수 있는 메뉴.
→ [api-and-cloudmonkey.md](./api-and-cloudmonkey.md): User가 어떻게 키로 인증하는지.

---

## 공식 문서 레퍼런스

- [Admin Guide — Accounts, Users, and Domains](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html)
- [Concepts: Account and Domain](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#account-and-domain)
- [Dynamic Roles](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html#using-dynamic-roles)
- [Setting Resource Limits](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html#setting-resource-limits)
- [Working with Projects](https://docs.cloudstack.apache.org/en/latest/adminguide/projects.html)
