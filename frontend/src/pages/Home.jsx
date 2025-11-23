import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaRegHeart, FaHeart } from "react-icons/fa";
import "../styles/Home.css";

function Home() {
    const navigate = useNavigate();
    const [marketType, setMarketType] = useState('ALL');
    const [rankType, setRankType] = useState('volume');
    const [stockList, setStockList] = useState([]);
    const [favorites, setFavorites] = useState(new Set());

    const isMarketOpen = () => {
        const now = new Date();
        const day = now.getDay();
        const hours = now.getHours();
        const minutes = now.getMinutes();
        if (day === 0 || day === 6) return false;
        const currentTime = hours * 100 + minutes;

        if (marketType === 'ALL') {
            return (currentTime >= 900 && currentTime < 1600) || (currentTime >= 2230 || currentTime < 500);
        } 
        if (marketType === 'DOMESTIC') {
            return currentTime >= 900 && currentTime < 1600;
        } 
        return (currentTime >= 2230 || currentTime < 500);
    };

    const fetchFavorites = async () => {
        try {
            const token = localStorage.getItem('accessToken');
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

    const fetchRankings = async () => {
        try {
            const res = await fetch(
                `http://localhost:8000/stocks/rank/${rankType}?market_type=${marketType}`
            );
            if (res.ok) {
                setStockList(await res.json());
            } else {
                setStockList([]);
            }
        } catch (error) {
            console.error("Fetch Error:", error);
            setStockList([]);
        }
    };

    useEffect(() => {
        fetchFavorites();
        fetchRankings();

        let interval = null;
        if (isMarketOpen()) {
            interval = setInterval(fetchRankings, 5000);
        }
        return () => interval && clearInterval(interval);
    }, [rankType, marketType]);

    const toggleFavorite = async (e, code) => {
        e.stopPropagation();
        const token = localStorage.getItem('accessToken');

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

    return (
        <div className="home-container">
            <h1>실시간 차트</h1>
            <hr></hr>
            <div className="button-container">
                <p>전체/국내/해외 시장과 거래량, 시가총액 등 순위를 선택할 수 있어요.</p>
                {/* 시장 구분 */}
                <div className="market-btn-group">
                    <button
                        className={`market-btn ${marketType === 'ALL' ? 'active' : ''}`}
                        onClick={() => setMarketType('ALL')}
                    >
                        전체
                    </button>

                    <button
                        className={`market-btn ${marketType === 'DOMESTIC' ? 'active' : ''}`}
                        onClick={() => setMarketType('DOMESTIC')}
                    >
                        국내
                    </button>

                    <button
                        className={`market-btn ${marketType === 'OVERSEAS' ? 'active' : ''}`}
                        onClick={() => setMarketType('OVERSEAS')}
                    >
                        해외
                    </button>
                </div>

                {/* 탭 */}
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

            {/* 테이블 */}
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
                                onClick={() => navigate(`/stock/${stock.code}`)}
                            >
                                <td>
                                    <span 
                                        className={`fav-btn ${favorites.has(stock.code) ? 'on' : ''}`}
                                        onClick={(e) => toggleFavorite(e, stock.code)}
                                    >
                                        {favorites.has(stock.code) ? <FaHeart /> : <FaRegHeart />}
                                    </span>
                                </td>

                                <td>
                                    <div className={getRankStyle(index + 1)}>
                                        {index + 1}
                                    </div>
                                </td>

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
