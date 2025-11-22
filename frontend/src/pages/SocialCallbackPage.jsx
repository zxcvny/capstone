import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";

function SocialCallbackPage() {
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        // URL 쿼리 파라미터에서 access_token 추출
        const searchParams = new URLSearchParams(location.search);
        const accessToken = searchParams.get("access_token");
        const error = searchParams.get("error");

        if (error) {
            alert("소셜 로그인 실패");
            navigate("/login");
            return;
        }

        if (accessToken) {
            console.log("소셜 로그인 성공! Access Token:", accessToken);
            // TODO: 토큰을 로컬 스토리지나 상태 관리 라이브러리에 저장
            // localStorage.setItem("access_token", accessToken);
            
            alert("소셜 로그인 성공!");
            navigate("/"); // 메인 페이지로 이동
        } else {
            alert("토큰이 없습니다.");
            navigate("/login");
        }
    }, [location, navigate]);

    return (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '50px' }}>
            <h2>로그인 처리 중...</h2>
        </div>
    );
}

export default SocialCallbackPage;