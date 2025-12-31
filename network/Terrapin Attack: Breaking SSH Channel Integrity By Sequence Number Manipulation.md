# Terrapin Attack: Breaking SSH Channel Integrity By Sequence Number Manipulation

## 출처
- **링크**: https://terrapin-attack.com/TerrapinAttack.pdf
- **학회**: USENIX Security Symposium 2024, Real World Crypto 2024, Black Hat USA 2024
- **저자**: Fabian Bäumer, Marcus Brinkmann, Jörg Schwenk (Ruhr University Bochum, Germany)
- **CVE**: CVE-2023-48795 (일반 프로토콜 결함), CVE-2023-46445/46446 (AsyncSSH 구현 결함)
- **공식 사이트**: https://terrapin-attack.com
- **GitHub**: https://github.com/RUB-NDS/Terrapin-Artifacts/

---

## AI 요약

### 연구 배경
SSH(Secure Shell)는 원격 터미널 로그인, **파일 전송(SFTP)**, VPN 등에 사용되는 인터넷 보안 표준 프로토콜이다. 인터넷 상의 1,500만 대 이상의 서버가 SSH를 사용하며, SFTP는 SSH의 서브시스템으로 동작한다.

이 논문은 **SSH 프로토콜 자체의 무결성(Integrity)을 깨는 최초의 실용적인 Prefix Truncation 공격**인 Terrapin Attack을 발표했다.

### 핵심 취약점
SSH 프로토콜의 Binary Packet Protocol(BPP)이 핸드셰이크 단계와 시퀀스 번호 처리에서 결함을 가지고 있다:

1. **시퀀스 번호가 핸드셰이크 전후로 리셋되지 않음**: 암호화되지 않은 핸드셰이크와 암호화된 세션이 동일한 시퀀스 번호 공간을 공유
2. **서명이 고정된 메시지 목록만 커버**: 전체 핸드셰이크 트랜스크립트가 아닌 일부만 보호
3. **ChaCha20-Poly1305와 Encrypt-then-MAC 모드의 설계 결함**: 공격자가 시퀀스 번호를 조작할 수 있는 여지 존재

### 공격 메커니즘
```
정상 흐름:
Client → [SSH_MSG_KEXINIT] → Server
Client ← [SSH_MSG_KEXINIT] ← Server
      ... (키 교환) ...
Client ← [SSH_MSG_NEWKEYS] ← Server
Client ← [SSH_MSG_EXT_INFO] ← Server  ← 이 메시지가 타겟!
```

**Terrapin 공격 흐름**:
1. 공격자(MitM: Man-in-the-Middle)가 핸드셰이크 중에 `SSH_MSG_IGNORE` 메시지를 주입
2. 주입된 메시지로 시퀀스 번호가 증가
3. 핸드셰이크 완료 후, 공격자가 `SSH_MSG_EXT_INFO` 메시지를 드랍
4. 시퀀스 번호가 이미 조작되었으므로, 클라이언트/서버가 메시지 누락을 감지 못함
5. 결과: **Extension Negotiation 메시지가 조용히 삭제됨**

### 영향받는 암호화 모드
| 암호화 모드 | 취약 여부 | 비고 |
|------------|----------|------|
| ChaCha20-Poly1305 | ✅ 취약 | OpenSSH 기본값, 실용적 공격 가능 |
| AES-CBC + Encrypt-then-MAC | ✅ 취약 | CBC 모드 필요 |
| AES-CTR + Encrypt-then-MAC | ⚠️ 이론적 취약 | 실용적 공격 불가 |
| AES-GCM | ❌ 안전 | 별도의 IV/nonce 사용 |
| Encrypt-and-MAC (원본) | ❌ 안전 | 평문 무결성 보호 |

**스캔 결과**: 인터넷 상 SSH 서버의 **77% 이상**이 실용적으로 공격 가능한 모드를 지원

### 실제 공격 시나리오

#### 시나리오 1: Extension Downgrade Attack
- `SSH_MSG_EXT_INFO` 메시지 삭제
- **결과**: RSA 공개키 인증 시 덜 안전한 알고리즘으로 다운그레이드
- SHA-2 대신 **SHA-1**로 폴백 (SHA-1은 충돌 공격에 취약)

#### 시나리오 2: Keystroke Timing Attack 활성화
- OpenSSH 9.5에서 도입된 키스트로크 타이밍 난독화 기능 비활성화
- **결과**: MitM 공격자가 SSH 패킷 타이밍 분석으로 **비밀번호 brute-force 가능**

#### 시나리오 3: AsyncSSH Rogue Session Attack (CVE-2023-46446)
- AsyncSSH의 상태 머신 결함과 결합
- **결과**: 피해자가 모르는 사이에 **다른 계정으로 로그인**되도록 조작
- 강력한 피싱 공격 및 암호화된 세션 내 MitM 가능

### 공격 조건
1. **MitM(Man-in-the-Middle) 위치 확보**: TCP/IP 레이어에서 트래픽 가로채기 및 수정 가능해야 함
2. **취약한 암호화 모드 사용**: ChaCha20-Poly1305 또는 CBC+EtM
3. **양쪽 모두 미패치 상태**: 클라이언트와 서버 중 하나만 패치되어도 여전히 취약

### 대응 방안

#### 1. "Strict Kex" 카운터메저 (OpenSSH 제안)
- 핸드셰이크 완료 시 **시퀀스 번호를 0으로 리셋**
- 인증되지 않은 핸드셰이크 메시지 주입 방지
- **주의**: 클라이언트와 서버 **양쪽 모두** 지원해야 효과 있음

#### 2. 취약한 암호화 알고리즘 비활성화
```bash
# /etc/ssh/sshd_config 또는 /etc/ssh/ssh_config에 추가
Ciphers aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr
MACs hmac-sha2-256,hmac-sha2-512
```

**비활성화해야 할 것**:
- `chacha20-poly1305@openssh.com` (cipher)
- `*-etm@openssh.com` (MACs)
- `*-cbc` (ciphers with CBC mode)

#### 3. 취약점 스캐너 사용
```bash
# Go로 작성된 스캐너
./terrapin-vulnerability-scanner --connect target.server.com:22
```

### 영향받는 구현체 (일부)
- OpenSSH (9.6에서 패치)
- PuTTY, KiTTY, WinSCP
- libssh, libssh2
- Paramiko (Python)
- AsyncSSH (Python)
- FileZilla
- Dropbear
- 그 외 수십 개 구현체

### 패치 타임라인
| 날짜 | 이벤트 |
|------|--------|
| 2023-10-17 | OpenSSH, AsyncSSH에 최초 보고 |
| 2023-11-08 | AsyncSSH 패치 버전 공개 |
| 2023-11-17 | 17개 SSH 구현체에 Round 1 공개 |
| 2023-11-21 | 12개 추가 구현체에 Round 2 공개 |
| 2023-12-11 | distros 메일링 리스트 공개 |
| 2023-12-18 | **공개 공개(Public Disclosure)** |

### 다른 프로토콜과의 비교
| 프로토콜 | Terrapin 취약 | 이유 |
|---------|--------------|------|
| SSH | ✅ | 시퀀스 번호 미리셋, 부분 핸드셰이크 인증 |
| TLS 1.3 | ❌ | 키 변경 시 시퀀스 번호 리셋, 전체 핸드셰이크 인증 |
| IPSec/IKE | ❌ | 시퀀스 번호 리셋 |
| TLS 1.2 이하 | ❌ | 시퀀스 번호 리셋 |

### 논문의 의의
- **최초의 실용적인 Prefix Truncation 공격**: 이론적으로만 언급되던 공격을 실제로 구현
- **암호화 네트워크 프로토콜의 새로운 공격 패밀리 정의**: 향후 유사 취약점 연구의 기반
- **대규모 영향**: 인터넷 SSH 서버 77%+ 영향, SFTP 포함 모든 SSH 서비스에 적용

---

## 내가 얻은 인사이트

### 1. SFTP 보안은 SSH 보안에 완전히 의존
- SFTP는 독립 프로토콜이 아니라 **SSH 서브시스템**
- SSH에 취약점이 있으면 SFTP도 자동으로 영향받음
- "SFTP는 안전하다"는 말은 "SSH가 안전하다"는 전제 하에만 성립

### 2. 10년 된 "안전한" 암호화 모드도 문제가 될 수 있다
- ChaCha20-Poly1305는 2013년 OpenSSH에 도입된 "최신 안전한" 알고리즘
- 그러나 **프로토콜 레벨 설계 결함** 때문에 10년 후 취약점 발견
- **교훈**: 암호화 알고리즘이 안전해도 프로토콜 설계가 잘못되면 무용지물

### 3. 양쪽 패치가 필수
- 서버만 패치하거나 클라이언트만 패치하면 **여전히 취약**
- 기업 환경에서 레거시 시스템이 많으면 패치 완료까지 수년 걸릴 수 있음
- **실무 시사점**: SFTP/SSH 클라이언트 버전 관리 정책 필요

### 4. MitM 조건은 생각보다 현실적
- "MitM이 필요하니까 안전하다"는 **착각**
- 로컬 네트워크(회사 Wi-Fi, 카페 등)에서는 MitM이 쉬움
- ARP 스푸핑, DNS 포이즈닝, 악성 라우터 등으로 충분히 달성 가능
