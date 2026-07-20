# 챗봇 텍스트 응답 마크다운 및 표 정규화 구현 계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 챗봇의 일반 텍스트 응답에서 마크다운 표 및 목록을 정규화하여 가독성을 높입니다.

**Architecture:** 프론트엔드에 `react-markdown`과 `remark-gfm` 패키지를 추가하고, 커스텀 스타일 컴포넌트 `ChatMarkdown`을 구현하여 `ChatbotWidget`의 일반 텍스트 응답 부위를 대체합니다.

**Tech Stack:** React 19, Tailwind CSS v4, Vite, react-markdown, remark-gfm

## Global Constraints

- 모든 설명과 계획서는 반드시 한국어로 작성함.
- package.json 라이브러리 버전 확인 및 React 19와 호환되도록 구성.
- 호출부-선언부 동기화 및 Dead Code 방지.

---

### Task 1: 마크다운 렌더링 의존성 패키지 설치

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `react-markdown`, `remark-gfm` 패키지 의존성 제공

- [ ] **Step 1: 패키지 설치 명령 실행**
  
  Run (in `frontend` directory):
  ```bash
  npm install react-markdown remark-gfm
  ```

- [ ] **Step 2: 패키지 추가 검증 및 빌드 확인**
  
  Run (in `frontend` directory):
  ```bash
  npm run build
  ```
  Expected: 빌드가 에러 없이 `dist/` 폴더 생성을 성공하는지 확인.

- [ ] **Step 3: 커밋**
  
  Run:
  ```bash
  git add frontend/package.json frontend/package-lock.json
  git commit -m "build: install react-markdown and remark-gfm dependencies"
  ```

---

### Task 2: ChatMarkdown 컴포넌트 생성 및 ChatMessage 연동

**Files:**
- Create: `frontend/src/features/chatbot/ChatMarkdown.jsx`
- Modify: `frontend/src/features/chatbot/ChatbotWidget.jsx`

**Interfaces:**
- Consumes: `react-markdown`, `remark-gfm` 패키지
- Produces: `ChatMarkdown` 컴포넌트가 `messageText` 프로퍼티를 받아 정규화된 마크다운 HTML을 반환.

- [ ] **Step 1: ChatMarkdown 컴포넌트 구현**
  
  새 파일 `frontend/src/features/chatbot/ChatMarkdown.jsx`를 생성하고 다음 코드를 작성합니다.
  
  ```jsx
  import ReactMarkdown from 'react-markdown'
  import remarkGfm from 'remark-gfm'

  export default function ChatMarkdown({ messageText }) {
    if (!messageText) return null

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        className="markdown-content whitespace-pre-wrap break-words text-xs leading-5 text-slate-100"
        components={{
          table: ({ node, ...props }) => (
            <div className="my-2 overflow-x-auto rounded border border-slate-700/80">
              <table className="w-full min-w-full border-collapse text-left text-[11px]" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-slate-900/80 text-[10px] uppercase tracking-[0.08em] text-slate-400" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody className="divide-y divide-slate-800/80 bg-slate-950/20" {...props} />
          ),
          tr: ({ node, ...props }) => <tr className="hover:bg-slate-800/20" {...props} />,
          th: ({ node, ...props }) => (
            <th className="whitespace-nowrap px-2.5 py-2 font-bold border-r border-slate-800/80 last:border-r-0" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="px-2.5 py-2 text-slate-200 border-r border-slate-800/80 last:border-r-0" {...props} />
          ),
          p: ({ node, ...props }) => <p className="mb-2 last:mb-0 leading-relaxed" {...props} />,
          ul: ({ node, ...props }) => <ul className="my-2 ml-4 list-disc space-y-1" {...props} />,
          ol: ({ node, ...props }) => <ol className="my-2 ml-4 list-decimal space-y-1" {...props} />,
          li: ({ node, ...props }) => <li className="text-[11px] text-slate-300" {...props} />,
          strong: ({ node, ...props }) => <strong className="font-bold text-cyan-300" {...props} />,
          em: ({ node, ...props }) => <em className="italic text-slate-300" {...props} />,
        }}
      >
        {messageText}
      </ReactMarkdown>
    )
  }
  ```

- [ ] **Step 2: ChatbotWidget.jsx에 ChatMarkdown 적용**
  
  `frontend/src/features/chatbot/ChatbotWidget.jsx` 파일 상단에 `ChatMarkdown` 임포트를 추가하고, `ChatMessage` 컴포넌트의 일반 텍스트 렌더링 부분을 대체합니다.
  
  임포트 추가:
  ```jsx
  import ChatMarkdown from './ChatMarkdown.jsx'
  ```
  
  렌더링 교체 (라인 209-214 부근):
  ```jsx
  // AS-IS:
              ) : hasTradeHistoryTable && !message.isStreaming ? (
                <TradeHistoryResults presentation={tradeHistoryPresentation} />
              ) : hasWatchlistTable && !message.isStreaming ? (
                <WatchlistResults presentation={watchlistPresentation} />
              ) : message.text}

  // TO-BE:
              ) : hasTradeHistoryTable && !message.isStreaming ? (
                <TradeHistoryResults presentation={tradeHistoryPresentation} />
              ) : hasWatchlistTable && !message.isStreaming ? (
                <WatchlistResults presentation={watchlistPresentation} />
              ) : (
                <ChatMarkdown messageText={message.text} />
              )}
  ```

- [ ] **Step 3: 수동 검증 및 빌드 확인**
  
  로컬 Vite 개발 서버를 구동하여 챗봇에서 마크다운 형식의 응답(예: 보유현황 표)을 입력받아 가로 스크롤 표 및 리스트 스타일이 어두운 테마에 맞춰 정상적으로 보이는지 수동 확인합니다.
  
  Run (in `frontend` directory):
  ```bash
  npm run build
  ```
  Expected: 빌드가 에러 없이 컴파일되는지 확인.

- [ ] **Step 4: 커밋**
  
  Run:
  ```bash
  git add frontend/src/features/chatbot/ChatMarkdown.jsx frontend/src/features/chatbot/ChatbotWidget.jsx
  git commit -m "feat: integrate ChatMarkdown to ChatbotWidget for parsing markdown tables"
  ```
