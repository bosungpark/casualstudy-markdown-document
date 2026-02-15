# gRPC Deep Dive: Service Definition to Wire Format

## 출처
- **아티클**: gRPC deep dive: from service definition to wire format
- **저자/출처**: Kreya (kreya.app)
- **링크**: https://kreya.app/blog/grpc-deep-dive/
- **보조 출처**: https://grpc.io/docs/what-is-grpc/core-concepts/

---

## AI 요약

### 1. gRPC란?

gRPC(Google Remote Procedure Call)는 Google이 개발한 고성능 오픈소스 RPC 프레임워크로, **Protocol Buffers**와 **HTTP/2**를 기반으로 동작한다. Contract-first 방식으로 `.proto` 파일에 서비스 인터페이스를 정의하고, `protoc` 컴파일러가 클라이언트 스텁과 서버 보일러플레이트를 자동 생성한다.

| 특성 | 설명 |
|------|------|
| 전송 프로토콜 | HTTP/2 |
| 직렬화 포맷 | Protocol Buffers (binary) |
| IDL | `.proto` 파일 |
| 통신 패턴 | Unary, Server Streaming, Client Streaming, Bidirectional Streaming |
| 브라우저 지원 | gRPC-Web을 통한 제한적 지원 |
| 보안 | TLS 기반 암호화 |

### 2. 4가지 RPC 통신 패턴

gRPC는 4가지 서비스 메서드 타입을 지원한다.

```
┌─────────────────────────────────────────────────────────────┐
│                    gRPC Communication Patterns              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1) Unary RPC            2) Server Streaming                │
│  Client ──Req──▶ Server  Client ──Req──▶ Server             │
│  Client ◀──Res── Server  Client ◀──Res── Server             │
│                          Client ◀──Res── Server             │
│                          Client ◀──Res── Server             │
│                                                             │
│  3) Client Streaming     4) Bidirectional Streaming         │
│  Client ──Req──▶ Server  Client ──Req──▶ Server             │
│  Client ──Req──▶ Server  Client ◀──Res── Server             │
│  Client ──Req──▶ Server  Client ──Req──▶ Server             │
│  Client ◀──Res── Server  Client ◀──Res── Server             │
│                          (독립적으로 읽기/쓰기)              │
└─────────────────────────────────────────────────────────────┘
```

| 패턴 | 요청 | 응답 | 사용 사례 |
|------|------|------|-----------|
| Unary | 단일 | 단일 | 일반 함수 호출, CRUD 연산 |
| Server Streaming | 단일 | 스트림 | 실시간 피드, 대량 데이터 조회 |
| Client Streaming | 스트림 | 단일 | 파일 업로드, 센서 데이터 집계 |
| Bidirectional Streaming | 스트림 | 스트림 | 채팅, 실시간 게임 |

```protobuf
service FruitService {
  // Unary
  rpc GetFruit (GetFruitRequest) returns (Fruit);
  // Server Streaming
  rpc ListFruits (ListFruitsRequest) returns (stream Fruit);
  // Client Streaming
  rpc RecordFruits (stream Fruit) returns (FruitSummary);
  // Bidirectional Streaming
  rpc FruitChat (stream FruitMessage) returns (stream FruitMessage);
}
```

### 3. HTTP/2 전송 계층

gRPC는 HTTP/2 위에서 동작하며, 모든 요청은 **HTTP POST** 메서드를 사용한다. Content-Type은 `application/grpc`이다.

```
┌─────────────────────────────────────────────────────────────┐
│                   HTTP/2 Stream (gRPC Call)                  │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ HEADERS      │   │ DATA         │   │ HEADERS      │    │
│  │ Frame        │   │ Frame(s)     │   │ Frame        │    │
│  │              │   │              │   │ (Trailers)   │    │
│  │ :method POST │   │ [5-byte hdr] │   │ grpc-status  │    │
│  │ :path /pkg.  │   │ [protobuf    │   │ grpc-message │    │
│  │  Svc/Method  │   │  payload]    │   │              │    │
│  │ content-type │   │              │   │              │    │
│  │ grpc-encoding│   │              │   │              │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│                                                             │
│  요청 메타데이터        애플리케이션 데이터     응답 상태 + 트레일러  │
└─────────────────────────────────────────────────────────────┘
```

**URL 경로 패턴**: `/{Package}.{Service}/{Method}`
- 예: `/fruit.v1.FruitService/GetFruit`

**HTTP/2의 이점**:
- **스트림 멀티플렉싱**: 단일 TCP 연결에서 수천 개의 동시 RPC 호출 가능
- **헤더 압축 (HPACK)**: 반복되는 헤더를 효율적으로 압축
- **양방향 스트리밍**: 클라이언트와 서버가 독립적으로 데이터 송수신
- **서버 푸시**: 클라이언트 요청 없이 서버가 먼저 데이터 전송 가능

### 4. 메시지 인코딩: 5바이트 헤더 (Length-Prefixed Framing)

모든 gRPC 메시지는 **5바이트 프리픽스**를 갖는 Length-Prefixed Framing을 사용한다.

```
┌──────────┬────────────────────┬─────────────────────────┐
│ Byte 0   │ Byte 1-4           │ Byte 5+                 │
│ 압축 플래그│ 메시지 길이 (Big-E) │ Protobuf 페이로드       │
├──────────┼────────────────────┼─────────────────────────┤
│ 0x00     │ 0x00 0x00 0x00 0x0a│ 08 96 01 12 05 ...      │
│ (비압축)  │ (10 bytes)         │ (실제 Protobuf 데이터)  │
└──────────┴────────────────────┴─────────────────────────┘
```

| 바이트 | 용도 | 설명 |
|--------|------|------|
| 0 | 압축 플래그 | `0` = 비압축, `1` = 압축 |
| 1-4 | 메시지 길이 | Big-Endian 4바이트 정수 |
| 5+ | 페이로드 | 직렬화된 Protobuf 메시지 |

**예시**: `Fruit { id: 150, name: "Apple" }` 메시지의 와이어 포맷:
```
00 00 00 00 0a 08 96 01 12 05 41 70 70 6c 65
│  │           │                              │
│  └─ 길이: 10 └── Protobuf: id=150, name="Apple"
└─ 비압축
```

### 5. Metadata와 Headers

Metadata는 RPC 호출에 대한 부가 정보를 key-value 쌍으로 전달한다. HTTP/2의 헤더와 트레일러로 매핑된다.

| 규칙 | 설명 |
|------|------|
| 키 이름 | 대소문자 구분 없음, ASCII 문자 + `-`, `_`, `.` 허용 |
| 예약 접두어 | `grpc-`로 시작하는 키는 프레임워크 예약 |
| 바이너리 값 | 키가 `-bin`으로 끝나면 바이너리 값 사용 가능 |
| 일반적 용도 | 인증 토큰, 트레이스 ID, 커스텀 메타데이터 |

### 6. 상태 코드와 에러 처리

gRPC는 HTTP 상태 코드와 별개로 자체 상태 코드 체계를 사용한다. HTTP 응답은 대부분 `200 OK`이며, 실제 gRPC 상태는 **트레일러**에 포함된다.

```
HTTP/2 Response Trailers:
  grpc-status: 0              ← gRPC 상태 코드
  grpc-message: success       ← 사람이 읽을 수 있는 메시지
  grpc-status-details-bin: ... ← Rich Error Model (base64)
```

**주요 gRPC 상태 코드**:

| 코드 | 이름 | 설명 |
|------|------|------|
| 0 | OK | 성공 |
| 1 | CANCELLED | 클라이언트가 취소 |
| 3 | INVALID_ARGUMENT | 잘못된 인수 |
| 4 | DEADLINE_EXCEEDED | 데드라인 초과 |
| 5 | NOT_FOUND | 리소스 없음 |
| 13 | INTERNAL | 내부 에러 |
| 14 | UNAVAILABLE | 서비스 불가 |

**Rich Error Model**: `google.rpc.Status` 메시지를 사용하여 구조화된 에러 상세 정보를 `grpc-status-details-bin` 트레일러에 base64로 인코딩하여 전달한다.

### 7. 압축 (Compression)

gRPC는 메시지 단위 압축을 지원한다.

```
요청 흐름:
Client                                    Server
  │                                         │
  │ grpc-accept-encoding: gzip, identity    │
  │ ──────────────────────────────────────▶  │
  │                                         │
  │ grpc-encoding: gzip                     │
  │ ◀──────────────────────────────────────  │
  │                                         │
  │ DATA: [01][length][gzip-compressed]     │
  │ ◀──────────────────────────────────────  │
  │  (압축 플래그 = 0x01)                    │
```

- 클라이언트가 `grpc-accept-encoding` 헤더로 지원 가능한 압축 알고리즘 광고
- 서버가 `grpc-encoding` 헤더로 선택한 알고리즘 응답
- 5바이트 헤더의 첫 번째 바이트(압축 플래그)로 개별 메시지의 압축 여부 결정

### 8. RPC 생명주기 (Lifecycle)

```
┌──────────────────────────────────────────────────────────────┐
│                    Unary RPC Lifecycle                        │
│                                                              │
│  Client                              Server                  │
│    │                                   │                     │
│    │ 1. Stub 메서드 호출                 │                     │
│    │──────────────────────────────────▶│                     │
│    │   (메타데이터 + 메서드명 + 데드라인)  │                     │
│    │                                   │                     │
│    │ 2. 초기 메타데이터 응답 (선택적)      │                     │
│    │◀──────────────────────────────────│                     │
│    │                                   │                     │
│    │ 3. 요청 메시지 수신                 │                     │
│    │                                   │── 비즈니스 로직 처리   │
│    │                                   │                     │
│    │ 4. 응답 + 상태 + 트레일러           │                     │
│    │◀──────────────────────────────────│                     │
│    │                                   │                     │
└──────────────────────────────────────────────────────────────┘
```

**Deadline/Timeout**: 클라이언트가 RPC 완료까지 대기할 최대 시간을 지정. 초과 시 `DEADLINE_EXCEEDED` 에러 반환.

**취소 (Cancellation)**: 클라이언트 또는 서버 모두 RPC를 즉시 종료할 수 있다. 단, **취소 전에 이루어진 변경은 롤백되지 않는다**.

**독립적 판단**: 클라이언트와 서버는 호출의 성공/실패를 독립적으로 판단하며, 양쪽의 결론이 일치하지 않을 수 있다.

### 9. gRPC-Web: 브라우저 호환성

웹 브라우저는 HTTP/2 트레일러에 직접 접근할 수 없다. gRPC-Web은 이를 해결하기 위해:

```
┌─────────────────────────────────────────────────────┐
│              gRPC-Web Adaptation                     │
│                                                     │
│  Browser ──▶ gRPC-Web Proxy ──▶ gRPC Server         │
│  (HTTP/1.1)   (Envoy 등)        (HTTP/2)            │
│                                                     │
│  차이점:                                             │
│  - 트레일러를 응답 본문에 인코딩                       │
│  - 텍스트 기반 인코딩(base64) 지원                    │
│  - Client Streaming, Bidi Streaming 미지원           │
└─────────────────────────────────────────────────────┘
```

### 10. Channel과 연결 관리

Channel은 특정 호스트와 포트의 gRPC 서버에 대한 연결을 추상화한다.

| 상태 | 설명 |
|------|------|
| IDLE | 초기 상태, 연결 시도 전 |
| CONNECTING | TCP 연결 수립 중 |
| READY | 연결 완료, RPC 전송 가능 |
| TRANSIENT_FAILURE | 일시적 실패, 재연결 시도 중 |
| SHUTDOWN | 채널 종료 |

---

## 내가 얻은 인사이트

### 프로토콜 설계 관점
1. **HTTP/2 위에서의 영리한 추상화**
   - gRPC는 새로운 전송 프로토콜을 만들지 않고, HTTP/2의 스트림 멀티플렉싱과 헤더 압축을 재활용했다. 기존 인프라(로드밸런서, 프록시)와의 호환성을 유지하면서 고성능 RPC를 구현한 설계가 인상적이다.

2. **상태 코드 분리의 의미**
   - HTTP 200을 반환하되 gRPC 상태 코드를 트레일러에 넣는 설계는, HTTP 계층의 인프라(프록시, CDN)를 방해하지 않으면서 애플리케이션 수준의 세밀한 에러 처리를 가능하게 한다. 이는 계층 분리(Separation of Concerns) 원칙을 프로토콜 수준에서 적용한 좋은 사례다.

3. **5바이트 Length-Prefixed Framing의 단순함**
   - 메시지 경계를 명확히 하는 5바이트 프리픽스는 극도로 단순하면서도 압축 토글, 가변 길이 메시지, 스트리밍을 모두 지원한다. 복잡한 프레이밍 프로토콜 없이도 필요한 기능을 달성한 미니멀한 설계다.

### 실무 적용 관점
1. **Deadline 전파의 중요성**
   - 마이크로서비스 체인에서 deadline이 전파되지 않으면 이미 타임아웃된 요청에 대해 하위 서비스가 계속 작업하는 낭비가 발생한다. gRPC의 deadline 메커니즘은 이 문제를 프레임워크 수준에서 해결한다.

2. **취소 후 롤백 불가에 대한 주의**
   - "Changes made before a cancellation are not rolled back"이라는 특성은 멱등성(Idempotency) 설계의 필요성을 더욱 강조한다. gRPC 메서드를 설계할 때 반드시 멱등성을 고려해야 한다.

3. **gRPC-Web의 제약과 트레이드오프**
   - 브라우저 환경에서 gRPC-Web은 Client Streaming과 Bidirectional Streaming을 지원하지 못한다. 프론트엔드-백엔드 통신에는 REST/GraphQL이, 서비스 간 통신에는 gRPC가 적합한 하이브리드 아키텍처가 현실적인 선택이다.
