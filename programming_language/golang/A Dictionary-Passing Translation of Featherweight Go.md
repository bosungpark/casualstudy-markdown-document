# A Dictionary-Passing Translation of Featherweight Go

## 출처
- **논문**: A Dictionary-Passing Translation of Featherweight Go
- **저자**: Martin Sulzmann, Stefan Wehr
- **게재**: arXiv:2106.14586 [cs.PL] (2021년 6월)
- **원문**: https://arxiv.org/abs/2106.14586

---

## AI 요약

### 핵심 문제: Go의 형식적 기반 부재

Go는 실무에서 빠르게 성장하는 언어지만, **일부 핵심 기능이 형식적 검증(formal investigation)이 부족**합니다:
- Overloaded Methods의 해결 메커니즘
- Structural Subtyping (구조적 서브타이핑)
- Interface 구현의 암묵적 만족

이 논문은 **Featherweight Go**라는 Go의 핵심 부분집합을 단순한 타겟 언어로 **번역(translation)**하여 이러한 기능들을 형식적으로 설명합니다.

### Featherweight Go란?

**Featherweight Java**를 본떠 만든 Go의 최소 부분집합:
```go
// Featherweight Go 예시
type Shape interface {
    Area() float64
}

type Circle struct {
    radius float64
}

func (c Circle) Area() float64 {
    return 3.14 * c.radius * c.radius
}
```

**포함하는 것**:
- Interface 정의
- Struct 정의
- Method 정의
- Structural Subtyping (암묵적 Interface 구현)

**제외하는 것**:
- Goroutines, Channels (동시성)
- Pointers, Slices
- 복잡한 제어 흐름

### Dictionary-Passing Translation

**핵심 아이디어**: Interface 호출을 **함수 테이블(Dictionary) 전달**로 변환

**원본 Go 코드**:
```go
// Interface 정의
type Stringer interface {
    String() string
}

// 구현
type Int int

func (n Int) String() string {
    return fmt.Sprintf("%d", n)
}

// 사용
func Print(s Stringer) {
    fmt.Println(s.String())
}

// 호출
Print(Int(42))
```

**Dictionary-Passing 번역 후**:
```go
// 1. Interface → Dictionary 구조체 (함수 테이블)
type StringerDict struct {
    String func(self interface{}) string
}

// 2. Int용 Dictionary 값 생성
var intStringerDict = StringerDict{
    String: func(self interface{}) string {
        n := self.(Int)
        return fmt.Sprintf("%d", n)
    },
}

// 3. Interface 파라미터 → Dictionary + 객체로 분리
func Print(dict StringerDict, s interface{}) {
    fmt.Println(dict.String(s))
}

// 4. 호출 시 Dictionary 명시적 전달
Print(intStringerDict, Int(42))
```

### 복잡한 예시: 여러 타입 처리

**원본 Go 코드**:
```go
type Shape interface {
    Area() float64
}

type Circle struct {
    radius float64
}

func (c Circle) Area() float64 {
    return 3.14 * c.radius * c.radius
}

type Rectangle struct {
    width, height float64
}

func (r Rectangle) Area() float64 {
    return r.width * r.height
}

func TotalArea(shapes []Shape) float64 {
    total := 0.0
    for _, s := range shapes {
        total += s.Area()  // Dynamic dispatch
    }
    return total
}
```

**Dictionary-Passing 번역**:
```go
// 1. Interface → Dictionary
type ShapeDict struct {
    Area func(self interface{}) float64
}

// 2. 각 타입별 Dictionary 생성
var circleShapeDict = ShapeDict{
    Area: func(self interface{}) float64 {
        c := self.(Circle)
        return 3.14 * c.radius * c.radius
    },
}

var rectangleShapeDict = ShapeDict{
    Area: func(self interface{}) float64 {
        r := self.(Rectangle)
        return r.width * r.height
    },
}

// 3. Interface 파라미터 → Dictionary + 객체 쌍의 리스트
type ShapeValue struct {
    dict ShapeDict
    obj  interface{}
}

func TotalArea(shapes []ShapeValue) float64 {
    total := 0.0
    for _, s := range shapes {
        total += s.dict.Area(s.obj)  // Dictionary를 통한 간접 호출
    }
    return total
}

// 4. 호출
shapes := []ShapeValue{
    {circleShapeDict, Circle{radius: 5}},
    {rectangleShapeDict, Rectangle{width: 3, height: 4}},
}
TotalArea(shapes)
```

### Embedded Interface (Interface 합성)

**Go의 Method Set**:
```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type ReadWriter interface {
    Reader  // Embedding
    Writer
}

type File struct {
    name string
}

func (f File) Read(p []byte) (n int, err error) {
    // 구현
    return 0, nil
}

func (f File) Write(p []byte) (n int, err error) {
    // 구현
    return 0, nil
}

func Copy(rw ReadWriter, data []byte) {
    rw.Read(data)
    rw.Write(data)
}
```

**Dictionary 번역**:
```go
// 1. 각 Interface → Dictionary
type ReaderDict struct {
    Read func(self interface{}, p []byte) (int, error)
}

type WriterDict struct {
    Write func(self interface{}, p []byte) (int, error)
}

// 2. Embedded Interface → Dictionary 합성
type ReadWriterDict struct {
    reader ReaderDict
    writer WriterDict
}

// 3. File용 Dictionary 생성
var fileReadWriterDict = ReadWriterDict{
    reader: ReaderDict{
        Read: func(self interface{}, p []byte) (int, error) {
            f := self.(File)
            // 구현
            return 0, nil
        },
    },
    writer: WriterDict{
        Write: func(self interface{}, p []byte) (int, error) {
            f := self.(File)
            // 구현
            return 0, nil
        },
    },
}

// 4. 메서드 호출
func Copy(dict ReadWriterDict, rw interface{}, data []byte) {
    dict.reader.Read(rw, data)
    dict.writer.Write(rw, data)
}

// 5. 호출
Copy(fileReadWriterDict, File{name: "test.txt"}, []byte{})
```

### Structural Subtyping의 형식화

**Go의 암묵적 구현**:
```go
// Interface 정의
type Stringer interface {
    String() string
}

// 명시적 implements 없이 구현
type Person struct {
    name string
}

func (p Person) String() string {  // 자동으로 Stringer 만족
    return p.name
}

func Greet(s Stringer) {
    fmt.Println("Hello, " + s.String())
}

// Person이 Stringer를 구현한다고 선언 안 해도 호출 가능
Greet(Person{name: "Alice"})
```

**번역 규칙**:
```go
// 컴파일러 검증 로직
Person이 Stringer를 만족하는가?
→ Person에 String() string 메서드가 있는가? ✓
→ personStringerDict 자동 생성 가능 ✓
→ Stringer 기대 위치에 Person 사용 가능 ✓

// 자동 생성되는 Dictionary
var personStringerDict = StringerDict{
    String: func(self interface{}) string {
        p := self.(Person)
        return p.name
    },
}

// Greet 번역
func Greet(dict StringerDict, s interface{}) {
    fmt.Println("Hello, " + dict.String(s))
}

// 호출 시 자동 Dictionary 삽입
Greet(personStringerDict, Person{name: "Alice"})
```

**Type Safety 보장**:
- **컴파일 타임**: Dictionary 생성 가능 여부 검증 → Method Not Found 에러 사전 차단
- **런타임**: 모든 Interface 호출이 Dictionary 함수 호출로 변환 → Type Assertion 실패 없음
- **형식적 증명**: "타입 T가 Interface I를 만족한다" ⇔ "T용 I-Dictionary를 생성할 수 있다"

### 동적 행동 보존 (Behavior Preservation)

**정리**: 번역 전후 프로그램의 실행 결과가 동일함

**예시**:
```go
// 원본 Go 프로그램 P
type Animal interface {
    Speak() string
}

type Dog struct{}
func (d Dog) Speak() string { return "Woof!" }

func main() {
    var a Animal = Dog{}
    fmt.Println(a.Speak())  // 출력: "Woof!"
}
```

```go
// Dictionary-Passing 번역 P'
type AnimalDict struct {
    Speak func(self interface{}) string
}

var dogAnimalDict = AnimalDict{
    Speak: func(self interface{}) string {
        return "Woof!"
    },
}

func main() {
    dict := dogAnimalDict
    obj := Dog{}
    fmt.Println(dict.Speak(obj))  // 출력: "Woof!"
}
```

**P의 실행 결과 = P'의 실행 결과** ("Woof!" 출력)

**형식적 증명**:
- **Operational Semantics**: 각 Go 표현식이 어떻게 평가되는지 정의
- **번역 규칙**: Interface 호출 → Dictionary 호출로 변환하는 규칙
- **Soundness 증명**: `P ⇓ v` (P가 값 v로 평가) ⇔ `P' ⇓ v` (번역된 P'도 같은 값 v로 평가)

### Generics (Type Parameters) 지원

Go 1.18+ Generics도 동일한 방식으로 번역 가능:

**원본 Go Generics**:
```go
func Map[T, U any](xs []T, f func(T) U) []U {
    result := make([]U, len(xs))
    for i, x := range xs {
        result[i] = f(x)
    }
    return result
}

// 사용
numbers := []int{1, 2, 3}
strings := Map(numbers, func(n int) string {
    return fmt.Sprintf("%d", n)
})
```

**Dictionary-Passing 번역**:
```go
// Type Parameter가 없는 버전으로 변환
func Map(
    dictT TypeDict,    // T 타입 정보
    dictU TypeDict,    // U 타입 정보
    xs interface{},    // []T → interface{}
    f func(interface{}) interface{},  // func(T) U → 일반 함수
) interface{} {  // []U → interface{}
    
    // Runtime type operations using dictT, dictU
    xsSlice := xs.([]interface{})
    result := make([]interface{}, len(xsSlice))
    for i, x := range xsSlice {
        result[i] = f(x)
    }
    return result
}

// 호출 시 Type Dictionary 명시적 전달
numbers := []interface{}{1, 2, 3}
strings := Map(
    intDict,      // T = int
    stringDict,   // U = string
    numbers,
    func(n interface{}) interface{} {
        return fmt.Sprintf("%d", n.(int))
    },
)
```

**핵심**: Type Parameter `[T, U any]` → Type Dictionary 파라미터로 변환

---

## 내가 얻은 인사이트

Go Interface의 본질은 "Implicit Vtable"이다. Go의 Structural Subtyping도 결국 **Method Set 매칭 + Vtable 자동 생성**의 결과. Dictionary-Passing은 이를 **컴파일 타임에 명시적으로** 만드는 것. Implicit Vtable과 Dictionary-Passing의 차이는 컴파일러와 개발자 중 누가 제어할 것인가?임. Dictionary-Passing이 낭만 있어보이나, 실용적이지는 않을 것 같음. 그냥 컴파일러에게 위임하는게 오히려 실수가 적을 것이라 생각함.