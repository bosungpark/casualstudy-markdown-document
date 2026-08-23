# PXE 서버 구축 - DHCP·TFTP·iPXE 체인로딩을 격리 환경에서 검증하기

## 출처

- **아티클/논문**: Chainloading iPXE
- **저자/출처**: iPXE project
- **링크**: https://ipxe.org/howto/chainloading

---

## AI 요약

### 1. PXE와 iPXE 체인로딩이란?

PXE(Preboot eXecution Environment)는 로컬 디스크보다 먼저 네트워크에서 부트 프로그램을 받아 실행하는 펌웨어 기능이다. DHCP는 클라이언트의 네트워크 설정과 부트 파일 위치를 알려주고, 펌웨어는 보통 TFTP로 첫 번째 NBP(Network Boot Program)를 내려받는다.

iPXE chainloading은 NIC에 들어 있는 제한적인 PXE ROM을 교체하지 않고, 그 ROM이 iPXE 바이너리를 먼저 내려받아 실행하게 하는 방식이다. 이후에는 iPXE의 HTTP·스크립팅 기능을 사용할 수 있다.

```text
[NIC의 PXE ROM]
      │ DHCP: IP와 boot file은?
      ▼
[DHCP 서버] ── boot file=undionly.kpxe, next-server=TFTP 주소
      │
      ▼ TFTP
[undionly.kpxe 실행]
      │ 다시 DHCP
      ▼
[DHCP 서버] ── 실제 boot.ipxe 또는 OS 부트 정보
      │
      ▼ HTTP
[kernel + initramfs] ──▶ OS 설치/부팅
```

### 2. 왜 PXE ROM에서 바로 OS를 받지 않고 iPXE를 한 번 거치는가?

기본 PXE ROM은 대개 TFTP 중심이고 표현력이 낮다. iPXE를 체인로딩하면 HTTP, 스크립트, 메뉴, 조건 분기와 같은 기능을 추가할 수 있다. 수많은 NIC의 ROM을 다시 굽지 않고도 부트 로직을 서버에서 바꿀 수 있다는 것이 원문의 핵심 동기다.

| 구간 | 역할 | 이 PoC의 구현 |
|---|---|---|
| DHCP | IP, next-server, boot file 전달 | `dnsmasq` |
| TFTP | 펌웨어가 이해하는 첫 NBP 전달 | `undionly.kpxe` |
| iPXE | 더 강력한 네트워크 부트 환경 | 공식 iPXE 바이너리 |
| HTTP | 스크립트·커널·initramfs의 빠른 전달 | `darkhttpd` |

TFTP가 나쁜 프로토콜이라서 완전히 제거하는 것이 아니다. 첫 단계의 펌웨어가 TFTP만 이해하므로 작은 iPXE 바이너리를 전달하는 부트스트랩에 사용하고, 큰 파일은 iPXE가 HTTP로 가져가게 한다.

### 3. 가장 중요한 함정: 무한 체인로딩

iPXE가 실행되면 네트워크 설정과 다음 부트 파일을 얻기 위해 DHCP를 다시 수행한다. DHCP 서버가 첫 요청과 두 번째 요청을 구분하지 않고 항상 `undionly.kpxe`를 반환하면 다음 루프가 생긴다.

```text
PXE ROM -> undionly.kpxe -> iPXE -> undionly.kpxe -> iPXE -> ...
```

원문은 세 가지 해결책을 제시한다.

1. TFTP 루트에 `autoexec.ipxe`를 두어 자동 실행한다.
2. DHCP 서버가 첫 PXE 요청과 iPXE의 재요청을 구분해 서로 다른 파일을 준다.
3. 고정 URL을 가리키는 스크립트를 iPXE 바이너리에 내장한다.

이 PoC는 두 번째 방법을 사용한다. `dnsmasq`가 iPXE의 DHCP option 175 유무를 기준으로 응답을 바꾼다.

```ini
dhcp-match=set:ipxe,175
dhcp-boot=tag:!ipxe,undionly.kpxe,pxe-server,172.30.0.2
dhcp-boot=tag:ipxe,http://172.30.0.2:8080/boot.ipxe
```

이 설정은 원문의 ISC dhcpd 예제를 그대로 복사한 것이 아니라, 원문이 설명한 “두 DHCP 요청을 구분한다”는 설계를 `dnsmasq`로 옮긴 PoC 구현이다.

### 4. BIOS와 UEFI는 첫 부트 파일이 다르다

원문은 레거시 BIOS 계열에는 `undionly.kpxe`, UEFI 시스템에는 `ipxe.efi`가 필요하다고 설명한다. DHCP option 93의 client architecture 값을 보고 적절한 바이너리를 선택할 수 있다.

| 클라이언트 | 대표 첫 부트 파일 | 비고 |
|---|---|---|
| Legacy BIOS PXE | `undionly.kpxe` | UNDI 드라이버 사용 |
| UEFI x86-64 | `ipxe.efi` 또는 서명된 EFI 체인 | Secure Boot 별도 고려 |

본 PoC는 흐름을 작게 유지하기 위해 legacy BIOS의 `undionly.kpxe` 경로만 검증한다. 실제 서버 팜에서는 아키텍처·펌웨어·Secure Boot 상태에 따른 분기가 필요하다.

### 5. 직접 실행한 격리형 PoC

PoC는 홈/사무실 LAN의 DHCP를 건드리지 않도록 Docker internal network 안에 서버와 가상 클라이언트를 둔다.

```text
Docker internal network: 172.30.0.0/24

┌──────────────────────────┐       ┌──────────────────────────┐
│ pxe-client               │       │ pxe-server 172.30.0.2    │
│ - Scapy DHCP client      │◀─────▶│ - dnsmasq DHCP/TFTP     │
│ - TFTP client            │       │ - darkhttpd             │
│ - HTTP verifier          │       │ - real iPXE/Alpine files│
└──────────────────────────┘       └──────────────────────────┘
```

실행:

```bash
cd "network/PXE 서버 구축 - DHCP·TFTP·iPXE 체인로딩 (실무 PoC)"
./run.sh
```

자동 검증 항목:

1. option 175가 없는 DHCPDISCOVER에 `undionly.kpxe`와 TFTP 서버 주소가 오는가?
2. 그 파일을 TFTP로 실제 내려받을 수 있으며 PXE NBP 구조 마커와 충분한 크기를 갖는가?
3. option 175가 있는 두 번째 DHCPDISCOVER에는 `boot.ipxe` HTTP URL이 오는가?
4. HTTP 서버에서 스크립트, Alpine kernel, initramfs, modloop를 모두 받을 수 있는가?

2026년 8월 9일 Docker Desktop에서 직접 실행한 결과는 다음과 같다.

```text
[PASS] DHCP #1 (legacy PXE ROM)
  offer=172.30.0.143 next-server=172.30.0.2 boot-file=undionly.kpxe
[PASS] TFTP: undionly.kpxe (72,270 bytes, PXE NBP markers found)
  sha256=882478541a5e38d7dc09f519cffa817778ff1f9cc0b66d98e7abe6b1527bd3cc
[PASS] DHCP #2 (chainloaded iPXE, option 175)
  boot-file=http://172.30.0.2:8080/boot.ipxe
[PASS] HTTP boot stage
  vmlinuz-virt       12,575,744 bytes
  initramfs-virt      9,637,032 bytes
  modloop-virt       22,867,968 bytes

PXE chain verified: DHCP -> TFTP iPXE -> DHCP -> HTTP boot payloads
```

이 PoC가 검증하지 않는 경계도 분명하다. Docker Desktop bridge는 주소가 없는 NIC의 `0.0.0.0 → 255.255.255.255` DHCP 패킷을 컨테이너 사이에서 전달하지 않는다. 클라이언트는 이미 받은 컨테이너 IP에서 서브넷 브로드캐스트로 DHCPDISCOVER를 보내고, BOOTP broadcast flag를 끈 상태로 유니캐스트 OFFER를 받는다. 실제 `dnsmasq`의 DHCP 분기와 boot option은 검증하지만 물리 NIC의 최초 프레임 조건까지 같지는 않다. 또한 PXE 펌웨어가 iPXE를 실행하고 커널에 제어권을 넘기는 단계는 에뮬레이션하지 않는다.

### 6. 실제 네트워크로 옮길 때 달라지는 것

| PoC | 실제 운영 |
|---|---|
| Docker internal network | 전용 provisioning VLAN 권장 |
| 단일 BIOS 경로 | option 93 기반 BIOS/UEFI 분기 |
| 임의 클라이언트 허용 | MAC allowlist·자산 DB 연계 |
| HTTP 평문 | 이미지 서명·해시·필요시 HTTPS |
| 단일 서버 | DHCP relay, TFTP/HTTP HA와 관측성 |

가장 위험한 실수는 테스트 DHCP 서버를 기존 LAN에 그대로 붙이는 것이다. 한 브로드캐스트 도메인에 DHCP 서버가 둘이면 클라이언트는 먼저 도착한 OFFER를 선택할 수 있어 다른 장비의 네트워크 설정까지 망가질 수 있다. 실습은 반드시 격리망에서 시작해야 한다.

---

## 내가 얻은 인사이트

### 부트스트랩 설계 관점

1. **PXE는 하나의 프로토콜이 아니라 단계별 계약의 묶음이다.**
   - DHCP는 위치를 알려주고, TFTP는 최소 실행기를 전달하며, iPXE와 HTTP가 실제 부트 정책과 큰 파일을 담당한다. 장애를 “PXE 실패” 하나로 부르지 말고 어느 계약에서 끊겼는지 나눠 봐야 한다.

2. **작고 보편적인 로더에서 강력한 로더로 넘어가는 패턴이다.**
   - 펌웨어 기능을 직접 확장하는 대신, 펌웨어가 이해하는 최소 TFTP 경로로 iPXE를 올리고 이후 정책을 소프트웨어로 가져온다. BIOS ROM을 바꾸지 않고도 서버 측 스크립트로 동작을 바꿀 수 있다.

### 운영 관점

3. **두 번째 DHCP 요청을 구분하는 것이 체인로딩의 핵심 상태 전이다.**
   - 동일한 클라이언트가 짧은 시간 안에 DHCP를 두 번 한다. 요청자를 구분하지 못하면 장애가 아니라 무한 루프가 되므로, option 175나 user class 같은 식별 신호가 구성의 중심이다.

4. **PXE의 실제 보안 경계는 부트 파일의 신뢰성이다.**
   - DHCP와 TFTP는 인증된 전달 채널이 아니다. 운영 환경에서는 전용 VLAN만으로 끝내지 말고 Secure Boot, 서명된 EFI 바이너리, 이미지 해시, 부트 서버 변경 통제를 함께 설계해야 한다.

### 실습 설계 관점

5. **DHCP 실습은 기능보다 격리가 먼저다.**
   - 컨테이너로 dnsmasq를 띄우는 것은 쉽지만 LAN에 잘못 노출하면 영향 범위가 크다. internal network와 포트 미공개를 PoC의 부가 설정이 아니라 첫 번째 요구사항으로 두는 것이 맞다.
