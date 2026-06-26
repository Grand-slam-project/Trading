# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가하여 백엔드 모듈을 임포트할 수 있게 함
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")

# Flask 앱 컨텍스트 설정 (current_app 등을 활용하는 경우를 대비)
from flask import Flask
app = Flask("test_app")
app.config["SUPABASE_URL"] = os.getenv("SUPABASE_URL")
app.config["SUPABASE_SERVICE_ROLE_KEY"] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

from backend.services.symbol_metadata import search_crypto_symbols
from backend.services.market_repository import MarketRepository

def test_dynamic_search():
    print("=== [테스트 1] 가상자산 동적 검색 검증 ===")
    for q in ["XRP", "리플", "솔라나", "SOL"]:
        results = search_crypto_symbols(q, limit=5)
        print(f"검색어: '{q}' -> 결과 개수: {len(results)}")
        for r in results:
            print(f"  - Symbol: {r['symbol']}, Name: {r['display_name']}, Market: {r['market']}, AssetType: {r['asset_type']}")

    print("\n=== [테스트 2] 주식 마스터 DB 동적 검색 검증 (정돈 필터 적용) ===")
    repo = MarketRepository()
    if repo.is_configured:
        import re
        for q in ["이노스페이스", "동화약품", "삼성", "000020"]:
            results = repo.search_stock_master(q, limit=5)
            print(f"검색어: '{q}' -> 결과 개수: {len(results)}")
            for r in results:
                # API 레벨에서 수행하는 가공 로직 모방
                clean_name = re.sub(r"^KR\d{10}", "", r["name"]).strip()
                print(f"  - Symbol: {r['symbol']}, Name: {clean_name}, MarketSegment: {r['market_segment']}, AssetType: {r['asset_type']}")
    else:
        print("경고: Supabase 설정이 되어 있지 않아 주식 검색은 건너뜁니다.")

if __name__ == "__main__":
    with app.app_context():
        test_dynamic_search()
