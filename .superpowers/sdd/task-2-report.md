# Task 2 보고서

- 작업명: DART 공시 피처 export 스크립트
- 수행 범위: `backend/scripts/export_dart_features.py`, `tests/backend/test_export_dart_features.py`
- 구현 내용:
  - `normalize_stock_code()`로 6자리 국내 종목코드 정규화를 추가했습니다.
  - `build_daily_dart_features()`로 공시와 AI 분석 결과를 일별/종목별 base DART 피처로 집계했습니다.
  - `build_shifted_dart_features()`로 당일 공시는 제외하고 과거 공시만 3일, 7일, 20일 rolling 피처에 반영하도록 구현했습니다.
  - CLI는 승인된 보정안대로 `--dates-source-path`를 사용하며 기본값은 `ml/data/raw/kr_stock_candles.csv`입니다.
- 테스트:
  - `python3 -m pytest tests/backend/test_export_dart_features.py -v`
  - 결과: 3 passed
- TDD Evidence:
  - RED: 이전 구현 에이전트가 테스트 파일을 먼저 작성했고, 당시 구현 모듈이 없어 import 단계에서 실패하는 구조였습니다.
  - GREEN: 구현 파일 추가 후 `python3 -m pytest tests/backend/test_export_dart_features.py -v`가 3개 모두 통과했습니다.
- 비고:
  - Supabase 네트워크 호출은 CLI 함수에만 두었고 테스트에서는 호출하지 않습니다.

## 2026-07-07 must-fix 반영

- 수정 범위:
  - `backend/scripts/export_dart_features.py`
  - `tests/backend/test_export_dart_features.py`
- 원인 분석:
  - 기존 `build_shifted_dart_features()`는 `feature_dates` 축에서만 shift + rolling을 계산해 비거래일 공시가 다음 거래일 피처 창에 편입되지 않았습니다.
- 수정 내용:
  - 심볼별로 `feature_dates`와 `daily_features` 날짜의 합집합 타임라인을 구성한 뒤, 그 축에서 same-day 제외 shift와 rolling 합계를 계산하고 최종 결과만 원래 `feature_dates`로 필터링하도록 변경했습니다.
  - `build_daily_dart_features()`에서 조인 키인 `rcept_no`가 비어 있는 공시 행은 집계에서 제외하도록 보정했습니다.
  - 주말 공시가 다음 feature date의 3d/7d/20d 창에 반영되는 회귀 테스트와 공백 `rcept_no` 스킵 테스트를 추가했습니다.
- 검증:
  - `python3 -m pytest tests/backend/test_export_dart_features.py -v`
  - 결과: `5 passed`
