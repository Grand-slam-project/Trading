# Task 3 작업 보고서

## 작업 개요
- `ml/src/build_features.py`에 선택 피처 경로 해석 helper를 추가했습니다.
- `apply_optional_features()`가 `optional_features.news_features_path`, `optional_features.crypto_market_features_path`, `optional_features.stock_event_features_path`를 설정 기반으로 읽도록 수정했습니다.
- `optional_features.dart_features_path`가 설정된 경우에만 국내주식용 DART 컬럼을 병합하도록 추가했습니다.
- `build_features()`의 선택 피처 보정 목록에 DART 컬럼 기본값 목록을 포함해 후속 파이프라인에서 결측으로 깨지지 않게 맞췄습니다.

## TDD 진행 기록
1. `tests/ml/test_build_features_optional_paths.py` 추가
   - 설정된 `dart_features_path`가 있을 때 DART 컬럼이 병합되는지 검증
   - 경로가 없을 때 DART 컬럼이 생기지 않는지 검증
2. 실패 확인
   - 첫 테스트가 `KeyError: 'dart_disclosure_count_3d'`로 실패
3. 최소 구현
   - 선택 피처 경로 해석 helper 추가
   - `STOCK` 자산군에서만 DART 병합 분기 추가
4. 재검증
   - 집중 테스트 2건 모두 통과

## 실행한 테스트
```bash
python3 -m pytest tests/ml/test_build_features_optional_paths.py -v
```

## 결과
- 선택 경로 기반 optional feature source 해석 동작 확인
- `dart_features_path` 미설정 시 DART 컬럼 비생성 확인
- 설정 시 DART 컬럼 병합 확인

## 우려 사항
- 현재 Task 3 범위에서는 설정 파일을 건드리지 않았습니다. 따라서 해외주식/코인 preset에 DART 피처가 실제로 연결되지는 않으며, preset 분리는 Task 4에서 최종 검증이 필요합니다.

## 2026-07-07 Task 3 must-fix 후속 조치

### 반영한 수정
- `ml/src/build_features.py`에 `DART_FEATURE_COLUMNS` 상수를 추가해 DART 컬럼 목록을 단일 정의로 통합했습니다.
- `optional_features.dart_features_path`가 없는 설정에서는 DART 병합, forward fill, 기본 zero-fill 어느 경로에서도 DART 컬럼이 생성되지 않도록 제한했습니다.
- DART 사용 허용 조건을 보수적으로 강화했습니다. `asset_type == "STOCK"` 이고 `dart_features_path`가 있으며, `model.version` 또는 `data.raw_candles_path` / `data.features_path` 중 하나에 `kr_stock` 표식이 있는 설정만 허용합니다.
- 위 조건을 만족하지 않는 미국주식 유사 설정이 DART를 사용하려고 하면 한국어 `ValueError`를 발생시키도록 가드를 추가했습니다.

### 추가한 회귀 테스트
- `build_features()` 경유 비-DART 설정에서 최종 결과에 DART 컬럼이 생기지 않는지 검증했습니다.
- `dart_features_path`가 있는 US-stock 유사 설정이 예외를 발생시키는지 검증했습니다.

### 검증
```bash
python3 -m pytest tests/ml/test_build_features_optional_paths.py -v
```

- 결과: 4 passed

## 2026-07-07 Task 3 KR 가드 오탐 후속 조치

### 반영한 수정
- `is_kr_stock_dart_config()`가 `market_scope`, `data.market_scope`, `model.market_scope`, `market_country`의 명시적 KR 신호를 우선 허용하도록 보정했습니다.
- 명시적 US/OVERSEAS/GLOBAL 신호나 `us_stock`, `overseas_stock` 경로/버전 표식은 계속 차단합니다.
- `kr_stock` 문자열이 없는 기존 국내주식 유사 config도 `market_scope: KR`이면 DART를 사용할 수 있도록 회귀 테스트를 추가했습니다.

### 검증
```bash
python3 -m pytest tests/ml/test_build_features_optional_paths.py -v
```

- 결과: 5 passed
