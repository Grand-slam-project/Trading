# Task 1 보고서

- 작업명: 학습 유니버스 3분리
- 수행 범위: `ml/data/reference/training_universes.json`, `tests/ml/test_training_universes.py`
- 구현 내용:
  - `stock_core_90`는 그대로 유지했습니다.
  - `stock_kr_core_45`를 추가해 국내주식 45개를 분리했습니다.
  - `stock_us_core_45`를 추가해 해외주식 45개를 분리했습니다.
  - JSON 키 순서는 `stock_core_90` 바로 뒤에 새 두 키가 오도록 정리했습니다.
- 테스트:
  - `python3 -m pytest tests/ml/test_training_universes.py -v`
  - 결과: 1 passed
- 비고:
  - 기존 `stock_core_90` 자동화는 제거하지 않았습니다.
  - 국내주식/해외주식 분리는 요청한 값 그대로 반영했습니다.
