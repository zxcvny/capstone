import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

import { FcGoogle } from "react-icons/fc";
import { RiKakaoTalkFill } from "react-icons/ri";

import Logo from "../components/Logo";
import axios from "../lib/axios";
import "../styles/AuthPage.css";

function SignUpPage() {
    const navigate = useNavigate();

    // --- 입력 상태 ---
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [name, setName] = useState("");
    
    const [emailId, setEmailId] = useState("");
    const [emailDomain, setEmailDomain] = useState("");
    const [customDomain, setCustomDomain] = useState("");

    const [phone, setPhone] = useState({ part1: "", part2: "", part3: "" });

    // --- 검증 상태 ---
    // availability: null(미확인), true(사용가능), false(중복)
    const [availability, setAvailability] = useState({ username: null, email: null });

    // --- 인증 상태 ---
    const [verification, setVerification] = useState({
        isSent: false,        // 인증번호 발송 여부
        code: "",             // 사용자가 입력한 코드
        sentCode: "",         // 서버로부터 받은 정답 코드
        isVerified: false,    // 최종 인증 완료 여부
        timer: 180,           // 입력 제한 시간 (3분)
        canResend: true,      // 재발급 버튼 활성화 여부
        resendTimer: 60,      // 재발급 대기 시간 (1분)
    });

    const timerRef = useRef(null);       // 입력 제한 타이머 ID
    const resendTimerRef = useRef(null); // 재발급 대기 타이머 ID

    // =================================================================
    // 1. 실시간 중복 확인 (Debounce 적용)
    // =================================================================

    // 아이디 중복 확인
    useEffect(() => {
        if (username.length < 5) {
            setAvailability(prev => ({ ...prev, username: null }));
            return;
        }
        // 0.5초 동안 입력이 없으면 API 호출
        const timer = setTimeout(() => checkExistence("username", username), 500);
        return () => clearTimeout(timer);
    }, [username]);

    // 이메일 중복 확인
    useEffect(() => {
        const domain = emailDomain === "etc" ? customDomain : emailDomain;
        if (!emailId || !domain) {
            setAvailability(prev => ({ ...prev, email: null }));
            return;
        }
        const fullEmail = `${emailId}@${domain}`;
        
        const timer = setTimeout(() => checkExistence("email", fullEmail), 500);
        return () => clearTimeout(timer);
    }, [emailId, emailDomain, customDomain]);

    // 중복 확인
    const checkExistence = async (field, value) => {
        try {
            const response = await axios.post("/auth/check-availability", { field, value });

            setAvailability(prev => ({
                ...prev,
                [field]: response.data.available
            }));

        } catch (error) {
            console.error("중복 확인 에러:", error);
            setAvailability(prev => ({ ...prev, [field]: false }));
        }
    };

    // =================================================================
    // 2. 전화번호 인증 로직
    // =================================================================

    const handlePhoneChange = (e, part) => {
        const value = e.target.value.replace(/\D/g, ""); // 숫자만 입력
        setPhone({ ...phone, [part]: value });
    };

    const isPhoneFilled = phone.part1.length === 3 && phone.part2.length >= 3 && phone.part3.length === 4;

    // 인증번호 발송 요청
    const sendVerification = async (e) => {
        e.preventDefault();
        if (!isPhoneFilled) return;
        if (!verification.canResend) return;

        const fullPhone = `${phone.part1}-${phone.part2}-${phone.part3}`;

        try {
            const response = await axios.post("auth/send-verification-code", { phone_number: fullPhone });
            const serverCode = response.data.code;

                // 상태 초기화 및 인증 시작
                setVerification(prev => ({
                    ...prev,
                    isSent: true,
                    sentCode: String(serverCode),
                    code: "",
                    isVerified: false,
                    timer: 180,
                    canResend: false,
                    resendTimer: 60
                }));

                alert(`[인증번호 발송]\n인증번호: ${serverCode}`);
                startTimers();

        } catch (error) {
            console.error("인증번호 요청 에러:", error);
            alert("인증번호 발송 실패. 잠시 후 다시 시도해주세요.")
        }
    };

    // 타이머 시작 함수
    const startTimers = () => {
        // 1. 입력 제한 타이머 (3분)
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => {
            setVerification(prev => {
                if (prev.timer <= 1) {
                    clearInterval(timerRef.current);
                    return { ...prev, timer: 0 };
                }
                return { ...prev, timer: prev.timer - 1 };
            });
        }, 1000);

        // 2. 재발급 대기 타이머 (1분)
        if (resendTimerRef.current) clearInterval(resendTimerRef.current);
        resendTimerRef.current = setInterval(() => {
            setVerification(prev => {
                if (prev.resendTimer <= 1) {
                    clearInterval(resendTimerRef.current);
                    return { ...prev, resendTimer: 0, canResend: true };
                }
                return { ...prev, resendTimer: prev.resendTimer - 1 };
            });
        }, 1000);
    };

    // 인증번호 입력 및 실시간 검증
    const handleCodeChange = (e) => {
        const inputCode = e.target.value.replace(/\D/g, ""); // 숫자만
        
        setVerification(prev => {
            // 입력값과 정답이 일치하고, 시간이 남아있으면 인증 성공
            const isMatch = inputCode === prev.sentCode && prev.timer > 0;
            
            if (isMatch) {
                clearInterval(timerRef.current);       // 타이머 정지
                clearInterval(resendTimerRef.current); // 재발급 타이머 정지
            }

            return {
                ...prev,
                code: inputCode,
                isVerified: isMatch
            };
        });
    };

    // 시간 포맷 (MM:SS)
    const formatTime = (seconds) => {
        const m = String(Math.floor(seconds / 60)).padStart(2, "0");
        const s = String(seconds % 60).padStart(2, "0");
        return `${m}:${s}`;
    };

    // =================================================================
    // 3. 회원가입 제출
    // =================================================================
    const handleSubmit = async (e) => {
        e.preventDefault();
        const domain = emailDomain === "etc" ? customDomain : emailDomain;
        const fullEmail = `${emailId}@${domain}`;
        const fullPhone = `${phone.part1}-${phone.part2}-${phone.part3}`;

        // 최종 유효성 검사
        if (username.length < 5) return alert("아이디는 5자 이상이어야 합니다.");
        if (availability.username !== true) return alert("아이디 중복 확인이 필요합니다.");
        if (availability.email !== true) return alert("이메일 중복 확인이 필요합니다.");
        if (password.length < 6) return alert("비밀번호는 6자 이상이어야 합니다. ");
        if (password !== passwordConfirm) return alert(" 비밀번호가 일치하지 않습니다.");
        if (!verification.isVerified) return alert("전화번호 인증을 완료해주세요.");

        const userData = {
            username: username,
            email: fullEmail,
            password: password,
            name: name,
            phone_number: fullPhone
        };

        try {
            await axios.post("/auth/register", userData);
            alert("회원가입이 완료되었습니다! 로그인 해주세요.");
            navigate("/login");
        } catch (error) {
            console.error("회원가입 요청 에러:", error);
            const msg = error.response?.data?.detail || "회원가입 실패";
            alert(msg);
        }
    };

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
                <h2 className="auth-title">회원가입</h2>
                <form className="signup-form" onSubmit={handleSubmit}>
                    
                    {/* 이메일 입력 */}
                    <div className="auth-input-group email">
                        <input
                            type="text" placeholder="이메일 아이디" className="email-id" required
                            value={emailId} onChange={(e) => setEmailId(e.target.value)}
                        />
                        <span className="email-at">@</span>
                        <div className="email-domain-wrapper">
                            {emailDomain === 'etc' && (
                                <input type="text" placeholder="직접 입력" className="email-custom-domain" required
                                    value={customDomain} onChange={(e) => setCustomDomain(e.target.value)}
                                />
                            )}
                            <select className="email-domain" required value={emailDomain} onChange={(e) => setEmailDomain(e.target.value)}>
                                <option value="">선택</option>
                                <option value="naver.com">naver.com</option>
                                <option value="gmail.com">gmail.com</option>
                                <option value="daum.net">daum.net</option>
                                <option value="etc">직접 입력</option>
                            </select>
                        </div>
                    </div>
                    {/* 이메일 중복 확인 메시지 */}
                    <div className="validation-msg">
                        {emailId && emailDomain && (
                            availability.email === true ? <span className="success">사용 가능한 이메일입니다.</span> :
                            availability.email === false ? <span className="error">이미 사용 중인 이메일입니다.</span> : ""
                        )}
                    </div>

                    {/* 이름 입력 */}
                    <div className="auth-input-group" style={{ paddingBottom: '20px'}}>
                        <input type="text" placeholder="이름" required 
                            value={name} onChange={(e) => setName(e.target.value)}
                        />
                    </div>

                    {/* 아이디 입력 */}
                    <div className="auth-input-group">
                        <input type="text" placeholder="아이디 (5자 이상)" required 
                            value={username} onChange={(e) => setUsername(e.target.value)}
                        />
                    </div>
                    {/* 아이디 중복 확인 메시지 */}
                    <div className="validation-msg">
                        {username.length > 0 && username.length < 5 && <span className="error">5자 이상 입력해주세요.</span>}
                        {username.length >= 5 && (
                            availability.username === true ? <span className="success">사용 가능한 아이디입니다.</span> :
                            availability.username === false ? <span className="error">이미 사용 중인 아이디입니다.</span> : ""
                        )}
                    </div>

                    {/* 비밀번호 입력 */}
                    <div className="auth-input-group">
                        <input type="password" placeholder="비밀번호 (6자 이상)" required 
                            value={password} onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <div className="validation-msg">
                        {password && password.length < 6 && <span className="error">비밀번호는 6자 이상이어야 합니다.</span>}
                    </div>
                    <div className="auth-input-group">
                        <input type="password" placeholder="비밀번호 확인" required 
                            value={passwordConfirm} onChange={(e) => setPasswordConfirm(e.target.value)}
                        />
                    </div>
                    <div className="validation-msg">
                        {password && passwordConfirm && password !== passwordConfirm && <span className="error">비밀번호가 일치하지 않습니다.</span>}
                    </div>

                    {/* 전화번호 입력 */}
                    <div className="auth-input-group phone-number">
                        <input type="text" placeholder="010" maxLength="3" required value={phone.part1} onChange={(e)=>handlePhoneChange(e,'part1')} disabled={verification.isVerified}/>
                        <span>-</span>
                        <input type="text" placeholder="1234" maxLength="4" required value={phone.part2} onChange={(e)=>handlePhoneChange(e,'part2')} disabled={verification.isVerified}/>
                        <span>-</span>
                        <input type="text" placeholder="5678" maxLength="4" required value={phone.part3} onChange={(e)=>handlePhoneChange(e,'part3')} disabled={verification.isVerified}/>
                        
                        <button 
                            type="button"
                            className="auth-verification-btn"
                            onClick={sendVerification}
                            disabled={!isPhoneFilled || (verification.isSent && !verification.canResend) || verification.isVerified}
                        >
                            {verification.isSent ? "재발급" : "인증번호 받기"}
                        </button>
                    </div>
                    {verification.isSent && !verification.canResend && !verification.isVerified && (
                        <div className="validation-msg info">
                            {verification.resendTimer}초 후 재발급 가능
                        </div>
                    )}

                    {/* 인증번호 입력 필드 (동적 생성) */}
                    {verification.isSent && (
                        <div className="auth-input-group verification-code">
                            <input
                                type="text"
                                placeholder="인증번호 6자리"
                                value={verification.code}
                                onChange={handleCodeChange}
                                maxLength="6"
                                disabled={verification.isVerified || verification.timer === 0}
                            />
                            {!verification.isVerified && <span className="timer">{formatTime(verification.timer)}</span>}
                        </div>
                    )}
                    {/* 인증 확인 메시지 */}
                    <div className="validation-msg">
                        {verification.isSent && !verification.isVerified && verification.code.length === 6 && (
                            verification.code !== verification.sentCode 
                            ? <span className="error">인증번호가 일치하지 않습니다.</span>
                            : "" 
                        )}
                        {verification.isVerified && <span className="success">인증이 완료되었습니다.</span>}
                        {verification.isSent && !verification.isVerified && verification.timer === 0 && <span className="error">인증 시간이 만료되었습니다. 재발급 받아주세요.</span>}
                    </div>

                    <button type="submit" className="auth-submit-btn">회원가입</button>
                </form>

                <div className="login-link">
                    <span>이미 계정이 있으신가요?</span>
                    <Link to="/login" className="link-to">로그인</Link>
                </div>

                <div className="divider"><span>또는</span></div>

                <div className="social-login">
                    <button 
                        className="social-button kakao" 
                        type="button" 
                        onClick={() => handleSocialLogin('kakao')}
                    >
                        <RiKakaoTalkFill /> 카카오로 시작하기
                    </button>
                    <button 
                        className="social-button google" 
                        type="button" 
                        onClick={() => handleSocialLogin('google')}
                    >
                        <FcGoogle /> 구글로 시작하기
                    </button>
                </div>
            </div>
        </div>
    );
}

export default SignUpPage;