import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { FcGoogle } from "react-icons/fc";
import { RiKakaoTalkFill } from "react-icons/ri";

import Logo from "../components/Logo";

import { useAuth } from "../context/AuthContext";
import axios from "../lib/axios";

import "../styles/AuthPage.css";

function LoginPage() {
    const navigate = useNavigate();
    const { login } = useAuth()

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loginError, setLoginError] = useState("");

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoginError("");

        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        try {
            const response = await axios.post("/auth/login", formData, {
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            });

            // 로그인 성공 시
            console.log("Access Token:", response.data.access_token)
            login(response.data.access_token);
            navigate("/");

        } catch (error) {
            console.error("로그인 요청 에러:", error);
            // 에러 메시지
            if (error.response && error.response.data) {
                const detail = error.response.data.detail;

                // 1. detail이 문자열이면 그대로 출력
                if (typeof detail === "string") {
                    setLoginError(detail);
                } 
                // 2. detail이 배열/객체면(FastAPI 기본 검증 에러) 첫 번째 메시지를 출력
                else if (Array.isArray(detail) && detail.length > 0) {
                    setLoginError(detail[0].msg || "입력값이 올바르지 않습니다."); // msg 또는 loc 등 확인
                } 
                // 3. 그 외의 경우
                else {
                    setLoginError(JSON.stringify(detail) || "로그인 실패");
                }
            } else {
                setLoginError("서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            }
        }
    };

    // 소셜 로그인
    const handleSocialLogin = (provider) => {
        // axios.defaults.baseURL 사용 가능
        window.location.href = `http://localhost:8000/auth/${provider}/login`;
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
                    
                    {/* 에러 메시지 표시 영역 */}
                    {loginError && (
                        <div className="validation-msg" style={{ marginBottom: '10px'}}>
                            <span className="error">{loginError}</span>
                        </div>
                    )}

                    <div className="login-options">
                        <label htmlFor="remember-check" className="remember-me">
                            {/* 기능 구현은 추후 백엔드 Refresh Token 연동 필요, 현재는 UI만 */}
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