# Towards Privacy-Preserving Social-Media SDKs on Android

## Source
- **논문**: [Towards Privacy-Preserving Social-Media SDKs on Android](https://www.usenix.org/system/files/usenixsecurity24-lu-haoran.pdf)
- **저자**: Haoran Lu, Yichen Liu, Xiaojing Liao, Luyi Xing (Indiana University Bloomington)
- **학회**: USENIX Security 2024
- **분야**: Mobile Security, Privacy, SDK Design

## AI Summary

### 1. 배경 및 문제의식
- 모바일 앱은 제3자 SDK(특히 소셜 플랫폼 SDK)를 광범위하게 통합.
- 교차 라이브러리 데이터 수집(XLDH, Cross-Library Data Harvesting): 앱 내 다른 라이브러리/모듈이 소셜 SDK가 다루는 풍부한 사용자 데이터를 수집·전파하는 위협.
- 기존 모바일 플랫폼 보호(권한, 샌드박스, 퍼미션 스코프)로는 XLDH를 충분히 제어하기 어려움.
- 규제 준수(GDPR/CCPA)와 사회적 기대에 따른 프라이버시 요구 증가.

### 2. 기여 및 제안
- **개념 일반화**: "프라이버시-보존 소셜 SDK"의 정의 및 앱 내 사용 방식 정식화.
- **근본 과제 정리**: XLDH 대응과 소셜 SDK 프라이버시 보장을 위한 설계 과제 도출.
- **PESP**: Clean-slate 설계의 E2E 시스템 제안(Privacy-Enhancing Social SDKs Platform, 가칭)으로 프라이버시-보존 SDK 구현 지원.
- **평가**: 효과성, 성능 오버헤드, 실용성 측면에서 만족스러운 결과.

### 3. 핵심 아이디어(PESP)
- **데이터 최소화**: 소셜 SDK의 입력/출력 단계에서 목적 기반 최소 데이터만 접근·반환.
- **경계 강제**: 앱 내 다른 라이브러리가 소셜 SDK 데이터에 간접 접근하려는 경로(IPC, 인텐트, 파일, 메모리 공유)를 정책으로 차단/검사.
- **정책 기반 사용**: 선언적 정책으로 어떤 데이터 타입/목적/사용 컨텍스트에서 접근 허용할지 지정.
- **감사·추적**: 소셜 SDK 데이터 접근 로그/증적을 수집해 규제·감사 대응.

### 4. 위협 모델과 해결 범위
- **위협**: 앱 내 서드파티 라이브러리/애드 네트워크/분석 SDK가 소셜 SDK 데이터에 비의도적 접근.
- **해결**: SDK 경계에서 데이터 흐름 제어, 목적 제한, 사용 컨텍스트 검증.
- **비해결**: 루트/OS 취약점, 하드웨어 레벨 공격 등 플랫폼 외부 위협은 범위 밖.

### 5. 평가 요약
- **효과성**: 주요 XLDH 경로 차단/완화.
- **오버헤드**: 실용 수준(앱 UX 저하 미미).
- **적용성**: 광범위한 소셜 SDK/앱 시나리오에 적용 가능.

## 내가 얻은 인사이트

### 1. SDK 경계에서의 데이터 가드레일
- **입력 최소화**: SDK API에서 필수 필드만 수용. 선택 필드는 기본 비활성.
- **출력 제어**: 응답에서 민감 필드 제거/가명화. `fields=...` 화이트리스트 방식.
- **목적 제한**: 호출 목적 태그(`purpose=login`, `purpose=share`)에 따라 허용 데이터 변동.

### 2. 앱 내 데이터 흐름 제어 패턴
- **Interceptor/Wrapper**: SDK 호출 전후 훅으로 검증/필터 적용.
- **IPC/Intent 정책**: 소셜 SDK 데이터가 IPC/인텐트로 외부 라이브러리에 전달될 때 정책 검사.
- **파일/메모리 경로 차단**: SDK가 반환한 데이터의 파일 저장/메모리 공유를 제한.

### 3. 선언적 정책 예시
```json
{
  "policy_version": 1,
  "purposes": {
    "login": {
      "allow_fields": ["user_id", "email_hash"],
      "deny_fields": ["raw_email", "phone"],
      "retention": "7d"
    },
    "share": {
      "allow_fields": ["post_id", "thumbnail_url"],
      "deny_fields": ["full_image", "location_precision"],
      "retention": "24h"
    }
  },
  "ipc_rules": {
    "allow_targets": ["com.example.app"],
    "deny_targets": ["*analytics*", "*adnetwork*"]
  }
}
```

### 4. 감사/컴플라이언스
- **접근 로그**: 목적, 필드, 호출자, 전달 경로, 결과를 기록.
- **감사 증적**: 정책 변경 이력, 위반 탐지, 사용자 동의 상태와 연계.

### 5. 운영 권고
- **기본 차단, 필요 시 허용**: 최소 권한 원칙.
- **테스트**: XLDH 경로 시나리오 기반 테스트(IPC/파일/인텐트/메모리 공유).
- **성능**: 정책 검사·필터링의 지연을 측정하고 임계치 내 유지.

---

**결론**: 이 논문은 소셜 SDK 통합 환경에서 XLDH 위협을 겨냥해, 데이터 최소화·경계 강제·정책 기반 사용·감사 추적을 결합한 PESP 설계를 제시한다. SDK를 설계·운영할 때 위 접근법을 반영하면, 프라이버시 준수와 보안 강화를 동시에 달성하면서 실무 적용성을 유지할 수 있다.
