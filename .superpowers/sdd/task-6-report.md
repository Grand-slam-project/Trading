# Task 6 작업 보고서: 스케줄러 3분리 shadow 실행

## 1. 개요 및 요구사항 이행
- **목적**: 주식 자동화 학습 기동 시 단일 프리셋만 처리하던 기존 방식을 보완하여, 여러 shadow 프리셋을 순회하며 독립적으로 수집/학습을 수행하도록 개선하고, DART 피처 사전 빌드 등 전처리 단계(`pre_build_commands`)를 서브프로세스로 안전하게 실행하도록 지원합니다.
- **주요 변경 사항**:
  1. `backend/services/ml_scheduler.py`에 `get_stock_shadow_preset_keys() -> list[str]` 함수 구현:
     - 반환 값: `["kr-stock-v1-full", "us-stock-v1-full", "stock-v8-full"]` 순서
  2. `start_ml_automation_scheduler` 내의 주식 자동화 로직을 이 목록을 순회하는 루프로 전환.
  3. 각 프리셋별로 독립적으로 `try-except` 블록을 구성하여, 하나의 프리셋이 실패하더라도 다른 프리셋의 파이프라인 수행에 영향이 가지 않도록 안정성 확보.
  4. 각 프리셋의 `dataset` 설정에서 `raw_output` 파일명을 읽어 캔들 수집 CSV 경로를 동적으로 지정하고, `training` 설정의 `pre_build_commands`가 존재하면 `subprocess.run`을 사용해 순차 실행하도록 로직 통합.
  5. `tests/backend/test_ml_scheduler_presets.py` 테스트 케이스 생성 및 pytest 검증 진행.

## 2. TDD 진행 및 검증 내역

### 1단계: 실패하는 테스트 작성 (RED)
- `tests/backend/test_ml_scheduler_presets.py`에 `get_stock_shadow_preset_keys()`를 임포트하여 반환 리스트를 검증하는 테스트 코드를 선행 작성했습니다.
- **실패 확인 로그**:
  ```bash
  $ python3 -m pytest tests/backend/test_ml_scheduler_presets.py
  ...
  ImportError: cannot import name 'get_stock_shadow_preset_keys' from 'backend.services.ml_scheduler'
  ```
  - 선언이 없으므로 정상적으로 `ImportError`가 발생하는 실패 상태(RED)를 검증했습니다.

### 2단계: 코드 구현 및 테스트 통과 (GREEN)
- `backend/services/ml_scheduler.py` 파일에 해당 함수를 추가하고 주식 자동화 루프를 완성했습니다.
- **테스트 통과 로그**:
  ```bash
  $ python3 -m pytest tests/backend/ -v
  tests/backend/test_export_dart_features.py::test_normalize_stock_code_preserves_six_digit_symbols PASSED [ 12%]
  tests/backend/test_export_dart_features.py::test_build_daily_dart_features_uses_analysis_sentiment_and_category PASSED [ 25%]
  tests/backend/test_export_dart_features.py::test_build_daily_dart_features_skips_blank_rcept_no PASSED [ 37%]
  tests/backend/test_export_dart_features.py::test_build_shifted_dart_features_uses_only_prior_disclosures PASSED [ 50%]
  tests/backend/test_build_shifted_dart_features_carries_weekend_disclosure_to_next_feature_date PASSED [ 62%]
  tests/backend/test_ml_automation_presets.py::test_kr_stock_automation_preset_uses_kr_universe_and_dart_prebuild PASSED [ 75%]
  tests/backend/test_ml_automation_presets.py::test_us_stock_automation_preset_uses_us_universe_without_dart_prebuild PASSED [ 87%]
  tests/backend/test_ml_scheduler_presets.py::test_get_stock_shadow_preset_keys PASSED [100%]

  ============================== 8 passed in 2.13s ===============================
  ```

## 3. 관련 커밋 정보
- **커밋 ID**: `a6a517b`
- **커밋 메시지**: `feat: implement stock shadow presets loop and pre_build_commands in ml_scheduler`
