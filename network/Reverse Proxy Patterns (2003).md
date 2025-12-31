# Reverse Proxy Patterns (2003)

## 출처
- **제목**: Reverse Proxy Patterns
- **저자**: Peter Sommerlad (스위스 Rapperswil 대학)
- **학회**: EuroPLoP 2003 (8th European Conference on Pattern Languages of Programs)
- **페이지**: 431-458 (28페이지)
- **링크**: https://www.researchgate.net/publication/221034753_Reverse_Proxy_Patterns

---

## AI 요약

### 배경: Forward Proxy vs Reverse Proxy

```
[Forward Proxy]
클라이언트 → 프록시 → 인터넷 → 서버
         (클라이언트 숨김)

[Reverse Proxy]  
클라이언트 → 인터넷 → 프록시 → 서버들
                    (서버 숨김)
```

- **Forward Proxy**: 브라우저에 설정, 클라이언트의 IP 숨김
- **Reverse Proxy**: 서버 앞에 위치, 클라이언트에게 투명함, 서버 구조 숨김

### 3가지 Reverse Proxy 패턴

#### 1. Protection Reverse Proxy (보호용)
**목적**: 애플리케이션 프로토콜 레벨에서 서버 보호

```
인터넷 → [방화벽] → [Protection Proxy] → 내부 서버들
                    ↓
              - 프로토콜 검증
              - 악성 요청 필터링
              - 취약한 서버 격리
```

**적용 시나리오**:
- 취약한 레거시 서버 보호
- WAF(Web Application Firewall) 기능
- SQL Injection, XSS 등 공격 차단

**Known Uses**: 금융권에서는 "인터넷으로 제공하는 모든 프로토콜에 reverse proxy 사용" 가이드라인

#### 2. Integration Reverse Proxy (통합용)
**목적**: 여러 서버를 단일 진입점으로 통합

```
                         ┌→ 서버 A (/app1)
클라이언트 → [Integration] ├→ 서버 B (/app2)  
              Proxy       └→ 서버 C (/api)
```

**제공 기능**:
- URL 재작성 (URL Rewriting)
- 내부 네트워크/호스트 구조 은닉
- 가상 통합 (물리적으로 분산된 서버를 논리적으로 통합)

**적용 시나리오**:
- 마이크로서비스 앞단
- 레거시 + 신규 시스템 통합
- 도메인 통합 (여러 서브도메인 → 단일 도메인)

#### 3. Front Door (프론트 도어)
**목적**: Single Sign-On과 접근 제어

```
클라이언트 → [Front Door] → 인증/인가 확인 → 백엔드 서버들
                ↓
         - SSO 세션 관리
         - 권한 검증
         - 감사 로깅
```

**적용 시나리오**:
- 중앙 집중식 접근 정책
- 개발 환경에서 외부 접근 통제
- 엔터프라이즈 SSO 구현

**Known Uses**: IBM Tivoli Access Manager, SYNLOGIC Frontdoor

### 패턴 조합

세 패턴은 독립적이지만 보통 **조합**해서 사용:

```
                    ┌─────────────────────────┐
                    │     Reverse Proxy       │
                    ├─────────────────────────┤
클라이언트 →        │ Front Door (인증/SSO)   │
                    │    +                    │  → 백엔드 서버들
                    │ Protection (보안)       │
                    │    +                    │
                    │ Integration (라우팅)    │
                    └─────────────────────────┘
```

### Forces (설계 시 고려사항)

| Force | 설명 |
|-------|------|
| **보안** | 서버를 직접 노출하면 취약점 공격 위험 |
| **통합** | 여러 서버를 하나처럼 보이게 해야 함 |
| **SSO** | 사용자가 한 번만 인증하길 원함 |
| **성능** | 프록시 계층이 지연 추가 |
| **복잡성** | 프록시 자체가 장애점이 될 수 있음 |
| **투명성** | 클라이언트는 프록시 존재를 모르는 게 이상적 |

### Related Patterns

- **Single Access Point** [Security Patterns]: Protection Reverse Proxy의 상위 패턴
- **Demilitarized Zone (DMZ)**: 프록시가 위치하는 네트워크 구역
- **Facade** [GoF]: 복잡한 서브시스템에 단순한 인터페이스 제공
- **Proxy** [GoF]: 객체 수준의 대리자 패턴

---
