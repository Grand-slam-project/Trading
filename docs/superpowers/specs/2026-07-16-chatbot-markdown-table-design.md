# 설계 문서: 챗봇 텍스트 응답 마크다운 및 표 정규화 렌더링 도입

본 문서는 챗봇의 일반 텍스트 응답 내에 포함된 마크다운 형식(특히 표와 리스트)이 챗봇 패널 내에서 깨져서 노출되는 현상을 해결하기 위해 `react-markdown` 및 `remark-gfm` 라이브러리를 적용하고 정규화된 테이블 스타일을 입히는 설계 문서입니다.

---

## 1. 개요 및 배경

* **현상**: AI 챗봇이 보유 자산 현황이나 비교 리스트 등을 출력할 때 마크다운 표(`| 컬럼 | ... |`) 형식을 사용하여 답변을 생성합니다. 그러나 프론트엔드 단에서 일반 텍스트(`{message.text}`)로 렌더링함에 따라 표 문법이 해석되지 않고 날것의 문자열로 표시되어 가독성이 심각하게 저하되고 있습니다.
* **목표**: 
  * 마크다운 파서 및 GFM(GitHub Flavored Markdown) 플러그인을 도입하여 텍스트 내의 표, 리스트, 강조 등을 자동으로 HTML 태그로 정규화합니다.
  * 기존의 정형화된 전용 UI 표(`TradeHistoryResults`, `WatchlistResults` 등)는 변함없이 유지하며 오직 일반 대화 텍스트 렌더링 영역만 선택적으로 적용하여 리스크를 방어합니다.

---

## 2. 아키텍처 및 변경점

### 2.1 프론트엔드 라이브러리 추가
* **대상**: `frontend/package.json`
* **패키지**:
  * `react-markdown`: 마크다운 텍스트를 안전하게 React 엘리먼트로 변환합니다. (React 19 호환)
  * `remark-gfm`: GitHub 스타일의 표(Table), 취소선, 체크리스트, 다이렉트 링크 렌더링을 지원하는 플러그인입니다.

### 2.2 신규 컴포넌트 추가 (`ChatMarkdown`)
* **대상 파일**: [ChatbotWidget.jsx](file:///Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/frontend/src/features/chatbot/ChatbotWidget.jsx) 내에 신규 서브 컴포넌트로 생성 혹은 독립 선언
* **기능**:
  * `ReactMarkdown`과 `remarkGfm`을 조합하여 수신된 `message.text`를 파싱합니다.
  * `components` 속성을 정의하여 파싱된 태그(`table`, `thead`, `tbody`, `tr`, `th`, `td`, `ul`, `ol`, `li`, `strong`)를 테마 디자인에 어울리도록 Tailwind v4 스타일을 강제 적용합니다.

### 2.3 렌더링 분기 수정 (`ChatMessage` 컴포넌트)
* **대상 파일**: [ChatbotWidget.jsx](file:///Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/frontend/src/features/chatbot/ChatbotWidget.jsx#L199-L214)
* **변경 내용**: 삼항 연산자의 마지막 텍스트 출력 분기인 `message.text`를 `<ChatMarkdown messageText={message.text} />`로 대체합니다.

---

## 3. 상세 스타일 정의 (Tailwind v4 기반)

마크다운 변환 시 챗봇 테마와 통일성을 유지하기 위한 컴포넌트 매핑 스타일 가이드입니다.

```jsx
const markdownComponents = {
  // 1. 테이블 컨테이너 및 표 레이아웃
  table: ({ node, ...props }) => (
    <div className="my-2.5 overflow-x-auto rounded border border-slate-700/80">
      <table className="w-full min-w-full border-collapse text-left text-[11px]" {...props} />
    </div>
  ),
  thead: ({ node, ...props }) => (
    <thead className="bg-slate-900/80 text-[10px] uppercase tracking-[0.08em] text-slate-400" {...props} />
  ),
  tbody: ({ node, ...props }) => (
    <tbody className="divide-y divide-slate-800/80 bg-slate-950/20" {...props} />
  ),
  tr: ({ node, ...props }) => (
    <tr className="hover:bg-slate-800/20" {...props} />
  ),
  th: ({ node, ...props }) => (
    <th className="whitespace-nowrap px-2.5 py-2 font-bold border-r border-slate-850/80 last:border-r-0" {...props} />
  ),
  td: ({ node, ...props }) => (
    <td className="px-2.5 py-2 text-slate-200 border-r border-slate-850/80 last:border-r-0" {...props} />
  ),
  
  // 2. 텍스트 단락 및 목록
  p: ({ node, ...props }) => (
    <p className="mb-2 last:mb-0 leading-relaxed break-words whitespace-pre-wrap" {...props} />
  ),
  ul: ({ node, ...props }) => (
    <ul className="my-2 ml-4 list-disc space-y-1" {...props} />
  ),
  ol: ({ node, ...props }) => (
    <ol className="my-2 ml-4 list-decimal space-y-1" {...props} />
  ),
  li: ({ node, ...props }) => (
    <li className="text-[11px] text-slate-300" {...props} />
  ),
  
  // 3. 텍스트 강조 및 스타일
  strong: ({ node, ...props }) => (
    <strong className="font-bold text-cyan-300" {...props} />
  ),
  em: ({ node, ...props }) => (
    <em className="italic text-slate-300" {...props} />
  ),
};
```

---

## 4. 검증 및 체크리스트

### 4.1 의존성 및 컴파일 검증
- [ ] `npm install react-markdown remark-gfm` 실행 시 React 19와의 충돌 여부 확인 및 빌드 에러 부재 검증.
- [ ] 개발 서버 실행 및 브라우저 콘솔의 에러/경고 확인.

### 4.2 기능 및 화면 검증
- [ ] 일반 마크다운 표(`| 컬럼 |`) 입력 시 깔끔한 테이블 레이아웃으로 변환되는지 확인.
- [ ] 챗봇의 좁은 너비에서 컬럼 수가 많을 때 잘리지 않고 가로 스크롤(`overflow-x-auto`)이 정상적으로 작동하는지 확인.
- [ ] 리스트, 강조 등 다른 마크다운 문법도 정상 스타일링되는지 확인.
- [ ] 기존 정형화 컴포넌트(`TradeHistoryResults`, `WatchlistResults` 등)의 화면에 왜곡이나 영향이 없는지 확인.
