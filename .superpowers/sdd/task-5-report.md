# Task 5 작업 보고서: 자동화 Preset과 Full-Run 출력 분리

## 1. 개요 및 요구사항 이행
- **목적**: 국내 주식(`kr-stock-v1-full`) 및 해외 주식(`us-stock-v1-full`) 프리셋을 분리하여 각각 DART 피처 생성 등 환경에 특화된 동작을 지원할 수 있도록 구현합니다.
- **주요 내용**:
  1. `kr-stock-v1-full` 프리셋: `stock_kr_core_45` 유니버스와 `kr_stock_candles.csv` 출력을 사용하고, 훈련 직전 `backend/scripts/export_dart_features.py`를 실행하는 `pre_build_commands` 지원.
  2. `us-stock-v1-full` 프리셋: `stock_us_core_45` 유니버스와 `us_stock_candles.csv` 출력을 사용하며 DART 피처 생성 사전 빌드가 포함되지 않음.
  3. `backend/routes/ml.py`의 full-run API에서 `dataset` 설정에 따라 캔들 저장 파일명(`raw_output`)을 동적 적용하도록 수정.
  4. full-run API 실행 중 훈련 파이프라인 구동 전에 `pre_build_commands` 설정이 있다면 이를 순차적으로 서브프로세스로 실행 및 오류 처리 기능 추가.

## 2. 변경 파일 및 상세 내역
- [ml_automation_service.py](file:///Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/backend/services/ml_automation_service.py):
  - `kr-stock-v1-full` 프리셋 정보 등록
  - `us-stock-v1-full` 프리셋 정보 등록
- [ml.py](file:///Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/backend/routes/ml.py):
  - `subprocess`, `sys` 모듈 임포트 추가
  - `run_ml_full_pipeline_job`의 `TOSS` / `STOCK` 분기에서 `raw_output` 파라미터를 읽어 저장할 CSV 파일명을 동적으로 처리하도록 수정
  - `run_ml_pipeline` 호출 전 프리셋의 `training` 설정 내 `pre_build_commands` 리스트에 정의된 각 명령어를 `subprocess.run`으로 실행하고 실패 시 `RuntimeError` 처리하도록 로직 적용
- [test_ml_automation_presets.py](file:///Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/tests/backend/test_ml_automation_presets.py):
  - 프리셋 키 `kr-stock-v1-full` 및 `us-stock-v1-full`이 올바른 정보로 파싱 및 반환되는지 확인하는 TDD 테스트 케이스 2건 구현

## 3. TDD 수행 및 검증 내역
1. **실패하는 테스트 작성** (`tests/backend/test_ml_automation_presets.py`)
   - `resolve_automation_preset("kr-stock-v1-full")` 호출 시 등록되지 않아 `ValueError`가 발생하는 것 확인.
2. **코드 구현 및 테스트 통과**
   - 프리셋 추가 및 프리셋 로딩 로직 검증 성공.
   - 백엔드 전체 테스트 통과 내역:
     ```bash
     $ python3 -m pytest tests/backend/ -v
     tests/backend/test_export_dart_features.py::test_normalize_stock_code_preserves_six_digit_symbols PASSED
     tests/backend/test_export_dart_features.py::test_build_daily_dart_features_uses_analysis_sentiment_and_category PASSED
     tests/backend/test_export_dart_features.py::test_build_daily_dart_features_skips_blank_rcept_no PASSED
     tests/backend/test_export_dart_features.py::test_build_shifted_dart_features_uses_only_prior_disclosures PASSED
     tests/backend/test_export_dart_features.py::test_build_shifted_dart_features_carries_weekend_disclosure_to_next_feature_date PASSED
     tests/backend/test_ml_automation_presets.py::test_kr_stock_automation_preset_uses_kr_universe_and_dart_prebuild PASSED
     tests/backend/test_ml_automation_presets.py::test_us_stock_automation_preset_uses_us_universe_without_dart_prebuild PASSED
     ============================== 7 passed in 0.79s ===============================
     ```

## 4. 커밋 정보
- **커밋 ID**: `c55c393`
- **메시지**: `feat: add split stock automation presets`
