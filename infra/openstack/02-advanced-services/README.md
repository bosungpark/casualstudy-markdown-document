# 02 · Advanced Services

Core 8개로도 VM은 잘 돌아간다. 여기부턴 **"이게 있으면 훨씬 편해지는"** 선택형 서비스들.

> 비유하자면, Core가 **기본 자동차**라면 Advanced는 **내비·블루투스·자율주행 옵션**. 필요한 옵션만 골라서 단다.

---

## 언제 뭐가 필요한가 — 상황별 가이드

```
"VM을 한두 개 만드는 게 아니라, 앱 스택 전체를 한 번에 배포하고 싶다"
    → Heat (템플릿으로 찍어내기)

"쿠버네티스 클러스터가 필요한데, 매번 kubeadm 치기 지겹다"
    → Magnum (버튼 하나로 K8s 생성)

"VM 여러 개 띄워놨는데 앞단에 로드밸런서 붙이고 싶다"
    → Octavia (AWS ELB 같은 것)

"VM이 아니라 물리 서버 자체를 셀프서비스로 빌려주고 싶다"
    → Ironic (베어메탈 프로비저닝)

"도메인 관리, DNS도 OpenStack으로 하고 싶다"
    → Designate (AWS Route 53)

"비밀번호, TLS 인증서, 암호화 키를 안전하게 저장하고 싶다"
    → Barbican (AWS KMS + Secrets Manager)

"파일 공유(NFS)가 필요하다"
    → Manila (AWS EFS)

"GPU, FPGA 같은 가속기도 스케줄링하고 싶다"
    → Cyborg
```

---

## 머릿속 그림 — Core 위에 어떻게 올라타나

```
┌───────────────────────────────────────────┐
│  Advanced Services (옵션)                │
│  ┌──────┐ ┌──────┐ ┌───────┐ ┌────────┐ │
│  │ Heat │ │Magnum│ │Octavia│ │ Ironic │ │
│  └──┬───┘ └──┬───┘ └───┬───┘ └───┬────┘ │
│     │       │          │         │       │
└─────┼───────┼──────────┼─────────┼───────┘
      │       │          │         │
      ▼       ▼          ▼         ▼
   Nova    Nova+       Neutron   (하드웨어
   Neutron Neutron+     +Nova     직접 제어)
   Cinder  Keystone
      │
      ▼
┌───────────────────────────────────────────┐
│  Core Services (필수)                    │
│  Keystone · Nova · Neutron · ...         │
└───────────────────────────────────────────┘
```

Advanced 서비스는 **대부분 Core 위에 얹혀** 작동한다. Heat는 Nova/Neutron을 호출해 VM을 찍어내고, Magnum은 Nova 위에 K8s 노드 VM을 띄운다. Ironic만 예외로 **하드웨어를 직접** 제어함.

---

## 간단 요약 — 한 줄씩

| 서비스 | 한 줄 | AWS 대응 | 문서 |
| --- | --- | --- | --- |
| **Heat** | "YAML로 인프라 찍어내기". VM, 네트워크, LB를 템플릿 하나로 배포 | CloudFormation | [heat-orchestration.md](./heat-orchestration.md) |
| **Magnum** | "K8s 클러스터를 API 한 번으로 생성". 노드 VM 자동 프로비저닝 | EKS | [magnum-k8s-on-openstack.md](./magnum-k8s-on-openstack.md) |
| **Octavia** | "VM 앞에 붙이는 로드밸런서". HTTPS 종료, 헬스체크, 세션 유지 | ELB/ALB | [octavia-lbaas.md](./octavia-lbaas.md) |
| **Ironic** | "VM이 아니라 진짜 서버를 빌려줌". PXE 부팅으로 물리 머신 프로비저닝 | EC2 bare metal (i3.metal) | [ironic-baremetal.md](./ironic-baremetal.md) |

---

## "필수 아님"을 다시 강조

이 디렉토리의 모든 서비스는 **선택사항**이다. VM만 굴리는 게 목표면 Core만으로 충분하다. 필요해진 순간에 **하나씩 붙이면 되는** 구조가 OpenStack의 철학.

> ⚠️ 함정: "이것도 있고 저것도 있다"고 다 깔면 운영 부담이 폭증한다. **정말 쓸 것만** 깐다.

---

## 다음 단계

- 구체적인 사용법은 각 서비스 문서(위 표 링크)로.
- 실제 설치는 → [../03-installation/](../03-installation/) (kolla-ansible 사용 시 `globals.yml`에서 `enable_heat: yes` 같이 플래그로 on/off).
- 심화 주제(LBaaS 아키텍처, Ironic과 Nova 통합 등)는 → [../05-deep-dives/](../05-deep-dives/)
