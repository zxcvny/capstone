import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaLock } from 'react-icons/fa'; // react-icons 설치 시 사용 권장
import '../styles/NotLogin.css';

function NotLogin() {
    const navigate = useNavigate();

    return (
        <div className="not-login-container">
            {/* 자물쇠 아이콘으로 '접근 불가/로그인 필요' 의미 전달 */}
            <div className="not-login-icon">
                <FaLock />
            </div>

            <h2 className="not-login-title">로그인이 필요한 서비스입니다</h2>
            
            <p className="not-login-desc">
                회원님, 해당 페이지는 로그인이 필요합니다.<br />
                로그인 후 나의 투자 내역과 실시간 정보를 확인해보세요.
            </p>

            <div className="not-login-btn-group">
                <button 
                    className="not-login-btn primary" 
                    onClick={() => navigate('/login')}
                >
                    로그인
                </button>
                <button 
                    className="not-login-btn secondary" 
                    onClick={() => navigate('/signup')}
                >
                    회원가입
                </button>
            </div>
        </div>
    );
}

export default NotLogin;