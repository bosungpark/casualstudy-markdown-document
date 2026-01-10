# PEP 3333 – WSGI Specification

## 출처
- **링크**: https://peps.python.org/pep-3333/

---

## AI 요약

### WSGI란 무엇인가?

**Web Server Gateway Interface (WSGI)**는 Python 웹 애플리케이션과 웹 서버 간의 **표준 인터페이스**입니다. 2003년 PEP 333으로 처음 제안되었고, Python 3 호환을 위해 2010년 PEP 3333으로 개정되었습니다.

**핵심 목적**:
- 웹 프레임워크(Django, Flask 등)와 웹 서버(Gunicorn, uWSGI 등)를 **분리**
- 어떤 프레임워크든 어떤 서버에서든 실행 가능하게 만듦
- Java의 Servlet API와 유사한 역할

---

### WSGI의 구조

```
[Web Server] ←─ WSGI ─→ [Web Application]
   (Nginx)                  (Flask, Django)
      ↓                            ↓
  HTTP 요청                     비즈니스 로직
```

**두 가지 핵심 컴포넌트**:

1. **서버/게이트웨이 측 (Server Side)**
   - HTTP 요청을 받아 WSGI 형식으로 변환
   - 애플리케이션 호출 후 응답을 HTTP로 반환

2. **애플리케이션 측 (Application Side)**
   - WSGI 호출을 받아 비즈니스 로직 처리
   - WSGI 형식으로 응답 반환

---

### WSGI Application의 인터페이스

**가장 단순한 WSGI 앱**:
```python
def simple_app(environ, start_response):
    """WSGI 애플리케이션의 필수 시그니처"""
    
    # 1. environ: 요청 정보 담긴 딕셔너리
    status = '200 OK'
    headers = [('Content-Type', 'text/plain')]
    
    # 2. start_response: 응답 시작 콜백
    start_response(status, headers)
    
    # 3. 반환: iterable (보통 리스트나 제너레이터)
    return [b'Hello World!\n']
```

**핵심 규칙**:
- 함수(또는 `__call__` 메서드를 가진 객체)
- 2개 인자: `environ`, `start_response`
- 반환: 바이트 문자열의 iterable

---

### environ 딕셔너리 구조

```python
environ = {
    # CGI 변수들
    'REQUEST_METHOD': 'GET',          # HTTP 메서드
    'PATH_INFO': '/api/users',        # URL 경로
    'QUERY_STRING': 'id=123',         # 쿼리 파라미터
    'CONTENT_TYPE': 'application/json',
    'CONTENT_LENGTH': '42',
    
    # WSGI 전용 변수
    'wsgi.version': (1, 0),
    'wsgi.url_scheme': 'https',
    'wsgi.input': <file-like object>,  # 요청 바디
    'wsgi.errors': <error stream>,
    'wsgi.multithread': True,
    'wsgi.multiprocess': False,
    
    # 서버 전용 변수 (선택)
    'SERVER_NAME': 'example.com',
    'SERVER_PORT': '443',
    
    # HTTP 헤더 (HTTP_ 접두사)
    'HTTP_HOST': 'example.com',
    'HTTP_USER_AGENT': 'Mozilla/5.0...',
}
```

---

### start_response 콜백

```python
def start_response(status, response_headers, exc_info=None):
    """
    status: '200 OK' 형식의 문자열
    response_headers: [('Header-Name', 'value'), ...] 리스트
    exc_info: 예외 발생 시 (type, value, traceback) 튜플
    """
    pass
```

**사용 예시**:
```python
start_response('200 OK', [
    ('Content-Type', 'application/json'),
    ('X-Custom-Header', 'value')
])
```

---

### 실제 프레임워크에서의 WSGI

**Flask 내부 구조**:
```python
# Flask의 실제 WSGI 구현 (단순화)
class Flask:
    def __call__(self, environ, start_response):
        """Flask 앱은 callable이므로 WSGI app"""
        # 1. 요청 객체 생성
        request = Request(environ)
        
        # 2. 라우팅 및 핸들러 실행
        response = self.dispatch_request(request)
        
        # 3. 응답 반환
        return response(environ, start_response)

# 사용
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello!'

# WSGI 서버에서 실행
# app 객체가 callable이므로 app(environ, start_response) 호출 가능
```

**Django의 경우**:
```python
# django/core/handlers/wsgi.py
class WSGIHandler:
    def __call__(self, environ, start_response):
        set_script_prefix(get_script_name(environ))
        signals.request_started.send(sender=self.__class__, environ=environ)
        request = self.request_class(environ)
        response = self.get_response(request)
        
        status = '%d %s' % (response.status_code, response.reason_phrase)
        response_headers = list(response.items())
        start_response(status, response_headers)
        
        return response
```

---

### Middleware의 개념

WSGI의 강력한 기능 중 하나는 **Middleware** - 서버와 앱 사이에 끼워넣을 수 있는 레이어입니다.

```python
class LoggingMiddleware:
    """모든 요청을 로깅하는 미들웨어"""
    
    def __init__(self, app):
        self.app = app  # 감쌀 앱
    
    def __call__(self, environ, start_response):
        # 요청 전처리
        print(f"Request: {environ['REQUEST_METHOD']} {environ['PATH_INFO']}")
        
        # 원래 앱 호출
        response = self.app(environ, start_response)
        
        # 응답 후처리
        print(f"Response sent")
        return response

# 사용
app = Flask(__name__)
app = LoggingMiddleware(app)  # 미들웨어로 감싸기
```

**실무 미들웨어 예시**:
- 인증/인가 (Auth middleware)
- CORS 헤더 추가
- 요청/응답 로깅
- 압축 (GZip middleware)
- 에러 핸들링

---

### WSGI 서버들

**주요 WSGI 서버**:

| 서버 | 특징 | 사용 사례 |
|------|------|-----------|
| **Gunicorn** | 간단, 안정적, pre-fork 모델 | 프로덕션 표준 |
| **uWSGI** | 고성능, 많은 기능 | 대규모 시스템 |
| **Waitress** | 순수 Python, 윈도우 지원 | 크로스 플랫폼 |
| **mod_wsgi** | Apache 모듈 | 레거시 시스템 |
| **Werkzeug** | 개발 전용 | 로컬 개발 |

**배포 구조**:
```
[Nginx] → [Gunicorn] → [Flask App]
  ↓          ↓            ↓
리버스 프록시  WSGI 서버   WSGI 앱
(정적 파일)  (다중 워커)  (비즈니스 로직)
```

---

### WSGI의 한계와 대안

**WSGI의 한계**:
1. **동기적 (Synchronous)**: 비동기 I/O 지원 안 함
   ```python
   # WSGI는 이런 코드 불가능
   async def app(environ, start_response):
       data = await fetch_data()  # 불가능!
       return [data]
   ```

2. **웹소켓 미지원**: HTTP만 가능
3. **HTTP/2 기능 제한**: Server Push 등 불가

**대안: ASGI (Asynchronous Server Gateway Interface)**:
```python
# ASGI 앱 예시
async def app(scope, receive, send):
    """ASGI는 비동기 지원"""
    
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello World',
        })
    
    elif scope['type'] == 'websocket':
        # 웹소켓도 처리 가능!
        await send({'type': 'websocket.accept'})
```

**ASGI 프레임워크/서버**:
- FastAPI, Starlette (프레임워크)
- Uvicorn, Daphne (서버)

---

### 주요 명세 세부사항

**1. 응답 바디는 iterable**:
```python
# OK - 리스트
return [b'Hello']

# OK - 제너레이터 (메모리 효율적)
def generate():
    yield b'Line 1\n'
    yield b'Line 2\n'
return generate()

# OK - 파일 객체
return open('large_file.txt', 'rb')
```

**2. close() 메서드**:
```python
class FileWrapper:
    def __init__(self, filelike):
        self.filelike = filelike
    
    def __iter__(self):
        return iter(self.filelike)
    
    def close(self):
        """리소스 정리"""
        if hasattr(self.filelike, 'close'):
            self.filelike.close()

# WSGI 서버는 응답 후 자동으로 close() 호출
```

**3. 에러 처리**:
```python
def app(environ, start_response):
    try:
        # 비즈니스 로직
        data = process_request()
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [data]
    
    except Exception as e:
        # exc_info 활용
        start_response(
            '500 Internal Server Error',
            [('Content-Type', 'text/plain')],
            sys.exc_info()  # (type, value, traceback)
        )
        return [b'Error occurred']
```

---

## 내가 얻은 인사이트
