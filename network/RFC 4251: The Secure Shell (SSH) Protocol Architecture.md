# RFC 4251: The Secure Shell (SSH) Protocol Architecture

## 출처
- **문서**: RFC 4251
- **링크**: https://www.rfc-editor.org/rfc/rfc4251.html
- **상태**: Standards Track (IETF 표준)
- **발행일**: January 2006
- **저자**: Tatu Ylonen (SSH Communications Security Corp), Chris Lonvick (Cisco Systems)
- **업데이트**: RFC 8308, RFC 9141

---

## AI 요약

### SSH란?
SSH(Secure Shell)는 **안전하지 않은 네트워크 위에서 안전한 원격 로그인 및 네트워크 서비스를 제공하는 프로토콜**이다. 1995년 Tatu Ylonen이 개발했으며, 기존의 Telnet, rlogin, FTP 등 평문 프로토콜을 대체하기 위해 설계되었다.

---

### SSH의 3계층 구조

SSH는 세 개의 독립적인 프로토콜 계층으로 구성된다:
```
┌─────────────────────────────────────────┐
│  Connection Protocol (RFC 4254)         │  ← 채널 다중화, 포트 포워딩
│  SSH-CONNECT                            │
├─────────────────────────────────────────┤
│  User Authentication Protocol (RFC 4252)│  ← 사용자 인증
│  SSH-USERAUTH                           │
├─────────────────────────────────────────┤
│  Transport Layer Protocol (RFC 4253)    │  ← 서버 인증, 암호화, 무결성
│  SSH-TRANS                              │
├─────────────────────────────────────────┤
│  TCP/IP (Port 22)                       │
└─────────────────────────────────────────┘
```

#### 1. Transport Layer Protocol (RFC 4253)
- **역할**: 서버 인증, 기밀성(암호화), 무결성, (선택적) 압축
- **제공 기능**:
  - 서버 호스트 키를 통한 **서버 인증**
  - Diffie-Hellman 기반 **키 교환**
  - 대칭키 **암호화** (AES, ChaCha20 등)
  - MAC을 통한 **데이터 무결성**
  - 고유한 **세션 ID** 생성
- **핵심**: Perfect Forward Secrecy(PFS) 제공 - 세션 키 유출되어도 과거 세션 안전

#### 2. User Authentication Protocol (RFC 4252)
- **역할**: 클라이언트 사용자를 서버에 인증
- **인증 방법**:
  - `publickey`: 공개키 인증 (가장 권장)
  - `password`: 비밀번호 인증
  - `hostbased`: 호스트 기반 인증
  - `keyboard-interactive`: 다단계 인증
- **전제 조건**: 반드시 Transport Layer가 먼저 수립되어야 함

#### 3. Connection Protocol (RFC 4254)
- **역할**: 암호화된 터널을 여러 논리적 **채널**로 다중화
- **제공 기능**:
  - Interactive shell 세션
  - TCP/IP 포트 포워딩 (터널링)
  - X11 포워딩
  - SFTP, SCP 등 서브시스템
- **채널**: 독립적인 데이터 스트림, 각각 flow control 적용

---

### Host Key (호스트 키)

호스트 키는 SSH 보안의 핵심이다.

#### 역할
- 클라이언트가 **서버의 정체성을 확인**하는 데 사용
- 키 교환 시 서버가 자신의 비밀키로 서명하여 인증

#### 신뢰 모델 (2가지)
| 모델 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **로컬 데이터베이스** | `~/.ssh/known_hosts`에 호스트명-키 매핑 저장 | 중앙 인프라 불필요 | 관리 부담 |
| **인증 기관 (CA)** | CA가 호스트 키에 서명, 클라이언트는 CA 루트만 저장 | 관리 용이 | 중앙 의존성 |

#### TOFU (Trust On First Use)
- 최초 연결 시 호스트 키 검증 없이 수락하는 옵션
- **위험**: MitM 공격에 취약
- **권장**: 최초 수락 후 로컬 DB에 저장, 이후 비교
```
The authenticity of host 'example.com (192.168.1.1)' can't be established.
ECDSA key fingerprint is SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no)?
```

---

### 키 교환 (Key Exchange)

#### Diffie-Hellman 키 교환
1. 클라이언트와 서버가 각각 임시 DH 파라미터 생성
2. 공개 값 교환
3. 양쪽이 동일한 **공유 비밀 (shared secret)** 계산
4. 공유 비밀 + 세션 데이터로 **세션 키** 파생

#### 파생되는 키들
- 암호화 키 (클라이언트→서버, 서버→클라이언트 별도)
- MAC 키 (양방향 별도)
- IV (Initialization Vector)

#### Perfect Forward Secrecy
- DH 임시 파라미터는 키 교환 후 **즉시 폐기**
- 서버 장기 비밀키 유출되어도 **과거 세션 복호화 불가**

---

### 암호화 알고리즘

#### 지원 암호화 (2006년 기준)
| 알고리즘 | 상태 | 비고 |
|---------|------|------|
| 3DES-CBC | REQUIRED | 호환성용, 느림 |
| AES-CBC | RECOMMENDED | 널리 사용 |
| AES-CTR | RECOMMENDED | CBC보다 안전 |
| AES-GCM | 이후 추가 | 인증 암호화 |
| ChaCha20-Poly1305 | 이후 추가 | OpenSSH 기본 |
| none | OPTIONAL | 디버깅 전용, **사용 금지** |

#### MAC 알고리즘
| 알고리즘 | 설명 |
|---------|------|
| hmac-sha1 | SHA-1 기반 HMAC |
| hmac-sha2-256 | SHA-256 기반 HMAC |
| hmac-sha2-512 | SHA-512 기반 HMAC |
| none | 디버깅 전용 |

---

### 메시지 번호 할당
```
Transport Layer:
  1-19   : 일반 (disconnect, ignore, debug 등)
  20-29  : 알고리즘 협상
  30-49  : 키 교환 방법별

User Authentication:
  50-59  : 인증 일반
  60-79  : 인증 방법별

Connection Protocol:
  80-89  : 연결 일반
  90-127 : 채널 관련

Reserved:
  128-191: 클라이언트 프로토콜용
  192-255: 로컬 확장용
```

---

### 보안 고려사항

#### 1. 난수 생성
- 모든 암호화 작업은 **고품질 난수**에 의존
- 엔트로피 부족 시 프로토콜 실행 **거부 권장**
- 세션별 랜덤 데이터로 세션 키 바인딩

#### 2. MitM (중간자 공격)
**3가지 시나리오**:
1. **최초 연결 시**: 공격자가 가짜 호스트 키 제공 → TOFU가 위험한 이유
2. **호스트 키 미검증**: 사회공학으로 가짜 키 배포
3. **세션 중 조작**: MAC으로 방어됨

**대응**:
- 호스트 키 fingerprint를 **대역외(out-of-band)** 검증
- DNS SSHFP 레코드 활용
- CA 서명된 호스트 키

#### 3. Replay 공격
- 32비트 **시퀀스 번호**가 MAC 입력에 포함
- 같은 패킷 재전송해도 시퀀스 번호 불일치로 거부
- **중요**: 2^32 패킷 전 반드시 **rekey** 필요 (약 1GB)

#### 4. Traffic Analysis
- 암호화해도 **패킷 타이밍/크기**로 정보 유출 가능
- 키스트로크 타이밍으로 비밀번호 길이 추측 가능
- **대응**: `SSH_MSG_IGNORE` 패킷, 랜덤 패딩

#### 5. DoS (서비스 거부)
- 키 교환은 CPU/메모리 집약적
- 인증 없이 키 교환만 반복하여 서버 자원 고갈 가능
- **대응**: 연결 속도 제한, 알려진 클라이언트만 허용

#### 6. Forward Secrecy
- DH 키 교환 사용 시 PFS 제공
- 세션 키 유출되면 해당 세션만 위험
- DH 파라미터는 메모리에서 **즉시 삭제**, 스왑 방지

---

### 인증 방법별 보안

| 방법 | 가정 | 위험 | 대응 |
|------|------|------|------|
| **publickey** | 클라이언트 미침해 | 비밀키 탈취 | 패스프레이즈, 스마트카드 |
| **password** | 서버 미침해 | 서버 침해 시 비밀번호 노출 | 공개키 인증으로 대체 |
| **hostbased** | 클라이언트 미침해 | 클라이언트 침해 시 무력화 | 다른 방법과 병용 |

---

### 알고리즘 네이밍 규칙
```
# IETF 표준 (@ 없음)
aes128-ctr
hmac-sha2-256
diffie-hellman-group14-sha1

# 로컬 확장 (@ 포함)
ourcipher-cbc@example.com
chacha20-poly1305@openssh.com
```

- `@` 없음: IANA 등록 필요
- `@` 있음: 도메인 소유자가 자유롭게 정의

---

### 관련 RFC 문서

| RFC | 제목 | 내용 |
|-----|------|------|
| RFC 4251 | SSH Protocol Architecture | 이 문서 (아키텍처 개요) |
| RFC 4252 | SSH Authentication Protocol | 사용자 인증 |
| RFC 4253 | SSH Transport Layer Protocol | 키 교환, 암호화 |
| RFC 4254 | SSH Connection Protocol | 채널, 포워딩 |
| RFC 4255 | DNS SSHFP RR | DNS로 호스트 키 배포 |
| RFC 4256 | Generic Message Exchange Auth | keyboard-interactive |
| RFC 8308 | Extension Negotiation | EXT_INFO 메시지 (Terrapin 공격 대상) |
| RFC 8332 | RSA with SHA-2 | rsa-sha2-256, rsa-sha2-512 |

---
