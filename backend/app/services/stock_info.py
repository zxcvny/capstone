import os
import re
import logging

logger = logging.getLogger(__name__)

class StockInfoService:
    def __init__(self):
        self.code_to_name = {}
        self.name_to_code = {}
        self.code_to_market = {}  # 코드별 시장 정보 (KR, NAS 등)
        
        # 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        
        # 1. 국내 주식 마스터 파일 로드
        kospi_path = os.path.join(app_dir, "kospi_code.mst")
        kosdaq_path = os.path.join(app_dir, "kosdaq_code.mst")
        self.load_master_file(kospi_path, "DOMESTIC")
        self.load_master_file(kosdaq_path, "DOMESTIC")
        
        # 2. 해외 주식(나스닥) 마스터 파일 로드
        nasdaq_path = os.path.join(app_dir, "NASMST.COD")
        self.load_overseas_master_file(nasdaq_path, "NAS")
        
    def load_master_file(self, filename: str, market_type: str):
        """국내 주식 마스터 파일 로드"""
        if not os.path.exists(filename):
            return

        try:
            with open(filename, "r", encoding="cp949") as f:
                for line in f:
                    code = line[0:9].strip()
                    # 표준코드 등이 섞여있어 정규식으로 종목명 추출
                    match = re.search(r'KR[A-Z0-9]{10}(.+?)(ST|MF|EF|DR|SW|SR|EN|BC|PF|IF)', line)
                    if match:
                        name = match.group(1).strip()
                        self.code_to_name[code] = name
                        self.name_to_code[name] = code
                        self.code_to_market[code] = "KR"
                    else:
                        fallback_name = line[21:60].strip()
                        if fallback_name:
                            self.code_to_name[code] = fallback_name
                            self.name_to_code[fallback_name] = code
                            self.code_to_market[code] = "KR"
                            
            logger.info(f"✅ {os.path.basename(filename)} 로드 완료.")
        except Exception as e:
            logger.error(f"⛔ {filename} 로드 실패: {e}")

    def load_overseas_master_file(self, filename: str, market_code: str):
        """해외 주식 마스터 파일 로드"""
        if not os.path.exists(filename):
            logger.warning(f"⚠️ {filename} 파일이 없습니다.")
            return

        try:
            with open(filename, "r", encoding="cp949", errors="ignore") as f:
                for raw in f:
                    cols = raw.strip().split("\t")
                    if len(cols) < 7:
                        continue

                    symbol = cols[4].strip()
                    name_kr = cols[6].strip()

                    if symbol and name_kr:
                        self.code_to_name[symbol] = name_kr
                        self.name_to_code[name_kr] = symbol
                        self.code_to_market[symbol] = market_code # 예: "NAS"

            logger.info(f"✅ 해외 마스터 파일 로드 완료.")

        except Exception as e:
            logger.error(f"⛔ 해외 마스터 로드 실패: {e}")

    def get_name(self, code: str) -> str:
        return self.code_to_name.get(code, code)

    def search_stocks(self, keyword: str, limit: int = 50):
        """
        종목 검색 (국내 + 해외 통합)
        - 검색어 적합도 점수(score)를 포함하여 반환
        - limit을 넉넉하게 반환하여 Router에서 시가총액 정렬 후 자를 수 있게 함
        """
        results = []
        clean_keyword = keyword.strip().upper()
        
        if not clean_keyword:
            return []

        for name, code in self.name_to_code.items():
            name_upper = name.upper()
            code_upper = code.upper()
            
            score = 100 # 기본값 (매칭 안됨)

            # 1순위: 정확히 일치
            if clean_keyword == name_upper or clean_keyword == code_upper:
                score = 1
            # 2순위: 시작 문자 일치
            elif name_upper.startswith(clean_keyword) or code_upper.startswith(clean_keyword):
                score = 2
            # 3순위: 포함
            elif clean_keyword in name_upper or clean_keyword in code_upper:
                score = 3
            
            if score < 100:
                results.append({
                    "code": code,
                    "name": name,
                    "market": self.code_to_market.get(code, "KR"),
                    "score": score # 정렬을 위한 점수
                })

        # 1차 정렬: 점수(낮은순) -> 이름길이(짧은순) -> 이름(가나다)
        # 여기서 상위 N개를 잘라야 API 호출 부하를 줄일 수 있습니다.
        results.sort(key=lambda x: (x['score'], len(x['name']), x['name']))
        
        return results[:limit]

stock_info_service = StockInfoService()