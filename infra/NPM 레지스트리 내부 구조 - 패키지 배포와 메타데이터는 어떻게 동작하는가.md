# NPM 레지스트리 내부 구조 - 패키지 배포와 메타데이터는 어떻게 동작하는가

## 출처
- **아티클/논문**: NPM registry internals
- **저자/출처**: Packagecloud Blog
- **링크**: https://blog.packagecloud.io/npm-registry-internals/

---

## AI 요약

### 1. NPM 레지스트리란?

NPM 레지스트리는 **Node.js 패키지 + 메타데이터 + API 엔드포인트의 모음**이다. 우리가 매일 쓰는 `npm install`, `npm publish`는 결국 이 레지스트리의 HTTP API를 호출하는 클라이언트일 뿐이다.

| 구성 요소 | 역할 |
|---|---|
| 패키지 파일 (tarball) | 실제 코드가 담긴 `.tgz` 압축 파일 |
| JSON 메타데이터 | 패키지 이름, 버전 목록, 의존성, 체크섬, tarball URL 등 |
| API 엔드포인트 | publish / unpublish / deprecate / dist-tag 등의 워크플로우 제공 |

핵심은 **레지스트리가 특별한 프로토콜이 아니라 평범한 HTTP + JSON**이라는 점이다. `curl`만으로도 레지스트리의 거의 모든 것을 들여다볼 수 있다.

### 2. npm publish - 배포는 어떻게 동작하는가

```
┌─────────────┐                          ┌──────────────────────┐
│  개발자 PC   │                          │   NPM 레지스트리       │
│             │  PUT /package-name       │                      │
│ npm publish ├─────────────────────────>│ 1. 요청 검증          │
│             │  body:                   │ 2. tarball 저장       │
│             │   - tarball (base64)     │ 3. 메타데이터 생성/갱신 │
│             │   - JSON 메타데이터       │    (install에서 사용)  │
└─────────────┘                          └──────────────────────┘
```

- `npm publish`를 실행하면 패키지 디렉터리가 tarball로 압축되고, **base64로 인코딩되어 JSON 메타데이터와 함께 하나의 PUT 요청 본문**에 담겨 레지스트리로 전송된다.
- 레지스트리는 이 요청을 처리하면서 **`npm install`이 사용할 JSON 메타데이터를 생성**한다. 즉, 배포 시점에 설치를 위한 데이터가 미리 만들어진다.

### 3. 레지스트리 메타데이터 - full vs abbreviated

패키지 하나당 레지스트리는 두 종류의 메타데이터를 제공한다.

| 구분 | Full 메타데이터 | Abbreviated 메타데이터 |
|---|---|---|
| 용도 | 패키지 정보 전체 조회 | `npm install`에 필요한 최소 정보 |
| 요청 방법 | 기본 GET 요청 | `Accept: application/vnd.npm.install-v1+json` 헤더 |
| 포함 필드 | 이름, 버전 목록, 작성자, 유지보수자, 라이선스, 체크섬, tarball URL, 생성/수정 시각 등 | 설치에 필요한 필드만 (응답 크기가 훨씬 작음) |

직접 확인해볼 수 있다:

```bash
# full 메타데이터
curl https://registry.npmjs.org/chalk | jq

# abbreviated 메타데이터 (install이 실제로 쓰는 것)
curl -H "Accept: application/vnd.npm.install-v1+json" \
     https://registry.npmjs.org/chalk | jq
```

메타데이터가 하는 일:
- 요청된 버전의 패키지 설치 정보 제공 (tarball URL, 체크섬)
- 해당 패키지가 필요로 하는 **의존성 목록** 제공

### 4. Scoped 패키지 - @scope/name의 URL 처리

`@elastic/eui`처럼 `@`로 시작하는 scoped 패키지는 이름에 `/`가 들어가므로, 레지스트리 URL에서는 **`%2F`로 인코딩**해야 한다.

```bash
# @elastic/eui의 메타데이터 조회
curl https://registry.npmjs.org/@elastic%2Feui

# abbreviated 버전
curl -H "Accept: application/vnd.npm.install-v1+json" \
     https://registry.npmjs.org/@elastic%2Feui
```

### 5. 핵심 워크플로우 API 4가지

| 워크플로우 | 명령어 | HTTP 동작 | 비고 |
|---|---|---|---|
| Publish | `npm publish` | PUT (tarball + 메타데이터) | 배포 시 latest 태그 자동 갱신 |
| Unpublish | `npm unpublish` | PUT(특정 버전) / DELETE(전체) | 공식 레지스트리는 배포 후 24시간 내에만 허용 |
| Deprecate | `npm deprecate` | PUT (메타데이터에 deprecate 필드 추가) | 패키지는 유지하되 경고 표시 |
| Dist-tags | `npm dist-tag` | 메타데이터의 태그-버전 매핑 수정 | `latest`, `beta` 같은 이름표 |

#### Unpublish vs Deprecate
- **unpublish는 위험하다.** 다른 패키지가 의존하고 있으면 그들의 빌드가 전부 깨진다 (left-pad 사태가 대표적). 그래서 공식 레지스트리는 24시간 제한을 둔다.
- 공개된 패키지를 내리고 싶다면 **deprecate가 권장** 방식이다. 패키지는 설치 가능하게 유지되고, 설치 시 경고 메시지만 표시된다.

#### Dist-tags 동작 원리

```
npm install example@beta
        │
        ▼
1. 레지스트리에서 example의 메타데이터 요청
        │
        ▼
2. 메타데이터의 dist-tags 매핑 확인
   { "latest": "2.1.0", "beta": "3.0.0-rc.1" }
        │
        ▼
3. beta → 3.0.0-rc.1 버전의 tarball 다운로드/설치
```

- 배포하면 최신 버전에 `latest` 태그가 자동으로 붙는다.
- `npm install package`처럼 태그를 생략하면 **암묵적으로 `latest` 태그**를 사용한다.
- 즉, dist-tag는 **버전 번호에 붙이는 사람이 읽을 수 있는 별명(alias)**이며, 메타데이터 안의 태그→버전 매핑 테이블로 구현된다.

### 6. 정리 - 배포 구조 전체 그림

```
 npm publish                      npm install chalk@beta
      │                                   │
      ▼                                   ▼
┌───────────────────────────────────────────────────┐
│                 NPM 레지스트리                       │
│                                                   │
│  [메타데이터 저장소]           [tarball 저장소]       │
│  - 버전 목록                  - chalk-2.1.0.tgz     │
│  - dist-tags 매핑             - chalk-3.0.0.tgz    │
│  - 의존성 정보                                      │
│  - 체크섬 + tarball URL  ──────────┘               │
└───────────────────────────────────────────────────┘
      ▲                                   │
      │ PUT (base64 tarball + JSON)       │ GET 메타데이터 → GET tarball
```

레지스트리는 결국 **"메타데이터 DB + 파일 저장소"를 HTTP API로 감싼 것**이고, publish는 쓰기, install은 읽기 경로다.

---

## 내가 얻은 인사이트

### 프로토콜 설계 관점

1. **레지스트리는 마법이 아니라 HTTP + JSON이다**
   - `curl`과 `jq`만으로 레지스트리의 모든 메타데이터를 검사할 수 있다는 점이 인상적이다. 사내 프록시 레지스트리(Verdaccio, Nexus 등)가 어떻게 npmjs.org를 흉내 낼 수 있는지도 이걸로 설명된다 — 동일한 URL 규약과 JSON 형식만 구현하면 되기 때문이다.

2. **읽기 경로 최적화: abbreviated 메타데이터**
   - 설치가 압도적으로 잦은 읽기 작업이므로, Accept 헤더 기반 content negotiation으로 응답 크기를 줄인 설계가 실용적이다. API 설계에서 "같은 리소스, 다른 상세도"가 필요할 때 별도 엔드포인트 대신 Accept 헤더를 쓰는 좋은 사례다.

3. **배포 시점에 설치용 데이터를 미리 만든다**
   - publish 시 레지스트리가 install용 메타데이터를 생성해두는 구조는 write 시점에 비용을 지불하고 read를 싸게 만드는 전형적인 read-heavy 시스템 설계다.

### 운영 관점

1. **unpublish 24시간 제한은 생태계 보호 장치다**
   - 한 패키지의 제거가 의존 그래프 전체를 무너뜨릴 수 있다는 점(left-pad 사태)에서, "삭제 대신 deprecate"라는 정책은 공유 인프라에서 파괴적 연산을 어떻게 다뤄야 하는지 보여준다. 사내 공유 라이브러리 운영에도 같은 원칙을 적용할 만하다.

2. **dist-tag는 배포 채널이다**
   - `latest`, `beta`, `next` 같은 태그는 사실상 릴리스 채널 역할을 한다. 버전 번호와 분리된 간접 참조(indirection) 레이어 하나로 카나리 배포·프리릴리스 채널을 구현한 것이 우아하다. 반대로, CI에서 `npm publish`가 자동으로 latest를 갱신한다는 점은 프리릴리스 배포 시 `--tag`를 빼먹으면 사고로 이어진다는 뜻이기도 하다.

3. **scoped 패키지의 %2F 인코딩**
   - 프록시나 방화벽이 URL 인코딩된 슬래시를 다르게 처리해서 scoped 패키지만 설치가 실패하는 문제의 원인을 이해할 수 있는 부분이다. 사내 레지스트리 미러 구축 시 주의할 지점.
