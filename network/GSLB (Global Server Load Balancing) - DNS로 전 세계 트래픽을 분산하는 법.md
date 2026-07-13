# GSLB (Global Server Load Balancing) - DNS로 전 세계 트래픽을 분산하는 법

## 출처
- **아티클/논문**: The Ultimate Guide to Global Server Load Balancing (GSLB)
- **저자/출처**: Loadbalancer.org Blog
- **링크**: https://www.loadbalancer.org/blog/ultimate-guide-to-gslb/

---

## AI 요약

### 1. GSLB란?

**GSLB(Global Server Load Balancing)** 는 여러 데이터센터/리전에 분산된 서버들 사이에서, **어느 데이터센터로 사용자를 보낼지를 DNS 단계에서 결정**하는 기술이다.

일반 로드밸런서(L4/L7)가 "한 데이터센터 **안**에서 서버들 사이"를 분산한다면, GSLB는 "**데이터센터들 사이**"를 분산한다.

| 구분 | Local LB (일반 로드밸런서) | GSLB |
|------|---------------------------|------|
| 분산 단위 | 서버(백엔드) | 데이터센터/리전 |
| 동작 계층 | L4/L7 (패킷/세션) | **DNS (이름 해석)** |
| 판단 기준 | 서버 부하/연결 수 | 지리 위치, 지연시간, DC 가용성 |
| 주 목적 | 서버 부하 분산 | **재해 복구, 지연 최소화, 규제 준수** |

---

### 2. 동작 원리: DNS 위임(Delegation)

핵심은 "**GSLB가 트래픽을 직접 받지 않는다**"는 점이다. GSLB는 **DNS 응답으로 어느 IP(VIP)를 줄지**만 결정하고, 실제 연결은 클라이언트가 그 IP로 직접 맺는다.

```
① 클라이언트 → Local DNS: "www.example.com 주소 뭐야?"
                   │
② Local DNS ─(NS 위임)→ GSLB(권한 DNS): 이 도메인은 GSLB가 답함
                   │
③ GSLB: 규칙 평가(위치·헬스·부하) → "가장 좋은 DC의 VIP = 1.2.3.4"
                   │
④ Local DNS ← IP(1.2.3.4) 응답, TTL 동안 캐싱
                   │
⑤ 클라이언트 ───직접 연결───→ 1.2.3.4 (해당 DC의 로컬 로드밸런서)
                                   │
                                └→ 실제 백엔드 서버로 분산
```

즉 GSLB는 **"교통 표지판"** 이지 "도로" 자체가 아니다. 트래픽이 GSLB를 통과하지 않으므로 처리량 병목이 없다.

> 대표 구현: **PowerDNS**(고성능 DNS 서버, DNSSEC 지원) + **Polaris**(로드밸런싱 방식·헬스 모니터·동적 가중치 추가) 조합.

---

### 3. 로드밸런싱(라우팅) 방식

| 방식 | 설명 |
|------|------|
| **Failover Group (fogroup)** | 우선순위 순서대로. Member 1 죽으면 → 2 → 3. Member 1 복구 시 다시 전체 트래픽 회수 (액티브-패시브) |
| **Weighted Round Robin (wrr)** | 각 멤버에 부여한 가중치 비율로 분산. 배치 처리로 결국 비율 수렴 |
| **Topology Weighted Round Robin (twrr)** | 가중치 + **지리 인식**. 특정 서브넷(리전)에서 온 요청은 그 리전 멤버로 우선 라우팅하되, 장애 시 자동 페일오버 |
| **지리/근접(Geo/Proximity)** | 클라이언트의 ISP DNS 서버 주소로 위치를 추정해 가장 가까운 DC로 |

**Active-Active vs Active-Passive**
- **Active-Active**: 모든 DC가 동시에 트래픽 수신(wrr/twrr). 글로벌 분산에 이상적
- **Active-Passive**: 평소 한 DC만, 장애 시 다른 DC로(fogroup). 재해 복구용
- twrr은 "주 DC 우선 + 자동 페일오버"라는 **하이브리드** 모델

---

### 4. 헬스체크(Health Check)

GSLB가 "죽은 DC로 안 보내는" 능력의 핵심.

| 유형 | 내용 |
|------|------|
| **HTTP/HTTPS** | GET 요청 후 특정 응답 코드 기대 |
| **TCP** | 포트 연결 확인, 옵션으로 send/receive 문자열 검증 |
| **Forced** | 수동으로 pass/fail 강제 지정(점검용) |
| **External Monitor** | 커스텀 스크립트(예: 인증 필요한 URL 검사) |
| **External Dynamic Weight** | CPU/디스크/네트워크 등 **실시간 지표로 가중치 자동 조정** |

---

### 5. TTL — GSLB의 아킬레스건

DNS 응답은 **TTL 동안 캐싱**된다. 여기서 GSLB의 가장 큰 한계가 나온다.

```
긴 TTL  → 세션 지속성 ↑, DNS 부하 ↓  |  하지만 장애 시 페일오버 느림 ❌
짧은 TTL → 빠른 페일오버 ✅          |  하지만 DNS 쿼리 폭증, 부하 ↑
```

- 클라이언트/리졸버가 이전 IP를 캐싱해 **로드밸런서 지시를 무시**하고 같은 DC로 계속 감 → "**hot node**" 발생
- DNS 설정 변경의 **수렴(convergence)에 수 시간**이 걸릴 수 있음

---

### 6. 주요 활용 사례

1. **재해 복구(Disaster Recovery)**: 한 DC 장애 시 자동으로 가장 가까운 정상 DC로 재라우팅 → 무중단
2. **지연 최소화(Latency)**: 지리적으로 가까운 DC로 보내 홉 수·왕복 시간 감소
3. **규제/데이터 주권(Compliance)**: 사용자 위치별로 적절한 DC 지정 → 데이터 저장·처리 지역 규제 준수(GDPR 등)
4. **오브젝트 스토리지**: 노드 용량 기반 동적 가중치로 멀티사이트 트래픽 분산

---

## 내가 얻은 인사이트

### 아키텍처 관점
1. **"GSLB는 결정하고, 연결은 클라이언트가 한다"**
   - GSLB가 트래픽을 통과시키지 않고 **DNS 응답만 조작**한다는 점이 본질이다. 덕분에 처리량 병목이 없지만, 대신 **DNS 캐싱이라는 통제 불가능한 변수**를 떠안는다. 이 트레이드오프가 GSLB의 모든 장단점을 설명한다.

2. **TTL은 CAP의 축소판**
   - 긴 TTL(가용성/성능) vs 짧은 TTL(빠른 정합성/페일오버)의 딜레마는 결국 **"얼마나 최신 상태를 반영할 것인가 vs 부하"** 문제다. GSLB의 페일오버가 "즉시"가 아니라 "TTL만큼 느리다"는 걸 반드시 설계에 반영해야 한다.

### 운영 관점
3. **GSLB는 만능 페일오버가 아니다**
   - "DC 하나 죽으면 GSLB가 알아서 옮겨주겠지"는 위험한 기대다. 클라이언트 캐싱·수 시간 수렴 때문에 **일부 사용자는 여전히 죽은 DC를 향한다**. 진짜 무중단을 원하면 GSLB(DNS 라우팅) + **Anycast/BGP나 L7 프록시 페일오버**를 함께 써서 계층을 이중화해야 한다.

4. **L7 기능의 상실**
   - 트래픽이 GSLB를 통과하지 않으므로 **콘텐츠 기반 라우팅, 세션 지속성 같은 L7 기능을 GSLB 계층에선 못 쓴다.** 그래서 GSLB는 항상 각 DC의 **로컬 로드밸런서(L7)와 2단 구조**로 조합된다: GSLB가 "어느 DC" → 로컬 LB가 "어느 서버".

### 트레이드오프 관점
5. **왜 요즘은 Anycast로 많이 가는가**
   - CDN/클라우드가 **Anycast(같은 IP를 여러 DC가 광고, BGP가 최단 경로로)** 를 선호하는 이유는, GSLB의 DNS 캐싱·TTL 지연 문제를 라우팅 계층에서 우회하기 때문이다. 다만 Anycast는 라우팅 인프라(BGP) 통제가 필요하고, GSLB는 DNS만 있으면 되므로 **진입 장벽이 낮다.** 규모·통제력에 따라 선택이 갈린다.

---

### 참고 소스
- [The Ultimate Guide to GSLB | Loadbalancer.org](https://www.loadbalancer.org/blog/ultimate-guide-to-gslb/)
- [What is Global Server Load Balancing (GSLB)? | A10 Networks](https://www.a10networks.com/glossary/what-is-global-server-load-balancing/)
- [What Is GSLB? | IBM](https://www.ibm.com/think/topics/global-server-load-balancing)
- [Global Server Load Balancing | NetScaler Docs](https://docs.netscaler.com/en-us/citrix-adc/current-release/global-server-load-balancing.html)
