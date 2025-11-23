import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { FcGoogle } from "react-icons/fc";
import { RiKakaoTalkFill } from "react-icons/ri";
import NotLogin from "../components/NotLogin";
import "../styles/MyInfo.css";

function MyInfo() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    // 상태 관리
    const [isResettingPw, setIsResettingPw] = useState(false);
    const [pwForm, setPwForm] = useState({
        currentPassword: "",
        newPassword: "",
        confirmPassword: ""
    });
    
    // 실시간 메시지 상태
    const [passwordMessage, setPasswordMessage] = useState("");
    const [isPwMatch, setIsPwMatch] = useState(false);

    // 소셜 제공자 표시 헬퍼
    const getProviderDisplay = (provider) => {
        if (provider === 'kakao') return <span><RiKakaoTalkFill /> 카카오 로그인</span>;
        if (provider === 'google') return <span><FcGoogle /> 구글 로그인</span>;
        return <span>Social Login</span>;
    };

    // 날짜 포맷팅
    const formatDate = (dateString) => {
        if (!dateString) return "-";
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR', { 
            year: 'numeric', month: 'long', day: 'numeric'
        });
    };

    // 입력 핸들러 및 실시간 검증
    const handlePwChangeInput = (e) => {
        const { name, value } = e.target;
        const updatedForm = { ...pwForm, [name]: value };
        setPwForm(updatedForm);

        // 변경할 비밀번호와 확인 비밀번호가 둘 다 입력되었을 때만 검사
        if (name === "newPassword" || name === "confirmPassword") {
            const newPw = name === "newPassword" ? value : pwForm.newPassword;
            const confirmPw = name === "confirmPassword" ? value : pwForm.confirmPassword;

            if (newPw && confirmPw) {
                if (newPw === confirmPw) {
                    setPasswordMessage("비밀번호가 일치합니다.");
                    setIsPwMatch(true);
                } else {
                    setPasswordMessage("비밀번호가 일치하지 않습니다.");
                    setIsPwMatch(false);
                }
            } else {
                setPasswordMessage("");
                setIsPwMatch(false);
            }
        }
    };

    // 비밀번호 변경 요청
    const handleSubmitPassword = async () => {
        if (!pwForm.currentPassword || !pwForm.newPassword || !pwForm.confirmPassword) {
            alert("모든 필드를 입력해주세요.");
            return;
        }
        
        if (!isPwMatch) {
            alert("변경할 비밀번호가 일치하지 않습니다.");
            return;
        }

        try {
            // 1단계: 현재 비밀번호 검증
            const formData = new URLSearchParams();
            formData.append("username", user.username);
            formData.append("password", pwForm.currentPassword);

            const loginResponse = await fetch("http://localhost:8000/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData
            });

            if (!loginResponse.ok) {
                alert("현재 비밀번호가 일치하지 않습니다.");
                return;
            }

            // 2단계: 검증 성공 시 비밀번호 변경 요청
            const token = localStorage.getItem("access_token");
            const updateResponse = await fetch("http://localhost:8000/users/me", {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ password: pwForm.newPassword })
            });

            if (updateResponse.ok) {
                alert("비밀번호가 변경되었습니다. 다시 로그인해주세요.");
                logout(); 
                navigate("/login");
            } else {
                const errorData = await updateResponse.json();
                alert(`변경 실패: ${errorData.detail}`);
            }
        } catch (error) {
            console.error("비밀번호 변경 오류:", error);
            alert("서버 오류가 발생했습니다.");
        }
    };

    // 회원 탈퇴 모달
    const [showWithdrawModal, setShowWithdrawModal] = useState(false);
    const handleWithdraw = async () => {
        try {
            const token = localStorage.getItem("access_token");
            const response = await fetch("http://localhost:8000/users/me", {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (response.ok) {
                alert("회원 탈퇴가 완료되었습니다.");
                logout();
                navigate("/");
            } else {
                const errorData = await response.json();
                alert(`탈퇴 실패: ${errorData.detail}`);
            }
        } catch (error) {
            console.error("회원 탈퇴 오류:", error);
            alert("서버 오류가 발생했습니다.");
        }
    };

    return (
        <div className="page-container">
            {user ? (
                <div className="myinfo-content">
                    <div className="myinfo-header">
                        <h1>내 정보</h1>
                        <p>고객님의 소중한 회원 정보입니다.</p>
                    </div>

                    <div className="user-info-card">
                        <div className="info-section">
                            <h3>기본 정보</h3>
                            <div className="info-grid">
                                <span className="info-label">계정 유형</span>
                                <span className="info-value">
                                    {user.is_social ? getProviderDisplay(user.social_provider) : "일반 로그인"}
                                </span>
                                <span className="info-label">이메일</span>
                                <span className="info-value">{user.email}</span>
                                <span className="info-label">이름</span>
                                <span className="info-value">{user.name}</span>
                                <span className="info-label">가입일</span>
                                <span className="info-value">{formatDate(user.created_at)}</span>
                            </div>
                        </div>

                        {!user.is_social && (
                            <>
                                <div className="info-section">
                                    <h3>추가 정보</h3>
                                    <div className="info-grid">
                                        <span className="info-label">아이디</span>
                                        <span className="info-value">{user.username}</span>
                                        <span className="info-label">전화번호</span>
                                        <span className="info-value">{user.phone_number || "-"}</span>
                                    </div>
                                </div>

                                <div className="info-section password-section">
                                    <h3>보안 설정</h3>
                                    {!isResettingPw ? (
                                        <button 
                                            className="btn-reset-pw"
                                            onClick={() => setIsResettingPw(true)}
                                        >
                                            비밀번호 변경하기
                                        </button>
                                    ) : (
                                        <div className="password-form">
                                            <div className="form-group">
                                                <label>현재 비밀번호</label>
                                                <input 
                                                    type="password" 
                                                    name="currentPassword"
                                                    value={pwForm.currentPassword}
                                                    onChange={handlePwChangeInput}
                                                    placeholder="사용 중인 비밀번호를 입력하세요"
                                                />
                                            </div>
                                            <div className="form-group">
                                                <label>새 비밀번호</label>
                                                <input 
                                                    type="password" 
                                                    name="newPassword"
                                                    value={pwForm.newPassword}
                                                    onChange={handlePwChangeInput}
                                                    placeholder="변경할 비밀번호를 입력하세요"
                                                />
                                            </div>
                                            <div className="form-group">
                                                <label>새 비밀번호 확인</label>
                                                <input 
                                                    type="password" 
                                                    name="confirmPassword"
                                                    value={pwForm.confirmPassword}
                                                    onChange={handlePwChangeInput}
                                                    placeholder="비밀번호를 한 번 더 입력하세요"
                                                />
                                                <span className={`pw-check-msg ${isPwMatch ? "success" : "error"}`}>
                                                    {passwordMessage}
                                                </span>
                                            </div>
                                            <div className="btn-group">
                                                <button className="btn-confirm" onClick={handleSubmitPassword}>변경 완료</button>
                                                <button 
                                                    className="btn-cancel" 
                                                    onClick={() => {
                                                        setIsResettingPw(false);
                                                        setPwForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
                                                        setPasswordMessage("");
                                                    }}
                                                >
                                                    취소
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>

                    <div className="withdraw-section">
                        <button 
                            className="btn-withdraw" 
                            onClick={() => setShowWithdrawModal(true)}
                        >
                            회원 탈퇴하기
                        </button>
                    </div>

                    {showWithdrawModal && (
                        <div className="modal-overlay">
                            <div className="modal-content">
                                <h3>회원 탈퇴</h3>
                                <p>정말로 탈퇴하시겠습니까?<br/>탈퇴 시 모든 정보가 삭제되며<br/>복구할 수 없습니다.</p>
                                <div className="modal-actions">
                                    <button className="btn-danger" onClick={handleWithdraw}>탈퇴</button>
                                    <button className="btn-secondary" onClick={() => setShowWithdrawModal(false)}>취소</button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                <NotLogin />
            )}
        </div>
    );
}

export default MyInfo;