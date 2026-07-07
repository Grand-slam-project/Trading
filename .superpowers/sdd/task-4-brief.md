### Task 4: 국내/해외 주식 모델 config 추가

**Files:**
- Create: `ml/configs/lgbm_kr_stock_v1.yaml`
- Create: `ml/configs/lgbm_kr_stock_risk_v1.yaml`
- Create: `ml/configs/lgbm_us_stock_v1.yaml`
- Create: `ml/configs/lgbm_us_stock_risk_v1.yaml`
- Create: `tests/ml/test_split_stock_configs.py`

**Interfaces:**
- Consumes:
  - `ml/configs/lgbm_stock_v11.yaml`
  - `ml/configs/lgbm_stock_risk_v11.yaml`
  - Task 3 `optional_features.dart_features_path`
- Produces:
  - model versions `lgbm_kr_stock_signal_v1`, `lgbm_kr_stock_risk_v1`
  - model versions `lgbm_us_stock_signal_v1`, `lgbm_us_stock_risk_v1`

- [ ] **Step 1: Write the failing tests**

Create `tests/ml/test_split_stock_configs.py`:

```python
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(name: str) -> dict:
    return yaml.safe_load((PROJECT_ROOT / "ml" / "configs" / name).read_text(encoding="utf-8"))


def test_kr_stock_config_uses_separate_paths_and_dart_features():
    config = load_config("lgbm_kr_stock_v1.yaml")
    risk_config = load_config("lgbm_kr_stock_risk_v1.yaml")

    assert config["data"]["raw_candles_path"] == "data/raw/kr_stock_candles.csv"
    assert config["data"]["features_path"] == "data/processed/kr_stock_features_lgbm_v1.csv"
    assert config["model"]["version"] == "lgbm_kr_stock_signal_v1"
    assert config["model"]["asset_type"] == "STOCK"
    assert config["optional_features"]["dart_features_path"] == "ml/data/raw/dart_features.csv"
    assert "dart_disclosure_count_20d" in config["model"]["feature_columns"]
    assert risk_config["model"]["version"] == "lgbm_kr_stock_risk_v1"
    assert risk_config["data"]["features_path"] == config["data"]["features_path"]


def test_us_stock_config_uses_separate_paths_and_excludes_dart_features():
    config = load_config("lgbm_us_stock_v1.yaml")
    risk_config = load_config("lgbm_us_stock_risk_v1.yaml")

    assert config["data"]["raw_candles_path"] == "data/raw/us_stock_candles.csv"
    assert config["data"]["features_path"] == "data/processed/us_stock_features_lgbm_v1.csv"
    assert config["model"]["version"] == "lgbm_us_stock_signal_v1"
    assert config["model"]["asset_type"] == "STOCK"
    assert "dart_features_path" not in config.get("optional_features", {})
    assert "dart_disclosure_count_20d" not in config["model"]["feature_columns"]
    assert risk_config["model"]["version"] == "lgbm_us_stock_risk_v1"
    assert risk_config["data"]["features_path"] == config["data"]["features_path"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/ml/test_split_stock_configs.py -v
```

Expected: FAIL because config files do not exist.

- [ ] **Step 3: Create config files**

Create the four config files by copying `lgbm_stock_v11.yaml` and `lgbm_stock_risk_v11.yaml`, then make these exact changes.

For `ml/configs/lgbm_kr_stock_v1.yaml`:

```yaml
data:
  raw_candles_path: data/raw/kr_stock_candles.csv
  features_path: data/processed/kr_stock_features_lgbm_v1.csv
  predictions_path: data/processed/kr_stock_predictions_lgbm_v1.csv
  backtest_up_only_summary_path: data/processed/kr_stock_backtest_up_only_v1.json
  backtest_up_only_daily_path: data/processed/kr_stock_backtest_up_only_daily_v1.csv
  backtest_composite_summary_path: data/processed/kr_stock_backtest_composite_v1.json
  backtest_composite_daily_path: data/processed/kr_stock_backtest_composite_daily_v1.csv
model:
  version: lgbm_kr_stock_signal_v1
  asset_type: STOCK
  output_path: models/lgbm_kr_stock_signal_v1.joblib
```

Keep the v11 feature columns and append the 21 DART columns from Task 2 to `model.feature_columns`.

Add:

```yaml
optional_features:
  dart_features_path: ml/data/raw/dart_features.csv
```

Set prediction risk path:

```yaml
prediction:
  risk_model_path: models/lgbm_kr_stock_risk_v1.joblib
```

For `ml/configs/lgbm_kr_stock_risk_v1.yaml`, copy `lgbm_stock_risk_v11.yaml`, point it to `data/processed/kr_stock_features_lgbm_v1.csv`, set version `lgbm_kr_stock_risk_v1`, output `models/lgbm_kr_stock_risk_v1.joblib`, and append the same 21 DART feature columns.

For `ml/configs/lgbm_us_stock_v1.yaml`, copy `lgbm_stock_v11.yaml`, use:

```yaml
data:
  raw_candles_path: data/raw/us_stock_candles.csv
  features_path: data/processed/us_stock_features_lgbm_v1.csv
  predictions_path: data/processed/us_stock_predictions_lgbm_v1.csv
  backtest_up_only_summary_path: data/processed/us_stock_backtest_up_only_v1.json
  backtest_up_only_daily_path: data/processed/us_stock_backtest_up_only_daily_v1.csv
  backtest_composite_summary_path: data/processed/us_stock_backtest_composite_v1.json
  backtest_composite_daily_path: data/processed/us_stock_backtest_composite_daily_v1.csv
model:
  version: lgbm_us_stock_signal_v1
  asset_type: STOCK
  output_path: models/lgbm_us_stock_signal_v1.joblib
prediction:
  risk_model_path: models/lgbm_us_stock_risk_v1.joblib
```

Do not add `optional_features.dart_features_path` and do not include DART columns.

For `ml/configs/lgbm_us_stock_risk_v1.yaml`, copy `lgbm_stock_risk_v11.yaml`, point it to `data/processed/us_stock_features_lgbm_v1.csv`, set version `lgbm_us_stock_risk_v1`, and output `models/lgbm_us_stock_risk_v1.joblib`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/ml/test_split_stock_configs.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/configs/lgbm_kr_stock_v1.yaml ml/configs/lgbm_kr_stock_risk_v1.yaml ml/configs/lgbm_us_stock_v1.yaml ml/configs/lgbm_us_stock_risk_v1.yaml tests/ml/test_split_stock_configs.py
git commit -m "feat: add split stock model configs"
```

---

