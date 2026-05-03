# Projects — 여러 Account의 협업 컨테이너

> **OpenStack Project와 의미가 다르다. CloudStack의 Project는 "Account 경계를 넘는 공유 공간".**

> 출처: [Admin Guide — Projects](https://docs.cloudstack.apache.org/en/latest/adminguide/projects.html).

---

## 1. 왜 필요?

```
시나리오: 같은 회사 안 두 팀이 공유 인프라를 운영
   ─ Account "dev-team"
   ─ Account "sre-team"
   ─ 둘이 함께 보고 관리해야 하는 VM/네트워크가 있음

방법 1: 한 Account로 합치기 → 빌링/권한 관리 깨짐
방법 2: 두 Account에 같은 권한 → 사실상 불가능
방법 3: ✅ Project 만들어서 양 Account 합류
```

---

## 2. 객체 모델

```
Domain: ROOT/acme
   │
   ├─ Account: dev-team
   │   ├─ User: alice
   │   └─ User: bob
   │
   ├─ Account: sre-team
   │   └─ User: carol
   │
   └─ Project: "shared-infra"
       ├─ Owner: alice  (dev-team)
       ├─ Member: bob   (dev-team)
       ├─ Member: carol (sre-team)   ← 다른 Account!
       └─ Resources: 공유 VM-X, Volume-Y, Network-Z
```

→ Project는 Domain 안에 있지만, **여러 Account가 가입 가능**.

### Project Member 권한

| Role | 설명 |
|---|---|
| **Project Admin (Owner)** | 멤버 추가/제거, 모든 자원 통제 |
| **Project Member** | 자원 사용/생성, 멤버 관리 X |

→ Project 안에서는 RBAC이 단순. 세밀한 권한은 Domain/Account 레벨에서.

---

## 3. Resource Ownership

Project 모드에서 만든 리소스는 **Project 소유**:

```
Account "dev-team" + No Project context:
  → VM 만들면 dev-team 소유

Account "dev-team" + Project context "shared-infra":
  → VM 만들면 shared-infra 소유
  → dev-team의 리소스 카운트엔 안 잡힘
```

빌링도 따로:
- Account 사용량은 Account의 VM/볼륨만
- Project 사용량은 별도로 집계

---

## 4. CLI 사용

```bash
# Project 생성
$ cmk create project name=shared-infra \
    displaytext="Shared infra" \
    domainid=<...>

# 멤버 초대 (이메일 또는 직접 추가)
$ cmk add accounttoproject \
    projectid=<...> \
    account=sre-team

# 또는 초대 수락 흐름
$ cmk update projectinvitation \
    projectid=<...> accept=true

# 자원 생성 시 projectid 지정
$ cmk deploy virtualmachine \
    projectid=<...> \
    serviceofferingid=<...> \
    templateid=<...> \
    zoneid=<...> \
    networkids=<...>

# 또는 cmk profile에서 컨텍스트 전환
$ cmk set asyncblock true
$ cmk -c project=shared-infra deploy virtualmachine ...

# Project 안 자원 보기
$ cmk list virtualmachines projectid=<...>
$ cmk list volumes projectid=<...>
$ cmk list networks projectid=<...>
```

---

## 5. Resource Limit

Project 단위로도 limit 적용 가능:

```bash
$ cmk update resourcelimit \
    projectid=<...> \
    resourcetype=0 \
    max=100
```

→ Domain/Account/Project 3계층 limit.

---

## 6. 자주 밟는 지뢰

- **Account에서 만든 자원이 Project에 안 보임** → 정상. Account 모드 / Project 모드는 분리.
- **Project Admin이 Account 권한까지 갖는 것 아님** → Project Admin은 그 Project 안에서만.
- **Project 삭제 시 안의 자원** → 명시적으로 cleanup 또는 자원 모두 삭제 후 Project 삭제.
- **Project에 다른 Domain의 Account 추가** → 보통 같은 Domain 안에서만. Cross-domain 시 admin이 별도 처리.

---

## 7. Account vs Project 의사결정 트리

```
"공유 인프라가 필요하다"
   │
   ├─ 한 팀(=한 Account)만 쓰나? → Account만 사용
   │
   ├─ 여러 팀(여러 Account)이 같이 보나?
   │   ├─ Project 만들고 멤버 초대
   │   └─ 자원은 Project 소유
   │
   └─ 다른 도메인까지 가로질러야?
       └─ Root Admin이 Domain 정책 검토
```

---

## 8. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Project (= 소유 단위) | **Account** |
| (없음 — Project 멤버는 자유 추가) | **Project** (Account 가로지르는 공유) |
| Project 내 quota | Project Resource Limit |
| Domain | Domain (CloudStack은 트리) |

→ "OpenStack Project" 의 의미는 CloudStack의 "Account". CloudStack의 "Project" 는 OpenStack에 직접 대응 객체가 없다.

---

## 다음

→ [../01-core-services/accounts-domains-projects.md](../01-core-services/accounts-domains-projects.md): 기본 객체 4개.
→ [regions-and-multi-zone.md](./regions-and-multi-zone.md): 다 합쳐서 Region/Zone 단위 큰 그림.

---

## 공식 문서 레퍼런스

- [Admin Guide — Projects](https://docs.cloudstack.apache.org/en/latest/adminguide/projects.html)
- [Configuring Projects](https://docs.cloudstack.apache.org/en/latest/adminguide/projects.html#configuring-projects)
