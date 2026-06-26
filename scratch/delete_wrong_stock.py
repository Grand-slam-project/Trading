# -*- coding: utf-8 -*-
import os
import sys
import requests
from pathlib import Path

# 프로젝트 루트를 path에 추가하여 백엔드 모듈을 임포트할 수 있게 함
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")

def main():
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_role_key:
        print("오류: Supabase 자격증명이 .env 파일에 누락되었습니다.")
        return

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json"
    }

    # 잘못 저장된 종목코드 '462350' (이노스페이스 오기입 데이터)
    wrong_symbol = "462350"
    correct_symbol = "461350"

    # 1. 잘못된 코드 삭제 처리
    print(f"1. kis_stock_master 테이블에서 잘못된 코드({wrong_symbol}) 삭제 시도...")
    res1 = requests.delete(
        f"{supabase_url}/rest/v1/kis_stock_master?symbol=eq.{wrong_symbol}",
        headers=headers
    )
    print(f"결과: {res1.status_code}")

    res2 = requests.delete(
        f"{supabase_url}/rest/v1/kis_stock_turnover_latest?symbol=eq.{wrong_symbol}",
        headers=headers
    )
    print(f"kis_stock_turnover_latest 삭제 결과: {res2.status_code}")

    # 2. 올바른 코드(461350) 삽입 처리 (DB 상에 없을 수도 있으므로 마스터에 직접 인서트)
    print(f"\n2. kis_stock_master 테이블에 올바른 코드({correct_symbol}) 등록 시도...")
    correct_row = {
        "symbol": correct_symbol,
        "name": "이노스페이스",
        "market_segment": "KOSDAQ",
        "market_country": "KR",
        "asset_type": "STOCK",
        "source": "TOSS",
        "is_active": True,
        "listed_at": None,
        "source_file_row": {}
    }
    
    # upsert 처리
    headers_write = {
        **headers,
        "Prefer": "resolution=merge-duplicates,return=minimal"
    }
    res3 = requests.post(
        f"{supabase_url}/rest/v1/kis_stock_master",
        headers=headers_write,
        json=[correct_row]
    )
    print(f"등록 결과: {res3.status_code}")

if __name__ == "__main__":
    main()
