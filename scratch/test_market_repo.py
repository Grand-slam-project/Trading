# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가하여 백엔드 모듈을 임포트할 수 있게 함
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# 환경 변수 로드 (.env 파일이 있을 것이므로 환경 변수가 세팅되어 있을 것임)
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")

from backend.services.market_repository import MarketRepository

def main():
    repo = MarketRepository()
    if not repo.is_configured:
        print("오류: Supabase 설정이 되어 있지 않습니다.")
        return

    print("Supabase 연결 성공. 종목 검색을 테스트합니다...")

    # 1. '이노스페이스' 검색 테스트
    print("\n[테스트 1] '이노스페이스' 이름으로 검색:")
    try:
        # kis_stock_master에서 직접 검색하기 위해 repository에 메서드가 없으므로 
        # list_symbols 또는 list_universe를 활용하거나 직접 requests를 이용해 봅니다.
        # list_universe의 경우 최대 5000개를 읽어올 수 있습니다.
        # 혹은 특정 종목 코드로 조회해봅니다. 이노스페이스 코드는 '461350'입니다.
        result = repo.list_symbols(["461350"])
        print(f"461350 (이노스페이스) 코드 조회 결과: {result}")
    except Exception as e:
        print(f"조회 실패: {e}")

if __name__ == "__main__":
    main()
