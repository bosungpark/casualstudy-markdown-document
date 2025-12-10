# Hero: On the Chaos When PATH Meets Modules

## 출처
- **논문**: Hero: On the Chaos When PATH Meets Modules
- **저자**: Ying Wang, Liang Qiao, Chang Xu, Yepang Liu, Shing-Chi Cheung, Na Meng, Hai Yu, Zhiliang Zhu
- **게재**: ICSE 2021 (43rd International Conference on Software Engineering)
- **원문**: https://arxiv.org/abs/2102.12105

---

## AI 요약

### 핵심 문제: GOPATH vs Go Modules의 충돌

Go는 2가지 **호환되지 않는** 라이브러리 참조 방식을 지원합니다:

**1. GOPATH Mode (구식, ~2018)**:
```bash
# 환경변수 기반
export GOPATH=$HOME/go

# 프로젝트 위치 강제
$GOPATH/src/github.com/user/project

# 의존성 위치
$GOPATH/src/github.com/dep/library
```

**2. Go Modules (신식, 2018~)**:
```bash
# go.mod 파일 기반
module github.com/user/project

require (
    github.com/dep/library v1.2.3
)

# 프로젝트 위치 자유
~/projects/myproject  # 어디든 가능
```

**문제**: 두 방식이 **동시에 존재**하며 **서로 충돌**합니다.

### 실제 발생하는 DM(Dependency Management) 이슈

**예시 1: Reference Inconsistency (참조 불일치)**

```
프로젝트 A (Go Modules):
go.mod → require github.com/lib/pq v1.3.0

프로젝트 B (GOPATH 의존):
import "github.com/lib/pq"  // 버전 명시 없음
→ $GOPATH/src/github.com/lib/pq 사용 (v1.8.0)

A와 B를 함께 사용하면?
→ v1.3.0 vs v1.8.0 충돌!
→ Build Failure
```

**예시 2: Missing go.mod**

```bash
# 프로젝트가 Go Modules를 쓴다고 주장
README.md: "This project uses Go modules"

# 실제로는 go.mod 파일 없음
$ ls
main.go  README.md  # go.mod 없음!

# 빌드 시도
$ go build
go: cannot find main module; see 'go help modules'
```

**예시 3: PATH Pollution**

```bash
# GOPATH에 오래된 버전 존재
$GOPATH/src/example.com/lib → v1.0.0

# go.mod에서 새 버전 요구
require example.com/lib v2.0.0

# 빌드러가 GOPATH를 먼저 찾음
$ go build
# v1.0.0 사용! (잘못된 버전)
```

### Hero의 작동 방식

**3단계 탐지 시스템**:

**1단계: Static Analysis (정적 분석)**

```go
// 코드 분석
import "github.com/dep/library"

// go.mod 분석
require github.com/dep/library v1.2.3

// 검증
import 경로 == require 경로? ✓
버전 일치? ✓
```

**2단계: Build Simulation (빌드 시뮬레이션)**

```bash
# 실제 빌드 없이 의존성 해결 시뮬레이션
$ hero simulate
→ GOPATH 체크
→ go.mod 체크
→ 충돌 탐지
```

**3단계: Cross-referencing (교차 참조)**

```
프로젝트가 의존하는 라이브러리들 분석:
- 라이브러리 A: GOPATH 사용
- 라이브러리 B: Go Modules 사용
→ 혼용 경고!
```

### 탐지된 DM 이슈 유형

**Type 1: Module-GOPATH Conflict**
```bash
# 프로젝트는 Modules 사용
go.mod 존재

# 하지만 GOPATH 환경변수 설정됨
export GOPATH=$HOME/go

# 의존성이 GOPATH에도 존재
$GOPATH/src/github.com/dep/lib (v1.0)
go.mod require github.com/dep/lib v2.0

→ 어느 버전 사용? (불명확)
```

**Type 2: Missing go.mod**
```bash
# Go 1.13+ 환경
$ go version
go version go1.16

# 프로젝트에 go.mod 없음
$ ls
main.go  vendor/

# 기본적으로 Modules 모드 활성화됨
$ go build
cannot find main module
```

**Type 3: Inconsistent Import Path**
```go
// go.mod
module example.com/myproject

// 코드에서
import "github.com/myproject/utils"  // ❌ 경로 불일치

// 올바른 경로
import "example.com/myproject/utils"  // ✓
```

**Type 4: Version Mismatch**
```go
// go.mod
require github.com/lib/pq v1.3.0

// 코드 주석
// This code requires github.com/lib/pq v1.8.0+
// ❌ go.mod와 주석 불일치
```

### Hero의 자동 수정 제안

**수정 1: go.mod 생성**
```bash
# 탐지: go.mod 없음
$ hero detect
Issue: Missing go.mod

# 제안
$ hero fix
Creating go.mod...

# 생성된 파일
module github.com/user/project

go 1.16

require (
    github.com/dep1 v1.2.3  # import 분석으로 자동 추출
    github.com/dep2 v2.0.0
)
```

**수정 2: Import Path 교정**
```go
// 탐지: import 경로와 module 경로 불일치
// go.mod
module example.com/myproject

// main.go (잘못됨)
import "github.com/myproject/utils"

// Hero 제안
import "example.com/myproject/utils"
```

**수정 3: GOPATH 제거 권장**
```bash
# 탐지: GOPATH와 Modules 혼용
export GOPATH=$HOME/go

# Hero 제안
1. go.mod 사용 확정
2. GOPATH 의존성 제거
3. go mod tidy로 정리
```

**수정 4: Vendor 디렉토리 정리**
```bash
# 탐지: vendor/ 와 go.mod 중복
vendor/
go.mod

# Hero 제안
rm -rf vendor/
go mod vendor  # go.mod 기준으로 재생성
```

### 실험 결과

**19,000개 인기 Go 프로젝트 분석**:

| 지표 | 결과 |
|------|------|
| 탐지율 | **98.5%** (벤치마크 기준) |
| 발견된 새 이슈 | **2,422개** (2,356 프로젝트) |
| 보고된 이슈 | 280개 |
| 확인된 이슈 | **181개 (64.6%)** |
| 수정 완료/진행 중 | **160개 (88.4%)** |
| Hero 제안 채택률 | **거의 100%** |

**이슈 분포**:
- Module-GOPATH Conflict: 42%
- Missing go.mod: 28%
- Import Path Inconsistency: 18%
- Version Mismatch: 12%

**영향받은 유명 프로젝트**:
- Kubernetes
- Docker
- Prometheus
- Istio
- Hugo

### 왜 이런 문제가 발생하나?

**1. 긴 전환 기간 (2018~현재)**
```
2009: Go 출시 (GOPATH만)
2018: Go Modules 도입
2021: 여전히 GOPATH 프로젝트 존재
→ 5년 이상 혼용 상태
```

**2. 레거시 코드**
```bash
# 오래된 튜토리얼/문서
"Step 1: export GOPATH=..."

# 개발자가 따라함
→ GOPATH 습관 유지
→ go.mod 추가 안 함
```

**3. Vendor 디렉토리 혼란**
```bash
# GOPATH 시절
vendor/  # 의존성 복사

# Modules 시대
go.mod + go.sum  # 의존성 선언

# 개발자 혼란
"vendor가 있는데 go.mod도 필요한가?"
→ 둘 다 유지 → 충돌
```

**4. Transitive Dependencies (전이 의존성)**
```
내 프로젝트 (Modules)
→ 라이브러리 A (Modules)
  → 라이브러리 B (GOPATH!)
    → 충돌 발생
```

### Hero의 한계

**1. 동적 Import 탐지 불가**
```go
// 런타임 Import (reflect 사용)
pkgName := "github.com/dep/lib"
pkg := reflect.ValueOf(pkgName)
→ Hero가 정적 분석으로 못 잡음
```

**2. 비표준 빌드 시스템**
```bash
# Makefile 사용
make build
→ go build를 직접 안 쓰면 Hero 분석 어려움
```

**3. Private Repository**
```go
// go.mod
require github.com/private/repo v1.0.0
→ Hero가 접근 불가 (인증 필요)
```

### Go Modules 모범 사례

**프로젝트 초기화**:
```bash
# 1. go.mod 생성
go mod init github.com/user/project

# 2. 의존성 자동 추가
go mod tidy

# 3. GOPATH 환경변수 제거
unset GOPATH

# 4. vendor 사용 시 (선택)
go mod vendor
```

**의존성 업데이트**:
```bash
# 특정 라이브러리 업데이트
go get github.com/dep/lib@v2.0.0

# go.mod 정리
go mod tidy

# go.sum 검증
go mod verify
```

**CI/CD 설정**:
```yaml
# .github/workflows/ci.yml
- name: Build
  run: |
    go mod download  # 의존성 다운로드
    go mod verify    # 검증
    go build
```

---

## 내가 얻은 인사이트

기술 전환의 혼란은 "호환성 유지" 때문이다. Go는 GOPATH를 버리고 Modules로 가고 싶었지만, 기존 프로젝트 깨지는 걸 막기 위해 **둘 다 지원**했고 그 결과 둘 다 망가졌다. 2,422개 프로젝트가 혼란에 빠졌다. Clean Break가 나았을 수도 있다.

**"작동한다"와 "올바르다"는 다르다.** 많은 프로젝트가 GOPATH 환경에서 빌드는 되지만, go.mod 없이 재현 불가능하거나 다른 환경에서 깨진다. Hero가 찾은 2,422개 이슈 중 상당수는 "지금은 작동하지만 언젠가 터질 폭탄"이다.
