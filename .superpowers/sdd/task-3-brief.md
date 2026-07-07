### Task 3: 선택 피처 경로와 DART 컬럼 병합 지원

**Files:**
- Modify: `ml/src/build_features.py`
- Create: `tests/ml/test_build_features_optional_paths.py`

**Interfaces:**
- Consumes:
  - config key `optional_features.news_features_path: str | None`
  - config key `optional_features.stock_event_features_path: str | None`
  - config key `optional_features.dart_features_path: str | None`
- Produces:
  - Function behavior: `apply_optional_features(features: pandas.DataFrame, config: dict) -> pandas.DataFrame` merges DART columns only when `dart_features_path` is configured.

- [ ] **Step 1: Write the failing tests**

Create `tests/ml/test_build_features_optional_paths.py`:

```python
from pathlib import Path

import pandas as pd

from ml.src.build_features import apply_optional_features


def test_apply_optional_features_merges_configured_dart_features(tmp_path: Path):
    dart_path = tmp_path / "dart_features.csv"
    dart_path.write_text(
        "\n".join(
            [
                "symbol,date,dart_disclosure_count_3d,dart_sentiment_sum_3d,dart_negative_count_3d,dart_positive_count_3d,dart_caution_count_3d,dart_disclosure_count_7d,dart_sentiment_sum_7d,dart_negative_count_7d,dart_positive_count_7d,dart_caution_count_7d,dart_disclosure_count_20d,dart_sentiment_sum_20d,dart_negative_count_20d,dart_positive_count_20d,dart_caution_count_20d,dart_ai_analyzed_count_20d,dart_contract_flag_20d,dart_financing_flag_20d,dart_shareholder_return_flag_20d,dart_risk_event_flag_20d,dart_earnings_flag_20d",
                "005930,2026-07-08,1,1,0,1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,0,0,0",
            ]
        ),
        encoding="utf-8",
    )
    features = pd.DataFrame(
        {
            "symbol": ["005930"],
            "date_merge_key": ["2026-07-08"],
        }
    )
    config = {
        "model": {"asset_type": "STOCK"},
        "optional_features": {"dart_features_path": str(dart_path)},
    }

    merged = apply_optional_features(features, config)

    assert merged.loc[0, "dart_disclosure_count_3d"] == 1
    assert merged.loc[0, "dart_contract_flag_20d"] == 1


def test_apply_optional_features_does_not_add_dart_columns_without_path():
    features = pd.DataFrame(
        {
            "symbol": ["005930"],
            "date_merge_key": ["2026-07-08"],
        }
    )
    config = {"model": {"asset_type": "STOCK"}}

    merged = apply_optional_features(features, config)

    assert "dart_disclosure_count_3d" not in merged.columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/ml/test_build_features_optional_paths.py -v
```

Expected: first test FAIL because `dart_features_path` is not merged.

- [ ] **Step 3: Implement configurable optional paths**

Modify `ml/src/build_features.py`.

Add this helper near `load_optional_feature_source`:

```python
def resolve_optional_feature_path(config: dict, key: str, default_relative_path: str) -> Path:
    configured_path = (config.get("optional_features") or {}).get(key)
    if configured_path:
        path = Path(str(configured_path))
        return path if path.is_absolute() else PROJECT_ROOT / path
    return PROJECT_ROOT / default_relative_path
```

In `apply_optional_features`, replace hard-coded path assignments:

```python
news_path = resolve_optional_feature_path(config, "news_features_path", "ml/data/raw/news_features.csv")
```

```python
crypto_path = resolve_optional_feature_path(config, "crypto_market_features_path", "ml/data/raw/crypto_market_features.csv")
```

```python
stock_path = resolve_optional_feature_path(config, "stock_event_features_path", "ml/data/raw/stock_event_features.csv")
```

Then add this block inside `if asset_type == "STOCK":` after `stock_df` merge:

```python
        dart_defaults = [
            "dart_disclosure_count_3d",
            "dart_sentiment_sum_3d",
            "dart_negative_count_3d",
            "dart_positive_count_3d",
            "dart_caution_count_3d",
            "dart_disclosure_count_7d",
            "dart_sentiment_sum_7d",
            "dart_negative_count_7d",
            "dart_positive_count_7d",
            "dart_caution_count_7d",
            "dart_disclosure_count_20d",
            "dart_sentiment_sum_20d",
            "dart_negative_count_20d",
            "dart_positive_count_20d",
            "dart_caution_count_20d",
            "dart_ai_analyzed_count_20d",
            "dart_contract_flag_20d",
            "dart_financing_flag_20d",
            "dart_shareholder_return_flag_20d",
            "dart_risk_event_flag_20d",
            "dart_earnings_flag_20d",
        ]
        dart_path_text = (config.get("optional_features") or {}).get("dart_features_path")
        if dart_path_text:
            dart_path = resolve_optional_feature_path(config, "dart_features_path", "ml/data/raw/dart_features.csv")
            dart_df = load_optional_feature_source(dart_path, asset_type, dart_defaults)
            if not dart_df.empty:
                features = pd.merge(features, dart_df, on=["symbol", "date_merge_key"], how="left")
```

Also add all `dart_defaults` values to the later zero-fill column list in `build_features`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/ml/test_build_features_optional_paths.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/src/build_features.py tests/ml/test_build_features_optional_paths.py
git commit -m "feat: support configured optional ml feature sources"
```

---

