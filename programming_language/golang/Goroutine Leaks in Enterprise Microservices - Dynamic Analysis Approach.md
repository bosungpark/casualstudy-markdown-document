# Unveiling and Vanquishing Goroutine Leaks in Enterprise Microservices: A Dynamic Analysis Approach

## 출처
- **링크**: https://arxiv.org/abs/2312.12002
- **저자**: Georgian-Vlad Saioc, Dmitriy Shirchenko, Milind Chabbi
- **발표**: CGO 2024

---

## AI 요약

### 문제 정의
Go 언어는 기업용 마이크로서비스 시스템에서 인기를 얻고 있으며, 경량 "goroutine"을 통해 동시성을 일급 시민(first-class citizen)으로 다룬다. Go는 goroutine 간 통신과 동기화를 위해 메시지 패싱(message-passing)을 권장하지만, 이를 부적절하게 사용하면 "부분 교착 상태(partial deadlock)"라는 미묘한 동시성 버그가 발생할 수 있다. 이는 차단된 송신자(또는 수신자)가 대응하는 수신자(또는 송신자)를 영원히 찾지 못해 해당 goroutine이 메모리를 누수시키는 문제다.

### 연구 방법
본 논문은 Uber의 Go 모노레포(7,500만 줄, 2,500개 이상의 마이크로서비스)에서 메시지 패싱과 그로 인한 부분 교착 상태의 발생 빈도를 체계적으로 연구했다. 두 가지 경량 동적 분석 도구를 개발했다:

1. **Goleak**: 단위 테스트 중 부분 교착 상태를 감지하여 새로운 버그 도입을 방지
2. **LeakProf**: 프로덕션 환경에 배포된 서비스에서 얻은 goroutine 프로파일을 사용하여 복잡한 제어 흐름, 탐색되지 않은 인터리빙, 테스트 커버리지 부족으로 인해 발생하는 복잡한 버그를 정확히 찾아냄

### 주요 결과
- **Goleak**: 레거시 코드에서 857개의 기존 goroutine 누수를 발견하고, 1년간 약 260개의 새로운 누수 도입을 방지
- **LeakProf**: 24개의 goroutine 누수를 발견하고 21개를 수정하여, 일부 프로덕션 서비스에서 최대 34% 성능 향상 및 9.2배 메모리 사용량 감소 달성

### 핵심 개념
- **Partial Deadlock**: 전체 시스템이 아닌 일부 goroutine만 영구적으로 차단되는 상태
- **Goroutine Leak**: 차단된 goroutine이 해제되지 않아 메모리가 누수되는 현상
- **Message Passing**: Go의 채널을 통한 goroutine 간 통신 메커니즘
- **Dynamic Analysis**: 실행 중인 프로그램을 분석하여 버그를 찾는 기법

---

## 내가 얻은 인사이트

고랭의 동시성은 생각보다 안전하지 않다.