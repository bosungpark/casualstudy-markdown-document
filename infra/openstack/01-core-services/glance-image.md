# Glance — VM 이미지 창고

> **OS 이미지(Ubuntu, CentOS, Windows…)를 보관하고 나눠주는 도서관.**

AWS의 AMI에 해당. "한 번 만든 이미지를 여러 VM으로 찍어내는" 템플릿 엔진이다.

---

## 한 줄 요약

Nova가 VM을 만들 때 **"Ubuntu 이미지 줘"** 하면 Glance가 꺼내준다. 저장은 로컬 파일, Swift, Ceph 중 아무거나 가능.

```
  개발자: "Ubuntu 22.04 이미지 업로드"
     ▼
  Glance: DB에 메타데이터(이름/크기/포맷) + 실제 파일은 백엔드에
     ▼
  Nova: "그 이미지 줘" → Glance가 스트리밍으로 전달
     ▼
  Compute 노드에 복사 → VM 부팅
```

---

## 내부 구성

```
[glance-api]  ── 업로드/다운로드 REST API
      │
      ▼
[백엔드 스토어]  ── 실제 파일이 사는 곳 (선택 가능)
   ├─ file:///  (로컬 디스크 — 개발용)
   ├─ Swift     (OpenStack 오브젝트 스토리지)
   ├─ Ceph RBD  (프로덕션 주류)
   └─ S3 호환
```

Glance 자체는 **메타데이터만** 가지고 있고, **실제 바이너리는 위임**한다. 그래서 "Glance 디스크가 부족해"라는 고민을 안 해도 됨.

---

## 이미지 포맷

| 포맷 | 설명 |
|---|---|
| **qcow2** | 가장 흔함. 씬 프로비저닝 + 스냅샷 지원 |
| **raw** | 그냥 원시 디스크. 빠르지만 용량 다 먹음 (Ceph와 궁합 좋음) |
| **vmdk** | VMware |
| **iso** | 설치 CD |
| **ami** | Amazon 호환 |

프로덕션 팁: **Ceph 쓰면 raw가 유리**하다. Ceph이 스냅샷을 대신 해주니까 qcow2의 장점이 희석됨.

---

## Visibility (공개 범위)

| 값 | 누가 볼 수 있음? |
|---|---|
| **private** | 만든 프로젝트만 |
| **shared** | 지정한 프로젝트들 (member add) |
| **community** | 모든 프로젝트가 볼 수 있으나, 검색 안 됨 (아는 사람만) |
| **public** | 모든 프로젝트가 자유롭게 (admin만 만들 수 있음) |

---

## 손으로 해보기

```bash
# 이미지 업로드
$ openstack image create \
    --disk-format qcow2 \
    --container-format bare \
    --file ubuntu-22.04.qcow2 \
    --public \
    ubuntu-22.04

# 목록
$ openstack image list

# 상세
$ openstack image show ubuntu-22.04

# 다운로드
$ openstack image save --file out.qcow2 ubuntu-22.04

# 삭제
$ openstack image delete ubuntu-22.04
```

---

## 이미지 라이프사이클

```
queued ──► saving ──► active ──► deleted
                 └──► killed  (업로드 실패)
```

- **queued**: 메타데이터만 있음, 아직 업로드 전
- **saving**: 업로드 진행 중
- **active**: 사용 가능
- **deleted**: 삭제됨

---

## 자주 밟는 지뢰

- **"Image size mismatch"** → 업로드 중 연결 끊김. 재업로드
- **VM 부팅 안 됨** → 이미지 포맷(qcow2/raw)과 `--disk-format` 불일치
- **cloud-init 안 먹힘** → 이미지에 cloud-init 패키지가 깔려 있어야 함. "cloud image"를 받아야지 설치 ISO는 안 됨
- **Ceph 백엔드인데 느림** → qcow2 대신 **raw**로 올려야 Copy-on-Write가 동작

---

## 이미지는 어디서 구하나

대부분 배포판이 **공식 cloud image**를 제공한다:

- Ubuntu: https://cloud-images.ubuntu.com
- CentOS/Rocky: https://cloud.centos.org
- Debian: https://cloud.debian.org

직접 설치 ISO로 만들면 cloud-init, qemu-guest-agent, SSH 키 주입 등이 안 되니 **공식 cloud image** 쓰는 게 정답.

---

## AWS 매핑

| AWS | Glance |
|---|---|
| AMI | Image |
| AMI가 S3에 저장됨 | Glance가 Swift/Ceph에 저장됨 |
| AMI 공유 (per-account) | shared visibility |
| Public AMI | public visibility |

구조가 거의 동일. AMI 써본 사람은 "이름만 다른 같은 것"으로 봐도 된다.

---

## 다음

→ [nova-compute.md](./nova-compute.md): Nova가 Glance에서 이미지를 어떻게 가져다 쓰는지  
→ [swift-object-storage.md](./swift-object-storage.md): Glance의 백엔드로 자주 쓰는 Swift
