from fastapi import APIRouter, Query
from app.services.stock_info import stock_info_service

router = APIRouter(prefix="/stocks", tags=["Stocks"])

@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1)):
    """
    종목 이름으로 검색 (예: '삼성')
    """
    return stock_info_service.search_stocks(keyword)