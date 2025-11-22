import { Link } from 'react-router-dom';
import { IoSearchOutline } from "react-icons/io5";
import Logo from "./Logo";
import { useAuth } from "../context/AuthContext";

function Header() {
    const { user, logout } = useAuth(); // user 정보와 로그아웃 함수 가져오기

    return(
        <header className="header-container">
            <div className="header-content-wrapper">
                <div className="header-logo">
                    <Logo />
                </div>
                <div className="header-search">
                    <form action="" className="search-form">
                        <IoSearchOutline className="search-icon" />
                        <input
                        type="text"
                        className="search-input"
                        placeholder="종목 검색"
                        />
                        <button type="submit" style={{ display: 'none' }}></button>
                    </form>
                </div>
                <div className="header-login">
                    {/* user가 있으면 이름 표시, 없으면 로그인 버튼 표시 */}
                    {user ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ fontWeight: 'bold', color: '#212529' }}>{user.name}님</span>
                            <button 
                                onClick={logout} 
                                className="login-btn"
                                style={{ cursor: 'pointer' }} // 스타일 추가 필요 시 css로 이동
                            >
                                로그아웃
                            </button>
                        </div>
                    ) : (
                        <Link to="/login" className="link-to login-btn">로그인</Link>
                    )}
                </div>
            </div>
        </header>
    )
}
export default Header;