# API and CloudMonkey — Signed Query 와 CLI

> **CloudStack은 모든 외부 호출이 단일 REST 엔드포인트의 Signed Query 다.**

OpenStack의 "토큰 헤더(X-Auth-Token)" 와는 완전히 다른 모델. AWS Signature V2와 비슷한 방식.

> 출처: [API Reference](https://cloudstack.apache.org/api.html) · [API Developer's Guide](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#the-cloudstack-api).

---

## 1. 단일 엔드포인트

```
https://<MS_IP>:8443/client/api?command=<API명>&...&apiKey=<...>&signature=<...>
```

OpenStack은 서비스마다 다른 엔드포인트(`:8774` Nova, `:9292` Glance, ...)인데 CloudStack은 **하나**.

```bash
$ curl -k "https://192.168.64.5:8443/client/api?command=listZones&response=json&apiKey=$KEY&signature=$SIG"
```

---

## 2. Signed Query — 작동 원리

> [Signing API Calls](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#signing-api-requests).

### 1단계: 파라미터 정렬

```
{command: "listVirtualMachines", apiKey: "abc123", response: "json"}
       ▼ 알파벳순 정렬 + URL encode
"apikey=abc123&command=listvirtualmachines&response=json"   (전부 lower-case)
```

### 2단계: HMAC-SHA1

```
signature = base64( HMAC_SHA1(secretKey, sorted_params_lower) )
```

### 3단계: 원본 파라미터에 signature 붙여서 전송

```
final = original_params + "&signature=" + url_encode(signature)
```

### 검증 (서버 측)

서버는:
1. 같은 정렬/소문자화로 재계산
2. apiKey 로 user 조회 → secretKey 로 HMAC 재계산
3. signature 일치하면 통과

→ **세션/토큰 없음. 매 요청 자체 완결.**

---

## 3. 왜 이렇게 했나 — 트레이드오프

| | Signed Query (CloudStack) | Bearer Token (OpenStack) |
|---|---|---|
| 세션 관리 | ❌ (stateless) | 토큰 1시간 만료 |
| 키 회수 | apiKey 폐기 → 즉시 무효 | 토큰 만료 또는 revocation list |
| 서버 부하 | HMAC 1회 (사실상 0) | Fernet 복호화 + 캐시 |
| 키 노출 시 | secretKey 영구 위험 (수동 회수) | 토큰 노출은 1시간만 위험 |
| 사용자 UX | apiKey 쌍 발급 필요 | username/password로 매번 |
| 봇/CI에 좋은가 | ✅ (그냥 키 쌍) | Application Credential 별도 |

→ "**서버 부하 zero**" 가 강점. 단, "**secretKey 노출은 영구 위험**" 이 약점.

---

## 4. apiKey / secretKey 발급

UI에서 사용자 프로필 → "Generate Keys" 또는:

```bash
# API로 발급 (admin 전용)
$ cmk register userkeys id=<user-id>
{
  "apikey": "abcdef...",
  "secretkey": "ghijkl..."
}
```

→ apiKey: 14~256바이트, 공개해도 무방 (URL에 들어감)
→ secretKey: 절대 공개 X. **HMAC 계산에만**

---

## 5. CloudMonkey (cmk) — 공식 CLI

> [CloudMonkey on PyPI](https://pypi.org/project/cloudmonkey/) · [GitHub](https://github.com/apache/cloudstack-cloudmonkey).

OpenStack의 `openstack` CLI 같은 도구. 서명 자동 처리, JSON 응답 가공.

### 설치

```bash
# Python 3
$ pip install cloudmonkey
$ cmk version
```

(Apple Silicon: 그냥 동작)

### 초기 설정

```bash
$ cmk set url https://192.168.64.5:8443/client/api
$ cmk set apikey <APIKEY>
$ cmk set secretkey <SECRETKEY>
$ cmk set timeout 3600
$ cmk set output table   # or json, csv, text

# 모든 명령 메타데이터 동기화 (서버 버전 매치)
$ cmk sync
```

`~/.cloudmonkey/config` 에 저장.

### 자주 쓰는 명령 패턴

```bash
# list 계열
$ cmk list zones
$ cmk list templates templatefilter=featured
$ cmk list virtualmachines state=Running
$ cmk list hosts

# create / deploy 계열
$ cmk deploy virtualmachine \
    serviceofferingid=<...> \
    templateid=<...> \
    zoneid=<...>

$ cmk create network ...

# 비동기 결과 확인
$ cmk query asyncjobs jobid=<...>

# 도움말
$ cmk list virtualmachines --help
```

### 다중 프로파일 (admin / user 전환)

```bash
$ cmk set profile admin
$ cmk set apikey ...

$ cmk set profile alice
$ cmk set apikey ...

$ cmk -p alice list virtualmachines
```

---

## 6. 비동기 잡 — query asyncjobs

대부분의 deploy/start/stop API는 **즉시 jobid를 반환**하고 백그라운드 처리.

```bash
$ cmk deploy virtualmachine ...
{"jobid": "abc-123"}

# 폴링
$ cmk query asyncjobs jobid=abc-123
{
  "jobstatus": 0,    # 0=running, 1=success, 2=failed
  "jobresult": null
}

# 잠시 후
$ cmk query asyncjobs jobid=abc-123
{
  "jobstatus": 1,
  "jobresult": {
    "virtualmachine": {
      "id": "...",
      "name": "test-vm",
      "state": "Running"
    }
  }
}
```

cmk는 기본으로 **자동 폴링** 한다. `asyncblock=false` 옵션으로 즉시 jobid만 받기 가능.

---

## 7. raw API 직접 호출 (curl)

cmk 없이도 가능.

```bash
#!/bin/bash
APIKEY="..."
SECRETKEY="..."
HOST="https://192.168.64.5:8443"

# 1. 파라미터 모음
PARAMS="command=listVirtualMachines&response=json&apiKey=$APIKEY"

# 2. 정렬 + 소문자
SORTED=$(echo "$PARAMS" | tr '&' '\n' | sort | tr '\n' '&' | sed 's/&$//' | tr 'A-Z' 'a-z')

# 3. HMAC-SHA1 + base64 + URL encode
SIG=$(echo -n "$SORTED" | openssl sha1 -hmac "$SECRETKEY" -binary | base64 | tr '+/' '-_' | sed 's/=$//')
SIG_ENC=$(printf '%s' "$SIG" | jq -sRr @uri)

# 4. 호출
curl -sk "$HOST/client/api?$PARAMS&signature=$SIG_ENC" | jq
```

(실전에서는 cmk나 SDK 권장.)

---

## 8. SDK 옵션

| 언어 | 라이브러리 |
|---|---|
| Python | [cs](https://pypi.org/project/cs/) (작고 핵심만), cloudstack (좀 더 풀) |
| Go | [go-cloudstack](https://github.com/apache/cloudstack-go) (공식) |
| Java | [cloudstack-java](https://github.com/apache/cloudstack/tree/main/sdk-java) |
| Terraform | [terraform-provider-cloudstack](https://registry.terraform.io/providers/cloudstack/cloudstack) |

---

## 9. 자주 밟는 지뢰

- **401 / signature mismatch** → URL 인코딩 정렬을 두 번 하거나 빠뜨림. cmk가 가장 안전.
- **자기 자신 인증서가 self-signed** → cmk는 `tlsverify` 옵션 또는 시스템 trust store에 추가.
- **API 메타데이터 mismatch** → `cmk sync` 안 해서 새 API 모름. MS 업그레이드 후 항상 sync.
- **파라미터 한글/특수문자** → URL 인코딩 신중. cmk는 자동.

---

## 10. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Keystone token (X-Auth-Token) | apiKey + signature (URL) |
| `openstack` CLI | `cmk` (cloudmonkey) |
| `openstack server create` | `cmk deploy virtualmachine` |
| Service catalog (toy 카탈로그) | (없음. 단일 엔드포인트) |
| token expiration | (없음. apiKey 폐기로 회수) |

---

## 다음

→ [accounts-domains-projects.md](./accounts-domains-projects.md): 어떤 사용자가 어느 키를 발급받나.
→ [service-offerings.md](./service-offerings.md): API 호출 시 넘기는 offeringid 가 뭔지.
→ [../05-deep-dives/api-auth-flow.md](../05-deep-dives/api-auth-flow.md): Signed Query 의 내부 검증 코드 흐름.

---

## 공식 문서 레퍼런스

- [API Reference (4.20)](https://cloudstack.apache.org/api.html)
- [Developer's Guide — The CloudStack API](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#the-cloudstack-api)
- [Signing API Requests](https://docs.cloudstack.apache.org/en/latest/developersguide/dev.html#signing-api-requests)
- [CloudMonkey GitHub](https://github.com/apache/cloudstack-cloudmonkey)
