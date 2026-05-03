# 05 · Deep Dives

핵심 컴포넌트 내부 동작 심화. 사용법은 [01-core-services/](../01-core-services/), 큰 그림은 [00-overview/](../00-overview/) 에 있다. 여기는 **"어떻게"** 가 궁금할 때.

| 문서 | 무엇을 다룸 |
|---|---|
| [api-auth-flow.md](./api-auth-flow.md) | Signed Query 의 내부 검증 알고리즘, RBAC 체크 |
| [scheduler-allocator-internals.md](./scheduler-allocator-internals.md) | DeploymentPlanner / HostAllocator / StoragePoolAllocator 내부 |
| [virtual-router-internals.md](./virtual-router-internals.md) | VR이 부팅하고 dnsmasq/iptables/HAProxy를 띄우는 흐름 |
