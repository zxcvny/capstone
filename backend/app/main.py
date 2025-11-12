from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.lifespan import lifespan
from app.routers import ws_router, users_auth

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # 교차-출처 요청을 보낼 수 있는 출처의 리스트
    allow_credentials=True, # 교차-출처 요청시 쿠키 지원 여부를 설정
    allow_methods=["*"], # 교차-출처 요청을 허용하는 HTTP 메소드의 리스트
    allow_headers=["*"], # 교차-출처를 지원하는 HTTP 요청 헤더의 리스트
)

# 라우터 연결
app.include_router(ws_router.router)
app.include_router(users_auth.router)

@app.get("/")
def read_root():
    return {"message": "Stock API"}