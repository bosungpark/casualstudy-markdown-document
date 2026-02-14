# FastAPI Dependency Injection 원리

## 출처
- **아티클**: Unlocking FastAPI's Power with Dependency Injection
- **출처**: Leapcell Blog
- **링크**: https://leapcell.io/blog/unlocking-fastapi-s-power-with-dependency-injection

---

## AI 요약

### 1. FastAPI의 Dependency Injection이란?

FastAPI의 DI 시스템은 **"함수가 곧 의존성"**이라는 철학을 기반으로 한다. Spring의 IoC 컨테이너나 별도 데코레이터 없이, **일반 함수 + `Depends()` 마커**만으로 의존성 그래프를 구성한다.

| 용어 | 의미 |
|------|------|
| **Dependency** | 다른 객체가 동작하기 위해 필요한 객체 또는 서비스 |
| **Dependent** | 의존성을 필요로 하는 함수 또는 클래스 |
| **IoC** | 제어 흐름을 프레임워크에 위임하는 설계 원칙 |
| **Injector** | 의존성을 생성하고 제공하는 주체 (FastAPI 자체) |
| **Provider** | `Depends()`로 감싸져 의존성을 공급하는 함수 |

---

### 2. 내부 동작 원리 — 요청 도착부터 주입까지

요청이 들어오면 FastAPI는 라우트 함수의 시그니처를 검사하여 다음 순서로 파라미터를 해석한다.

```
[HTTP Request]
      │
      ▼
┌─────────────────────────┐
│  1. 시그니처 검사         │  라우트 함수의 파라미터를 순회
│     (Signature Inspect)  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  2. 파라미터 분류         │  타입 힌트 + 기본값으로 역할 결정
│     (Parameter Classify) │
│                          │
│  ┌─ 타입 힌트만 있음      │ → path / query / body 파라미터
│  └─ Depends() 기본값     │ → 의존성으로 인식
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  3. 의존성 그래프 구축    │  Depends() 체이닝을 재귀적으로 탐색
│     (Build Dep Graph)    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  4. Top-Down 해석        │  그래프를 순회하며 함수 호출
│     + 요청 단위 캐싱      │  동일 의존성은 1회만 실행
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  5. 반환값 주입           │  해석된 값을 핸들러 파라미터에 바인딩
│     (Inject Results)     │
└────────┬────────────────┘
         │
         ▼
    [핸들러 실행]
         │
         ▼
┌─────────────────────────┐
│  6. Cleanup (yield 이후)  │  yield 기반 의존성의 finally 블록 실행
└─────────────────────────┘
```

**핵심 포인트**: `Depends`는 실행자가 아니라 **마커(marker)**다. 실제 실행은 FastAPI의 의존성 해석 엔진이 요청 시점에 수행한다.

---

### 3. 의존성 해석의 핵심 메커니즘

#### 3-1. 요청 단위 캐싱 (Per-Request Caching)

같은 요청 내에서 동일한 의존성이 여러 번 참조되면 **한 번만 실행**하고 결과를 재사용한다.

```
                    get_db()
                   ╱        ╲
          get_user()     get_items()
                   ╲        ╱
                  handler()

→ get_db()는 1회만 호출, 같은 세션 객체가 get_user와 get_items에 주입됨
```

#### 3-2. 재귀적 체이닝 (Sub-Dependency Chaining)

의존성 함수 자체가 다른 `Depends()`를 선언할 수 있다. FastAPI가 이를 재귀적으로 해석하므로 핸들러 시그니처를 깔끔하게 유지할 수 있다.

```
auth_header → verify_token → get_current_user → handler

핸들러는 get_current_user만 선언하면 됨.
내부 의존성 체인은 프레임워크가 자동으로 해석.
```

#### 3-3. 비동기 지원

| 의존성 유형 | 실행 방식 |
|------------|----------|
| `async def` 의존성 | 이벤트 루프에서 직접 실행 |
| 일반 `def` 의존성 | threadpool에서 실행 (블로킹 방지) |

---

### 4. `yield` 기반 생명주기 관리

일반 `return`과 달리 `yield`를 사용하면 **리소스 획득-사용-해제** 패턴을 선언적으로 표현할 수 있다.

```python
def get_db():
    db = SessionLocal()       # 리소스 획득
    try:
        yield db              # ← 이 시점에 핸들러에 주입
    finally:
        db.close()            # 응답 완료 후 정리 (에러 발생 시에도 보장)

@app.get("/items/")
def read_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

```
요청 도착 → get_db() 호출 → yield db → [핸들러 실행] → 응답 전송 → finally: db.close()
```

이 패턴은 Python의 **context manager**와 동일한 원리이며, 에러가 발생하더라도 `finally` 블록이 반드시 실행된다.

---

### 5. 주요 활용 패턴

#### 패턴 1: 인증 — 기본 함수 의존성

```python
from fastapi import FastAPI, Depends, HTTPException, status

def get_current_user(token: str):
    if token == "secret-token":
        return {"username": "admin", "id": 1}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

@app.get("/users/me/")
async def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user
```

FastAPI가 `token`을 쿼리 파라미터에서 자동 추출하고, 반환값을 `current_user`에 바인딩한다.

#### 패턴 2: 설정 — `lru_cache` 싱글턴

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "My App"
    admin_email: str = "admin@example.com"

@lru_cache()
def get_settings():
    return Settings()

@app.get("/info/")
def get_app_info(settings: Settings = Depends(get_settings)):
    return {"app_name": settings.app_name}
```

`@lru_cache()`로 감싸면 Settings 객체가 **프로세스 수명 동안 한 번만** 생성된다. `Depends`의 요청 단위 캐싱과는 별개로, 애플리케이션 레벨 싱글턴을 구현하는 방법이다.

#### 패턴 3: 서비스 레이어 분리

```python
class ItemService:
    def get_all_items(self):
        return [{"id": 1, "name": "Item A"}]

    def create_item(self, name: str):
        return {"id": 3, "name": name, "status": "created"}

def get_item_service():
    return ItemService()

@app.get("/items/")
def list_items(service: ItemService = Depends(get_item_service)):
    return service.get_all_items()
```

핸들러가 비즈니스 로직을 직접 갖지 않고, 서비스 객체를 주입받아 위임한다.

---

### 6. 테스트 — `dependency_overrides`

```python
# 프로덕션 의존성
def get_current_user_prod(token: str):
    if token == "prod-secret":
        return {"username": "prod_user", "id": 1}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

# Mock 의존성
def get_current_user_mock():
    return {"username": "test_user", "id": 99}

# 테스트에서 교체
def test_protected_route():
    app.dependency_overrides[get_current_user_prod] = get_current_user_mock
    response = client.get("/protected/")
    assert response.json() == {"message": "Hello, test_user!"}
    app.dependency_overrides = {}   # 반드시 정리
```

`dependency_overrides`는 **함수 객체를 키로 사용하는 딕셔너리**다. 원본 함수를 키로, mock 함수를 값으로 매핑하면 FastAPI가 의존성 해석 시 mock을 대신 호출한다.

pytest fixture와 결합하면 자동화가 가능하다:

```python
@pytest.fixture(autouse=True)
def override_get_current_user():
    app.dependency_overrides[get_current_user_prod] = get_current_user_mock
    yield
    app.dependency_overrides = {}
```

---

### 7. 의존성 생명주기 정리

| 생명주기 | 구현 방법 | 사용 사례 |
|----------|----------|----------|
| **요청 단위** (Per-Request) | `def` / `async def` + `Depends()` | DB 세션, 인증 토큰 |
| **요청 단위 + Cleanup** | `yield` + `Depends()` | 커넥션 반환, 트랜잭션 롤백 |
| **애플리케이션 단위** (Singleton) | `@lru_cache()` + `Depends()` | 설정, 외부 클라이언트 |
| **라우터 단위** | `APIRouter(dependencies=[...])` | 특정 라우터 공통 인증 |

---

## 내가 얻은 인사이트

### 설계 원칙 관점

1. **함수 = 의존성이라는 단순함**
   - Spring은 클래스 + 어노테이션 + 컨테이너, NestJS는 데코레이터 + 모듈 시스템이 필요하지만, FastAPI는 순수 함수 하나로 의존성을 정의한다. 이 단순함이 학습 곡선을 극적으로 낮추면서도 표현력을 잃지 않는 핵심 설계 결정이다.

2. **마커 패턴의 장점**
   - `Depends()`가 실행자가 아닌 마커라는 점은 중요하다. 의존성 선언과 실행이 분리되어 있으므로 프레임워크가 그래프 구축 → 캐싱 → 주입 순서를 최적화할 수 있다. 이는 Spring의 BeanFactory가 빈 정의와 빈 생성을 분리하는 것과 같은 원리다.

3. **yield = 선언적 리소스 관리**
   - try/finally를 직접 작성하지 않아도, yield를 사용하면 프레임워크가 생명주기를 보장한다. Python의 contextmanager와 같은 원리이며, 리소스 누수를 구조적으로 방지하는 패턴이다.

### 실무 적용 관점

1. **캐싱 레벨을 의식적으로 선택해야 한다**
   - `Depends()`의 요청 단위 캐싱과 `@lru_cache()`의 프로세스 단위 캐싱은 완전히 다른 레벨이다. DB 세션처럼 요청마다 새로 만들어야 하는 것과, 설정처럼 한 번만 만들면 되는 것을 혼동하면 커넥션 누수나 stale 데이터 문제가 발생할 수 있다.

2. **`dependency_overrides`는 테스트 전략의 핵심이다**
   - 함수 객체를 키로 사용하는 방식 덕분에, 프로덕션 코드를 전혀 수정하지 않고 테스트에서 의존성을 교체할 수 있다. 이는 인터페이스 기반 DI를 쓰는 언어들보다 오히려 더 간결한 테스트 코드를 만든다.
