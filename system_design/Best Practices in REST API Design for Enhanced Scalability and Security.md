# Best Practices in REST API Design for Enhanced Scalability and Security

## Source
- **논문/아티클**: [Best Practices in REST API Design for Enhanced Scalability and Security](https://urfjournals.org/open-access/best-practices-in-rest-api-design-for-enhanced-scalability-and-security.pdf)
- **발행처**: URF Journals

## AI Summary

### 1. 리소스 모델링 & 엔드포인트 규칙
- **명확한 리소스**: 복수형 명명(`GET /users`, `POST /users`), 하위 리소스(`GET /users/{id}/posts`).
- **일관된 URI**: 동사 대신 명사 중심, 상태 변화를 HTTP 메서드로 표현.
- **페이징/정렬/필터링**: `?page=1&limit=50&sort=-created_at&status=active` 표준화.
- **관계 표현**: 하이퍼미디어/HATEOAS 링크 또는 `rel` 필드로 관계 노출.
	 - 예시(HATEOAS 링크):
		 ```json
		 {
			 "id": "user_123",
			 "name": "Alice",
			 "links": [
				 { "rel": "self", "href": "/v1/users/user_123" },
				 { "rel": "update", "href": "/v1/users/user_123" },
				 { "rel": "delete", "href": "/v1/users/user_123" },
				 { "rel": "posts", "href": "/v1/users/user_123/posts" },
				 { "rel": "organization", "href": "/v1/orgs/org_77" }
			 ]
		 }
		 ```
	 - 예시(컬렉션 응답 내 관계 링크):
		 ```json
		 {
			 "data": [
				 {
					 "id": "post_9",
					 "title": "Hello",
					 "links": [
						 { "rel": "self", "href": "/v1/posts/post_9" },
						 { "rel": "author", "href": "/v1/users/user_123" },
						 { "rel": "comments", "href": "/v1/posts/post_9/comments" }
					 ]
				 }
			 ],
			 "links": [
				 { "rel": "self", "href": "/v1/users/user_123/posts?cursor=abc&limit=20" },
				 { "rel": "next", "href": "/v1/users/user_123/posts?cursor=def&limit=20" }
			 ]
		 }
		 ```
	 - 예시(rel 필드로 간단 관계 표현):
		 ```json
		 {
			 "id": "order_555",
			 "user_id": "user_123",
			 "rel": {
				 "user": { "type": "belongs_to", "id": "user_123" },
				 "items": { "type": "has_many", "ids": ["item_1", "item_2"] },
				 "payment": { "type": "has_one", "id": "pay_777" }
			 }
		 }
		 ```
	 - 예시(JSON:API 스타일):
		 ```json
		 {
			 "data": {
				 "type": "posts",
				 "id": "post_9",
				 "attributes": { "title": "Hello" },
				 "relationships": {
					 "author": {
						 "links": { "related": "/v1/posts/post_9/author" },
						 "data": { "type": "users", "id": "user_123" }
					 },
					 "comments": {
						 "links": { "related": "/v1/posts/post_9/comments" }
					 }
				 }
			 }
		 }
		 ```

### 2. 버저닝 전략
- **URI 버전**: `/v1/`, `/v2/`로 명확히 구분(브레이킹 변경 시).
- **헤더 버전**: `Accept: application/vnd.company.resource+json; version=2`로 세분화.
- **호환성 유지**: 필드 추가는 브레이킹 변경 아님, 제거/타입 변경은 새 버전.
 - **Deprecated 관리**: 응답 헤더에 `Deprecation`/`Sunset` 노출, 문서에 제거 일정 명시.

### 3. 표준 HTTP 메서드 & 상태코드
- **메서드**: `GET` 조회, `POST` 생성, `PUT` 전치 업데이트, `PATCH` 부분 업데이트, `DELETE` 삭제.
- **상태코드**: `200/201/202/204`, 클라이언트 오류 `400/401/403/404/409/422`, 서버 오류 `500/502/503/504`.
- **에러 바디**: `code`, `message`, `details`, `trace_id` 포함한 일관 포맷.
 - **에러 예시**:
	 ```json
	 {
		 "code": "VALIDATION_ERROR",
		 "message": "field 'email' must be a valid address",
		 "details": [{"field": "email", "issue": "format"}],
		 "trace_id": "01HXYZ..."
	 }
	 ```

### 4. 인증/인가 & 보안
- **인증**: OAuth2/OIDC(Authorization Code + PKCE), 서비스-투-서비스는 Client Credentials.
- **인가**: RBAC/ABAC 정책, 리소스 수준 스코프(`scope: orders:read`).
- **TLS 강제**: HTTPS-only, HSTS, 안전한 쿠키(`Secure`, `HttpOnly`, `SameSite`).
- **입력 검증**: 스키마 기반(JSON Schema), 서버측 검증 우선.
- **비밀 관리**: 헤더 토큰, 키 회전, 비밀은 절대 쿼리스트링 금지.
 - **보안 헤더**: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.
 - **PII 최소화**: 로그에서 PII 제거/마스킹, 데이터 보존 기간 명시.

### 5. 성능 & 확장성
- **캐싱**: `ETag`/`Last-Modified`, `Cache-Control`(CDN 친화), 조건부 요청(`If-None-Match`).
- **압축**: `gzip/br`, 큰 응답 스트리밍.
- **페이지네이션**: 커서 기반(`?cursor=...&limit=...`)로 대규모 컬렉션 처리.
- **레이트 리밋**: `429 Too Many Requests`, 헤더(`X-RateLimit-*`)로 한도 노출.
- **배치/비동기**: 배치 엔드포인트, 장시간 작업은 `202 Accepted` + 작업 리소스(`GET /jobs/{id}`).
 - **캐시 예시**:
	 - 응답 헤더: `ETag: "W/\"users-12345\""`, `Cache-Control: public, max-age=60`.
	 - 조건부 GET: `If-None-Match: "W/\"users-12345\""` → `304 Not Modified`.

### 6. 일관된 스키마 & 문서화
- **OpenAPI/Swagger**: 스키마 우선 설계, SDK 자동 생성.
- **스키마 진화**: 필드 추가는 허용, 제거는 새 버전. `additionalProperties: false`로 엄격성 제어.
- **예제 제공**: 요청/응답 샘플, 에러 케이스 포함.
 - **OpenAPI 스니펫**:
	 ```yaml
	 paths:
		 /v1/users:
			 get:
				 parameters:
					 - in: query
						 name: cursor
						 schema: { type: string }
					 - in: query
						 name: limit
						 schema: { type: integer, minimum: 1, maximum: 100 }
				 responses:
					 '200':
						 headers:
							 X-RateLimit-Remaining:
								 schema: { type: integer }
						 content:
							 application/json:
								 schema:
									 type: object
									 properties:
										 data:
											 type: array
											 items: { $ref: "#/components/schemas/User" }
										 next_cursor:
											 type: string
	 ```

### 7. 관측성 & 트레이싱
- **리퀘스트 ID**: `trace_id`/`span_id` 헤더 전파(W3C Trace-Context).
- **감사로그**: 민감 리소스에 변경 추적, PII 최소 저장.
- **메트릭**: p50/p95/p99 지연, 오류율, 리밋 히트율.
 - **헤더 표준화**: `traceparent`, `tracestate` 수용, 서버가 없으면 생성하여 반환.

### 8. 안정성 & 탄력성
- **리트라이 정책**: 멱등성 키로 안전 리트라이(`Idempotency-Key`), 지수 백오프 + Jitter.
- **서킷브레이커/타임아웃**: 다운스트림 보호, 슬로우 소비자 방지.
- **Partial Failure 처리**: 배치 응답에 per-item 상태와 에러.
 - **멱등성 예시**:
	 - 요청 헤더: `Idempotency-Key: 8f1b...`
	 - 서버: 키+요청 바디 해시로 결과 캐싱 → 중복 POST 보호.
