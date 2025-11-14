## Why Large Language Models Hallucinate

https://www.youtube.com/watch?v=cfqtFvWOfg0&list=PLOspHqNVtKAAsiohuZj1Bt4XpA3_bkS3c&index=4

https://cdn.openai.com/pdf/d04913be-3f6f-4d2b-b283-ff432ef4aaa5/why-language-models-hallucinate.pdf

Hallucinate: 문장, 맥락, 사실관계에 어긋나는 정보를 반환하는 것

llm이 결과를 도출하는 방식은 엔지니어에게도 블랙박스이므로 확실하지는 않다. Hallucination은 학습 시의 데이터 퀄리티에 영향을 받기도 하고, 불완전한 답을 반환하는 것이 더 큰 보상을 주기 때문이기도 하다.
때로는 입력의 맥락이 Hallucination을 일으키기도 하다. 한 스레드에서 대화 주제가 변하는 것을 예로 들 수 있다.

시스템에 명확한 지침을 주면 이런 현상을 조금은 완화할 수 있다.
적극적 완화 전략을 통해 온도를 조절하는 것도 하나의 방법이다.
멀티샷 프롬프팅이라는 방법도 프롬프트에 다양한 용례를 제공함으로서 정확도를 높이는 방법이 될 수 있다고 한다.