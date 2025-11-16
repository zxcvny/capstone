import { Link } from 'react-router-dom';
import { IoSearchOutline } from "react-icons/io5";
import logo from '../assets/logo.png'

function Header() {
    return(
        <header className="header-container">
            <div className="header-content-wrapper">
                <div className="header-logo">
                    <a href="/"><img src={logo} alt="Zero to Mars Logo" /></a>
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
                    <Link to="login" className="link-to login-btn">로그인</Link>
                </div>
            </div>
        </header>
    )
}
export default Header;