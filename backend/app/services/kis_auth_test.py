import asyncio
from app.services.kis_auth import kis_auth

async def main():
    token = await kis_auth.get_access_token()
    approval = await kis_auth.get_approval_key()

    print("발급된 Access Token:", token)
    print("발급된 Approval Key:", approval)

if __name__ == "__main__":
    asyncio.run(main())

# (app) C:\capstone\backend>python -m app.services.kis_auth_test