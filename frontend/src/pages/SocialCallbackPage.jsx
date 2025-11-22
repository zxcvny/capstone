import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function SocialCallbackPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuth();
    const processed = useRef(false);

    useEffect(() => {
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
            console.log("소셜 로그인 성공!");
            login(accessToken);
            
            processed.current = true;
            alert("소셜 로그인 성공!");
            navigate("/"); 
        }
    }, [location, navigate, login]);

    return (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '50px' }}>
            <h2>로그인 처리 중...</h2>
        </div>
    );
}

export default SocialCallbackPage;