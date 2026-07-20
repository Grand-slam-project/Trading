# 바이낸스 현물 ↔ 선물 내부 이체(USDT) 기능 구현 계획서

본 계획서는 바이낸스 현물(Spot) 지갑과 USD-M 선물(Futures) 지갑 간의 USDT 자금 이체(Universal Transfer) 기능을 연동하고 사용자 UI를 구축하는 구현 계획을 서술합니다.

## Global Constraints (전역 제약 조건)
1. **한국어 설명 규칙**: 모든 설명, 계획서, 마크다운 문서는 한국어로만 작성합니다. (코드 및 코드 내 주석은 영문 표준을 따릅니다.)
2. **에러 처리 표준화**: 바이낸스 API 오류 발생 시 예외 원시 문자열을 그대로 노출하지 않고, `format_error_payload`를 사용해 표준 에러 구조(`message`, `error.title`, `error.action` 등)로 프론트엔드에 응답합니다.
3. **인증 보안**: 사용자 API Key를 로드할 때 반드시 평문이 아닌 복호화 서비스를 경유합니다 (`_load_exchange_client` 사용).
4. **TDD 준수**: 백엔드 코드 수정 시 반드시 검증용 테스트 코드를 작성하거나 수정한 뒤 성공 여부를 검증합니다.

---

## Tasks

### Task 3: 바이낸스 내부 이체 API 클라이언트 연동
- **설명**: `backend/services/binance_client.py`의 `BinanceSpotClient` 클래스에 내부 이체를 지원하는 `transfer_internal` 메서드를 추가합니다.
- **요구사항**:
  - 바이낸스 Universal Transfer API `POST /sapi/v1/asset/transfer`를 호출하도록 연동합니다.
  - 파라미터: `type` (이체 방향: `MAIN_UMFUTURE` 또는 `UMFUTURE_MAIN`), `asset` (기본값 `"USDT"`), `amount` (이체 수량)
  - `type`이 유효한 방향인지, `amount`가 0보다 큰지 검증합니다.
  - 서명된 요청을 만들기 위해 기존 `self._signed_request` 헬퍼 메서드를 사용합니다.
  - 성공 시 `{"transaction_id": str(tranId), "raw": response_json}` 형태로 결과를 구조화하여 반환합니다.
- **테스트**:
  - `tests/test_binance_client.py` 또는 모의(mock) 테스트 환경을 구성하여 `transfer_internal` 기능의 동작(API 호출 및 반환 형식)을 테스트합니다.

### Task 4: 바이낸스 내부 이체 라우트 추가 및 통합
- **설명**: `backend/routes/transfer.py`에 바이낸스 내부 이체 API 엔드포인트를 구현합니다.
- **요구사항**:
  - 엔드포인트: `POST /api/transfer/binance/internal`
  - 요청 본문: `{ "direction": "MAIN_UMFUTURE" | "UMFUTURE_MAIN", "amount": 10.5 }`
  - Authorization 헤더로부터 `user_id`를 검출하고, 실거래 API Key를 복구해 클라이언트를 로드합니다.
  - `amount`에 대해 0보다 큰 부동 소수점 값인지 확인하는 유효성 검사를 진행합니다.
  - `BinanceSpotClient.transfer_internal`을 사용해 이체를 실행합니다.
  - 성공 시 `{ "success": true, "message": "바이낸스 내부 이체 성공", "data": { "transaction_id": "..." } }`를 반환합니다.
  - 예외 발생 시 `format_error_payload`를 사용해 에러 구조를 포맷팅하고 HTTP 400 또는 500 응답을 반환합니다.
- **테스트**:
  - Flask Test Client를 사용하거나 API 수동 테스트 스크립트를 사용해 `/api/transfer/binance/internal` 호출 테스트를 수행합니다.

### Task 5: 프론트엔드 PC 자산 탭 UI 연동
- **설명**: PC 버전의 자산 보유 현황 페이지([AssetsTab.jsx](file:///Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/frontend/src/pages/AssetsTab.jsx))에 내부 이체 모달 및 버튼을 추가합니다.
- **요구사항**:
  - "계좌별 자산 요약" 섹션의 바이낸스 현물/선물 카드 영역 근처에 `[바이낸스 내부 이체]` 버튼을 추가합니다.
  - 버튼 클릭 시 `BinanceInternalTransferModal` 모달이 표시되도록 구현합니다.
  - 모달 UI에는 다음을 포함합니다:
    - 이체 방향 선택 (현물 ➡️ 선물, 선물 ➡️ 현물)
    - 출발 지갑의 USDT 잔고(사용 가능 금액) 표시
    - 이체 수량 입력 필드 및 `[최대]` 입력 버튼
    - 최종 승인 경고 문구 및 체크박스
    - "이체 실행" 버튼 및 로딩/메시지 상태 표시
  - 이체 성공 시 모달을 닫고, 전체 자산을 새로고침하는 함수를 호출하여 화면의 잔고가 즉시 갱신되도록 합니다.

### Task 6: 프론트엔드 모바일 자산 탭 UI 연동
- **설명**: 모바일 버전의 자산 보유 현황 페이지([MobileAssetsTab.jsx](file:///Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/frontend/src/pages/mobile/MobileAssetsTab.jsx))에 내부 이체 모달 및 버튼을 동일하게 추가합니다.
- **요구사항**:
  - 모바일 자산 요약 카드 아래에 내부 이체 버튼을 배치합니다.
  - PC 버전과 동일한 모달 제어 상태 및 API 연동 로직을 구성합니다.
  - 테일윈드를 이용해 모바일 터치 환경에 잘 맞도록 스타일링합니다.
