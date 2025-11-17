import { Link } from "react-router-dom";
import { FcGoogle } from "react-icons/fc";
import { RiKakaoTalkFill } from "react-icons/ri";
import Logo from "../components/Logo";
import "../styles/AuthPage.css";

function LoginPage() {
    return (
        <div className="auth-container">
            <div className="auth-card">
                <div className="mini-logo">
                    <Logo v="mini" />
                </div>
                <h2 className="auth-title">로그인</h2>
                <form action="" className="login-form">
                    <div className="auth-input-group">
                        <input type="text" id="username" placeholder="아이디" required />
                    </div>
                    <div className="auth-input-group">
                        <input type="password" id="password" placeholder="비밀번호" required />
                    </div>
                    <div className="login-options">
                        <label htmlFor="" className="remember-me">
                            <input type="checkbox" /> 로그인유지
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
                    <button className="social-button kakao">
                        <RiKakaoTalkFill />
                        카카오 로그인
                    </button>
                    <button className="social-button google">
                        <FcGoogle />
                        구글 로그인
                    </button>
                </div>
            </div>
        </div>
    )
}
export default LoginPage;