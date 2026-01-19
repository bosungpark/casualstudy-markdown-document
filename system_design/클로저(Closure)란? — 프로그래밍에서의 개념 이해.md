# **클로저(Closure)란? — 프로그래밍에서의 개념 이해**

## 출처

* **링크**:

  * MDN Web Docs – Closures (영문) ([MDN Web Docs][1])
  * Wikipedia – Closure (computer programming) ([위키백과][2])
  * 코드트리 “자바스크립트 클로저 개념” ([프리미엄콘텐츠][3])

---

## AI 요약

**클로저(Closure)**는 **함수와 그 함수가 선언될 때의 렉시컬 환경(lexical environment)** 을 **함께 묶은 구조**입니다. 즉, 함수가 정의된 위치의 **변수 스코프를 기억하며 사용할 수 있는 함수**를 의미합니다. ([MDN Web Docs][1])

함수 내부에서 외부 함수의 변수를 사용하고, 그 외부 함수가 실행을 마친 이후에도 그 변수에 접근·반영할 수 있는 특징을 가집니다. ([mimo.org][4])

정리하면:

* **렉시컬 스코프 기반** – 정의된 스코프를 기준으로 환경을 캡처합니다. ([MDN Web Docs][1])
* **상태 유지** – 외부 함수 종료 이후에도 상태를 기억합니다. ([mimo.org][4])
* **일급 함수 활용** – 반환되거나 전달되는 함수가 환경을 함께 가지고 다닙니다. ([위키백과][2])


---

## 파이썬 코드 예시

### 1. 기본 클로저 구조
```python
def outer(msg):
  def inner():
    print(msg)
  return inner

f = outer('Hello, Closure!')
f()  # 출력: Hello, Closure!
```

### 2. 상태 은닉(캡슐화) 예시
```python
def make_counter():
  count = 0
  def inc():
    nonlocal count
    count += 1
    return count
  return inc

counter = make_counter()
print(counter())  # 1
print(counter())  # 2
print(counter())  # 3
```

### 3. 함수형 프로그래밍 패턴
```python
def make_adder(x):
  return lambda y: x + y

add5 = make_adder(5)
print(add5(10))  # 15
```

### 4. 콜백 활용 예시
```python
def make_printer(prefix):
  def printer(msg):
    print(f"{prefix}: {msg}")
  return printer

info = make_printer("INFO")
info("클로저는 유용하다!")  # INFO: 클로저는 유용하다!
```

---

## 내가 얻은 인사이트

* 클로저는 단순히 “함수가 외부 변수를 참조하는 것”을 넘어, **함수 생성 당시 환경을 저장하고 실행 시점까지 유지하는 개념**이라는 점이 핵심이었음. ([위키백과][2])

* **렉시컬 스코프**와 **일급 함수(first-class function)** 개념을 이해하면 클로저가 왜 존재하고 어떻게 동작하는지 명확해짐. ([MDN Web Docs][1])

* 클로저는 **상태를 은닉하고 캡슐화**하는 데 유용하며, 객체지향의 private 멤버처럼 상태를 제어할 수 있음. ([mimo.org][4])

* 언어별로 **문법이나 구현 방식**은 다르지만(예: JavaScript, Python, Swift), 기본 개념은 동일함 — 함수 + 환경. ([프리미엄콘텐츠][3])
