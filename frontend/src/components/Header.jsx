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
    const { user, logout } = useAuth();

    useEffect(() => {
        const fetchStocks = async () => {
            if (keyword.length < 1) {
                setResults([]);
                return;
            }
            try {
                // 백엔드에서 market 정보가 포함된 JSON을 반환함
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

    const handleStockClick = (market, code) => {
        // navigate('/stock-detail/' + market + '/' + code);
         navigate(`stock/${market}/${code}`); // 또는 API 호출
    };

    const formatPrice = (price) => {
        if (!price || price === "-") return "-";
        // 백엔드에서 이미 원화 정수로 변환해서 보내주므로 콤마만 찍으면 됨
        return parseInt(price).toLocaleString();
    };

    const handleLogout = () => {
        if (window.confirm("정말 로그아웃 하시겠습니까?")) {
            logout();
        }
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
                                const rate = parseFloat(stock.change_rate);
                                const rateClass = rate > 0 ? "up" : rate < 0 ? "down" : "";
                                
                                // [수정] 마켓 정보(KR/NAS)에 따라 라벨 표시
                                const marketLabel = stock.market === "NAS" ? "미국" : "국내";
                                const marketStyle = {
                                    fontSize: "10px",
                                    padding: "2px 4px",
                                    borderRadius: "4px",
                                    marginRight: "6px",
                                    backgroundColor: stock.market === "NAS" ? "#e3f2fd" : "#f1f3f5",
                                    color: stock.market === "NAS" ? "#1976d2" : "#495057",
                                    fontWeight: "bold"
                                };

                                return (
                                    <li key={stock.code} onClick={() => handleStockClick(stock.market, stock.code)}>
                                        <div className="search-result-left">
                                            {/* 마켓 뱃지 추가 */}
                                            <span style={marketStyle}>{marketLabel}</span>
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
                    {user ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ fontWeight: 'bold', color: '#212529' }}>{user.name}님</span>
                            <button 
                                onClick={handleLogout} 
                                className="logout-btn"
                                style={{ cursor: 'pointer' }}
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