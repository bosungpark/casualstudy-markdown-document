# Hidden Technical Debt in Machine Learning Systems

## 출처
- **논문**: Hidden Technical Debt in Machine Learning Systems
- **저자**: D. Sculley, Gary Holt, Daniel Golovin, Eugene Davydov, Todd Phillips, Dietmar Ebner, Vinay Chaudhary, Michael Young, Jean-François Crespo, Dan Dennison (Google)
- **게재**: NIPS 2015 (Advances in Neural Information Processing Systems 28)
- **원문**: https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html

---

## AI 요약

### 핵심 주장: ML의 빠른 성공은 공짜가 아니다

**일반적 인식**:
```
"ML로 빠르게 예측 시스템 구축!"
"며칠 만에 프로토타입 완성!"
"정확도 95% 달성!"
→ Quick Win
```

**현실**:
```
초기 구축: 1주
유지보수: 수년간 엄청난 비용
→ Technical Debt (기술 부채) 폭발
```

**비유**:
```
신용카드로 빠르게 구매 (ML 프로토타입)
↓
매달 이자 지불 (유지보수 비용)
↓
원금보다 이자가 더 많아짐 (Technical Debt)
```

### Technical Debt란?

**전통적 소프트웨어 공학**:
```
나쁜 코드 작성 (빨리 만들려고)
→ 나중에 리팩토링 필요
→ 기술 부채 누적
```

**ML에서는**:
```
코드 부채 + ML 특유의 부채
→ "Hidden" Technical Debt
→ 보이지 않다가 갑자기 폭발
```

### ML System의 구조: Only a Small Fraction is ML Code

**실제 ML 시스템**:
```
┌─────────────────────────────────────────┐
│         Configuration (설정)             │
├─────────────────────────────────────────┤
│      Data Collection (데이터 수집)        │
├─────────────────────────────────────────┤
│    Data Verification (데이터 검증)        │
├─────────────────────────────────────────┤
│  Feature Extraction (특징 추출)          │
├──────────────┬──────────────────────────┤
│              │                          │
│   Process    │    ML Code (매우 작음!)   │
│  Management  │                          │
│              │                          │
├──────────────┴──────────────────────────┤
│       Analysis Tools (분석 도구)          │
├─────────────────────────────────────────┤
│   Machine Resource Mgmt (리소스 관리)     │
├─────────────────────────────────────────┤
│      Serving Infrastructure (서빙)       │
├─────────────────────────────────────────┤
│         Monitoring (모니터링)             │
└─────────────────────────────────────────┘
```

**핵심**: ML 코드는 전체의 **5% 미만**!

### ML-Specific Risk Factors (ML 특유 위험 요소)

#### 1. Entanglement (얽힘)

**CACE Principle**: Changing Anything Changes Everything

**예시**:
```python
# 모델 A: 광고 클릭 예측
model_A = train(features_A, label_clicks)

# 모델 B: 구매 예측
model_B = train(features_B, label_purchases)

# features_A와 features_B가 공유하는 특징이 있으면
# 모델 A 변경 → 모델 B 성능 영향!
```

**실제 사례**:
```
Feature "user_age" 범위 변경 (0-100 → 0-150)
→ 모델 A: 클릭 예측 정확도 유지
→ 모델 B: 구매 예측 정확도 5% 하락!
→ 모델 C: 추천 시스템 완전히 망가짐
```

**왜 이런가?**
```
ML 모델 = 전체 입력 공간에 민감
하나의 특징 변경 → 전체 학습 파라미터 변화
→ Hyperparameter도 재조정 필요
→ 다른 모델에 cascading 효과
```

#### 2. Hidden Feedback Loops (숨겨진 피드백 루프)

**Direct Feedback**:
```
추천 시스템:
모델 예측 → 사용자에게 노출 → 사용자 클릭
→ 클릭 데이터가 다시 학습 데이터로
→ 모델이 자신의 예측을 강화
→ "부자는 더 부자 되고" 현상
```

**예시**:
```
Day 1: 모델이 "고양이 영상" 추천
      → 사용자 클릭 (50%)
Day 2: 클릭 데이터로 재학습
      → "고양이 영상" 더 많이 추천
Day 3: 사용자는 고양이만 보게 됨
      → "개 영상"은 영원히 추천 안 됨
→ Filter Bubble
```

**Hidden Feedback**:
```
모델 A가 모델 B의 입력에 영향

예시:
검색 순위 모델 A → 검색 결과 순서 변경
→ 사용자 클릭 패턴 변경
→ 광고 클릭 예측 모델 B의 학습 데이터 변경
→ 모델 B 성능 변화
→ 모델 A도 영향받음 (순환 의존)
```

#### 3. Undeclared Consumers (선언되지 않은 소비자)

**문제**:
```
모델 A의 출력을 다른 팀이 몰래 사용

예시:
팀 A: "사용자 임베딩" 모델 개발
      → embedding.pkl 파일 저장

팀 B: embedding.pkl 읽어서 추천 시스템에 사용
      (팀 A에게 알리지 않음)

팀 A: 임베딩 차원 512 → 256으로 변경
      → 팀 B 시스템 완전히 망가짐!
      → 팀 A는 모름
```

**실제 사례 (Google)**:
```
하나의 모델 출력을 50개 이상의 시스템이 사용
→ 모델 변경 시 누가 영향받는지 알 수 없음
→ "Visibility Debt" (가시성 부채)
```

#### 4. Data Dependencies (데이터 의존성)

**코드 의존성보다 더 위험**:

**Unstable Data Dependencies**:
```python
# 외부 시스템의 데이터에 의존
user_features = fetch_from_external_api()

# 외부 시스템 변경 (팀 A 모름)
# 예: "age" 필드 삭제
→ 모델 학습 실패!
```

**Underutilized Dependencies**:
```
100개 특징 사용
→ 실제로 유용한 것: 10개
→ 나머지 90개: 성능 향상 미미
→ 하지만 유지보수 비용은 100개 분
→ "Legacy Features" (레거시 특징)
```

**예시**:
```
초기: 5개 특징으로 시작
매달: 2-3개 특징 추가 (성능 0.1% 향상)
1년 후: 30개 특징
→ 각 특징의 파이프라인 유지보수 필요
→ 제거하면 어떤 영향? 모름
→ 그냥 유지 (부채 누적)
```

#### 5. Configuration Debt (설정 부채)

**ML 시스템의 설정**:
```
모델 하이퍼파라미터:
- learning_rate: 0.001
- batch_size: 32
- epochs: 100
- dropout: 0.5

데이터 파이프라인:
- 특징 선택
- 정규화 방법
- 샘플링 비율

모델 서빙:
- 버전 관리
- A/B 테스트 비율
- 롤백 정책
```

**문제**:
```python
# config.py (수백 줄)
LEARNING_RATE = 0.001  # 왜 0.001? 누가 설정? 언제?
HIDDEN_UNITS = 128     # 왜 128? 64는 안 되나?
DROPOUT = 0.5          # 실험 결과? 아니면 추측?

# 주석 없음, 버전 관리 없음
# 변경 이력 추적 불가
→ Configuration Debt
```

**실제 사례**:
```
Google: config 파일이 수천 줄
→ 어떤 설정이 실제로 사용되는지 모름
→ 실험 중 임시로 추가한 설정이 그대로 남음
→ 제거하면 위험 (영향 모름)
```

#### 6. Changes in External World (외부 세계 변화)

**Fixed Threshold Problem**:
```python
# 스팸 분류
if score > 0.5:
    label = "spam"

# 6개월 후: 스팸 패턴 변화
# 새로운 스팸: score = 0.45 (경계선)
# Threshold 0.5는 이제 낡음
→ 재조정 필요
```

**Monitoring Debt**:
```
모델 성능 모니터링:
- 정확도: 95% 유지 ✓

하지만:
- 데이터 분포 변화 감지: 없음
- 특징 중요도 변화 감지: 없음
- 외부 시스템 변화 감지: 없음
→ "Silent Failure" (조용한 실패)
```

**예시**:
```
COVID-19 발생:
기존 모델: 2019년 데이터로 학습
→ 사용자 행동 패턴 완전히 변화
→ 모델 정확도 유지 (표면상)
→ 실제로는 완전히 틀린 예측
→ 모니터링 없어서 모름
```

### System-Level Anti-Patterns (시스템 레벨 안티패턴)

#### 1. Glue Code (접착 코드)

**문제**:
```python
# 범용 ML 패키지 사용
from sklearn import RandomForestClassifier

# 우리 데이터 형식으로 변환 (Glue Code)
def convert_our_data_to_sklearn_format(data):
    # 100줄의 변환 코드
    ...

# 학습
model = RandomForestClassifier()
model.fit(convert_our_data_to_sklearn_format(train_data))

# 예측 시에도 변환 필요
predictions = model.predict(convert_our_data_to_sklearn_format(test_data))
```

**부채**:
```
Glue Code > 실제 ML 코드
→ 유지보수 비용 증가
→ 버그 가능성 증가
→ 성능 저하 (변환 오버헤드)
```

#### 2. Pipeline Jungles (파이프라인 정글)

**진화 과정**:
```
Version 1: data → preprocess → model
Version 2: data → preprocess → feature_eng → model
Version 3: data → preprocess_v2 → feature_eng → model
Version 4: data → preprocess_v2 → feature_eng → extra_features → model

# preprocess_v1 제거 못함 (누가 쓰는지 모름)
# extra_features 필요한지 모름
→ Pipeline Jungle
```

**실제 사례**:
```
Google:
데이터 준비 파이프라인 수십 개
→ 어떤 것이 실제로 사용되는지 모름
→ 중복 코드 많음
→ 유지보수 불가능
→ 처음부터 다시 작성 (Big Bang Rewrite)
```

#### 3. Dead Experimental Codepaths (죽은 실험 코드)

**문제**:
```python
# main.py
if use_experimental_feature:  # 항상 False
    # 500줄의 실험 코드
    ...
else:
    # 실제 사용 코드
    ...

# 실험 끝났지만 코드는 남음
# 제거하면 위험할 것 같아서 그냥 둠
→ Dead Code Debt
```

### Mitigation Strategies (완화 전략)

#### 1. Test in Production (프로덕션 테스트)

**Progressive Rollouts**:
```
1% 트래픽 → 새 모델 테스트
→ 문제 없으면 5% → 10% → 50% → 100%
→ 문제 발생 시 즉시 롤백
```

**A/B Testing**:
```
그룹 A: 기존 모델 (50% 사용자)
그룹 B: 새 모델 (50% 사용자)
→ 비즈니스 메트릭 비교
→ 승자 선택
```

#### 2. Versioning (버저닝)

**모델 버전 관리**:
```
model_v1.pkl (2024-01-01)
model_v2.pkl (2024-02-01)
model_v3.pkl (2024-03-01)

# 각 버전:
# - 학습 데이터
# - 하이퍼파라미터
# - 성능 메트릭
# - 배포 이력
→ 추적 가능
```

#### 3. Reproducibility (재현 가능성)

**요구사항**:
```
동일한 데이터 + 동일한 코드 + 동일한 설정
= 동일한 모델

필요:
- 데이터 버전 관리
- 코드 버전 관리
- 설정 버전 관리
- 랜덤 시드 고정
```

#### 4. Monitoring (모니터링)

**메트릭 종류**:
```
1. 성능 메트릭:
   - 정확도, F1 Score, AUC

2. 데이터 메트릭:
   - 특징 분포 변화
   - 결측값 비율
   - 이상치 탐지

3. 시스템 메트릭:
   - 레이턴시
   - 처리량
   - 에러율

4. 비즈니스 메트릭:
   - 매출
   - 사용자 만족도
   - 전환율
```

### Google의 실제 교훈

**사례 1: Prediction Bias Detection**
```
문제: 모델이 특정 그룹에 편향
해결: Calibration plot으로 시각화
     → 편향 발견 → 재학습
```

**사례 2: Continuous Training**
```
문제: 모델 성능이 시간에 따라 하락
해결: 매일 자동 재학습
     → Fresh 데이터로 업데이트
```

**사례 3: Feature Engineering Debt**
```
문제: 특징이 수백 개로 증가
해결: Feature Importance 분석
     → 하위 50% 특징 제거
     → 성능 유지, 복잡도 감소
```

---

## 내가 얻은 인사이트

ML의 특징에 따라 약간의 차이가 있을 뿐, 전통적 소프트웨어에서 기피되는 행동은 ML에서도 환영받지 못하는 것 같다.