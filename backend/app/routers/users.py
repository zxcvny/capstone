import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.future import select
from app.database import get_db
from app.models.user import User
from app.models.user_stock import UserStock
from app.schemas.user import UserPublic, UserUpdate, MessageResponse
from app.services.user_services import user_service
from app.services.stock_info import stock_info_service
from app.core.security.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users", 
    tags=["User-Profile"],
    dependencies=[Depends(get_current_user)] 
)

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """현재 로그인된 사용자 정보 반환"""
    return current_user

@router.patch("/me", response_model=UserPublic)
async def update_users_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """현재 로그인된 (일반) 사용자 정보 수정"""
    
    # [중요] 소셜 로그인 사용자인지 확인 (hashed_password 유무로 판별)
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소셜 로그인 사용자는 이 정보를 수정할 수 없습니다."
        )
        
    try:
        updated_user = await user_service.update_user(db, user=current_user, user_in=user_in)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"⛔ 사용자 정보 수정 중 예외: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류 발생")

@router.delete("/me", response_model=MessageResponse)
async def delete_users_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """현재 로그인된 사용자 탈퇴 (비활성화)"""
    try:
        await user_service.deactivate_user(db, user=current_user)
        return MessageResponse(message="회원 탈퇴(비활성화) 처리되었습니다.")
    except Exception as e:
        logger.error(f"⛔ 회원 탈퇴 처리 중 예외: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류 발생")


@router.get("/me/favorites")
async def get_my_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """내 관심 종목 조회"""
    result = await db.execute(select(UserStock).where(UserStock.user_id == current_user.user_id))
    stocks = result.scalars().all()
    return stocks

@router.post("/me/favorites/{code}")
async def add_favorite(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """관심 종목 추가"""
    # 중복 체크
    result = await db.execute(
        select(UserStock).where(UserStock.user_id == current_user.user_id, UserStock.stock_code == code)
    )
    if result.scalars().first():
        return {"message": "Already added"}

    name = stock_info_service.get_name(code)
    new_fav = UserStock(user_id=current_user.user_id, stock_code=code, stock_name=name)
    db.add(new_fav)
    await db.commit()
    return {"message": "Added", "code": code, "name": name}

@router.delete("/me/favorites/{code}")
async def remove_favorite(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """관심 종목 삭제"""
    result = await db.execute(
        select(UserStock).where(UserStock.user_id == current_user.user_id, UserStock.stock_code == code)
    )
    fav = result.scalars().first()
    if fav:
        await db.delete(fav)
        await db.commit()
        return {"message": "Deleted"}
    return {"message": "Not found"}