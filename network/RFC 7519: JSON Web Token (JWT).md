# RFC 7519: JSON Web Token (JWT)

## 출처
- **제목**: JSON Web Token (JWT)
- **저자**: Michael B. Jones (Microsoft), John Bradley (Ping Identity), Nat Sakimura (NRI)
- **발행**: IETF, May 2015 (Standards Track)
- **링크**: https://datatracker.ietf.org/doc/html/rfc7519
- **관련 RFC**: RFC 7515 (JWS), RFC 7516 (JWE), RFC 7518 (JWA), RFC 8725 (Best Practices)

---

## AI 요약

### JWT란?

JWT(JSON Web Token, 발음: "jot")는 두 당사자 간에 **클레임(claims)**을 안전하게 전송하기 위한 컴팩트하고 URL-safe한 토큰 형식.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### 구조: 3개의 Base64URL 인코딩된 파트

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Header    │ . │   Payload   │ . │  Signature  │
│   (JOSE)    │   │  (Claims)   │   │             │
└─────────────┘   └─────────────┘   └─────────────┘
```

#### 1. Header (JOSE Header)
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

#### 2. Payload (Claims Set)
```json
{
  "iss": "https://auth.example.com",
  "sub": "user123",
  "aud": "https://api.example.com",
  "exp": 1735689600,
  "iat": 1735603200,
  "nbf": 1735603200,
  "jti": "unique-token-id",
  "role": "admin"
}
```

#### 3. Signature
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret
)
```

### Registered Claims (표준 클레임)

| 클레임 | 이름 | 설명 |
|--------|------|------|
| `iss` | Issuer | 토큰 발급자 |
| `sub` | Subject | 토큰의 주체 (사용자 ID 등) |
| `aud` | Audience | 토큰 수신자 (API 서버 등) |
| `exp` | Expiration | 만료 시간 (Unix timestamp) |
| `nbf` | Not Before | 이 시간 이전에는 유효하지 않음 |
| `iat` | Issued At | 발급 시간 |
| `jti` | JWT ID | 토큰 고유 식별자 (재사용 방지) |

### 서명 알고리즘

| 종류 | 알고리즘 | 키 방식 | 용도 |
|------|----------|---------|------|
| **HMAC** | HS256, HS384, HS512 | 대칭키 (shared secret) | 단일 서비스 |
| **RSA** | RS256, RS384, RS512 | 비대칭키 (private/public) | 분산 시스템 |
| **ECDSA** | ES256, ES384, ES512 | 비대칭키 (타원곡선) | 모바일, IoT |
| **None** | none | 없음 | ⚠️ 디버깅 전용 |

### JWT vs 세션 기반 인증

```
[세션 기반]
클라이언트 → 서버: 로그인
서버 → DB: 세션 저장
서버 → 클라이언트: 세션 ID (쿠키)
클라이언트 → 서버: 요청 + 세션 ID
서버 → DB: 세션 조회 (매 요청마다!)

[JWT 기반]
클라이언트 → 서버: 로그인
서버 → 클라이언트: JWT (self-contained)
클라이언트 → 서버: 요청 + JWT
서버: 서명 검증만 (DB 조회 없음!)
```

### 사용 패턴

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 주요 보안 취약점 (RFC 8725 + 실무)

### 1. None Algorithm Attack
```json
// 공격자가 헤더를 변조
{ "alg": "none", "typ": "JWT" }
```
서버가 `alg: none`을 허용하면 서명 없이 토큰이 유효해짐.

**대응**: 알고리즘 화이트리스트 강제
```python
# ❌ 취약
jwt.decode(token, secret)

# ✅ 안전
jwt.decode(token, secret, algorithms=["HS256"])
```

### 2. Algorithm Confusion Attack (RS256 → HS256)

```
[정상 흐름 - RS256]
서버: private key로 서명
검증: public key로 검증

[공격]
1. 공격자가 서버의 public key 획득 (보통 공개됨)
2. 토큰 헤더를 RS256 → HS256으로 변경
3. public key를 HMAC secret으로 사용해 서명
4. 서버가 public key를 secret으로 착각하고 검증 통과!
```

**공격 과정**:
```python
# 1. 원본 토큰 (RS256)
{"alg": "RS256", "typ": "JWT"}

# 2. 공격자가 변조
{"alg": "HS256", "typ": "JWT"}

# 3. 공격자가 public key로 HMAC 서명
HMACSHA256(header + "." + payload, public_key)
```

**대응**: 알고리즘별 키 타입 검증
```python
# 키 타입과 알고리즘 일치 확인
if alg.startswith("HS") and not isinstance(key, bytes):
    raise InvalidKeyError()
```

### 3. Weak Secret (브루트포스)

```bash
# hashcat으로 HMAC secret 크래킹
hashcat -m 16500 jwt.txt wordlist.txt
```

**대응**: 최소 256비트 랜덤 시크릿
```python
import secrets
secret = secrets.token_bytes(32)  # 256 bits
```

### 4. JWK Injection (jwk/jku 헤더)

```json
// 공격자가 자신의 키를 주입
{
  "alg": "RS256",
  "jwk": {
    "kty": "RSA",
    "n": "공격자_public_key...",
    "e": "AQAB"
  }
}
```

서버가 토큰 내 `jwk` 파라미터의 키로 검증하면 공격자 키 신뢰.

**대응**: 토큰 내 키 무시, 서버 로컬 키만 사용

### 5. kid (Key ID) Injection

```json
// SQL Injection
{ "kid": "key1' OR '1'='1", "alg": "HS256" }

// Path Traversal
{ "kid": "../../etc/passwd", "alg": "HS256" }
```

**대응**: kid 파라미터 sanitization

### 취약점 요약 체크리스트

```
┌─────────────────────────────────────────────────────────────┐
│                    JWT 취약점 체크리스트                      │
├─────────────────────────────────────────────────────────────┤
│ □ alg: none 허용?              → 화이트리스트 강제           │
│ □ 알고리즘 검증 없이 디코딩?     → 명시적 알고리즘 지정        │
│ □ 약한 HMAC secret?            → 256비트+ 랜덤 시크릿        │
│ □ RS/HS 키 혼동?               → 키 타입 별도 검증           │
│ □ jwk/jku 헤더 신뢰?           → 토큰 내 키 무시             │
│ □ kid SQL/Path injection?      → 입력값 검증                │
│ □ exp 검증 누락?               → 만료 시간 필수 검증          │
│ □ aud 검증 누락?               → 대상자 검증                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Best Practices (RFC 8725 기반)

### 필수 검증 항목
```python
def validate_jwt(token, expected_audience, expected_issuer):
    payload = jwt.decode(
        token,
        key=SECRET_KEY,
        algorithms=["RS256"],           # 1. 알고리즘 화이트리스트
        audience=expected_audience,      # 2. aud 검증
        issuer=expected_issuer,          # 3. iss 검증
        options={
            "require": ["exp", "iat", "sub"],  # 4. 필수 클레임
            "verify_exp": True,          # 5. 만료 검증
        }
    )
    return payload
```

### 토큰 설계 원칙

| 원칙 | 이유 |
|------|------|
| **짧은 만료 시간** | Access Token: 15분~1시간 |
| **민감 정보 제외** | Payload는 암호화 아님, Base64일 뿐 |
| **Refresh Token 분리** | Access Token 탈취 시 피해 최소화 |
| **jti로 재사용 방지** | 토큰 블랙리스트 또는 일회용 토큰 |
| **HTTPS 필수** | 전송 중 탈취 방지 |

### Access Token + Refresh Token 패턴

```
┌─────────┐                      ┌─────────┐
│ Client  │                      │ Server  │
└────┬────┘                      └────┬────┘
     │ 1. 로그인 (credentials)        │
     │ ──────────────────────────────>│
     │                                │
     │ 2. Access Token (15min)        │
     │    + Refresh Token (7days)     │
     │ <──────────────────────────────│
     │                                │
     │ 3. API 요청 + Access Token     │
     │ ──────────────────────────────>│
     │                                │
     │ 4. Access Token 만료 (401)     │
     │ <──────────────────────────────│
     │                                │
     │ 5. Refresh Token으로 갱신      │
     │ ──────────────────────────────>│
     │                                │
     │ 6. 새 Access Token             │
     │ <──────────────────────────────│
```

---

## 내가 얻은 인사이트

### 1. "Self-contained"의 양날의 검

**장점**: DB 조회 없이 검증 → 스케일아웃 용이
**단점**: 즉시 무효화 불가 → 토큰 탈취 시 만료까지 유효

```
세션: 서버가 상태 보유 → 즉시 무효화 가능
JWT: 클라이언트가 상태 보유 → 발급 후 통제 어려움
```

**해결책**: 짧은 만료 + Refresh Token + 토큰 블랙리스트 (하이브리드)

### 2. Signature ≠ Encryption

```
JWT는 서명(Signature)이지 암호화(Encryption)가 아님!
Payload는 누구나 디코딩 가능 (Base64일 뿐)
```

```bash
# 누구나 payload 확인 가능
echo "eyJzdWIiOiIxMjM0NTY3ODkwIn0" | base64 -d
# {"sub":"1234567890"}
```

민감 정보는 JWE(JSON Web Encryption) 사용하거나 아예 넣지 말 것.
