# WebRTC DataChannel - 순수 P2P 통신과 DTLS 종단간 암호화, NAT 트래버설

## 출처
- **아티클/문서**: Browser APIs and Protocols: WebRTC (High Performance Browser Networking, Chapter 18)
- **저자/출처**: Ilya Grigorik (O'Reilly)
- **링크**: https://hpbn.co/webrtc/

> 보조 참고(주 출처 아님): MDN WebRTC API, RFC 8831(WebRTC Data Channels), RFC 8832(SCTP DataChannel Establishment Protocol).

---

## AI 요약

### 1. WebRTC DataChannel이란?

WebRTC(Web Real-Time Communication)는 브라우저/앱 사이에 **서버를 경유하지 않는 직접 P2P 연결**을 맺어 오디오·비디오·임의의 애플리케이션 데이터를 주고받는 기술이다. 그중 **DataChannel(`RTCDataChannel`)** 은 미디어가 아닌 **임의의 바이너리/텍스트 데이터**를 P2P로 전송하는 채널로, WebSocket과 비슷한 API를 제공하지만 전송 경로가 서버가 아니라 상대 피어다.

핵심은 다음 두 가지다.
- **연결을 맺기 위해서는 중앙 서버(시그널링)가 필요하지만, 일단 연결되면 데이터는 피어끼리 직접 흐른다.**
- **모든 데이터는 DTLS로 의무적으로 암호화된다.** (옵션이 아님)

| 특성 | 내용 |
|---|---|
| 전송 단위 | 메시지 지향(message-oriented), 바이너리/텍스트 모두 지원 |
| 기반 프로토콜 | UDP → ICE → DTLS → SCTP |
| 암호화 | **항상 강제** (DTLS, 비활성화 불가) |
| 신뢰성/순서 | 채널마다 설정 가능 (reliable/unreliable, ordered/unordered) |
| 다중화 | SCTP 위에서 여러 채널 native 멀티플렉싱 |
| 경로 | 서버 비경유 P2P (NAT 뚫기 실패 시에만 TURN 릴레이) |
| 제약 | **양쪽 피어가 동시에 온라인이어야 함** |

### 2. 프로토콜 스택 - DataChannel은 무엇 위에 올라가는가

DataChannel은 단일 프로토콜이 아니라 4계층의 조합 위에 동작한다.

```
        ┌─────────────────────────────────────┐
        │   RTCDataChannel API (앱 데이터)      │
        ├─────────────────────────────────────┤
        │   SCTP   (멀티플렉싱, 흐름/혼잡 제어,    │
        │           부분 신뢰성/순서 제어)         │
        ├─────────────────────────────────────┤
        │   DTLS   (종단간 암호화 + 키 협상)       │  ← 의무 암호화
        ├─────────────────────────────────────┤
        │   ICE / STUN / TURN  (NAT 트래버설)    │
        ├─────────────────────────────────────┤
        │   UDP    (P2P 연결성)                  │
        └─────────────────────────────────────┘
```

| 계층 | 역할 |
|---|---|
| UDP | 피어 간 기본 연결성 제공 (비신뢰, 비순서) |
| ICE/STUN/TURN | NAT/방화벽을 뚫고 양쪽이 도달 가능한 경로를 찾음 |
| DTLS | UDP 위에서 TLS급 암호화 + 키 교환 (종단간 암호화) |
| SCTP | UDP의 한계를 보완 — 다중 채널 멀티플렉싱, 흐름/혼잡 제어, **설정 가능한 신뢰성·순서** |

> 핵심: TCP는 신뢰+순서가 묶여 있어 **head-of-line blocking**을 피할 수 없지만, SCTP는 메시지 지향이라 "신뢰성은 보장하되 순서는 보장하지 않는" 조합이 가능하다. 이것이 DataChannel이 WebSocket보다 유연한 이유다.

### 3. 전체 연결 수립 흐름 (시그널링 → ICE → DTLS → SCTP)

```
   Peer A (Amy)                Signaling Server               Peer B (Bob)
       │                            │                              │
       │  ── createOffer() ────►    │                              │
       │     setLocalDescription    │                              │
       │  ───── SDP offer ─────────►│───── SDP offer ─────────────►│
       │                            │                  setRemoteDescription
       │                            │                  createAnswer()
       │                            │                  setLocalDescription
       │◄──── SDP answer ───────────│◄──── SDP answer ─────────────│
       │  setRemoteDescription      │                              │
       │                            │                              │
       │  ◄═══ ICE candidates (trickle, 양방향, 시그널링 경유) ═══►  │
       │                            │                              │
       ├══════════════ (여기서부터 P2P, 서버 비경유) ═══════════════┤
       │                                                           │
       │  ◄─── ICE connectivity checks (STUN binding) ────────►    │
       │  ◄────────── DTLS handshake (2 RTT) ─────────────────►    │  키 협상
       │  ◄────────── SCTP handshake (TCP 유사) ──────────────►    │
       │                                                           │
       │  ◄═════════ DataChannel: 암호화된 P2P 데이터 ═════════►    │
       │                                                           │
```

1. **시그널링(Signaling)**: SDP offer/answer와 ICE 후보를 교환하는 단계. WebRTC는 시그널링의 **전송 방식이나 프로토콜을 규정하지 않는다** (WebSocket, HTTP, SIP, Jingle 등 자유). 즉 "연결을 소개해주는 중개자"는 앱이 직접 구현한다.
2. **ICE**: NAT를 뚫고 양쪽이 통신 가능한 경로(후보 쌍)를 찾는다.
3. **DTLS handshake**: 자가서명 인증서로 TLS 핸드셰이크를 수행, **공유 비밀(shared secret)** 을 만든다. **2 RTT** 소요.
4. **SCTP handshake**: TCP와 유사한 핸드셰이크 후 실제 채널 개통.

### 4. ICE / STUN / TURN - NAT 트래버설

대부분의 단말은 NAT 뒤에 있어 공인 IP가 없다. ICE(Interactive Connectivity Establishment)는 가능한 모든 경로(후보)를 모아 실제로 뚫리는 경로를 찾는다.

**후보(candidate) 3종류와 우선순위:**

```
우선순위:  host  >  srflx(server reflexive)  >  relay
            ▲           ▲                         ▲
   로컬 IP/포트    STUN으로 알아낸 공인 IP      TURN 릴레이 주소
  192.168.1.73:    50.76.44.100:60834           (최후의 수단)
   60834 typ host    typ srflx
```

ICE 에이전트는 로컬 IP를 먼저 검사하고, 그다음 공인 주소, **TURN은 last resort**로만 사용한다.

| 항목 | STUN | TURN |
|---|---|---|
| 약자 | Session Traversal Utilities for NAT | Traversal Using Relays around NAT |
| 역할 | 자신의 공인 IP/포트 발견 | 데이터를 중계(relay) |
| 데이터 경로 | **P2P 직접** | **서버 경유 릴레이** |
| 사용 시점 | 직접 연결 가능할 때 | 직접 연결 실패(예: symmetric NAT) 시 |
| 서버 비용 | 거의 없음(질의만) | 모든 트래픽이 서버를 통과 → 대역폭 비용 큼 |
| 사용 비율 | 대다수 | **약 8% 사용자가 TURN 필요** |

> Symmetric NAT 등으로 STUN만으로 직접 연결이 안 되면 TURN으로 폴백한다. TURN은 "P2P"라는 본래 이점을 깨고 서버가 모든 트래픽을 중계하므로 대역폭·운영 비용이 발생한다. 다만 약 8% 사용자에게만 필요해 비용을 어느 정도 제한할 수 있다.

**Trickle ICE**: 모든 후보를 다 모은 뒤 한 번에 보내지 않고, SDP offer를 먼저 보낸 뒤 후보를 발견하는 대로 점진적으로 흘려보내(`onicecandidate` → `addIceCandidate()`) 연결 지연을 줄인다.

### 5. DTLS 종단간 암호화

- WebRTC 명세는 **모든 전송 데이터(오디오/비디오/앱 데이터)의 암호화를 의무화**한다. 끄는 옵션이 없다.
- DTLS는 TLS와 동일한 보안 보장을 UDP 위에서 제공한다. UDP의 비신뢰성에 대응하기 위해:
  - 핸드셰이크 레코드에 **fragment offset + sequence number**를 명시 (핸드셰이크만을 위한 "mini-TCP")
  - 손실 패킷 재전송 타이머
  - DTLS 레코드는 단일 패킷에 맞아야 하고, 순서 뒤바뀜에 대응하기 위해 스트림 암호 대신 블록 암호 사용
- **키 재사용**: DTLS 핸드셰이크가 만든 shared secret이 SRTP/SRTCP(미디어)의 키 재료로 재사용된다. 즉 DTLS가 완료되어야 미디어/데이터 전송이 시작된다.
- 핸드셰이크는 **2 RTT** 소요 → 연결 설정 지연의 주요 원인 중 하나.

### 6. DataChannel 신뢰성/순서 설정

SCTP 덕분에 채널마다 신뢰성과 순서를 독립적으로 고를 수 있다.

| 설정 | ordered | reliable | 의미/용도 |
|---|---|---|---|
| 기본값 | Yes | Yes | TCP와 동일한 보장 (WebSocket 대체) |
| unordered + reliable | No | Yes | 전달 보장하되 순서 무관 → HOL blocking 회피 |
| ordered + 부분 신뢰 | Yes | Partial | 재전송 한도 지정 (게임 상태 등) |
| unordered + unreliable | No | No | UDP 유사 (실시간 위치/입력 등) |

**부분 신뢰성 옵션 (둘은 상호 배타적):**
- `maxRetransmits`: 최대 재전송 횟수
- `maxRetransmitTime` (= `maxPacketLifeTime`): 메시지 포기까지의 ms

```javascript
// 순서 무관 + 최대 N번 재전송
const conf1 = { ordered: false, maxRetransmits: customNum };
// 순서 보장 + 일정 ms 지나면 포기
const conf2 = { ordered: true, maxRetransmitTime: customMs };
const dc = pc.createDataChannel("namedChannel", conf1);
```

> 주의: unreliable 채널을 쓸 때는 **메시지 하나가 단일 패킷(약 1,150 bytes 미만)에 들어가는 것이 이상적**이다. SCTP 데이터 청크는 메시지당 28 bytes(공통 헤더 12 + 데이터 청크 헤더 16) 오버헤드가 있고, IP/UDP/DTLS/SCTP 헤더를 빼면 SCTP 페이로드 최대치가 약 1,150 bytes다.

### 7. DataChannel vs WebSocket 비교

| 항목 | WebSocket | DataChannel |
|---|---|---|
| 암호화 | 선택 가능 (ws/wss) | **항상 강제 (DTLS)** |
| 신뢰성 | reliable 고정 | 설정 가능 |
| 순서 | ordered 고정 | 설정 가능 |
| 멀티플렉싱 | 기본 없음(확장 필요) | **native 지원 (SCTP)** |
| 전송 단위 | 메시지 지향 | 메시지 지향 |
| 바이너리 | 지원 | 지원 |
| P2P | 불가 (서버 경유) | **가능 (피어 직접)** |

### 8. 코드 예시 (RTCPeerConnection / createDataChannel)

**Initiator (offer를 보내는 쪽):**
```javascript
const ice = { iceServers: [
  { urls: "stun:stun.l.google.com:19302" },
  { urls: "turn:turnserver.com", username: "user", credential: "pass" }
]};

const signalingChannel = new SignalingChannel();   // 앱이 구현
const pc = new RTCPeerConnection(ice);

const dc = pc.createDataChannel("namedChannel", { ordered: false });

pc.createOffer().then(offer => {
  pc.setLocalDescription(offer);
  signalingChannel.send(offer.sdp);                // 시그널링으로 offer 전달
});

pc.onicecandidate = (evt) => {                     // trickle ICE
  if (evt.candidate) signalingChannel.send(evt.candidate);
};

signalingChannel.onmessage = (msg) => {
  if (msg.candidate) pc.addIceCandidate(msg.candidate);
};

dc.onopen = () => dc.send("hello peer");            // 연결되면 직접 전송
dc.onmessage = (e) => console.log(e.data);
```

**Responder (answer를 보내는 쪽):**
```javascript
let pc;
signalingChannel.onmessage = (msg) => {
  if (msg.offer) {
    pc = new RTCPeerConnection(ice);
    pc.setRemoteDescription(msg.offer);
    pc.createAnswer().then(answer => {
      pc.setLocalDescription(answer);
      signalingChannel.send(answer.sdp);
    });
  } else if (msg.candidate) {
    pc.addIceCandidate(msg.candidate);
  }
};

pc.ondatachannel = (evt) => {                       // 상대가 만든 채널 수신
  const dc = evt.channel;
  dc.onmessage = (e) => console.log(e.data);
};
```

---

## 내가 얻은 인사이트

### 아키텍처 관점
1. **"서버 비경유 종단간 암호화"는 공짜가 아니라 복잡도와 맞바꾼 것이다**
   - DataChannel은 데이터가 서버를 거치지 않으므로 서버가 평문을 볼 수 없는 강한 프라이버시를 기본 제공한다. 하지만 이를 위해 UDP → ICE → DTLS → SCTP라는 4계층 스택과, SDP/ICE 교환을 위한 별도 시그널링 인프라를 앱이 직접 구축해야 한다. "P2P라서 서버가 필요 없다"는 오해와 달리, **연결을 맺는 동안에는 반드시 시그널링 서버가 필요**하다.

2. **암호화가 의무라는 점이 설계 단순화의 미덕**
   - WebSocket은 ws/wss 선택이 가능해 평문 실수가 가능하지만, WebRTC는 DTLS를 끌 수 없다. 보안을 옵션이 아니라 프로토콜의 일부로 못박은 것은 "안전하지 않은 기본값"을 원천 차단하는 좋은 설계 철학이다. 대가는 연결 설정 시 DTLS 2 RTT의 지연이다.

### 트레이드오프 관점
3. **TURN은 P2P의 이상을 깨는 현실적 타협**
   - Symmetric NAT 등으로 직접 연결이 불가능한 약 8% 사용자를 위해 TURN 릴레이가 필요하다. TURN을 쓰는 순간 데이터가 서버를 통과하므로 (1) P2P의 대역폭 절감 이점이 사라지고 (2) 서버가 모든 트래픽을 중계하는 비용·확장성 문제가 생긴다. **"P2P 100%"는 환상이며, TURN 대역폭 예산을 반드시 운영 비용에 반영해야 한다.**

4. **연결 설정 지연(latency)이 누적 구조**
   - STUN 질의 RTT + ICE connectivity check + DTLS 2 RTT + SCTP 핸드셰이크가 직렬로 쌓인다. 따라서 "연결을 자주 맺었다 끊는" 패턴은 비효율적이고, Trickle ICE로 후보 수집과 협상을 병렬화해 첫 연결 지연을 줄이는 것이 중요하다.

### 적용 관점
5. **"양쪽이 동시에 온라인" 제약이 유스케이스를 결정한다**
   - HTTP는 서버가 항상 listen하지만, 피어는 오프라인이거나 거절할 수 있다. DataChannel은 본질적으로 **동기적(synchronous) 통신**이라, 영상통화·실시간 게임·화면 공유·파일 직접 전송처럼 양쪽이 동시에 접속한 시나리오에 적합하다. 반대로 메시지를 쌓아뒀다 나중에 전달하는 비동기 메시징(오프라인 메시지, 푸시)에는 부적합하며, 이 경우 서버 기반 큐가 필요하다.

6. **신뢰성/순서를 채널 단위로 고를 수 있는 것이 진짜 차별점**
   - SCTP의 부분 신뢰성(`maxRetransmits`, `maxPacketLifeTime`) 덕분에 "최신 게임 상태만 중요하고 오래된 패킷은 버려도 되는" 케이스를 TCP의 HOL blocking 없이 구현할 수 있다. 한 연결에서 제어용(ordered+reliable)과 실시간용(unordered+unreliable) 채널을 멀티플렉싱하는 설계가 가능하다 — 이는 WebSocket으로는 추가 구현 없이는 흉내 내기 어렵다.
