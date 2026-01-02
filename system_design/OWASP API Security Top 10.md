# OWASP API Security Top 10

## 출처
- **링크**: https://owasp.org/www-project-api-security/

---

## AI 요약

OWASP(Open Web Application Security Project)에서 발표한 **API 보안 취약점 Top 10 (2023 버전)**. API가 현대 애플리케이션의 핵심이 되면서 공격 대상이 되고 있어, 개발자와 보안 담당자가 알아야 할 주요 위험을 정리한 문서.

### Top 10 목록

| 순위 | 취약점 | 설명 |
|------|--------|------|
| **API1** | Broken Object Level Authorization (BOLA) | 객체 ID 조작으로 다른 사용자 데이터 접근. **API 공격의 40% 차지** |
| **API2** | Broken Authentication | 인증 토큰 탈취, 크리덴셜 스터핑, 브루트포스 공격 |
| **API3** | Broken Object Property Level Authorization | 과도한 데이터 노출 + Mass Assignment 통합. 객체 속성 레벨 권한 검증 부재 |
| **API4** | Unrestricted Resource Consumption | Rate Limiting 없음 → DoS, 비용 폭증 |
| **API5** | Broken Function Level Authorization | 관리자/일반 기능 분리 미흡 → 권한 상승 |
| **API6** | Unrestricted Access to Sensitive Business Flows | 비즈니스 로직 악용 (티켓 매점매석, 스팸 댓글 등) |
| **API7** | Server Side Request Forgery (SSRF) | 서버가 악의적 URI로 요청하도록 유도 |
| **API8** | Security Misconfiguration | 잘못된 설정, 불필요한 기능 활성화, 기본 비밀번호 |
| **API9** | Improper Inventory Management | API 버전 관리 미흡, 문서화 부재, deprecated 엔드포인트 노출 |
| **API10** | Unsafe Consumption of APIs | 서드파티 API 데이터를 과신하여 검증 없이 사용 |

### 2019 → 2023 변경점
- **통합**: Excessive Data Exposure + Mass Assignment → API3 (BOPLA)
- **신규**: SSRF (API7), Unrestricted Access to Business Flows (API6), Unsafe Consumption (API10)
- **삭제**: Injection, Insufficient Logging & Monitoring (다른 리스트에서 다룸)

### 핵심 대응 원칙
1. **모든 엔드포인트에 객체/함수 레벨 권한 검증** 적용
2. **Rate Limiting** 필수 구현
3. **입력값 검증** - 서드파티 API 응답 포함
4. **API 인벤토리** 관리 및 버전 deprecation 정책 수립
5. **최소 권한 원칙** 적용

---

## 내가 얻은 인사이트

1. 객체 ID 조작으로 다른 사용자 데이터 접근하는 경우가 40%이라는 것은 꽤나 놀랍다. 말도 안되는 것 같으면서도 또 말이 되는 것도 같아서, 당연한 것을 지키는 것이 새삼 중요하다는 생각이 든다.
2. 과도한 데이터 노출 역시 동일한 맥락으로 와닿는다. 개발자로서 다른 개발자와의 협업을 위해 간혹 좋게 좋게 설계를 타협하고 싶은 생각이 들 때가 간혹 있는데 이런 상황이 참 난처한 것 같다.
3. 생각보다 특별히 창의적인 문제라기 보다는 귀찮거나 타협해서 생기는 문제인 듯 하다.