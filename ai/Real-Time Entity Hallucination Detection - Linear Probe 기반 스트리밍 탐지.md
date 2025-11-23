# Real-Time Entity Hallucination Detection - Linear Probe 기반 스트리밍 탐지

## 출처
- **링크**: https://arxiv.org/abs/2509.03531

---

## AI 요약

**Real-Time Entity Hallucination Detection**은 LLM 장문 생성에서 **엔티티 레벨 환각**(이름, 날짜, 인용 등 날조)을 **토큰별로 실시간 탐지**하는 방법입니다. **Claude 4 Sonnet + 웹 검색**으로 자동 라벨링한 데이터셋으로 **linear probe**를 훈련하며, Llama-3.3-70B에서 **AUC 0.90 (LoRA probe)** 달성, Semantic Entropy (0.71 AUC) 대비 **19%p 향상**. **단일 forward pass**로 작동해 **외부 검증 없이 스트리밍 탐지** 가능합니다.

**핵심**: 엔티티 중심 라벨링 → 토큰 단위 학습 → 생성 중 실시간 플래그

**기존 방법의 한계**

장문 생성 환각 탐지는 기존에 **SAFE**(Wei et al., 2024b), **FactScore**(Min et al., 2023) 같은 **외부 검증 파이프라인**에 의존했습니다. 작동 방식: (1) 생성된 텍스트에서 atomic claim 추출 → (2) 각 claim마다 외부 증거 검색 → (3) LLM으로 claim 검증. 문제: **계산 비용과 지연이 막대**해서 실시간 탐지 불가능. 예를 들어 한 문장이 수십 개 claim으로 분해되고, 각각에 여러 검색 쿼리와 LLM API 호출 필요.

**Semantic Entropy 같은 불확실성 기반 방법**도 한계가 있습니다. 10회 샘플링 + NLI 클러스터링으로 **10x 계산 비용**, 장문에서는 **AUC 0.71**로 성능 저하. **SelfCheckGPT**도 5-10회 생성 필요.

**기존 probe 연구**(Marks & Tegmark 2024, Orgad et al. 2025)는 **short-form QA에 집중**, 장문 일반화 미검증. **CH-Wang et al. (2024)**은 span-level probe를 사용하지만 **입력 컨텍스트 불일치 탐지**(예: 문서 요약 시 원본과 다른 내용)에 초점을 맞춰, **세계 지식 대비 사실 오류**를 탐지하는 본 연구와는 목표가 다릅니다.

**본 연구의 접근**

**엔티티 레벨 환각**에 집중합니다. Claim-level이 아닌 **entity-level**(이름, 날짜, 인용 등)로 타깃을 좁히면 (1) **토큰 경계가 명확**해서 실시간 탐지 가능, (2) **잘못된 claim은 보통 날조된 엔티티를 포함**하므로 효과적.

**자동 라벨링 파이프라인**: Claude 4 Sonnet + 웹 검색으로 엔티티 추출 & 검증. 각 엔티티를 "Supported", "Not Supported", "Insufficient Information"로 라벨링. 토큰은 포함된 엔티티의 라벨을 상속.

```python
# 라벨링 프롬프트 (간소화)
"""
For each entity:
1. Extract minimal text span (just the entity)
2. Use web search to verify
3. Label as:
   - "Supported": Verified as correct
   - "Not Supported": Fabricated or incorrect
   - "Insufficient Information": Cannot verify

Return JSON:
[
  {
    "text": "Sarah Chen",
    "label": "Supported",
    "verification_note": "..."
  }
]
"""
```

**LongFact++** 데이터셋 구축: LongFact의 10배 크기, 다양한 도메인 (의료, 법률, 전기, 인용 중심 쿼리) 포함. 22,000개 프롬프트 풀에서 각 모델이 샘플링 (Llama-3.1-8B: 8,000개, Llama-3.3-70B: 8,000개).

**Linear Probe 훈련**

```python
class HallucinationProbe:
    def __init__(self, model, layer=0.95):
        self.model = model
        self.layer = int(0.95 * model.num_layers)  # 95% 레이어
        self.probe_head = nn.Linear(hidden_dim, 1)  # Linear probe
        self.lora = None  # Optional: LoRA adapters
    
    def forward(self, input_ids):
        outputs = self.model(input_ids, output_hidden_states=True)
        h = outputs.hidden_states[self.layer]  # (batch, seq_len, hidden_dim)
        
        # Token-level hallucination probability
        p = torch.sigmoid(self.probe_head(h))  # (batch, seq_len, 1)
        return p.squeeze(-1)
```

**Probe loss: Token-wise + Span-max**

문제: 라벨링된 span이 실제 오류보다 긴 경우가 많음. 예: "born in 2002"에서 "02"만 틀렸는데 전체 span이 hallucinated로 라벨링.

해결책: **Span-max loss** (Tillman & Mossing 2025, Sharma et al. 2025)

```python
# Loss function
loss_probe = (1 - ω) * token_wise_BCE + ω * span_max_BCE

# Token-wise: 모든 토큰에 대해 BCE
token_wise_BCE = Σ w_i * BCE(y_i, p_i)  # w_i는 entity 토큰에 가중치 10

# Span-max: 각 span의 최대 확률에 대해 BCE
span_max_BCE = Σ BCE(y_s, max(p_i for i in span s))

# ω는 0→1로 annealing: 초반엔 dense gradient, 후반엔 sharp focus
```

**LoRA Probe with KL Regularization**

Linear probe만으로는 한계가 있어 **LoRA probe** 추가: 모든 레이어에 LoRA adapter 삽입 + probe head.

문제: LoRA 훈련 시 **모델 출력 분포가 바뀜** → 생성 품질 저하 위험.

해결책: **KL regularization**

```python
# Total loss
loss_total = (1 - λ_reg) * loss_probe + λ_reg * loss_KL

# KL divergence: 원본 모델과 LoRA 모델 간 분포 차이 최소화
loss_KL = (1/T) * Σ D_KL(π_LoRA(·|q,t) || π_original(·|q,t))

# λ_reg = 0.5 추천: AUC 0.8898, KL div 0.0046, Win rate 52.8%
```

**KL regularization vs LM regularization**: LM loss는 차선책. KL이 **직접적으로 분포 변화를 제어**하며 smooth Pareto frontier 형성. LM은 overfitting 위험.

**성능 벤치마크**

**Long-form (LongFact, HealthBench)**

| 방법 | Llama-3.1-8B AUC | R@0.1 | Llama-3.3-70B AUC | R@0.1 |
|------|------------------|-------|-------------------|-------|
| Perplexity | 0.76 | 0.36 | 0.71 | 0.30 |
| Entropy | 0.74 | 0.29 | 0.71 | 0.30 |
| **Semantic Entropy** | 0.72 | 0.27 | **0.71** | 0.39 |
| **Linear probe** | **0.85** | **0.59** | **0.87** | **0.65** |
| **LoRA probe** | **0.89** | **0.68** | **0.90** | **0.72** |

**Short-form (TriviaQA)**: LoRA probe 0.98 AUC (Llama-3.3-70B)

**Math (MATH)**: Linear probe 0.86 AUC (Llama-3.3-70B) - **엔티티 없는 reasoning task에도 일반화**

**핵심 인사이트**: LoRA probe가 **19%p AUC 향상** (0.71 → 0.90), **R@0.1은 0.39 → 0.72로 85% 향상**

**일반화 실험**

**Long-form → Short-form**: Long-form 훈련 probe가 short-form에서도 잘 작동 (AUC 차이 <0.05). 역은 안 됨: Short-form 훈련은 long-form에서 0.10 AUC 하락. **결론**: Long-form 데이터 필수.

**Cross-model 일반화**: 한 모델에서 훈련한 probe가 다른 모델 출력에서도 작동 (off-diagonal AUC 차이 0.02-0.04). **모델 간 전이 가능** → 범용 환각 탐지기.

**Scaling effects**: (1) 큰 모델에서 훈련한 probe가 더 강력 (row-wise), (2) 모든 probe가 작은 모델 출력을 더 잘 탐지 (column-wise) - 큰 모델이 아는 사실을 작은 probe가 검증 못할 수 있음.

**Selective Answering**

실시간 탐지를 활용한 **선택적 응답**: 토큰별 probe 점수를 모니터링하다가 threshold 초과 시 생성 중단 & "I don't know" 응답.

**SimpleQA 결과 (Llama-3.3-70B)**:
- No intervention: Conditional accuracy 27.9%, Attempt rate 76.1%
- Selective answering (t=0.5): Conditional accuracy **50.4%**, Attempt rate **19.1%**

**Trade-off**: 정확도 ↑, 시도율 ↓. 고위험 환경 (의료, 법률)에서 유용.

**Label Quality 검증**

**Human agreement**: 50개 샘플에서 84% 일치

**Controlled hallucination injection**: Wikipedia 문서를 LLM으로 paraphrase한 뒤 의도적으로 오류 주입 (904개). 결과:
- Recall: 80.6% (729/904 탐지)
- False positive rate: 15.8% (정상 엔티티를 오탐)

**보수적 라벨링**: Over-flagging 경향. 이는 loss function의 span-max + entity 가중치로 완화 (missed hallucination에 대한 페널티 감소).

**Black-box Self-Evaluation**

"모델에게 직접 물어보기" 실험: 생성 후 "Does this sentence contain hallucination?" 질문.

결과: Short-form (TriviaQA)에서는 어느 정도 작동 (0.81-0.89 AUC), **Long-form에서는 실패** (0.58-0.68 AUC). Supervised fine-tuning도 미미한 개선만.

**결론**: 장문에서는 self-evaluation 불가능 → Internal representations 필요.

**실전 배포 고려사항**

**Probe 위치**: Layer 0.95 (final layer 직전) - 정보가 충분히 응축된 위치.

**KL regularization 필수**: λ_KL=0.5로 **Win rate 52.8% 유지** (원본 대비 높음), MMLU 71.2% (원본 70.9%), KL div 0.0046 (거의 0).

**Anecdotal evidence**: LoRA 훈련 후 모델이 더 조심스러워짐.

예시 1 (Rugby referee 질문):
- Baseline: "Chris Busby" (틀림, 확신)
- LoRA: "Christopher Lincoln or 'Lincoln' but I cannot confirm this, a more reliable source would be needed." (여전히 틀림, but **불확실성 인정**)

예시 2 (Anagram):
- Baseline: "Lynyrd Skynyrd" (틀림, 확신)
- LoRA: "I couldn't find any information" (**거부**)

예시 3 (Medical advice):
- Baseline: "lithium is generally considered compatible with breastfeeding" (**위험한 과장**)
- LoRA: "lithium and valproate are generally used with caution in breastfeeding" (**적절한 주의**)

**한계**

1. **라벨 노이즈**: 80.6% recall, 15.8% FPR → 성능 상한 제약
2. **실용성 부족**: R@0.1 ~0.7 → 10% FPR에서 30% 환각 놓침. Selective answering은 50% 정확한 답변 희생.
3. **엔티티 중심 제약**: Reasoning 오류는 미탐지 가능 (단, MATH에서 의외로 잘 작동 → broader signal 학습 가능성)
4. **Context hallucination 미지원**: 제공된 source material과의 불일치는 탐지 안 함 (CH-Wang et al. 2024와 대조)

**구현 예시**

```python
# Production deployment
class RealTimeHallucinationMonitor:
    def __init__(self, model, probe_threshold=0.5):
        self.model = model
        self.probe = LoRAProbe(model, lambda_KL=0.5)
        self.threshold = probe_threshold
    
    def generate_with_monitoring(self, prompt, max_len=512):
        tokens = []
        for i in range(max_len):
            # Forward pass with probe
            outputs = self.model(prompt + tokens, return_hidden=True)
            next_token = outputs.token
            
            # Probe score for this token
            h = outputs.hidden_states[-2]  # Layer 0.95
            score = self.probe(h[-1])  # Last token
            
            if score > self.threshold:
                # High hallucination risk → abstain
                return tokens + ["[I don't know]"]
            
            tokens.append(next_token)
            if next_token == EOS:
                break
        
        return tokens
```

**Comparison with Semantic Entropy**

| 특징 | Linear/LoRA Probe | Semantic Entropy |
|------|-------------------|------------------|
| **샘플링** | 단일 forward pass | 10회 생성 |
| **속도** | 실시간 | 10x 느림 |
| **AUC (long-form)** | 0.90 | 0.71 |
| **Model access** | Hidden states 필요 | Sampling만 |
| **Training** | 필요 | Zero-shot |
| **Cross-model** | 전이 가능 | N/A |

**선택 기준**:
- **실시간 요구** → Probe
- **정확도 최우선 + 느려도 됨** → Semantic Entropy
- **White-box 불가능** → Semantic Entropy (black-box 가능)
- **고위험 환경** → Probe (fast screening) + SE (double-check)

**Dataset 기여**

**공개 데이터셋**: LongFact++, 라벨링된 완료 (all models), cross-model 재사용 가능 → [https://github.com/obalcells/hallucination_probes](https://github.com/obalcells/hallucination_probes)

**Annotation pipeline**: Claude 4 Sonnet + web search → 재현 가능한 자동 라벨링. 다른 도메인/언어로 확장 가능.

---

## 내가 얻은 인사이트

- 다른 프로브 관련 접근법과 마찬가지로 환각 날 때의 뇌파 패턴은 유사하므로 일반화가 가능하다는 이야기인거 같음
- 한 번의 forward pass + 실시간 성이라는 것이 장점이고 토큰보다는 엔티티 단위로 세밀하게 보아도 대부분의 케이스를 커버한다는 내용이 말하고자하는 차별점인 거 같음