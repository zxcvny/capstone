import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { IoSearchOutline } from "react-icons/io5";
import Logo from "./Logo";
import { useAuth } from "../context/AuthContext";

function Header() {
    const [keyword, setKeyword] = useState("");
    const [results, setResults] = useState([]);
    const [showResults, setShowResults] = useState(false);
    const navigate = useNavigate();
    const searchRef = useRef(null);
    const { user, logout } = useAuth(); // user 정보와 로그아웃 함수 가져오기

    useEffect(() => {
        const fetchStocks = async () => {
            if (keyword.length < 1) {
                setResults([]);
                return;
            }
            try {
                const response = await fetch(`http://localhost:8000/stocks/search?keyword=${keyword}`);
                if (response.ok) {
                    const data = await response.json();
                    setResults(data);
                    setShowResults(true);
                }
            } catch (error) {
                console.error("검색 실패:", error);
            }
        };

        const debounce = setTimeout(() => {
            fetchStocks();
        }, 300);

        return () => clearTimeout(debounce);
    }, [keyword]);

    useEffect(() => {
        function handleClickOutside(event) {
            if (searchRef.current && !searchRef.current.contains(event.target)) {
                setShowResults(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    const handleStockClick = (code) => {
        setKeyword("");
        setShowResults(false);
        navigate(`/stock/${code}`);
    };

    // 숫자 포맷팅 함수 (콤마 추가)
    const formatPrice = (price) => {
        if (!price || price === "-") return "-";
        return parseInt(price).toLocaleString();
    };

    return (
        <header className="header-container">
            <div className="header-content-wrapper">
                <div className="header-logo">
                    <Logo />
                </div>
                
                <div className="header-search" ref={searchRef}>
                    <form className="search-form" onSubmit={(e) => e.preventDefault()}>
                        <IoSearchOutline className="search-icon" />
                        <input
                            type="text"
                            className="search-input"
                            placeholder="종목명 검색"
                            value={keyword}
                            onChange={(e) => setKeyword(e.target.value)}
                            onFocus={() => { if(results.length > 0) setShowResults(true); }}
                        />
                    </form>

                    {showResults && results.length > 0 && (
                        <ul className="search-results-dropdown">
                            {results.map((stock) => {
                                // 등락률에 따른 색상 클래스 결정
                                const rate = parseFloat(stock.change_rate);
                                const rateClass = rate > 0 ? "up" : rate < 0 ? "down" : "";
                                
                                return (
                                    <li key={stock.code} onClick={() => handleStockClick(stock.code)}>
                                        <div className="search-result-left">
                                            <span className="stock-name">{stock.name}</span>
                                            <span className="stock-code">({stock.code})</span>
                                        </div>
                                        <div className="search-result-right">
                                            <span className={`stock-price ${rateClass}`}>
                                                {formatPrice(stock.price)}원
                                            </span>
                                            <span className={`stock-rate ${rateClass}`}>
                                                {stock.change_rate}%
                                            </span>
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>
                    )}
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
    );
}

export default Header;