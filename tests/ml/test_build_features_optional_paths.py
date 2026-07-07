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
