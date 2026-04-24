# Horizon — 클릭으로 OpenStack 조작

> **REST API를 클릭 가능한 UI로 바꿔주는 Django 웹앱.**

CLI 치기 귀찮을 때 쓴다. 없어도 OpenStack은 잘 돌아간다 — **필수가 아니라 편의 도구.**

---

## 한 줄 요약

Horizon은 **얇은 프록시**다. 자체 DB 없음. 사용자가 클릭하면 내부적으로 `openstack server create` 같은 API를 호출한다.

```
  브라우저 → Horizon(Django) → Keystone/Nova/Neutron/... REST API
                 ↑
           Horizon은 자기 데이터 없음
```

---

## 주요 화면

```
┌─────────────────────────────────────┐
│ [프로젝트 뷰]                       │
│  ├─ Compute: 인스턴스, 이미지, 키쌍│
│  ├─ 네트워크: 네트워크, 라우터     │
│  ├─ 볼륨: 볼륨, 스냅샷             │
│  └─ 오브젝트: 컨테이너              │
│                                     │
│ [관리자 뷰] (admin만)              │
│  ├─ Hypervisor                     │
│  ├─ Flavor 관리                    │
│  ├─ 도메인/프로젝트 관리           │
│  └─ 시스템 정보                    │
│                                     │
│ [Identity 뷰]                      │
│  └─ 사용자/역할/프로젝트 관리      │
└─────────────────────────────────────┘
```

프로젝트(일반 사용자) / 관리자(admin) / Identity 뷰가 **Role에 따라** 다르게 보인다.

---

## 로그인 흐름

```
[1] 사용자가 ID/PW 입력
[2] Horizon → Keystone: 토큰 발급
[3] 토큰을 Django 세션에 저장
[4] 이후 모든 클릭 → Horizon이 해당 토큰으로 각 서비스 API 호출
[5] 결과를 HTML로 렌더링
```

**브라우저는 토큰을 직접 보지 않는다.** Django 세션 쿠키만 갖고 있고, 토큰은 서버 측에 저장.

---

## 플러그인 구조

Horizon은 핵심 서비스(Nova/Neutron/...)만 기본 지원. 다른 서비스는 **dashboard 플러그인**으로 붙인다.

- **Octavia-dashboard**: 로드밸런서
- **Magnum-UI**: Kubernetes
- **Designate-dashboard**: DNS
- **Heat-dashboard**: 스택 템플릿
- **Manila-UI**: 파일 공유

플러그인 설치 = pip install + `local_settings.py` 에 등록.

---

## Horizon이 죽었을 때

- ❌ 웹 UI 안 됨
- ✅ CLI (`openstack ...`) 정상 동작
- ✅ API 직접 호출 정상 동작
- ✅ VM, 볼륨, 네트워크 전부 멀쩡

운영자 편의 도구일 뿐, **데이터 플레인에 없다**. 재시작 부담 적음.

---

## 설정 요점 (local_settings.py)

```python
# Keystone URL
OPENSTACK_KEYSTONE_URL = "http://controller:5000/v3"

# 기본 Role
OPENSTACK_KEYSTONE_DEFAULT_ROLE = "member"

# 여러 리전 지원
AVAILABLE_REGIONS = [
    ("http://region1:5000/v3", "Region1"),
    ("http://region2:5000/v3", "Region2"),
]

# 세션 타임아웃
SESSION_TIMEOUT = 3600
```

---

## 자주 밟는 지뢰

- **"Unable to connect to the Keystone"** → `OPENSTACK_KEYSTONE_URL` 오타 / 방화벽
- **로그인 후 리디렉트 루프** → 시간 동기화 문제(NTP) 또는 세션 쿠키 설정
- **플러그인 설치했는데 메뉴 안 나옴** → `_<plugin>.py` 파일이 `enabled/` 디렉토리에 있어야 함
- **느리다** → 매 페이지마다 여러 API 호출. **Memcached** 캐시 켜기 필수
- **HTTPS 안 됨** → Apache/nginx에 인증서 + `CSRF_COOKIE_SECURE=True`

---

## AWS 매핑

| AWS | Horizon |
|---|---|
| AWS Management Console | Horizon |

그게 다다. 구조상 동등. 다만 AWS Console은 AWS가 직접 만든 것이고, Horizon은 **오픈소스 + 플러그인 구조**라는 차이.

---

## Skyline — 새로운 대안

요즘 **Skyline**이라는 새 대시보드가 뜨고 있다.

- React 기반 (Horizon은 Django)
- 더 빠르고 현대적 UX
- 2020년대 이후 프로젝트

신규 구축 시 **Skyline을 고려해볼 가치** 있음. Horizon은 여전히 표준이지만 UI가 올드하다.

---

## 다음

→ 각 서비스의 CLI 먼저 익히고 → Horizon에서 같은 작업 찾아보면 둘 다 빨리 는다.  
→ [../03-installation/devstack/](../03-installation/devstack/) 에 설치하면 Horizon이 기본 포함.
