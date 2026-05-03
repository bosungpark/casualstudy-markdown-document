# 02 · Advanced Services

핵심 4종(MS / Hypervisor / Networking / Storage) 위에 얹히는 부가 컴포넌트.

> 출처: [Apache CloudStack Admin Guide](https://docs.cloudstack.apache.org/en/latest/adminguide/).

| 문서 | 무엇을 다룸 |
|---|---|
| [system-vms.md](./system-vms.md) | SSVM / CPVM / Virtual Router 의 자세한 동작 |
| [vpc.md](./vpc.md) | Multi-Tier 가상 사설망, ACL, Site-to-Site VPN |
| [projects.md](./projects.md) | 여러 Account의 협업 컨테이너 |
| [regions-and-multi-zone.md](./regions-and-multi-zone.md) | Region 단위 Multi-Zone, Multi-MS 토폴로지 |

OpenStack의 [02-advanced-services](../../openstack/02-advanced-services/) (Heat, Magnum, Octavia, Ironic) 와 비교하면, CloudStack은 **부가 기능을 별도 프로젝트로 분리하지 않고 MS 안 + System VM 으로 통합**한 점이 특징.

| OpenStack 부가 | CloudStack 대응 |
|---|---|
| Heat (오케스트레이션) | (제한적 — AutoScale, 또는 Terraform 별도) |
| Octavia (LBaaS) | Network Offering의 LB Service (VR 안 HAProxy) |
| Magnum (K8s) | CKS (CloudStack Kubernetes Service) — 별도 |
| Ironic (BareMetal) | Bare Metal Compute (제한적) |
| Designate (DNS) | (없음 — VR이 DNS 제공) |
| Barbican (Secrets) | (없음 — User Data + 외부 Vault) |
