# PEP 484 – Type Hints (Python 타입 힌트 표준)

## 출처
- **문서**: PEP 484 – Type Hints
- **저자**: Guido van Rossum 외
- **게재**: Python Enhancement Proposal, 2014
- **원문**: https://peps.python.org/pep-0484/

---

## AI 요약

### PEP 484란?
- **Python 3.5부터 공식 도입된 타입 힌트(type hint) 표준**
- 변수, 함수 인자/리턴값에 타입 정보를 명시할 수 있게 함
- **런타임 강제는 없음** (정적 분석 도구 mypy, pyright 등에서 활용)

### 핵심 개념

#### 1. 타입 힌트 문법
```python
def greeting(name: str) -> str:
    return 'Hello ' + name

age: int = 10
```
- 함수 인자와 리턴값에 `:`와 `->`로 타입 명시
- 변수에도 `var: type = value` 형태로 사용

#### 2. 주요 타입
- **기본 타입**: int, float, str, bool, None
- **컨테이너**: List[int], Dict[str, int], Tuple[str, int], Set[float]
- **Optional**: Optional[int] (int 또는 None)
- **Union**: Union[int, str] (int 또는 str)
- **Any**: Any (모든 타입 허용)
- **Callable**: Callable[[int, str], bool] (함수 타입)
- **TypeVar**: 제네릭 타입 변수

#### 3. 타입 별칭과 NewType
```python
UserId = int  # 타입 별칭
from typing import NewType
UserName = NewType('UserName', str)
```
- 타입 별칭: 의미 부여용
- NewType: 완전히 새로운 타입처럼 취급

#### 4. 제네릭(Generic) 타입
```python
from typing import TypeVar, List
T = TypeVar('T')
def first(xs: List[T]) -> T:
    return xs[0]
```
- TypeVar로 임의 타입 지원

#### 5. Forward Reference (순환 참조)
```python
class Tree:
    def __init__(self, left: 'Tree' = None, right: 'Tree' = None):
        self.left = left
        self.right = right

def f(tree: 'Tree') -> None:
    ...
```
- **Forward Reference(순환 참조)**란, 아직 정의되지 않은 타입을 문자열로 미리 참조하는 기능임.
- 예를 들어, 자기 자신을 타입으로 갖는 재귀적 자료구조(Tree, Node 등)에서 필요함.
- 파이썬은 함수/클래스 정의 시점에 타입이 실제로 존재하지 않아도, 문자열로 타입 힌트를 적으면 나중에 해석함.
- mypy 등 타입 검사기는 문자열을 실제 타입으로 나중에 해석(resolve)함.
- **Python 3.7+**에서는 `from __future__ import annotations`를 쓰면 모든 타입 힌트가 자동으로 문자열로 처리되어, Forward Reference가 더 간편해짐.

#### 6. 타입 검사 도구
- **mypy, pyright, pyre** 등에서 정적 타입 검사 지원
- 런타임에는 타입 정보가 무시됨 (오류 발생 X)

### 실제 예시
```python
from typing import List, Optional, Dict, Any

def find_user(users: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    for user in users:
        if user['name'] == name:
            return user
    return None
```

### 한계 및 주의점
- **런타임 강제 없음**: 타입 오류가 있어도 실행은 됨
- **동적 타입 언어 특성상 완전한 타입 안전성 보장 불가**
- **복잡한 타입(중첩 제네릭 등)은 가독성 저하**
- **타입 힌트는 선택 사항** (기존 코드와 호환)

---

## 내가 얻은 인사이트

타이핑은 파이썬의 설계 단계에서 고려했어야 했을 치명적인 실수. 파이썬 타입 너무 불편함.