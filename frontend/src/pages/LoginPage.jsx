import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FcGoogle } from "react-icons/fc";
import { RiKakaoTalkFill } from "react-icons/ri";
import Logo from "../components/Logo";
import "../styles/AuthPage.css";

const BASE_URL = "http://localhost:8000";

function LoginPage() {
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const handleLogin = async (e) => {
        e.preventDefault();
        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        try {
            const response = await fetch(`${BASE_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                console.log("Access Token:", data.access_token);
                alert("로그인 성공!");
                navigate("/"); 
            } else {
                const errData = await response.json();
                alert(errData.detail || "로그인에 실패했습니다.");
            }
        } catch (error) {
            console.error("로그인 요청 에러:", error);
            alert("서버 오류가 발생했습니다.");
        }
    };

    // [추가] 소셜 로그인 핸들러
    const handleSocialLogin = (provider) => {
        window.location.href = `${BASE_URL}/auth/${provider}/login`;
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <div className="mini-logo">
                    <Logo v="mini" />
                </div>
                <h2 className="auth-title">로그인</h2>
                <form className="login-form" onSubmit={handleLogin}>
                    <div className="auth-input-group">
                        <input 
                            type="text" 
                            id="username" 
                            placeholder="아이디 또는 이메일" 
                            required 
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                        />
                    </div>
                    <div className="auth-input-group">
                        <input 
                            type="password" 
                            id="password" 
                            placeholder="비밀번호" 
                            required 
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <div className="login-options">
                        <label htmlFor="remember-check" className="remember-me">
                            <input type="checkbox" id="remember-check" /> 로그인유지
                        </label>
                        <Link to="/find-password" className="link-to find-password">비밀번호 찾기</Link>
                    </div>
                    <button type="submit" className="auth-submit-btn">로그인</button>
                </form>
                <div className="signup-link">
                    <span>계정이 없으신가요?</span>
                    <Link to="/signup" className="link-to">회원가입</Link>
                </div>
                <div className="divider">
                    <span>또는</span>
                </div>
                <div className="social-login">
                    <button className="social-button kakao" onClick={() => handleSocialLogin('kakao')}>
                        <RiKakaoTalkFill />
                        카카오 로그인
                    </button>
                    <button className="social-button google" onClick={() => handleSocialLogin('google')}>
                        <FcGoogle />
                        구글 로그인
                    </button>
                </div>
            </div>
        </div>
    )
}
export default LoginPage;