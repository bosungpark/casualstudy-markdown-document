# Twelve-Factor App

## 출처
- **링크**: https://12factor.net/
- **저자**: Adam Wiggins (2011)

---

## AI 요약

Twelve-Factor App은 현대적인 SaaS(Software as a Service) 애플리케이션을 구축하기 위한 12가지 방법론입니다. 클라우드 네이티브 환경에서 확장 가능하고 유지보수가 용이한 애플리케이션을 개발하기 위한 모범 사례를 제시합니다.

**12가지 원칙:**
1. **Codebase**: 버전 관리되는 하나의 코드베이스, 다양한 배포
2. **Dependencies**: 명시적으로 선언되고 분리된 의존성
3. **Config**: 환경별 설정을 환경 변수에 저장
4. **Backing Services**: 백엔드 서비스를 연결된 리소스로 취급
5. **Build, Release, Run**: 빌드, 릴리스, 실행 단계를 엄격히 분리
6. **Processes**: 애플리케이션을 하나 이상의 stateless 프로세스로 실행
7. **Port Binding**: 포트 바인딩을 통해 서비스 공개
8. **Concurrency**: 프로세스 모델을 통한 확장
9. **Disposability**: 빠른 시작과 graceful shutdown으로 안정성 극대화
10. **Dev/Prod Parity**: 개발, 스테이징, 프로덕션 환경을 최대한 유사하게 유지
11. **Logs**: 로그를 이벤트 스트림으로 취급
12. **Admin Processes**: 관리/유지보수 작업을 일회성 프로세스로 실행
