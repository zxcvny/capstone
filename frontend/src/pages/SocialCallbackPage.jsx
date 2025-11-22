import { useEffect, useRef } from "react"; // useRef 추가
import { useNavigate, useLocation } from "react-router-dom";

function SocialCallbackPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const processed = useRef(false); // 처리 여부를 기록할 ref

    useEffect(() => {
        // 이미 처리되었다면 실행하지 않음
        if (processed.current) return;

        const searchParams = new URLSearchParams(location.search);
        const accessToken = searchParams.get("access_token");
        const error = searchParams.get("error");

        if (error) {
            processed.current = true;
            alert("소셜 로그인 실패");
            navigate("/login");
            return;
        }

        if (accessToken) {
            console.log("소셜 로그인 성공! Access Token:", accessToken);
            // TODO: 토큰 저장 로직 (Context 또는 localStorage 등)
            
            processed.current = true; // 처리 완료 표시
            alert("소셜 로그인 성공!");
            navigate("/"); 
        } else {
            // 토큰이 없는 경우 처리 (useEffect가 두 번 실행될 때 타이밍 이슈 방지)
            // processed.current = true; 
            // alert("토큰이 없습니다.");
            // navigate("/login");
        }
    }, [location, navigate]);

    return (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '50px' }}>
            <h2>로그인 처리 중...</h2>
        </div>
    );
}

export default SocialCallbackPage;