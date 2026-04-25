# Keystone Token Flow — 토큰은 어떻게 만들어지고 검증되나

> **Fernet 토큰의 내부 구조부터 검증 흐름까지.** "X-Auth-Token 헤더"의 실체.

[01-core-services/keystone-identity.md](../01-core-services/keystone-identity.md) 가 "사용자 관점"이라면, 이 문서는 **구현자 관점**. 토큰 한 줄이 어떻게 만들어지고 어떻게 검증되는지 따라간다.

---

## 1. Fernet 토큰의 정체 — 그냥 암호화된 문자열

```
gAAAAABm... (200바이트 안팎)
```

이게 Fernet 토큰. Base64로 인코딩된 **암호문**이다. 안에 들어있는 평문은 대략 이런 구조:

```
[user_id][methods][project_id][expires_at][audit_ids][system_scope][...]
```

**Fernet = AES-128-CBC + HMAC-SHA256** 기반의 표준 암호화 포맷. Heroku가 만들었고, Keystone이 채택.

```python
# 의사 코드
plaintext = pack(user_id, project_id, expires_at, ...)
ciphertext = AES_encrypt(plaintext, key)
hmac = HMAC_SHA256(ciphertext, key)
token = base64(version || timestamp || iv || ciphertext || hmac)
```

핵심: **토큰 자체가 모든 정보를 갖고 있음**. Keystone DB를 조회할 필요 없이 검증 가능. → **stateless**.

---

## 2. 토큰 발급 흐름 — `openstack token issue` 의 내부

```
[1] 클라이언트 → Keystone POST /v3/auth/tokens
    Body: {
      "auth": {
        "identity": {"methods": ["password"], "password": {...}},
        "scope": {"project": {"name": "demo", "domain": {...}}}
      }
    }

[2] Keystone (Identity 백엔드, 보통 SQL):
      ├─ User "alice" 존재 확인
      ├─ password hash 비교 (PBKDF2/scrypt)
      └─ 통과 → user_id 확보

[3] Keystone (Scope 검증):
      ├─ Project "demo" 존재? user가 멤버?
      └─ Role assignment 조회 → ["member"]

[4] Keystone (Token Provider = Fernet):
      ├─ payload 생성 (user_id, project_id, methods, expires_at, audit_id)
      ├─ msgpack으로 직렬화
      ├─ Fernet 키로 암호화
      └─ Base64 → 토큰 문자열

[5] Keystone (Catalog 조회):
      └─ endpoint 테이블에서 모든 서비스 URL 수집

[6] 응답:
    Header: X-Subject-Token: gAAAAABm...
    Body: {
      "token": {
        "user": {...},
        "project": {...},
        "roles": [{"name": "member"}],
        "catalog": [...],
        "expires_at": "2026-04-25T17:00:00Z"
      }
    }
```

**중요**: 토큰 자체는 **헤더로 따로** 전달된다. body는 디코딩된 사용자 친화 정보일 뿐.

---

## 3. 토큰 검증 흐름 — Nova가 토큰 받았을 때

Nova가 `X-Auth-Token: gAAA...` 받으면 어떻게 검증하나?

```
[1] Nova-API (keystonemiddleware.auth_token):
      ├─ 캐시에 토큰 hash 있나? → 있으면 즉시 통과
      └─ 없으면 ↓

[2] Nova → Keystone GET /v3/auth/tokens
    Header: X-Auth-Token: <자기 service 계정의 토큰>
            X-Subject-Token: <검증할 사용자 토큰>

[3] Keystone (Fernet provider):
      ├─ Base64 디코딩
      ├─ HMAC 검증 (위변조 체크)
      ├─ AES 복호화 (현재 또는 과거 키로)
      ├─ payload 풀어서 user_id, project_id, expires_at 추출
      ├─ 만료 시간 체크
      └─ 응답에 user/project/roles 채워서 반환

[4] Nova-API:
      ├─ 응답 캐시 (memcached, 보통 5~10분 TTL)
      ├─ request 객체에 user_id/project_id/roles 주입
      └─ 다음 미들웨어로

[5] Nova의 Policy Engine (oslo.policy):
      └─ "이 API는 role=member 필요" → 통과 여부 결정
```

**관건**: Keystone은 매 요청마다 호출되지 않는다. **caching**이 있어서 같은 토큰은 5분간 캐시.

---

## 4. Fernet 키 관리 — 멀티 노드의 함정

Fernet 키는 `/etc/keystone/fernet-keys/` 에 평문으로 있다.

```
$ ls /etc/keystone/fernet-keys/
0   1   2

# 파일 내용 (32바이트 base64-urlsafe 키)
$ cat /etc/keystone/fernet-keys/0
sIuwaTMjRLKPi67DEB0Au37jK7Q-KVOYhYmDfh6QIo4=
```

| 파일명 | 역할 |
|---|---|
| `0` | **Staged key** — 곧 primary 될 예정 |
| 가장 큰 숫자 | **Primary key** — 새 토큰 발급에 사용 |
| 그 외 | **Secondary keys** — 검증만 |

### 키 로테이션

```bash
$ keystone-manage fernet_rotate --keystone-user keystone --keystone-group keystone
```

이게 하는 일:
1. 기존 staged(0) → primary로 승격 (이름 +1)
2. 새 staged(0) 생성
3. `max_active_keys` 초과한 가장 오래된 키 삭제

```
로테이션 전:    0(staged), 1(primary), 2(secondary)
로테이션 후:    0(new staged), 1(staged→primary), 2(primary→secondary), 3(secondary→삭제)
```

### 멀티 노드 함정

```
Keystone-A: keys = [0, 1, 2]   ← rotate 후
Keystone-B: keys = [0, 1]      ← 아직 sync 안 됨
                ▲
       토큰 검증 실패! "Invalid token"
```

해결:
- 키 디렉토리를 **rsync / NFS / Barbican** 으로 동기화
- 모든 노드 키 동기화 후에만 새 토큰 발급되도록 순서 보장

---

## 5. Service Catalog — endpoint 테이블 하나

```sql
-- keystone DB
SELECT id, service_id, region, url, interface FROM endpoint;
```

이게 `openstack catalog list` 의 원천.

```
+----+----------+--------+----------------------------+----------+
| id | service  | region | url                        | iface    |
+----+----------+--------+----------------------------+----------+
| .. | nova     | RegOne | http://controller:8774/... | public   |
| .. | nova     | RegOne | http://internal:8774/...   | internal |
| .. | nova     | RegOne | http://admin:8774/...      | admin    |
| .. | neutron  | RegOne | http://controller:9696     | public   |
+----+----------+--------+----------------------------+----------+
```

**interface 종류**:
- `public`: 외부에서 접근. HTTPS 권장
- `internal`: 서비스 간 통신용. 빠른 내부망
- `admin`: 관리 작업용 (deprecated, 이제 public과 통합 추세)

토큰 발급 시 catalog가 통째로 응답에 포함되어 클라이언트가 "Nova 어디?"를 알게 된다.

---

## 6. Application Credential — 서비스 계정 토큰

봇/CI에서 비밀번호 쓰기 싫을 때:

```bash
# 사용자가 본인 권한 일부를 위임
$ openstack application credential create my-bot \
    --role member --description "CI bot"

+--------------+-----------------------+
| Field        | Value                 |
+--------------+-----------------------+
| id           | abc123                |
| secret       | xyzSECRET             |  ← 한 번만 보임
| roles        | member                |
| user_id      | <alice-uuid>          |
+--------------+-----------------------+

# 봇은 이 ID/secret으로 토큰 발급
$ export OS_APPLICATION_CREDENTIAL_ID=abc123
$ export OS_APPLICATION_CREDENTIAL_SECRET=xyzSECRET
$ export OS_AUTH_TYPE=v3applicationcredential
$ openstack token issue
```

장점:
- 본인 비번 안 나눠줌
- 권한 범위 좁힘 (특정 role만)
- `--unrestricted` 안 쓰면 다른 application credential 생성 불가 (권한 확장 차단)

---

## 7. 디버깅 팁

### 토큰 디코딩 (admin 권한 필요)

```python
from keystone.token.providers.fernet import token_formatters
formatter = token_formatters.BaseTokenFormatter()
payload = formatter.unpack(b'gAAA...')
print(payload)
```

### 만료 시간 줄이기 (테스트)

```ini
# /etc/keystone/keystone.conf
[token]
expiration = 3600    # 1시간 (기본)
allow_expired_window = 172800  # 만료 후에도 잠깐 인정 (in-flight 보호)
```

### 토큰 디버그 로그

```ini
[DEFAULT]
debug = True
```

대신 토큰이 로그에 찍히니 **운영에선 절대 금지**.

---

## 8. Federation — 외부 IdP 연동

기업에선 SAML/OIDC로 사내 SSO와 연동.

```
사용자 → SP-initiated SSO
    ▼
[Keystone Service Provider]
    ├─ "외부 IdP로 가" (SAML AuthnRequest)
    ▼
[기업 IdP (예: Okta, Keycloak)]
    ├─ 사용자 로그인 + MFA
    ▼
[Keystone Service Provider]
    ├─ SAML assertion 검증
    ├─ Attribute Mapping → user, group, role 결정
    └─ Fernet 토큰 발급
```

내부 사용자 DB 없이도 OpenStack 사용 가능. 대기업 환경에서 사실상 표준.

---

## 9. 주요 코드 위치 (참고)

| 파일 | 역할 |
|---|---|
| `keystone/auth/plugins/password.py` | 비번 인증 |
| `keystone/token/providers/fernet/core.py` | Fernet 토큰 생성/검증 |
| `keystone/token/token_formatters.py` | payload 직렬화 (msgpack) |
| `keystone/middleware/auth_token.py` (keystonemiddleware 패키지) | 다른 서비스에서 토큰 검증 미들웨어 |

---

## 핵심 요약

```
Fernet 토큰 = AES + HMAC 으로 서명된 자체 완결 페이로드
         ↓
  Keystone DB 안 거치고 복호화만으로 검증 가능 (stateless)
         ↓
  → 수평 확장 쉬움
  → 단점: 키 동기화 필요
         ↓
  키 로테이션은 staged → primary → secondary 슬라이딩
         ↓
  서비스 간 토큰 검증은 keystonemiddleware.auth_token + 캐시
```

> 💡 **제일 헷갈리는 포인트**: 토큰 검증할 때 Nova가 Keystone에 보내는 요청도 **자기 토큰이 필요**하다. 즉 Nova 서비스 계정이 Keystone에 미리 인증되어 있어야 함. `nova.conf`의 `[keystone_authtoken]` 섹션이 그 자격증명.

---

## 다음

→ [nova-scheduler-internals.md](./nova-scheduler-internals.md): 토큰 통과한 다음 Nova가 어디로 VM 보낼지 결정하는 알고리즘  
→ [neutron-ovn-internals.md](./neutron-ovn-internals.md): 같은 토큰으로 호출되는 네트워크 서비스 내부
