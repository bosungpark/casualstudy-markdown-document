# Code Execution with MCP - 토큰 98.7% 절감하는 차세대 에이전트 패턴

## 출처
- **아티클**: Code execution with MCP: Building more efficient AI agents
- **저자/출처**: Anthropic Engineering Blog
- **링크**: https://www.anthropic.com/engineering/code-execution-with-mcp

---

## AI 요약

### 1. 한 줄 요약

> **MCP 서버에 직접 도구를 호출하지 말고, MCP 서버를 "코드 API"로 노출해서 에이전트가 코드를 작성해 호출하게 하라.** 이렇게 하면 동일 작업의 토큰 소비가 **150,000 → 2,000 (98.7% 감소)**까지 줄어든다.

| 항목 | 내용 |
|------|------|
| **핵심 패턴** | 에이전트가 도구를 직접 호출하는 대신 코드를 작성해 실행 |
| **MCP의 역할** | 도구 호출 프로토콜 → "코드에서 import할 수 있는 API" |
| **토큰 절감** | 150k → 2k (98.7%) |
| **트레이드오프** | 샌드박싱·리소스 제한·모니터링 인프라 필요 |

---

### 2. 기존 MCP 도구 호출 방식의 두 가지 비효율

#### ① 도구 정의 오버로드
MCP 클라이언트가 **모든 도구 정의를 사전에 컨텍스트에 로드**한다.
- 도구마다 매개변수 설명, 반환 타입, 예시가 토큰을 소비
- 수천 개 도구가 연결되면 "**요청을 읽기도 전에 수십만 토큰을 처리**"

```
[Agent 시작]
   ↓
┌────────────────────────────────────────────┐
│ Context: ~200k tokens                      │
│  ├─ Tool 1 정의 (params, schema, examples) │
│  ├─ Tool 2 정의                            │
│  ├─ ...                                   │
│  └─ Tool N 정의 ← 사용자 요청 도달 전에 이미 가득 찬 상태 │
└────────────────────────────────────────────┘
```

#### ② 중간 결과의 추가 토큰 소비
도구 호출 결과가 **모두 모델 컨텍스트를 통과**한다.

**예시: 2시간 회의 녹취록을 Google Drive → Salesforce로 옮기기**

```
┌──────────────┐     ┌────────┐     ┌──────────────┐
│ Google Drive │ ──→ │ Model  │ ──→ │  Salesforce  │
│ (transcript) │     │context │     │              │
└──────────────┘     └────────┘     └──────────────┘
                          ↑
                  전체 녹취록이 두 번 흐름
                  → ~50,000 추가 토큰
```

녹취록 본문은 모델이 "보고 판단할" 필요가 없는 데이터인데도 굳이 컨텍스트를 두 번 통과한다.

---

### 3. Code Execution 접근법

MCP 서버를 **파일시스템 위의 코드 API로 노출**하고, 에이전트가 그 API를 import해서 코드를 작성한다.

#### 디렉터리 구조

```
servers/
├── google-drive/
│   ├── getDocument.ts
│   └── index.ts
├── salesforce/
│   ├── updateRecord.ts
│   └── index.ts
└── slack/
    ├── getChannelHistory.ts
    └── index.ts
```

#### 에이전트가 작성하는 코드 (전체 워크플로우 1번에)

```typescript
import * as gdrive from './servers/google-drive';
import * as salesforce from './servers/salesforce';

const transcript = (await gdrive.getDocument({
  documentId: 'abc123'
})).content;

await salesforce.updateRecord({
  objectType: 'SalesMeeting',
  recordId: '00Q5f000001abcXYZ',
  data: { Notes: transcript }
});
```

#### 토큰 비교

| 방식 | 토큰 |
|------|------|
| 전통적 도구 호출 | **150,000** |
| Code Execution    | **2,000**   |
| **절감율** | **98.7%** |

핵심은 **녹취록 본문이 모델 컨텍스트를 통과하지 않는다는 점**이다. 데이터는 실행 환경 안에서 직접 흐르고, 모델은 "어떻게 흘릴지"를 코드로 기술할 뿐이다.

---

### 4. 5가지 핵심 이점

#### ① Progressive Disclosure (점진적 도구 공개)

> "모델은 파일시스템 탐색에 뛰어나다. 도구를 파일로 제시하면 모두 미리 읽지 않고 **필요한 정의만 읽는다.**"

```
[Agent]
  ├─ ls servers/             ← 사용 가능한 서버 목록
  ├─ cat servers/gdrive/index.ts  ← 필요한 것만 읽기
  └─ search_tools("salesforce")   ← 검색으로 찾기
```

#### ② Context-Efficient Tool Results (맥락 효율적 결과 처리)

10,000행 스프레드시트를 가져와 5건만 보고 싶을 때:

```typescript
const allRows = await gdrive.getSheet({ sheetId: 'abc123' });
const pendingOrders = allRows.filter(row =>
  row["Status"] === 'pending'
);
console.log(pendingOrders.slice(0, 5));  // 5행만 컨텍스트로
```

```
┌────────────────────┐
│  10,000 rows       │ → 실행 환경
└────────────────────┘
         ↓ filter + slice
┌────────────────────┐
│  5 rows only       │ → 모델 컨텍스트
└────────────────────┘
```

#### ③ More Powerful Control Flow (강력한 제어 흐름)

폴링·재시도·조건 분기를 **코드 한 번에**:

```typescript
let found = false;
while (!found) {
  const messages = await slack.getChannelHistory({ channel: 'C123456' });
  found = messages.some(m => m.text.includes('deployment complete'));
  if (!found) await new Promise(r => setTimeout(r, 5000));
}
```

기존 방식이라면 매 폴링마다 모델이 호출되어 "다시 호출해" 결정을 내려야 한다. 코드로 작성하면 **모델은 이 루프를 한 번 설계하고 끝난다.**

#### ④ Privacy-Preserving Operations (개인정보 보호)

중간 결과가 **실행 환경에만 머무르고 모델에 들어가지 않는다.**

```
[Google Sheets]                 [Salesforce]
  ├─ email, phone               ├─ email, phone
  ├─ name             ──────→   ├─ name
  └─ address                    └─ address
        ↑                              ↑
        └─── 실제 PII는 여기로만 흐름 ─────┘

           [Model context]
           email: [EMAIL_1]   ← 토큰화된 placeholder만
           phone: [PHONE_1]
           name:  [NAME_1]
```

MCP 클라이언트가 PII를 자동으로 `[EMAIL_1]` 같은 placeholder로 치환하면, **모델은 구조만 보고 결정을 내리고 실제 값은 만지지 않는다.**

#### ⑤ State Persistence & Skill Development (상태 유지 및 스킬 축적)

중간 결과 저장:
```typescript
await fs.writeFile('./workspace/leads.csv', csvData);
```

재사용 가능한 함수로 진화:
```typescript
export async function saveSheetAsCsv(sheetId: string) {
  const data = await gdrive.getSheet({ sheetId });
  const csv = data.map(row => row.join(',')).join('\n');
  await fs.writeFile(`./workspace/sheet-${sheetId}.csv`, csv);
}
```

> "에이전트가 작동하는 코드를 저장하여 **미래 사용을 위한 재사용 가능한 함수**로 만들 수 있다."

이는 사실상 에이전트가 **자기 자신의 표준 라이브러리를 키워가는 것**이다.

---

### 5. 트레이드오프와 한계

| 항목 | 직접 호출 | Code Execution |
|------|----------|----------------|
| 토큰 효율 | ❌ 낮음 | ✅ 매우 높음 |
| 복잡한 워크플로우 | ❌ 호출 체인 길어짐 | ✅ 코드로 자연스럽게 |
| 인프라 단순성 | ✅ 단순 | ❌ 샌드박스·리소스 제한·모니터링 필요 |
| 보안 표면적 | ✅ 작음 | ❌ 임의 코드 실행 위험 |
| 디버깅 | ✅ 호출 단위 추적 쉬움 | ❌ 실행 로그 별도 관측 필요 |

> "코드 실행은 자체 복잡성을 도입한다. 에이전트가 생성한 코드를 실행하려면 **적절한 샌드박싱, 리소스 제한, 모니터링이 있는 보안 실행 환경**이 필요하다."

**언제 Code Execution을 선택할까?**
- 도구가 많고(수십~수백 개) 워크플로우가 복잡할 때
- 대용량 데이터를 다루며 모델이 모두 볼 필요는 없을 때
- PII·기밀 데이터를 모델에 노출하지 않아야 할 때
- 반복·조건 분기가 많은 작업일 때

**Code Execution이 과한 경우:**
- 단순한 1~2회 도구 호출
- 샌드박스 인프라가 없는 초기 PoC
- 결과 데이터 자체가 LLM 추론 입력인 경우

---

### 6. 결론 (원문 요지)

> "MCP는 에이전트가 많은 도구와 시스템에 연결하기 위한 **기초 프로토콜**을 제공하지만, 너무 많은 서버가 연결되면 도구 정의와 결과가 과도한 토큰을 소비하여 에이전트 효율성을 떨어뜨린다. Code execution은 이러한 확립된 **소프트웨어 엔지니어링 패턴을 에이전트에 적용**하여, 익숙한 프로그래밍 구조로 MCP 서버와 상호작용할 수 있도록 한다."

---

## 내가 얻은 인사이트
