# API Auth Flow — Signed Query 의 내부

> **CloudStack의 모든 외부 호출은 query string에 HMAC-SHA1 서명을 붙인다. 어떻게 서버가 검증하나.**

[01-core-services/api-and-cloudmonkey.md](../01-core-services/api-and-cloudmonkey.md) 가 "사용자 관점" 이라면, 여기는 **MS 안의 검증 코드 흐름**.

> 출처: [Developer's Guide — Signing API Requests](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#signing-api-requests) · [소스: ApiServer.java](https://github.com/apache/cloudstack/blob/main/server/src/main/java/com/cloud/api/ApiServer.java).

---

## 1. 요청 한 컷

```
GET /client/api?command=listVirtualMachines
              &response=json
              &apiKey=abc123
              &signature=base64(HMAC_SHA1(secretKey, sorted_params_lower))
              HTTP/1.1
```

세션 없음. **요청 자체가 자기 자신을 증명**.

---

## 2. 서명 알고리즘

### 클라이언트 (cmk 또는 SDK)

```python
# 의사 코드
def sign(params: dict, secret_key: str) -> str:
    # 1. signature 빼고 모든 파라미터
    p = {k: v for k, v in params.items() if k != "signature"}

    # 2. 알파벳 순 정렬
    sorted_keys = sorted(p.keys())

    # 3. URL encode + 소문자
    pairs = [
        f"{k.lower()}={url_encode(p[k]).lower()}"
        for k in sorted_keys
    ]
    canonical = "&".join(pairs)

    # 4. HMAC-SHA1 → base64
    sig = base64(HMAC_SHA1(secret_key, canonical))

    return sig
```

⚠️ 핵심:
- **소문자**: key와 value 둘 다 (대소문자 다르면 fail)
- **URL encode 후 소문자화**: `%2F` → `%2f`
- **알파벳 정렬**: `apikey, command, response, ...` 순
- **signature 자기 자신 제외**

### 서버 측 검증

`ApiServer.java` 의 핵심 흐름:

```java
// 1. 요청에서 signature 분리
String signature = params.remove("signature");

// 2. 같은 알고리즘으로 재계산
String canonical = sortAndLowerCase(params);   // 같은 알고리즘
byte[] expected = hmacSha1(user.getSecretKey(), canonical);
String expectedB64 = Base64.encode(expected);

// 3. 비교
if (!constantTimeEquals(signature, expectedB64)) {
    throw new ServerApiException(ErrorCode.UNAUTHORIZED, "Invalid signature");
}
```

---

## 3. apiKey → User 조회

```java
// apiKey로 user_account 테이블 조회
User user = userDao.findByApiKey(apiKey);
if (user == null || user.getState() != Active) {
    throw new ServerApiException(UNAUTHORIZED);
}

// secret_key 컬럼이 검증에 사용됨
String secretKey = user.getSecretKey();
```

DB 테이블 `user`:

| 컬럼 | 의미 |
|---|---|
| `id` | user_id |
| `account_id` | 소속 Account |
| `username` | 로그인 ID |
| `password` | 해시 (UI 로그인용) |
| `api_key` | API용 (대문자/숫자 32자) |
| `secret_key` | API용 (HMAC 키) |
| `state` | enabled/disabled/locked |

**apiKey 노출 = signature 위조 가능 X (secretKey 모르므로)**.
**secretKey 노출 = 영구 위험 → 즉시 회수 + 새 키 발급**.

---

## 4. RBAC — 권한 검사

서명 검증 통과 후, **이 명령을 호출할 권한이 있나?** 체크.

```
[1] User → Account → Role 추적
[2] Role의 RolePermission 목록에서 이 API에 대한 allow/deny 검색
[3] account_type 별 기본 권한 체크 (legacy commands.properties)
```

### `commands.properties` (legacy)

기본 4개 Account Type 별로 어느 API를 쓸 수 있나 매핑:

```properties
# 1=admin, 2=domain-admin, 3=resource-admin, 0=user
deployVirtualMachine=15      # 1+2+4+8 모두 (모든 type)
listVirtualMachines=15
deleteCluster=1              # admin만
```

### Dynamic Roles (4.9+)

DB의 `roles` + `role_permissions` 테이블로 동적 정의:

```sql
SELECT rule, permission, sort_order
FROM role_permissions
WHERE role_id = (SELECT role_id FROM account WHERE id = ?)
ORDER BY sort_order;
```

순회하며 첫 매치(allow/deny)를 적용. 와일드카드: `list*`, `create*`, `*`.

---

## 5. AccessChecker

핵심 자바 인터페이스: `AccessChecker.checkAccess(Account, ControlledEntity)`.

```
사용자가 다른 Account의 VM을 조작 시도?
   ▼
1) 사용자가 admin? → 통과
2) 같은 Account? → 통과
3) Domain admin이고 그 VM의 Domain이 자기 하위? → 통과
4) 그 외 → 401/403
```

각 API 호출 시 entity 단위로 호출됨. 예: `deployVirtualMachine` 은 **service offering, template, network, volume** 모두 권한 체크.

---

## 6. 토큰 캐시? — 없다

OpenStack의 keystonemiddleware 같은 캐시 레이어 없음.

```
매 요청마다:
  signature 재계산 → 비교
  + DB 조회 (apiKey → user, role)
```

- HMAC-SHA1: 사실상 cost zero
- DB 조회: 인덱싱 잘 되어 있음 (apiKey unique index)
- 결과: 부하 작은 환경에서는 문제 없음

대규모 환경(QPS 수천+) 에서는:
- MS의 user/role을 in-memory 캐시 (이미 일부 캐시됨)
- DB read replica
- HAProxy + 다중 MS

---

## 7. SSO — SAML / OAuth (4.13+)

> [SAML 2.0 SSO](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html#using-saml-sso).

UI 로그인은 SAML/OAuth 위임 가능:

```
사용자 → CloudStack UI → "Login with SSO"
   ▼
   Redirect → IdP (Okta/Keycloak/Azure AD)
   ▼
   IdP 인증 + SAML assertion
   ▼
   CloudStack: assertion 검증 → CSRF 세션 발급
   ▼
   로그인 완료
```

API 호출은 여전히 apiKey/secretKey. SSO는 UI 전용.

---

## 8. UI 세션 — 로그인 후 흐름

UI는 사용자 친화 인터페이스 → 내부적으로는 다음을 함:

```
1. POST /client/api?command=login&username=...&password=...
   → 응답: sessionkey + JSESSIONID 쿠키
   + 임시 apiKey/secretKey 발급 (registered 안 된 경우)

2. 이후 모든 호출:
   - JSESSIONID 쿠키
   - sessionkey query parameter
   - signature 같이 보냄

3. 로그아웃:
   POST /client/api?command=logout
```

→ 즉 UI는 **자동으로 signature 계산** 해서 요청 보냄. 사용자는 의식 못 함.

---

## 9. 시간/Replay 공격 보호

⚠️ Signed Query에는 **timestamp가 명시 X** (AWS SigV2와 다름).

→ 같은 signed URL 을 재사용 가능. **secretKey 노출 = 모든 과거/미래 호출 가능**.

운영 권장:
- TLS 강제 (HTTPS 8443) — query string이 평문으로 흘러도 TLS로 보호
- secretKey 정기 회전
- `expires=...` 파라미터 일부 SDK가 추가하는 패턴 (호환 X 주의)

---

## 10. 디버깅

### 401 발생 시

```
Cause 1: apiKey 오타 / 비활성 user
   → DB 조회: SELECT state FROM user WHERE api_key = '...'

Cause 2: signature 알고리즘 mismatch
   → 클라이언트 측 hex/base64 인코딩 잘못
   → 정렬/소문자화 빠짐

Cause 3: parameter 변형 (예: + vs %20)
   → URL encoding 일관성 부족
```

### 자세한 로그

```
$ vi /etc/cloudstack/management/log4j-cloud.xml
<logger name="com.cloud.api.ApiServer">
  <level value="DEBUG"/>
</logger>

$ systemctl restart cloudstack-management
$ tail -f /var/log/cloudstack/management/management-server.log | grep -i api
```

→ 요청 파라미터 + 계산된 canonical 문자열까지 찍힘. 클라이언트 쪽과 비교.

---

## 11. 코드 위치 (참고)

| 파일 | 역할 |
|---|---|
| `server/src/main/java/com/cloud/api/ApiServer.java` | 진입점 (Tomcat Servlet) |
| `server/src/main/java/com/cloud/api/auth/APIAuthenticator.java` | 인증 인터페이스 |
| `server/src/main/java/com/cloud/api/auth/APIAuthenticationManagerImpl.java` | 검증 로직 |
| `server/src/main/java/org/apache/cloudstack/acl/RoleManagerImpl.java` | RBAC |
| `engine/schema/src/main/java/com/cloud/user/UserVO.java` | user 모델 |

---

## 12. OpenStack Keystone과 비교

| | CloudStack Signed Query | OpenStack Keystone |
|---|---|---|
| 외부 인증 시스템 | 없음 (자체 검증) | 별도 서비스 |
| 토큰 만료 | 없음 (apiKey 폐기로) | 1시간 (Fernet) |
| 토큰 캐시 | 없음 (서명 재계산) | memcached 5~10분 |
| 서명 vs 토큰 | HMAC | 암호화된 페이로드 |
| 멀티 노드 키 sync | 없음 (apiKey는 user 단위) | Fernet 키 동기화 필요 |
| Replay 보호 | TLS + 키 회전 | 토큰 만료 |
| Federation | SAML/OAuth (UI만) | 1급 (API+UI) |

→ 단순함의 대가는 **Replay 보호 약함**. TLS와 key rotation 으로 보완.

---

## 다음

→ [scheduler-allocator-internals.md](./scheduler-allocator-internals.md): 인증 통과 후 Allocator가 호스트 고르는 흐름.
→ [../04-operations/troubleshooting.md](../04-operations/troubleshooting.md): 401 디버깅 실전.

---

## 공식 문서 레퍼런스

- [Developer's Guide — The CloudStack API](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#the-cloudstack-api)
- [Signing API Requests](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#signing-api-requests)
- [Admin Guide — SAML SSO](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html#using-saml-sso)
- [GitHub — apache/cloudstack: ApiServer.java](https://github.com/apache/cloudstack/blob/main/server/src/main/java/com/cloud/api/ApiServer.java)
