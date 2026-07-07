### Task 2: DART 공시 피처 export 스크립트

**Files:**
- Create: `backend/scripts/export_dart_features.py`
- Create: `tests/backend/test_export_dart_features.py`

**Interfaces:**
- Consumes:
  - `dart_disclosures` rows with `rcept_no`, `stock_code`, `report_nm`, `rcept_dt`
  - `dart_disclosure_analyses` rows with `rcept_no`, `category`, `sentiment`, `confidence`
- Produces:
  - Function `normalize_stock_code(value: object) -> str`
  - Function `build_daily_dart_features(disclosures: list[dict], analyses: list[dict]) -> pandas.DataFrame`
  - Function `build_shifted_dart_features(feature_dates: pandas.DataFrame, daily_features: pandas.DataFrame) -> pandas.DataFrame`
  - CLI output CSV columns:
    - `symbol`
    - `date`
    - `dart_disclosure_count_3d`
    - `dart_sentiment_sum_3d`
    - `dart_negative_count_3d`
    - `dart_positive_count_3d`
    - `dart_caution_count_3d`
    - `dart_disclosure_count_7d`
    - `dart_sentiment_sum_7d`
    - `dart_negative_count_7d`
    - `dart_positive_count_7d`
    - `dart_caution_count_7d`
    - `dart_disclosure_count_20d`
    - `dart_sentiment_sum_20d`
    - `dart_negative_count_20d`
    - `dart_positive_count_20d`
    - `dart_caution_count_20d`
    - `dart_ai_analyzed_count_20d`
    - `dart_contract_flag_20d`
    - `dart_financing_flag_20d`
    - `dart_shareholder_return_flag_20d`
    - `dart_risk_event_flag_20d`
    - `dart_earnings_flag_20d`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/test_export_dart_features.py`:

```python
import pandas as pd

from backend.scripts.export_dart_features import (
    build_daily_dart_features,
    build_shifted_dart_features,
    normalize_stock_code,
)


def test_normalize_stock_code_preserves_six_digit_symbols():
    assert normalize_stock_code("5930") == "005930"
    assert normalize_stock_code("005930") == "005930"
    assert normalize_stock_code("005930.0") == "005930"
    assert normalize_stock_code(None) == ""


def test_build_daily_dart_features_uses_analysis_sentiment_and_category():
    disclosures = [
        {
            "rcept_no": "202607070001",
            "stock_code": "005930",
            "report_nm": "단일판매ㆍ공급계약체결",
            "rcept_dt": "2026-07-07",
        },
        {
            "rcept_no": "202607070002",
            "stock_code": "005930",
            "report_nm": "유상증자결정",
            "rcept_dt": "2026-07-07",
        },
    ]
    analyses = [
        {
            "rcept_no": "202607070001",
            "category": "수주·공급계약",
            "sentiment": "positive",
            "confidence": "high",
        },
        {
            "rcept_no": "202607070002",
            "category": "자금조달·증권발행",
            "sentiment": "caution",
            "confidence": "medium",
        },
    ]

    frame = build_daily_dart_features(disclosures, analyses)
    row = frame.iloc[0].to_dict()

    assert row["symbol"] == "005930"
    assert row["date"] == "2026-07-07"
    assert row["dart_disclosure_count"] == 2.0
    assert row["dart_sentiment_score"] == 0.5
    assert row["dart_positive_count"] == 1.0
    assert row["dart_caution_count"] == 1.0
    assert row["dart_contract_flag"] == 1.0
    assert row["dart_financing_flag"] == 1.0


def test_build_shifted_dart_features_uses_only_prior_disclosures():
    feature_dates = pd.DataFrame(
        {
            "symbol": ["005930", "005930", "005930"],
            "date": pd.to_datetime(["2026-07-07", "2026-07-08", "2026-07-09"]),
        }
    )
    daily_features = pd.DataFrame(
        {
            "symbol": ["005930"],
            "date": ["2026-07-07"],
            "dart_disclosure_count": [1.0],
            "dart_sentiment_score": [1.0],
            "dart_negative_count": [0.0],
            "dart_positive_count": [1.0],
            "dart_caution_count": [0.0],
            "dart_info_count": [0.0],
            "dart_ai_analyzed_count": [1.0],
            "dart_contract_flag": [1.0],
            "dart_financing_flag": [0.0],
            "dart_shareholder_return_flag": [0.0],
            "dart_risk_event_flag": [0.0],
            "dart_earnings_flag": [0.0],
        }
    )

    shifted = build_shifted_dart_features(feature_dates, daily_features)
    rows = shifted.sort_values("date").to_dict("records")

    assert rows[0]["dart_disclosure_count_3d"] == 0.0
    assert rows[1]["dart_disclosure_count_3d"] == 1.0
    assert rows[2]["dart_disclosure_count_3d"] == 1.0
    assert rows[1]["dart_contract_flag_20d"] == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/backend/test_export_dart_features.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.scripts.export_dart_features'`.

- [ ] **Step 3: Implement `export_dart_features.py`**

Create `backend/scripts/export_dart_features.py`:

```python
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


SENTIMENT_SCORE = {
    "positive": 1.0,
    "negative": -1.0,
    "caution": -0.5,
    "info": 0.0,
}

CATEGORY_GROUPS = {
    "dart_contract_flag": ["수주", "공급계약", "계약"],
    "dart_financing_flag": ["유상증자", "자금조달", "증권", "사채", "전환"],
    "dart_shareholder_return_flag": ["배당", "자사주", "주주환원", "소각"],
    "dart_risk_event_flag": ["거래정지", "상장폐지", "관리종목", "불성실", "감사의견", "횡령", "배임", "회생", "영업정지", "감자"],
    "dart_earnings_flag": ["영업실적", "손익구조", "매출액", "영업이익"],
}

BASE_DART_COLUMNS = [
    "dart_disclosure_count",
    "dart_sentiment_score",
    "dart_positive_count",
    "dart_negative_count",
    "dart_caution_count",
    "dart_info_count",
    "dart_ai_analyzed_count",
    *CATEGORY_GROUPS.keys(),
]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_stock_code(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value).strip().upper()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if text.isdigit() and len(text) <= 6:
        return text.zfill(6)
    return text


def build_daily_dart_features(disclosures: list[dict[str, Any]], analyses: list[dict[str, Any]]) -> pd.DataFrame:
    analysis_by_receipt = {str(row.get("rcept_no") or ""): row for row in analyses}
    rows: list[dict[str, Any]] = []

    for disclosure in disclosures:
        symbol = normalize_stock_code(disclosure.get("stock_code"))
        receipt_no = str(disclosure.get("rcept_no") or "")
        received_date = pd.to_datetime(disclosure.get("rcept_dt"), errors="coerce")
        if not symbol or not receipt_no or pd.isna(received_date):
            continue

        analysis = analysis_by_receipt.get(receipt_no) or {}
        sentiment = str(analysis.get("sentiment") or "info")
        category = str(analysis.get("category") or "")
        report_name = str(disclosure.get("report_nm") or "")
        category_text = f"{report_name} {category}"

        row = {
            "symbol": symbol,
            "date": received_date.strftime("%Y-%m-%d"),
            "dart_disclosure_count": 1.0,
            "dart_sentiment_score": SENTIMENT_SCORE.get(sentiment, 0.0),
            "dart_positive_count": 1.0 if sentiment == "positive" else 0.0,
            "dart_negative_count": 1.0 if sentiment == "negative" else 0.0,
            "dart_caution_count": 1.0 if sentiment == "caution" else 0.0,
            "dart_info_count": 1.0 if sentiment == "info" else 0.0,
            "dart_ai_analyzed_count": 1.0 if analysis else 0.0,
        }
        for column, keywords in CATEGORY_GROUPS.items():
            row[column] = 1.0 if any(keyword in category_text for keyword in keywords) else 0.0
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["symbol", "date", *BASE_DART_COLUMNS])

    return (
        pd.DataFrame(rows)
        .groupby(["symbol", "date"], as_index=False)[BASE_DART_COLUMNS]
        .sum()
        .sort_values(["symbol", "date"])
        .reset_index(drop=True)
    )


def build_shifted_dart_features(feature_dates: pd.DataFrame, daily_features: pd.DataFrame) -> pd.DataFrame:
    base = feature_dates[["symbol", "date"]].copy()
    base["symbol"] = base["symbol"].map(normalize_stock_code)
    base["date"] = pd.to_datetime(base["date"], errors="coerce")
    base = base.dropna(subset=["date"]).sort_values(["symbol", "date"])
    base["date_key"] = base["date"].dt.strftime("%Y-%m-%d")

    daily = daily_features.copy()
    if daily.empty:
        daily = pd.DataFrame(columns=["symbol", "date", *BASE_DART_COLUMNS])
    daily["symbol"] = daily["symbol"].map(normalize_stock_code)
    daily["date_key"] = pd.to_datetime(daily["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    merged = base.merge(daily[["symbol", "date_key", *BASE_DART_COLUMNS]], on=["symbol", "date_key"], how="left")
    merged[BASE_DART_COLUMNS] = merged[BASE_DART_COLUMNS].fillna(0.0)

    frames: list[pd.DataFrame] = []
    for symbol, group in merged.groupby("symbol", sort=False):
        group = group.sort_values("date").copy()
        shifted = group[BASE_DART_COLUMNS].shift(1).fillna(0.0)
        output = group[["symbol", "date"]].copy()
        for window in [3, 7, 20]:
            rolling = shifted.rolling(window, min_periods=1).sum()
            output[f"dart_disclosure_count_{window}d"] = rolling["dart_disclosure_count"]
            output[f"dart_sentiment_sum_{window}d"] = rolling["dart_sentiment_score"]
            output[f"dart_negative_count_{window}d"] = rolling["dart_negative_count"]
            output[f"dart_positive_count_{window}d"] = rolling["dart_positive_count"]
            output[f"dart_caution_count_{window}d"] = rolling["dart_caution_count"]
        output["dart_ai_analyzed_count_20d"] = shifted["dart_ai_analyzed_count"].rolling(20, min_periods=1).sum()
        for column in CATEGORY_GROUPS:
            output[f"{column}_20d"] = shifted[column].rolling(20, min_periods=1).max()
        frames.append(output)

    result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["symbol", "date"])
    result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
    return result


def fetch_supabase_rows(table: str, select: str, params: dict[str, str], batch_size: int = 1000) -> list[dict[str, Any]]:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not service_key:
        raise RuntimeError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 필요합니다.")

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        request_params = {"select": select, "limit": str(batch_size), "offset": str(offset), **params}
        response = requests.get(
            f"{supabase_url}/rest/v1/{table}",
            headers=headers,
            params=request_params,
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return rows


def main() -> None:
    load_env_file(PROJECT_ROOT / "backend" / ".env")
    parser = argparse.ArgumentParser(description="DART 공시 분석 결과를 ML raw 피처 CSV로 변환합니다.")
    parser.add_argument("--dates-source-path", default="ml/data/raw/kr_stock_candles.csv")
    parser.add_argument("--output", default="ml/data/raw/dart_features.csv")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    args = parser.parse_args()

    dates_source_path = (PROJECT_ROOT / args.dates_source_path).resolve()
    dates_source_frame = pd.read_csv(dates_source_path, dtype={"symbol": "string"}, low_memory=False)
    feature_dates = dates_source_frame[["symbol", "date"]].drop_duplicates()
    start_date = args.start_date or pd.to_datetime(feature_dates["date"]).min().strftime("%Y-%m-%d")
    end_date = args.end_date or pd.to_datetime(feature_dates["date"]).max().strftime("%Y-%m-%d")

    disclosures = fetch_supabase_rows(
        "dart_disclosures",
        "rcept_no,stock_code,report_nm,rcept_dt",
        {"rcept_dt": f"gte.{start_date}", "order": "rcept_dt.asc,rcept_no.asc"},
    )
    disclosures = [
        row
        for row in disclosures
        if pd.to_datetime(row.get("rcept_dt"), errors="coerce").strftime("%Y-%m-%d") <= end_date
    ]
    analyses = fetch_supabase_rows(
        "dart_disclosure_analyses",
        "rcept_no,category,sentiment,confidence",
        {},
    )

    daily = build_daily_dart_features(disclosures, analyses)
    shifted = build_shifted_dart_features(feature_dates, daily)
    output_path = (PROJECT_ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shifted.to_csv(output_path, index=False)
    print(json.dumps({"output": str(output_path), "rows": len(shifted)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/backend/test_export_dart_features.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/export_dart_features.py tests/backend/test_export_dart_features.py
git commit -m "feat: export dart features for kr stock models"
```

---

