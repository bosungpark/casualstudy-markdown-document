# Model Cards for Model Reporting

## 출처
- **논문**: Model Cards for Model Reporting
- **저자**: Margaret Mitchell, Simone Wu, Andrew Zaldivar, Parker Barnes, Lucy Vasserman, Ben Hutchinson, Elena Spitzer, Inioluwa Deborah Raji, Timnit Gebru (Google)
- **게재**: FAT* 2019 (Conference on Fairness, Accountability, and Transparency)
- **원문**: https://arxiv.org/abs/1810.03993

---

## AI 요약

### 핵심 주장: 모델에 "영양 성분표" 붙이자

**문제**:
```
ML 모델 배포 시:
"정확도 95%입니다!"
→ 어떤 데이터로 측정?
→ 어떤 그룹에서 95%?
→ 어디서 쓰면 안 됨?
→ 모름!
```

**제안**:
```
식품 영양 성분표처럼
모델에도 "Model Card" 첨부
→ 성능, 한계, 의도된 용도 명시
```

## Model Card란?

**짧은 문서 (1-2페이지)**:

```markdown
# Toxicity Detection Model v1.2

## Intended Use
- 목적: 온라인 댓글 유해성 탐지
- 사용 가능: 커뮤니티 모더레이션
- 사용 금지: 법적 판단, 고용 결정

## Performance
- 전체 정확도: 92%
- 그룹별 성능:
  * 백인: 94%
  * 흑인: 87% (편향 존재)
  * 아시아인: 91%

## Limitations
- 온라인 댓글로만 학습
- 문맥 이해 부족 (반어법 오탐)
- 새로운 은어 탐지 못 함

## Data
- 학습 데이터: Wikipedia Talk, 2015-2017
- 크기: 200만 댓글
- 언어: 영어만
```

## 핵심 구성 요소

### 1. Model Details (모델 상세)

```markdown
- 모델 타입: BERT-base
- 버전: v1.2 (2024-01-15)
- 개발자: Google Research
- 라이선스: Apache 2.0
- 연락처: model-cards@google.com
```

### 2. Intended Use (의도된 용도)

**Primary Use Cases**:
```
✓ 온라인 댓글 필터링
✓ 유해 콘텐츠 사전 검열
✓ 커뮤니티 가이드라인 자동 체크
```

**Out-of-Scope Uses**:
```
✗ 법정 증거
✗ 채용 심사
✗ 의료 진단
✗ 영어 외 언어
```

### 3. Factors (영향 요인)

**Demographic Factors**:
```
- 인종/민족
- 성별
- 연령
- 지리적 위치
- 소득 수준
```

**Relevant Factors**:
```
독성 탐지 모델:
- 문화적 맥락 (욕설 기준 다름)
- 시간대 (온라인 활동 패턴)
- 플랫폼 (Reddit vs Twitter 차이)
```

### 4. Metrics (평가 지표)

**단순 정확도만으로 부족**:

```
전체 정확도: 92%

하지만:
- False Positive (오탐): 8%
  → 정상 댓글을 유해로 잘못 판단
  
- False Negative (미탐): 12%
  → 유해 댓글을 정상으로 놓침
  
- 그룹별 차이:
  흑인 영어(AAVE): 오탐률 15%
  표준 영어: 오탐률 5%
  → 편향 존재!
```

### 5. Evaluation Data (평가 데이터)

```markdown
## Training Data
- 출처: Wikipedia Talk Pages
- 기간: 2015-2017
- 크기: 200만 댓글
- 레이블: 크라우드소싱 (10명 이상 합의)

## Test Data
- 출처: 동일 (시간 분리)
- 크기: 20만 댓글
- 분포: 유해 10%, 정상 90%

## Known Biases
- Wikipedia 편집자 = 주로 백인 남성
- 특정 주제 과다 대표 (기술, 역사)
- 구어체/은어 부족
```

### 6. Quantitative Analyses (정량 분석)

**교차 그룹 분석**:

| 그룹 | 정확도 | FPR | FNR |
|------|--------|-----|-----|
| 전체 | 92% | 8% | 12% |
| 남성 | 93% | 7% | 10% |
| 여성 | 90% | 10% | 15% |
| 백인 | 94% | 6% | 9% |
| 흑인 | 87% | 15% | 18% |
| LGBTQ+ | 85% | 18% | 20% |

**해석**:
```
LGBTQ+ 관련 댓글:
→ 오탐률 18% (정상을 유해로)
→ 이유: 학습 데이터에 LGBTQ+ 용어가
        "공격적"으로 레이블됨
→ 사용 금지: LGBTQ+ 커뮤니티
```

### 7. Ethical Considerations (윤리 고려사항)

```markdown
## Known Limitations
- 문맥 이해 부족 (풍자/반어법 오탐)
- 은어/신조어 탐지 실패
- 다국어 미지원

## Potential Harms
- 표현의 자유 억압 (과도한 검열)
- 특정 집단에 대한 차별적 적용
- 오탐으로 인한 부당한 계정 정지

## Mitigation Strategies
- 인간 리뷰 필수 (자동 처벌 금지)
- 정기적 재학습 (새로운 표현 반영)
- 그룹별 성능 모니터링
```

### 8. Caveats and Recommendations (주의사항)

```markdown
## When to Use
- 1차 필터링 (최종 결정 아님)
- 대량 데이터 사전 검토
- 인간 모더레이터 보조 도구

## When NOT to Use
- 단독 판단 기준
- 법적 결정
- 실시간 자동 차단
- 영어 외 언어

## Updates
- 분기별 재학습 권장
- 새로운 은어/표현 반영
- 편향 지표 재평가
```

## 실제 예시: Google의 두 Model Cards

### 1. Smiling Detection Model

**의도된 용도**:
```
✓ 사진 자동 정리 (웃는 얼굴 태그)
✓ 카메라 앱 셔터 타이밍
✗ 감정 분석
✗ 고용 결정
```

**성능 (Fitzpatrick Skin Type별)**:
```
Type I-II (밝은 피부): 95%
Type III-IV (중간 피부): 92%
Type V-VI (어두운 피부): 84%

→ 편향 존재! 어두운 피부에서 성능 하락
```

**권장사항**:
```
- 피부색 다양한 데이터로 재학습 필요
- 의료/보안 용도 금지
- 사용자 피드백 수집
```

### 2. Toxicity Detection Model

**False Positive 분석**:
```
"I'm a gay man and proud!"
→ "gay" 단어로 인해 독성으로 오탐

"Black lives matter"
→ "Black" 단어로 인해 독성으로 오탐

→ 특정 그룹 표현이 부당하게 검열됨
```

**완화 전략**:
```
- Identity 용어 화이트리스트
- 문맥 기반 재학습
- 커뮤니티별 맞춤 임계값
```

## Model Cards의 효과

**투명성 증가**:
```
배포 전: "이 모델 어디서 쓸 수 있나요?" → 모름
배포 후: Model Card 읽고 → 명확히 판단
```

**책임감 강화**:
```
개발자: "모든 성능 지표 공개해야 함"
→ 편향 발견 → 개선 동기
```

**오용 방지**:
```
사용자: "고용 심사에 쓸까?"
Model Card: "Out-of-Scope" 명시
→ 오용 방지
```

**신뢰 구축**:
```
명확한 한계 공개
→ 사용자가 정보에 기반한 결정
→ 신뢰 증가
```

## 현실적 한계

**1. 작성 비용**:
```
모델 개발: 1개월
Model Card 작성: 1주
→ 개발자 부담
```

**2. 업데이트 필요**:
```
모델 재학습마다 Card도 업데이트
→ 유지보수 비용
```

**3. 표준화 부재**:
```
팀마다 다른 형식
→ 비교 어려움
```

## 권장 사항

**최소 포함 항목**:
```markdown
1. Model Details (버전, 날짜)
2. Intended Use (✓/✗)
3. Performance (전체 + 그룹별)
4. Limitations (명확히)
5. Data (출처, 크기, 편향)
```

**작성 프로세스**:
```
1. 개발 초기부터 작성 시작
2. 평가 때마다 업데이트
3. 다양한 이해관계자 검토
4. 배포 전 최종 확인
```

---

## 내가 얻은 인사이트

문서화를 잘하자! 구글도 ML도 예외아님.