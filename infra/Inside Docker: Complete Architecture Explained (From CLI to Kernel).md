# Inside Docker: Complete Architecture Explained (From CLI to Kernel)

## 출처

* **링크**: [https://dev.to/srinivasamcjf/inside-docker-the-complete-architecture-explained-from-cli-to-kernel-4mf1](https://dev.to/srinivasamcjf/inside-docker-the-complete-architecture-explained-from-cli-to-kernel-4mf1)

---

## AI 요약

이 아티클은 `docker run` 명령이 실행된 순간부터 실제 리눅스 커널에서 컨테이너 프로세스가 생성되기까지의 **전체 경로**를 단계별로 설명한다.

핵심 흐름은 다음과 같다.

1. 사용자가 `docker run`을 실행하면 Docker CLI는 **Docker Daemon(dockerd)** 에 REST API 요청을 보낸다.
2. `dockerd`는 컨테이너 생성을 직접 수행하지 않고, **containerd**에게 작업을 위임한다.
3. containerd는 각 컨테이너마다 **containerd-shim** 프로세스를 생성하여 컨테이너의 생명주기를 관리한다.
4. 실제 컨테이너 프로세스 생성은 **runc**가 담당하며,
   이때 Linux의 **namespace, cgroups** 를 설정해 격리된 실행 환경을 만든다.
5. 컨테이너는 “가상 머신”이 아니라 **호스트 커널 위에서 실행되는 일반 프로세스**이며,
   단지 커널 기능을 이용해 격리된 것일 뿐이다.

즉 Docker는 하나의 거대한 기술이 아니라,

* 데몬
* 런타임(containerd, runc)
* 리눅스 커널 기능
  을 **조합한 오케스트레이션 레이어**라는 점을 강조한다.

---

## 내가 얻은 인사이트

Docker의 본질은 “컨테이너 기술”이 아니라 **역할 분리된 파이프라인 설계**에 가깝다.

* `dockerd`는 사용자 경험(API, UX)에 집중하고
* `containerd`는 컨테이너 라이프사이클에 집중하며
* `runc`는 순수하게 “프로세스를 어떻게 격리해서 띄울 것인가”만 담당한다.

이 구조 덕분에:

* Docker 없이도 containerd + runc만으로 컨테이너 실행이 가능하고
* Kubernetes가 Docker를 걷어내고도(containerd 채택) 아무 문제 없었던 이유가 명확해진다.

**Docker는 컨테이너를 “만드는 기술”이 아니라,
컨테이너 실행을 표준화한 조정자(orchestrator)였다.**
