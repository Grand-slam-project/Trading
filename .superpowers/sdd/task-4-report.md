# Task 4: 국내/해외 주식 모델 config 추가 결과 보고서

## 1. 작업 개요
- 국내/해외 주식 모델의 학습 환경을 독립적으로 구성하기 위해 기존 `lgbm_stock_v11.yaml` 및 `lgbm_stock_risk_v11.yaml` 설정을 기반으로 분할된 4개의 YAML 설정 파일을 신규 구축하였습니다.
- 한국 주식(KR)의 경우 DART 공시 피처 21개를 `model.feature_columns`에 추가 적용하고 `optional_features.dart_features_path` 경로를 지정하였습니다.
- 미국 주식(US)의 경우 DART 피처를 제외하고 설정 파일을 구성하였습니다.

## 2. 신규 생성 파일
- `ml/configs/lgbm_kr_stock_v1.yaml`: 한국 주식 시그널 예측 설정 (DART 피처 21개 포함)
- `ml/configs/lgbm_kr_stock_risk_v1.yaml`: 한국 주식 리스크 예측 설정 (DART 피처 21개 포함)
- `ml/configs/lgbm_us_stock_v1.yaml`: 미국 주식 시그널 예측 설정 (DART 피처 제외)
- `ml/configs/lgbm_us_stock_risk_v1.yaml`: 미국 주식 리스크 예측 설정 (DART 피처 제외)
- `tests/ml/test_split_stock_configs.py`: 분할된 설정의 정합성 검증 유닛 테스트

## 3. 유닛 테스트 결과 (TDD 수행 내역)
TDD 절차에 의거하여, 구현 완료 전 실패하는 유닛 테스트의 예외(FileNotFoundError)를 먼저 확인한 후, config 설정을 생성하여 통과시켰습니다.

### 3.1. 초기 테스트 실패 확인 (레코드)
```text
tests/ml/test_split_stock_configs.py::test_kr_stock_config_uses_separate_paths_and_dart_features FAILED
tests/ml/test_split_stock_configs.py::test_us_stock_config_uses_separate_paths_and_excludes_dart_features FAILED

E       FileNotFoundError: [Errno 2] No such file or directory: '.../ml/configs/lgbm_kr_stock_v1.yaml'
```

### 3.2. 최종 테스트 통과 확인 (레코드)
```text
platform darwin -- Python 3.13.5, pytest-8.3.4, pluggy-1.5.0
collected 2 items

tests/ml/test_split_stock_configs.py::test_kr_stock_config_uses_separate_paths_and_dart_features PASSED [ 50%]
tests/ml/test_split_stock_configs.py::test_us_stock_config_uses_separate_paths_and_excludes_dart_features PASSED [100%]

============================== 2 passed in 0.03s ===============================
```

## 4. 커밋 ID 및 상태
- 상태: **DONE**
- 커밋 ID: `b0fed133cd5c68a0c59c09fe9bd2d3bbfc35eea4`
- 커밋 메시지: `feat: add split stock model configs`
