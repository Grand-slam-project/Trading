### Task 5: 자동화 preset과 full-run 출력 분리

**Files:**
- Modify: `backend/services/ml_automation_service.py`
- Modify: `backend/routes/ml.py`
- Create: `tests/backend/test_ml_automation_presets.py`

**Interfaces:**
- Consumes:
  - Task 1 universe keys
  - Task 4 config files
- Produces:
  - preset key `kr-stock-v1-full`
  - preset key `us-stock-v1-full`
  - full-run support for `dataset.raw_output`
  - full-run support for `training.pre_build_commands: list[list[str]]`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/test_ml_automation_presets.py`:

```python
from backend.services.ml_automation_service import resolve_automation_preset


def test_kr_stock_automation_preset_uses_kr_universe_and_dart_prebuild():
    preset = resolve_automation_preset("kr-stock-v1-full")

    assert preset["dataset"]["preset"] == "stock_kr_core_45"
    assert preset["dataset"]["raw_output"] == "kr_stock_candles.csv"
    assert preset["training"]["config"] == "ml/configs/lgbm_kr_stock_v1.yaml"
    assert preset["training"]["risk_config"] == "ml/configs/lgbm_kr_stock_risk_v1.yaml"
    assert preset["training"]["summary_output"] == "ml/data/processed/kr_stock_v1_summary.json"
    assert preset["training"]["pre_build_commands"] == [
        [
            "python",
            "backend/scripts/export_dart_features.py",
            "--dates-source-path",
            "ml/data/raw/kr_stock_candles.csv",
            "--output",
            "ml/data/raw/dart_features.csv",
        ]
    ]


def test_us_stock_automation_preset_uses_us_universe_without_dart_prebuild():
    preset = resolve_automation_preset("us-stock-v1-full")

    assert preset["dataset"]["preset"] == "stock_us_core_45"
    assert preset["dataset"]["raw_output"] == "us_stock_candles.csv"
    assert preset["training"]["config"] == "ml/configs/lgbm_us_stock_v1.yaml"
    assert preset["training"]["risk_config"] == "ml/configs/lgbm_us_stock_risk_v1.yaml"
    assert "pre_build_commands" not in preset["training"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/backend/test_ml_automation_presets.py -v
```

Expected: FAIL with `ValueError: 알 수 없는 자동화 프리셋입니다: kr-stock-v1-full`.

- [ ] **Step 3: Add automation presets**

Modify `backend/services/ml_automation_service.py` and add:

```python
    "kr-stock-v1-full": {
        "label": "국내주식 v1 자동 수집+학습 (DART shadow)",
        "dataset": {
            "asset_type": "STOCK",
            "exchange": "TOSS",
            "preset": "stock_kr_core_45",
            "symbols": [],
            "interval": "1d",
            "count": 700,
            "sleep_seconds": 2.0,
            "retry": 3,
            "retry_wait_seconds": 60.0,
            "append": True,
            "include_macro": True,
            "chunk_size": 0,
            "chunk_index": 1,
            "raw_output": "kr_stock_candles.csv",
        },
        "training": {
            "config": "ml/configs/lgbm_kr_stock_v1.yaml",
            "risk_config": "ml/configs/lgbm_kr_stock_risk_v1.yaml",
            "summary_output": "ml/data/processed/kr_stock_v1_summary.json",
            "skip_build_features": False,
            "pre_build_commands": [
                [
                    "python",
                    "backend/scripts/export_dart_features.py",
                    "--dates-source-path",
                    "ml/data/raw/kr_stock_candles.csv",
                    "--output",
                    "ml/data/raw/dart_features.csv",
                ]
            ],
        },
    },
    "us-stock-v1-full": {
        "label": "해외주식 v1 자동 수집+학습 (shadow)",
        "dataset": {
            "asset_type": "STOCK",
            "exchange": "TOSS",
            "preset": "stock_us_core_45",
            "symbols": [],
            "interval": "1d",
            "count": 700,
            "sleep_seconds": 2.0,
            "retry": 3,
            "retry_wait_seconds": 60.0,
            "append": True,
            "include_macro": True,
            "chunk_size": 0,
            "chunk_index": 1,
            "raw_output": "us_stock_candles.csv",
        },
        "training": {
            "config": "ml/configs/lgbm_us_stock_v1.yaml",
            "risk_config": "ml/configs/lgbm_us_stock_risk_v1.yaml",
            "summary_output": "ml/data/processed/us_stock_v1_summary.json",
            "skip_build_features": False,
        },
    },
```

- [ ] **Step 4: Modify full-run output and pre-build handling**

Modify `backend/routes/ml.py`.

In the TOSS/STOCK branch of `run_ml_full_pipeline_job`, replace:

```python
output = os.path.join(project_root_path, "ml", "data", "raw", "stock_candles.csv")
```

with:

```python
raw_output_name = dataset_config.get("raw_output", "stock_candles.csv")
output = os.path.join(project_root_path, "ml", "data", "raw", raw_output_name)
```

Before `result = run_ml_pipeline(...)`, run configured pre-build commands:

```python
        for command in training_config.get("pre_build_commands") or []:
            resolved_command = [
                sys.executable if token == "python" else token
                for token in command
            ]
            completed = subprocess.run(
                resolved_command,
                cwd=project_root_path,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    "사전 피처 생성 명령이 실패했습니다: "
                    + " ".join(command)
                    + "\n"
                    + completed.stderr[-4000:]
                )
```

Add imports at top:

```python
import subprocess
import sys
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/backend/test_ml_automation_presets.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/ml_automation_service.py backend/routes/ml.py tests/backend/test_ml_automation_presets.py
git commit -m "feat: add split stock automation presets"
```

---

