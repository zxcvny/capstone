import logging
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.kis_token import KISToken

logger = logging.getLogger(__name__)

class KISAuth:
    def __init__(self):
        self.access_token = None
        self.approval_key = None
        self.base_url = settings.KIS_BASE_URL

    async def _load_token_from_db(self, session: AsyncSession, token_name: str):
        result = await session.execute(select(KISToken).where(KISToken.token_name == token_name))
        token = result.scalars().first()
        if token and token.expires_at > datetime.now(timezone.utc):
            return token.token_value, token.expires_at
        return None, None
    
    async def _save_token_to_db(self, session: AsyncSession, token_name: str, token_value: str, expires_at: datetime):
        try:
            result = await session.execute(select(KISToken).where(KISToken.token_name == token_name))
            token = result.scalars().first()
            
            if token:
                logger.info(f"DB: 기존 토큰 업데이트 시도: {token_name}")
                token.token_value = token_value
                token.expires_at = expires_at
            else:
                logger.info(f"DB: 새 토큰 생성 시도: {token_name}")
                token = KISToken(
                    token_name=token_name,
                    token_value=token_value,
                    expires_at=expires_at
                )
            
            session.add(token)
            await session.commit()
            logger.info(f"✅ DB: {token_name} 커밋 성공")

        except Exception as e:
            logger.error(f"⛔ DB 커밋 실패! 롤백합니다. 오류: {e}", exc_info=True)
            await session.rollback()
            raise

    async def get_access_token(self):
        """
        REST API용 Access Token
        DB에서 먼저 확인 후, 없거나 만료되면 새로 발급
        """
        async with AsyncSessionLocal() as session:
            token_value, expires_at = await self._load_token_from_db(session, "access_token")
            now = datetime.now(timezone.utc)

            if token_value and expires_at > now:
                self.access_token = token_value
                return self.access_token
            
            logger.info("DB에 access_token이 없거나 만료됨. KIS에서 새로 발급합니다.")
            url = f"{self.base_url}/oauth2/tokenP"
            data = {
                "grant_type": "client_credentials",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data)
                response.raise_for_status()
                result = response.json()

            self.access_token = result["access_token"]
            expires_dt = now + timedelta(seconds=int(result["expires_in"]))

            await self._save_token_to_db(session, "access_token", self.access_token, expires_dt)
            return self.access_token
    
    async def get_approval_key(self):
        """
        WEBSOCKET 용 approval key
        DB에서 먼저 확인 후, 없거나 만료되면 새로 발급
        """
        async with AsyncSessionLocal() as session:
            token_value, expires_at = await self._load_token_from_db(session, "approval_key")
            now = datetime.now(timezone.utc)

            if token_value and expires_at > now:
                self.approval_key = token_value
                return self.approval_key
            
            logger.info("DB에 approval_key가 없거나 만료됨. KIS에서 새로 발급합니다.")
            url = f"{self.base_url}/oauth2/Approval"
            
            headers = {"content-type": "application/json; utf-8"}
            data = {
                "grant_type": "client_credentials",
                "appkey": settings.KIS_APP_KEY,
                "secretkey": settings.KIS_SECRET_KEY
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()

            self.approval_key = result["approval_key"]
            expires_in_seconds = 24 * 3600
            expires_dt = now + timedelta(seconds=expires_in_seconds)

            await self._save_token_to_db(session, "approval_key", self.approval_key, expires_dt)

            return self.approval_key
    
kis_auth = KISAuth()