# PXE 서버 체인로딩 PoC

Docker 전용 네트워크 안에서 실제 `dnsmasq` DHCP/TFTP 서버와 HTTP 서버를 띄우고 다음 체인을 검증한다.

```text
legacy PXE DHCP -> TFTP undionly.kpxe -> iPXE DHCP -> HTTP boot.ipxe/kernel/initramfs
```

## 안전 경계

DHCP 서버를 개발자의 LAN 인터페이스에 노출하면 기존 공유기 DHCP와 충돌할 수 있다. 이 구성은 다음 장치로 그 위험을 차단한다.

- Docker 네트워크에 `internal: true` 적용
- DHCP/TFTP 포트를 호스트에 publish하지 않음
- 서버 주소를 격리망의 `172.30.0.2`로 고정
- 클라이언트가 받은 임대 주소를 실제 인터페이스에 적용하지 않음

Docker Desktop bridge는 아직 주소가 없는 NIC의 `0.0.0.0 → 255.255.255.255` DHCP 패킷을 컨테이너 사이에서 전달하지 않는다. 검증 클라이언트는 Docker가 배정한 `172.30.0.3`에서 `172.30.0.255`로 DHCPDISCOVER를 브로드캐스트하고, BOOTP broadcast flag를 끈 상태로 유니캐스트 OFFER를 받는다. 따라서 `dnsmasq`의 DHCP 분기와 boot option은 검증하지만, 주소가 전혀 없는 물리 NIC의 최초 프레임 조건까지 동일하게 에뮬레이션하지는 않는다.

## 실행

Docker Desktop이 필요하다.

```bash
cd "network/PXE 서버 구축 - DHCP·TFTP·iPXE 체인로딩 (실무 PoC)"
./run.sh
```

첫 실행에는 iPXE 및 Alpine 3.24.1 netboot 파일과 컨테이너 이미지를 내려받는다. 이후에는 Docker 빌드 캐시를 사용한다.

예상 결과:

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

## 무엇을 직접 검증하는가

| 단계 | 실제 구성 | 검증 방법 |
|---|---|---|
| DHCP #1 | `dnsmasq`가 IP·TFTP 서버·`undionly.kpxe` 제공 | Scapy로 DHCPDISCOVER/OFFER 교환 |
| TFTP | `dnsmasq` 내장 TFTP가 실제 iPXE 바이너리 제공 | TFTP로 받아 크기, PXE NBP 마커(`!PXE`, `PXENV+`), SHA-256 검사 |
| DHCP #2 | option 175가 있는 iPXE 요청에는 HTTP 스크립트 제공 | 두 번째 DHCP OFFER의 boot file 검사 |
| HTTP | `darkhttpd`가 스크립트와 실제 Alpine netboot 파일 제공 | 모든 파일을 내려받아 내용과 크기 검사 |

이 PoC는 펌웨어가 바이너리를 실행하고 커널로 제어권을 넘기는 단계까지 에뮬레이션하지 않는다. 그 단계는 실제 PC의 Network Boot 또는 브리지된 QEMU VM으로 확장할 수 있다.

## 설정 살펴보기

```bash
sed -n '1,200p' dnsmasq.conf
sed -n '1,120p' http/boot.ipxe
docker compose logs pxe-server
```

## 종료

```bash
docker compose down
```
