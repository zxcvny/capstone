from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy import update 
from datetime import datetime, timedelta, timezone

from app.models.user_model import User, SocialAccount, AuthProvider, RefreshToken
from app.schemas.user_schemas import UserUpdate
from app.core.config import settings
from app.core.security import hash_password

import uuid

class UserService:
    async def get_user_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """ID로 마스터 사용자 조회"""
        result = await db.execute(select(User).where(User.user_id == user_id))
        return result.scalars().first()
    
    async def get_user_by_username_or_email(self, db: AsyncSession, username_or_email: str) -> User | None:
        """이메일 또는 유저이름으로 마스터 사용자 조회"""
        result = await db.execute(
            select(User).where(
                (User.username == username_or_email) | (User.email == username_or_email)
            )
        )
        return result.scalars().first()

    async def get_user_by_social(self, db: AsyncSession, provider: AuthProvider, provider_user_id: str) -> User | None:
        """소셜 계정 정보로 마스터 사용자 찾기"""
        result = await db.execute(
            select(SocialAccount)
            .where(SocialAccount.provider == provider, SocialAccount.provider_user_id == provider_user_id)
            .options(joinedload(SocialAccount.user)) # User 정보 join
        )
        social_account = result.scalars().first()
        return social_account.user if social_account else None

    async def create_user_general(
        self, 
        db: AsyncSession, 
        username: str,
        email: str,
        password: str,
        name: str,
        phone_number: str | None = None
    ) -> User:
        """일반 회원가입으로 신규 사용자 생성"""
        
        hashed_pass = hash_password(password)
        
        new_user = User(
            username=username,
            email=email, 
            hashed_password=hashed_pass,
            name=name,
            phone_number=phone_number
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return new_user

    async def create_user_social(
        self, 
        db: AsyncSession, 
        provider: AuthProvider, 
        provider_user_id: str, 
        name: str,
        email: str | None = None,
        phone_number: str | None = None
    ) -> User:
        """소셜 로그인으로 신규 사용자 생성"""
        
        new_user = User(
            email=email, 
            name=name,
            phone_number=phone_number
        )
        db.add(new_user)
        await db.flush() # user_id를 받아오기 위해 flush

        new_social_account = SocialAccount(
            user_id=new_user.user_id,
            provider=provider,
            provider_user_id=provider_user_id
        )
        db.add(new_social_account)
        
        await db.commit()
        await db.refresh(new_user)
        
        return new_user

    async def get_or_create_user_social(
        self, 
        db: AsyncSession, 
        provider: AuthProvider, 
        provider_user_id: str, 
        name: str,
        email: str | None = None,
        phone_number: str | None = None
    ) -> User:
        """소셜 로그인 시 사용자 조회 또는 생성"""
        
        user = await self.get_user_by_social(db, provider, provider_user_id)
        if user:
            return user
        
        # 이메일이 이미 존재하면 계정 통합 로직 추가(나중에)
        
        user = await self.create_user_social(db, provider, provider_user_id, name, email, phone_number)
        return user
    
    async def save_refresh_token(
        self, 
        db: AsyncSession, 
        user_id: uuid.UUID, 
        token: str,
    ) -> RefreshToken:
        """
        Refresh Token을 DB에 저장
        """
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        expires_at = datetime.now(timezone.utc) + expires_delta

        new_token = RefreshToken(
            user_id=user_id,
            token=token, # 암호화되지 않은 실제 토큰 (보안 강화를 위해 해싱할 수도 있음)
            expires_at=expires_at,
        )
        db.add(new_token)
        await db.commit()
        await db.refresh(new_token)
        return new_token

    async def get_user_by_refresh_token(
        self, 
        db: AsyncSession, 
        token: str
    ) -> User | None:
        """
        (토큰 재발급 시 사용)
        유효한 Refresh Token으로 사용자 조회
        """
        result = await db.execute(
            select(RefreshToken)
            .where(
                RefreshToken.token == token,
                RefreshToken.is_revoked == False, # 폐기되지 않았고
                RefreshToken.expires_at > datetime.now(timezone.utc) # 만료되지 않은
            )
            .options(joinedload(RefreshToken.user)) # User 정보 join
        )
        refresh_token_obj = result.scalars().first()

        if refresh_token_obj:
            refresh_token_obj.is_revoked = True
            db.add(refresh_token_obj)
            await db.commit()

            return refresh_token_obj.user
        return None
    
    async def update_user(
        self, 
        db: AsyncSession, 
        user: User,
        user_in: UserUpdate
    ) -> User:
        """사용자 정보(이름, 이메일, 폰, 비밀번호) 업데이트"""
        
        update_data = user_in.model_dump(exclude_unset=True)

        if "password" in update_data:
            hashed_pass = hash_password(update_data["password"])
            user.hashed_password = hashed_pass
            del update_data["password"]
        
        for field, value in update_data.items():
            setattr(user, field, value)
            
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def deactivate_user(
        self, 
        db: AsyncSession, 
        user: User
    ) -> None:
        """
        사용자 비활성화 (회원 탈퇴)
        - is_active를 False로 설정
        - 모든 Refresh Token을 폐기(revoke)
        """
        user.is_active = False
        db.add(user)
        
        # 이 사용자의 모든 유효한 리프레시 토큰을 폐기
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.user_id,
                RefreshToken.is_revoked == False
            )
            .values(is_revoked=True)
        )
        
        await db.commit()

user_service = UserService()