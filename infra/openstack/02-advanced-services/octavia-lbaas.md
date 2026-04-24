# Octavia — 로드밸런서 셀프서비스

> **VM 여러 개 앞에 붙이는 로드밸런서를 API 한 번으로 만들어줌.**

AWS ELB / ALB / NLB에 해당. 웹서버 3대 앞에 붙여서 트래픽 분산하는 그거.

---

## 왜 필요한가

VM 3대로 웹서버를 돌린다 치자. 사용자에게 어떻게 연결?

- ❌ VM 3개 IP를 다 알려줌 → 장애시 수동 전환
- ❌ DNS Round Robin → 장애 감지 못 함, 캐시 이슈
- ✅ **로드밸런서** → 공인IP 하나, 뒤에 VM N개, 자동 헬스체크

Octavia가 이 LB를 **"만들어달라고 API 치면"** 자동으로 띄워준다.

---

## 한 줄 요약

Octavia는 **HAProxy 가상머신(amphora)를 띄워서** 로드밸런서를 구현한다. 그래서 "VM이 LB가 된다"는 재밌는 구조.

```
  사용자 → Octavia API: "LB 만들어줘"
     ▼
  Octavia → Nova: amphora VM 1~2대 생성
     ▼
  amphora 안에 HAProxy 설치 + 설정
     ▼
  사용자에게 VIP(Virtual IP) 반환
```

---

## 구조 한눈에

```
    [클라이언트]
         │
         ▼ VIP (예: 203.0.113.10:443)
    ┌─────────┐
    │ amphora │ ◄── HAProxy가 돌고 있는 VM (Octavia가 관리)
    │(HAProxy)│
    └────┬────┘
         │ round-robin / least-conn / source-hash
         ├────────────┬──────────────┐
         ▼            ▼              ▼
      [member1]   [member2]     [member3]   ← 뒤에 서 있는 실제 VM
      10.0.0.11   10.0.0.12    10.0.0.13
```

---

## 핵심 객체

| 객체 | 설명 |
|---|---|
| **Load Balancer** | LB 본체 (VIP를 가짐) |
| **Listener** | 어떤 포트/프로토콜 받을지 (예: 443/HTTPS) |
| **Pool** | 뒷단 서버 그룹 |
| **Member** | Pool 안의 개별 서버 (VM + 포트) |
| **Health Monitor** | 헬스체크 규칙 (예: `/health` 에 HTTP 200) |
| **L7 Policy / Rule** | URL 기반 라우팅 (예: `/api/*` → pool A, `/*` → pool B) |
| **Amphora** | 실제 HAProxy를 돌리는 VM. Octavia의 일꾼 |

---

## 손으로 해보기

```bash
# 1) LB 생성 (공인망에 VIP)
$ openstack loadbalancer create \
    --name web-lb \
    --vip-subnet-id public-subnet

# 2) Listener (HTTPS 443)
$ openstack loadbalancer listener create \
    --name https \
    --protocol HTTPS --protocol-port 443 \
    --default-tls-container-ref <barbican-cert> \
    web-lb

# 3) Pool (뒷단 서버 묶음)
$ openstack loadbalancer pool create \
    --name web-pool \
    --protocol HTTP --lb-algorithm ROUND_ROBIN \
    --listener https

# 4) Member 추가 (실제 VM들)
$ openstack loadbalancer member create \
    --address 10.0.0.11 --protocol-port 80 \
    web-pool
$ openstack loadbalancer member create \
    --address 10.0.0.12 --protocol-port 80 \
    web-pool

# 5) Health Monitor
$ openstack loadbalancer healthmonitor create \
    --type HTTP --url-path /health \
    --delay 5 --timeout 3 --max-retries 3 \
    web-pool

# 6) VIP 확인
$ openstack loadbalancer show web-lb
```

---

## LB 알고리즘

| 알고리즘 | 언제 |
|---|---|
| **ROUND_ROBIN** | 기본. 순서대로 분배 |
| **LEAST_CONNECTIONS** | 연결 수 적은 서버에 우선 |
| **SOURCE_IP** | 같은 클라이언트 → 같은 서버 (세션 유지) |

L4 전용이면 `--protocol TCP`, L7이면 `HTTP/HTTPS`.

---

## Amphora 토폴로지

| 모드 | 설명 |
|---|---|
| **SINGLE** | amphora 1대. 싸지만 SPOF |
| **ACTIVE_STANDBY** | 2대. VRRP로 Failover (기본 권장) |
| **ACTIVE_ACTIVE** | 여러 대. 수평 확장. 아직 실험적 |

```bash
$ openstack loadbalancer create \
    --name prod-lb \
    --vip-subnet-id public-subnet \
    --flavor active-standby
```

---

## HTTPS 종료 — Barbican과 연동

HTTPS 인증서는 **Barbican**(시크릿 저장소)에 올려두고 Listener가 참조.

```
Barbican: TLS 인증서 저장
    │
    ▼
Octavia Listener: "HTTPS 443, 인증서는 Barbican의 이 UUID"
    │
    ▼
amphora: 인증서 내려받아 HAProxy 설정
```

이러면 **클라이언트 → LB는 HTTPS, LB → 서버는 HTTP**로 끊을 수 있음 (TLS termination).

---

## K8s와의 연동

Magnum으로 만든 K8s 클러스터에서 `Service type=LoadBalancer` 쓰면:

```
kubectl apply -f service-lb.yaml
    ▼
OpenStack Cloud Provider 플러그인
    ▼
Octavia API 호출 → LB 자동 생성
    ▼
Service.status.loadBalancer.ingress에 VIP 주입
```

즉 **K8s 리소스 하나가 Octavia LB 하나**로 매핑된다. 쓰면 편하다.

---

## 자주 밟는 지뢰

- **amphora 생성 실패** → amphora 이미지 등록 안 됨, 전용 flavor/네트워크 설정 누락
- **Health check 계속 DOWN** → Security Group에서 LB → member 방향 허용했는지
- **TLS 인증서 로드 실패** → Barbican secret에 octavia 사용자 ACL 부여
- **SSL Passthrough 안 됨** → TCP 리스너로 바꿔서 서버에서 TLS 종료하게
- **LB 지우는 데 오래 걸림** → amphora VM 삭제까지 가야 완료

---

## AWS 매핑

| AWS | Octavia |
|---|---|
| Classic ELB | TCP/HTTP Listener |
| ALB (L7) | HTTP Listener + L7 Policy |
| NLB (L4) | TCP Listener |
| Target Group | Pool |
| Target | Member |
| Health Check | Health Monitor |
| ACM 인증서 | Barbican Secret |

---

## 다음

→ [../01-core-services/neutron-networking.md](../01-core-services/neutron-networking.md): Floating IP / Security Group (LB 작동 조건)  
→ [magnum-k8s-on-openstack.md](./magnum-k8s-on-openstack.md): K8s가 Octavia를 자동 호출하는 구조
