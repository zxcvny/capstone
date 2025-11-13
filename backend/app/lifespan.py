import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import init_db, engine
from app.services.kis_auth import kis_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ----- 앱 시작 -----
    logger.info("🚀 FastAPI 앱이 시작됩니다...")
    logger.info("✅ 데이터베이스 연결 및 테이블 생성을 시도합니다.")

    await init_db()

    try:
        logger.info("🔑 KIS Access Token 발급/갱신을 시도합니다...")
        await kis_auth.get_access_token()
        logger.info("✅ KIS Access Token 준비 완료.")
        
        logger.info("🔑 KIS Approval Key 발급/갱신을 시도합니다...")
        await kis_auth.get_approval_key()
        logger.info("✅ KIS Approval Key 준비 완료.")
        
    except Exception as e:
        # DB 저장 오류를 포함한 모든 KIS 인증 오류를 여기서 잡습니다.
        logger.error(f"⛔ 앱 시작 중 KIS 토큰 발급/저장 실패: {e}", exc_info=True)

    yield
    # ----- 앱 종료 -----
    logger.info("⏳ FastAPI 앱이 종료됩니다...")
    if engine:
        logger.info("✅ 데이터베이스 엔진 연결을 종료합니다.")
        await engine.dispose()
        logger.info("✅ 데이터베이스 엔진이 종료되었습니다.")

