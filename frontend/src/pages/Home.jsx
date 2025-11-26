import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { FaRegHeart, FaHeart } from "react-icons/fa";
import { useAuth } from "../context/AuthContext";
import "../styles/Home.css";

function Home() {
    const navigate = useNavigate();
    const { user } = useAuth();
    
    // 상태 관리
    const [marketType, setMarketType] = useState('ALL');
    const [rankType, setRankType] = useState('volume');
    const [stockList, setStockList] = useState([]);
    const [favorites, setFavorites] = useState(new Set());
    
    // 웹소켓 객체 관리용 Ref
    const wsRef = useRef(null);

    // --------------------------------------------------------------------------
    // 1. 관심 종목 가져오기 (초기 1회)
    // --------------------------------------------------------------------------
    const fetchFavorites = async () => {
        try {
            const token = localStorage.getItem('access_token');
            if (!token) return;
            const res = await fetch('http://localhost:8000/users/me/favorites', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setFavorites(new Set(data.map(item => item.stock_code)));
            }
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        fetchFavorites();
    }, []);

    // --------------------------------------------------------------------------
    // 2. 실시간 랭킹 웹소켓 연결 (핵심 로직)
    // --------------------------------------------------------------------------
    useEffect(() => {
        // 기존 연결이 있다면 종료
        if (wsRef.current) {
            wsRef.current.close();
        }

        // 웹소켓 연결 URL 생성 (쿼리 파라미터로 옵션 전달)
        const wsUrl = `ws://localhost:8000/realtime/rankings?rank_type=${rankType}&market_type=${marketType}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log(`📡 랭킹 소켓 연결됨: ${marketType} - ${rankType}`);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // 데이터가 배열 형태로 정상적으로 오면 State 업데이트
                if (Array.isArray(data)) {
                    setStockList(data);
                }
            } catch (e) {
                console.error("WS 데이터 파싱 에러", e);
            }
        };

        ws.onerror = (error) => {
            console.error("WS 에러:", error);
        };

        // 컴포넌트가 사라지거나 옵션이 바뀔 때 연결 종료 (Clean-up)
        return () => {
            if (ws.readyState === 1) {
                ws.close();
            }
        };
    }, [marketType, rankType]); // 탭을 바꿀 때마다 재연결

    // --------------------------------------------------------------------------
    // 3. 유틸리티 및 이벤트 핸들러
    // --------------------------------------------------------------------------
    const toggleFavorite = async (e, code) => {
        e.stopPropagation();
        const token = localStorage.getItem('access_token'); 

        if (!token) return alert("로그인이 필요합니다.");

        const isFav = favorites.has(code);
        const method = isFav ? 'DELETE' : 'POST';

        try {
            const res = await fetch(
                `http://localhost:8000/users/me/favorites/${code}`,
                {
                    method,
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );
            if (res.ok) {
                const newFavs = new Set(favorites);
                isFav ? newFavs.delete(code) : newFavs.add(code);
                setFavorites(newFavs);
            }
        } catch (e) { console.error(e); }
    };

    const formatNumber = (num) => num ? Number(num).toLocaleString() : '-';

    const formatAmount = (amt) => {
        if (!amt) return '-';
        const num = Number(amt);
        if (num >= 100000000) return (num / 100000000).toFixed(1) + '억';
        if (num >= 10000) return (num / 10000).toFixed(0) + '만';
        return num.toLocaleString();
    };

    const getColor = (rate) => {
        const r = parseFloat(rate);
        return r > 0 ? 'up' : r < 0 ? 'down' : 'none';
    };

    const getRankStyle = (rank) => {
        if (rank === 1) return 'rank rank1';
        if (rank === 2) return 'rank rank2';
        if (rank === 3) return 'rank rank3';
        return 'rank';
    };

    const tabs = [
        { id: 'volume', label: '거래량' },
        { id: 'amount', label: '거래대금' },
        { id: 'cap', label: '시가총액' },
        { id: 'rise', label: '급상승' },
        { id: 'fall', label: '급하락' }
    ];

    // --------------------------------------------------------------------------
    // 4. 렌더링 (JSX)
    // --------------------------------------------------------------------------
    return (
        <div className="home-container">
            {/* 비로그인 사용자 배너 */}
            {!user && (
                <section className="guest-welcome-banner">
                    <div className="banner-content">
                        <h2>투자의 모든 것, 한눈에 확인하세요</h2>
                        <p>국내/해외 실시간 시세 조회부터 관심 종목 관리까지.</p>
                        <p>지금 바로 시작해보세요!</p>
                        <div className="banner-buttons">
                            <Link to="/login" className="link-to banner-btn login-fill">로그인 하러가기</Link>
                            <Link to="/signup" className="link-to banner-btn signup-outline">회원가입</Link>
                        </div>
                    </div>
                </section>
            )}

            <h1>실시간 차트</h1>
            <hr></hr>
            
            <div className="button-container">
                <p>전체/국내/해외 시장과 거래량, 시가총액 등 순위를 선택할 수 있어요.</p>
                
                {/* 시장 구분 버튼 */}
                <div className="market-btn-group">
                    <button className={`market-btn ${marketType === 'ALL' ? 'active' : ''}`} onClick={() => setMarketType('ALL')}>전체</button>
                    <button className={`market-btn ${marketType === 'DOMESTIC' ? 'active' : ''}`} onClick={() => setMarketType('DOMESTIC')}>국내</button>
                    <button className={`market-btn ${marketType === 'OVERSEAS' ? 'active' : ''}`} onClick={() => setMarketType('OVERSEAS')}>해외</button>
                </div>

                {/* 순위 타입 탭 */}
                <div className="tab-wrapper">
                    {tabs.map(tab => (
                        <button 
                            key={tab.id} 
                            className={`tab-btn ${rankType === tab.id ? 'active' : ''}`}
                            onClick={() => setRankType(tab.id)}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* 랭킹 테이블 */}
            <div className="table-wrapper">
                <table className="stock-table">
                    <thead>
                        <tr>
                            <th>관심</th>
                            <th>순위</th>
                            <th>종목명</th>
                            <th>현재가</th>
                            <th>등락률</th>
                            <th>거래량</th>
                            <th>거래대금</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stockList.map((stock, index) => (
                            <tr 
                                key={stock.code} 
                                className="stock-row"
                                onClick={() => {
                                    // 클릭 시 상세 페이지 이동
                                    const targetMarket = stock.market || (marketType === 'DOMESTIC' ? 'KR' : 'NAS');
                                    navigate(`/stock/${targetMarket}/${stock.code}`);
                                }}
                            >
                                <td>
                                    <span 
                                        className={`fav-btn ${favorites.has(stock.code) ? 'on' : ''}`}
                                        onClick={(e) => toggleFavorite(e, stock.code)}
                                    >
                                        {favorites.has(stock.code) ? <FaHeart /> : <FaRegHeart />}
                                    </span>
                                </td>
                                <td><div className={getRankStyle(index + 1)}>{index + 1}</div></td>
                                <td className="stock-name">
                                    <div className="name">{stock.name}</div>
                                    <div className="code">{stock.code}</div>
                                </td>
                                <td className="price">{formatNumber(stock.price)}원</td>
                                <td className={`rate ${getColor(stock.change_rate)}`}>
                                    {stock.change_rate > 0 ? '+' : ''}{parseFloat(stock.change_rate).toFixed(2)}%
                                </td>
                                <td>{formatNumber(stock.volume)}</td>
                                <td>{formatAmount(stock.amount)}</td>
                            </tr>
                        ))}
                        
                        {/* 로딩 표시 (리스트 비었을 때) */}
                        {stockList.length === 0 && (
                            <tr>
                                <td colSpan="7" className="loading">
                                    데이터를 불러오는 중입니다... ⏳
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default Home;