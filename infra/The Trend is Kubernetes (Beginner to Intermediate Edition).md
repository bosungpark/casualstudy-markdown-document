# The Trend is Kubernetes (Beginner to Intermediate Edition)

## 출처
- **링크**:  https://www.inflearn.com/en/course/%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4-%EA%B8%B0%EC%B4%88

---

## Introduction

1. 서버 자원을 효율적으로 쓰기 위한 가상화 기술
2. Linux (자원 격리) -> VM (OS 기동) -> Container (OS 기동 X) -> **Container 오케스트레이터**

---

## Kubernetes Cluster Installation

1. Vagrant: VirtualBox 등 다양한 가상화 소프트웨어와 연동 가능, 명령어 한 줄로 VM 생성, 시작, 중지, 삭제 가능

---

## Pod - Container, Label, NodeSchedule

1. Container: Pod 안에는 하나의 독립적인 서비스를 구동할 수 있는 컨테이너가 있다. 컨테이너에는 하나 이상의 포트를 가질 수 있지만 중복된 포트를 가질 수는 없다. Pod 안에 컨테이너들은 하나의 호스트(기기)로 묶이게 된다. Pod 생성 시에 고유한 IP(주소)가 할당되는데 만약 Pod에 문제가 생기면 시스템이 재생성하고 이때 IP가 변경된다.
2. Label: Pod 뿐 아니라 모든 오브젝트에 달 수 있다. 목적에 따라 오브젝트를 분류하고, 오브젝트를 따로 연결하기 위한 목적이다. 키-값의 한 쌍으로 구성된다. 하나의 Pod에는 여러 Label을 달 수 있다.
3. NodeSchedule: Pod는 여러 노드들 중 하나에 올라가야 한다. 직접 선택하는 방법과 NodeSchedule을 이용하는 방법이 있다. NodeSchedule는 사용량에 따라 자동으로 스케줄 해준다.

---

## Service - Practice

1. 

---
