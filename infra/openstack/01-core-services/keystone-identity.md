# Keystone — OpenStack의 문지기

> **"너 누구야? 자격 있어? 어느 방으로 갈래?"** 를 담당.

OpenStack의 모든 서비스(Nova, Cinder, Neutron…) 앞에 Keystone이 서 있다. **토큰 없으면 아무도 못 들어간다.**

---

## 왜 필요한가

Keystone이 없으면 누가 보낸 요청인지 모른다. 해커도 admin이 된다. 그래서 필요한 것:

1. **누구?** (Identity)
2. **비번 맞아?** (Authentication)
3. **이거 할 권한 있어?** (Authorization)
4. **Nova API 주소 어디야?** (Service Catalog)

이 4가지를 혼자 다 한다.

---

## 비유: 호텔 프론트 데스크

```
   [프론트 = Keystone]
        │
        ├─ 신분증 확인
        ├─ 방 키(토큰) 발급
        └─ "수영장은 B1" 안내

   [객실=Nova] [수영장=Cinder] [짐=Swift]
        ↑ 방 키 없으면 입장 불가
```

체크인 한 번 → 방 키(토큰) 받음 → 이후 모든 시설은 키만 보여주면 끝.

---

## 토큰 흐름 (VM 만들기)

```
사용자 → Keystone: "alice/1234/dev-team"
Keystone → 사용자: 토큰 gAAA...  (+ 서비스 주소록)

사용자 → Nova: POST /servers  (Header: X-Auth-Token: gAAA...)
Nova → Keystone: "이 토큰 진짜?"
Keystone → Nova: "alice, dev-team, member 역할. 유효."
Nova: "VM 만들어줄게"
```

비밀번호는 **Keystone한테만 한 번** 보낸다. 나머지 서비스는 평생 모른다.

---

## 핵심 객체 5개

| 객체 | 한 줄 |
|---|---|
| **User** | 사람 (`alice`) |
| **Project** | 리소스 상자 (VM/볼륨이 여기 소속). AWS Account 같은 느낌 |
| **Role** | 역할 이름표 (`admin`, `member`, `reader`) |
| **Token** | 한시적 방 키 (기본 1시간) |
| **Endpoint** | 서비스 주소록 ("Nova는 :8774") |

**권한 = User + Project + Role** 3요소 조합. 이걸 **Role Assignment**라 부른다.

```
alice + dev-team + member   → dev-team에서 VM 만들 수 있음
alice + prod-team + reader  → prod-team에서는 보기만
```

---

## 손으로 해보기

```bash
# 토큰 받기
$ openstack token issue

# 서비스 주소록 보기
$ openstack catalog list

# 사용자/프로젝트/역할 연결
$ openstack project create --domain Default dev-team
$ openstack user create --domain Default --password-prompt alice
$ openstack role add --project dev-team --user alice member

# 누가 어디서 뭐 할 수 있나
$ openstack role assignment list --names
```

---

## 토큰은 Fernet

현재 기본은 **Fernet 토큰**. 암호화된 짧은 문자열, DB 저장 불필요, 빠름. 기본 만료 1시간.

> 프로덕션 함정: Keystone 여러 대면 **Fernet 키를 노드 간 공유**해야 함. 안 그러면 A에서 발급한 토큰을 B가 검증 못 함.

---

## 자주 밟는 지뢰

- **401 Unauthorized** → 환경변수(`openrc`) source 안 했거나 토큰 만료
- **Project not found** → 도메인 지정 안 함 (`--domain`)
- **403 Forbidden** → 토큰은 OK, 역할(Role)이 부족
- **Keystone 다운 = OpenStack 전체 다운** → 프로덕션은 3대 HA 필수

---

## AWS IAM 치트시트

| AWS | Keystone |
|---|---|
| IAM User | User |
| AWS Account | Project (+ Domain) |
| IAM Policy | 각 서비스의 `policy.yaml` |
| STS 임시자격 | Token |

AWS는 IAM 하나가 다 함. Keystone은 **인증만** 하고 권한 판정은 각 서비스에 분산.

---

## 다음

→ [nova-compute.md](./nova-compute.md) 에서 토큰 들고 실제 VM 만드는 흐름.  
→ [../03-installation/devstack/](../03-installation/devstack/) 에서 직접 깔고 `openstack token issue` 쳐보는 게 가장 빠르다.
