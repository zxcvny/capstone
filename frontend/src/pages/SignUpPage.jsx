import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { FcGoogle } from "react-icons/fc";
import { RiKakaoTalkFill } from "react-icons/ri";
import Logo from "../components/Logo";
import "../styles/AuthPage.css";

function SignUpPage() {
    const [emailDomain, setEmailDomain] = useState('');
    const [customDomain, setCustomDomain] = useState('');

    const [phone, setPhone] = useState({ part1: '', part2: '', part3: '' });
    const [verificationCode, setVerificationCode] = useState('');
    const [showVerification, setShowVerification] = useState(false);
    const [timer, setTimer] = useState(180);
    const [isButtonDisabled, setIsButtonDisabled] = useState(true);
    const [buttonText, setButtonText] = useState("인증번호 받기");

    const timerRef = useRef(null);

    // 전화번호 입력 변화 체크
    const handlePhoneChange = (e, part) => {
        const value = e.target.value.replace(/\D/g, ""); // 숫자만
        setPhone({ ...phone, [part]: value });
    }

    // 인증번호 받기 버튼 클릭
    const sendVerification = (e) => {
        e.preventDefault();
        if (isButtonDisabled) return;

        setShowVerification(true);
        setTimer(180); // 타이머 초기화
        setButtonText("인증번호 다시 받기");

        // 타이머 시작
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => {
            setTimer(prev => {
                if (prev <= 1) {
                    clearInterval(timerRef.current);
                    alert("인증 시간이 초과되었습니다.");
                    setShowVerification(false);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
    }

    // 전화번호 입력이 모두 채워졌을 때 버튼 활성화
    useEffect(() => {
        const isComplete = phone.part1.length === 3 && phone.part2.length === 4 && phone.part3.length === 4;
        setIsButtonDisabled(!isComplete);
    }, [phone]);

    // 타이머 표시 포맷
    const formatTime = (seconds) => {
        const m = String(Math.floor(seconds / 60)).padStart(2, "0");
        const s = String(seconds % 60).padStart(2, "0");
        return `${m}:${s}`;
    }

    return (
        <div className="auth-container">
            <div className="auth-card">
                <div className="mini-logo">
                    <Logo v="mini" />
                </div>
                <h2 className="auth-title">회원가입</h2>
                <form className="signup-form">
                    {/* 이메일 */}
                    <div className="auth-input-group email">
                        <input
                            type="text"
                            placeholder="이메일 아이디"
                            className="email-id"
                            required
                        />
                        <span className="email-at">@</span>
                        <div className="email-domain-wrapper">
                            {emailDomain === 'etc' && (
                                <input
                                    type="text"
                                    placeholder="직접 입력"
                                    value={customDomain}
                                    onChange={(e) => setCustomDomain(e.target.value)}
                                    className="email-custom-domain"
                                    required
                                />
                            )}
                            <select
                                className="email-domain"
                                value={emailDomain}
                                onChange={(e) => setEmailDomain(e.target.value)}
                                required
                            >
                                <option value="">선택</option>
                                <option value="naver.com">naver.com</option>
                                <option value="gmail.com">gmail.com</option>
                                <option value="daum.net">daum.net</option>
                                <option value="etc">직접 입력</option>
                            </select>
                        </div>
                    </div>
                    {/* 이름 */}
                    <div className="auth-input-group">
                        <input
                         type="text"
                         placeholder="이름"
                         required
                        />
                    </div>
                    {/* 로그인 아이디 */}
                    <div className="auth-input-group">
                        <input type="text" placeholder="로그인 아이디" required />
                    </div>

                    {/* 비밀번호 */}
                    <div className="auth-input-group">
                        <input type="password" placeholder="비밀번호" required />
                    </div>
                    <div className="auth-input-group">
                        <input type="password" placeholder="비밀번호 확인" required />
                    </div>

                    {/* 전화번호 + 인증번호 버튼 */}
                    <div className="auth-input-group phone-number">
                        <input type="text" placeholder="010" maxLength="3"
                               value={phone.part1} onChange={(e)=>handlePhoneChange(e,'part1')} required />
                        <span>-</span>
                        <input type="text" placeholder="1234" maxLength="4"
                               value={phone.part2} onChange={(e)=>handlePhoneChange(e,'part2')} required />
                        <span>-</span>
                        <input type="text" placeholder="5678" maxLength="4"
                               value={phone.part3} onChange={(e)=>handlePhoneChange(e,'part3')} required />
                        <button className="auth-verification-btn"
                                onClick={sendVerification}
                                disabled={isButtonDisabled}>
                            {buttonText}
                        </button>
                    </div>

                    {/* 인증번호 입력 */}
                    {showVerification && (
                        <div className="auth-input-group verification-code">
                            <input
                                type="text"
                                placeholder="인증번호 입력"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value)}
                                maxLength="6"
                            />
                            <span className="timer">{formatTime(timer)}</span>
                        </div>
                    )}

                    <button type="submit" className="auth-submit-btn">회원가입</button>
                </form>

                <div className="login-link">
                    <span>이미 계정이 있으신가요?</span>
                    <Link to="/login" className="link-to">로그인</Link>
                </div>

                <div className="divider"><span>또는</span></div>

                <div className="social-login">
                    <button className="social-button kakao">
                        <RiKakaoTalkFill /> 카카오로 시작하기
                    </button>
                    <button className="social-button google">
                        <FcGoogle /> 구글로 시작하기
                    </button>
                </div>
            </div>
        </div>
    )
}

export default SignUpPage;
