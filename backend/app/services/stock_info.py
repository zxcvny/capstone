# app/services/stock_info.py

import os
import re
import logging

logger = logging.getLogger(__name__)

class StockInfoService:
    def __init__(self):
        self.code_to_name = {}
        self.name_to_code = {}
        
        # 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        
        # KOSPI와 KOSDAQ 파일 모두 로드
        kospi_path = os.path.join(app_dir, "kospi_code.mst")
        kosdaq_path = os.path.join(app_dir, "kosdaq_code.mst")
        
        # 순차적으로 로드 (하나의 딕셔너리에 합쳐짐)
        self.load_master_file(kospi_path)
        self.load_master_file(kosdaq_path)
        
    def load_master_file(self, filename: str):
        """
        마스터 파일을 로드하여 메모리에 캐싱합니다.
        """
        if not os.path.exists(filename):
            logger.warning(f"⚠️ {filename} 파일이 없습니다. 해당 시장의 종목명은 표시되지 않습니다.")
            return

        try:
            # cp949 인코딩으로 파일 열기
            with open(filename, "r", encoding="cp949") as f:
                for line in f:
                    code = line[0:9].strip()
                    # 정규식 파싱
                    match = re.search(r'KR[A-Z0-9]{10}(.+?)(ST|MF|EF|DR|SW|SR|EN|BC|PF|IF)', line)
                    
                    if match:
                        name = match.group(1).strip()
                        self.code_to_name[code] = name
                        self.name_to_code[name] = code
                    else:
                        # 정규식 실패 시 fallback
                        fallback_name = line[21:60].strip()
                        if fallback_name:
                            self.code_to_name[code] = fallback_name

            logger.info(f"✅ {os.path.basename(filename)} 로드 완료. (현재 누적 매핑: {len(self.code_to_name)}개)")
            
        except Exception as e:
            logger.error(f"⛔ {filename} 로드 중 오류 발생: {e}")

    # ... (나머지 메서드는 동일)
    def get_name(self, code: str) -> str:
        return self.code_to_name.get(code, code)

    def search_stocks(self, keyword: str, limit: int = 20):
        """
        종목 이름 또는 코드로 검색
        """
        results = []
        
        # 검색어 공백 제거 및 대문자 변환 (영어 종목명 검색 시 유용)
        clean_keyword = keyword.strip().upper()
        
        if not clean_keyword:
            return []

        for name, code in self.name_to_code.items():
            # 1. 이름에 검색어가 포함되어 있는지 확인 (한글)
            # 2. 코드 자체가 검색어와 일치하는지 확인 (종목 코드로 검색 시)
            if clean_keyword in name or clean_keyword in code:
                results.append({
                    "code": code,
                    "name": name,
                    # 시장 정보(코스피/코스닥)를 마스터 파일 파싱 때 저장해뒀다면 여기에 추가 가능
                })
                
                if len(results) >= limit:
                    break
                    
        return results

stock_info_service = StockInfoService()