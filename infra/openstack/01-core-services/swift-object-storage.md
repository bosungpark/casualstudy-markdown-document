# Swift — 파일 무제한 창고

> **HTTP로 파일을 쌓고 꺼내는 대규모 분산 저장소.**

AWS의 S3. 파일 개수 제한 없이 쌓을 수 있고, 디스크 몇 대 죽어도 안 사라진다.

---

## 한 줄 요약

Cinder가 "VM 옆에 붙이는 디스크"라면, Swift는 "HTTP로만 접근하는 파일 서랍"이다. 랜덤 액세스, 작은 수정 같은 건 안 되고 **통째로 PUT / GET / DELETE**만 가능.

```
  $ curl -X PUT .../my-bucket/photo.jpg  --data-binary @photo.jpg
  $ curl      .../my-bucket/photo.jpg  > got.jpg
  $ curl -X DELETE .../my-bucket/photo.jpg
```

---

## 3계층 네임스페이스

```
Account (테넌트)
  └── Container (버킷)
        └── Object (파일)
```

S3로 치면:
- Account = AWS 계정
- Container = 버킷
- Object = S3 오브젝트

---

## 내부 구성

```
[proxy-server]          클라이언트 요청 라우팅 (앞단)
     │
     ▼  (Ring을 참고)
[account-server]        계정 메타데이터
[container-server]      컨테이너 목록
[object-server]         실제 파일 저장 (3곳에 복제)
```

**Ring**: 어떤 오브젝트를 **어느 디스크**에 둘지 결정하는 일관된 해시 테이블. 디스크 추가/제거 시 **최소 이동**으로 리밸런싱.

---

## 3x 복제 (또는 Erasure Coding)

```
object "photo.jpg"
    ▼ (Ring이 계산)
    ├─ node-01 /disk-a/
    ├─ node-05 /disk-c/  ← 같은 파일이 3개 복제본
    └─ node-09 /disk-b/
```

- 디스크 하나 죽어도 멀쩡
- 노드 하나 죽어도 멀쩡
- 자동 **replicator**가 주기적으로 누락된 복제본 복구

대용량은 복제 대신 **Erasure Coding**(RAID 비슷, 스토리지 효율↑) 선택 가능.

---

## Eventually Consistent

쓰자마자 다른 노드에서 읽으면 **옛 버전이 잠깐 보일 수 있다**.

- 3개 중 2개에 쓰면 성공으로 간주 (Quorum)
- 나머지 1개는 백그라운드로 동기화
- 대부분 수 초 내 일관성 확보

→ DB처럼 강한 일관성 필요한 용도엔 부적합. 백업/로그/이미지/정적 파일 같은 **WORM(Write Once Read Many)** 에 적합.

---

## 손으로 해보기

```bash
# 컨테이너 만들기
$ openstack container create photos

# 파일 업로드
$ openstack object create photos cat.jpg

# 목록
$ openstack object list photos

# 다운로드
$ openstack object save photos cat.jpg

# 대용량 파일 (> 5GB) → SLO(Static Large Object)로 분할 업로드
$ swift upload photos big.iso --segment-size 1G

# S3 API로도 접근 (swift3 미들웨어 또는 Ceph RGW)
$ s3cmd --host=... put cat.jpg s3://photos/
```

---

## 특징 요약

| 항목 | 값 |
|---|---|
| 접근 | HTTP 만 |
| 수정 | ❌ (통째로 덮어쓰기만) |
| 랜덤 seek | ❌ |
| 단일 오브젝트 최대 | 5GB (그 이상은 SLO/DLO로 분할) |
| 일관성 | Eventually |
| 복제 | 3x 기본 (또는 EC) |
| 용도 | 백업, 로그, 이미지, 정적 파일, 아카이브 |

---

## 자주 밟는 지뢰

- **대용량 업로드 실패** → 5GB 넘으면 SLO 필요. `swift` CLI가 자동 분할
- **쓴 직후 404** → Eventually consistent. 1~2초 뒤 다시 시도
- **Public URL 안 나옴** → `tempurl` 미들웨어 + 키 설정 필요
- **Swift vs Ceph RGW** → 요즘 신규 구축은 **Ceph RGW가 Swift API 호환** 제공해서 Ceph로 통일하는 경우 많음

---

## Swift vs Ceph (RGW) — 선택 가이드

| 기준 | Swift | Ceph RGW |
|---|---|---|
| 오브젝트만 필요 | ✅ 가볍고 튼튼 | 오버킬 |
| 블록(RBD) + 오브젝트 + 파일(CephFS) 다 필요 | ❌ | ✅ 통합 |
| 초대규모 (수백 PB) | ✅ 검증됨 (Rackspace) | ✅ 검증됨 |
| 일관성 | Eventually | Strong (쓰면 즉시 읽힘) |

실무에선 **새로 깐다면 Ceph RGW**, **이미 Swift 깔려 있으면 유지**가 많음.

---

## AWS 매핑

| AWS S3 | Swift |
|---|---|
| Bucket | Container |
| Object | Object |
| Account | Account |
| Presigned URL | tempurl |
| Versioning | Versioning (컨테이너 설정) |
| Lifecycle | Expiring objects |

S3 API 호환 미들웨어가 있어서 `s3cmd`, `aws-cli`, `boto3`로도 Swift에 접근 가능.

---

## 다음

→ [glance-image.md](./glance-image.md): VM 이미지의 백엔드로 자주 쓰이는 Swift  
→ [cinder-block-storage.md](./cinder-block-storage.md): Cinder Backup의 기본 저장소도 Swift
