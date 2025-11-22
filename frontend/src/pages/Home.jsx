import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function Home() {
    const navigate = useNavigate();
    const [marketType, setMarketType] = useState('DOMESTIC');
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
        if (currentTime >= 900 && currentTime < 1600) return true;
        return false;
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
        if (marketType === 'OVERSEAS') {
            setStockList([]);
            return;
        }
        try {
            const res = await fetch(`http://localhost:8000/stocks/rank/${rankType}`);
            if (res.ok) {
                const data = await res.json();
                setStockList(data);
            }
        } catch (error) {
            console.error("Fetch Error:", error);
        }
    };

    useEffect(() => {
        fetchFavorites();
        fetchRankings();
        
        let interval = null;
        if (isMarketOpen()) {
            interval = setInterval(fetchRankings, 5000);
        }
        return () => { if (interval) clearInterval(interval); };
    }, [rankType, marketType]);

    const toggleFavorite = async (e, code) => {
        e.stopPropagation();
        const token = localStorage.getItem('accessToken');
        if (!token) {
            alert("로그인이 필요합니다.");
            return;
        }
        const isFav = favorites.has(code);
        const method = isFav ? 'DELETE' : 'POST';
        try {
            const res = await fetch(`http://localhost:8000/users/me/favorites/${code}`, {
                method: method,
                headers: { 'Authorization': `Bearer ${token}` }
            });
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
        return r > 0 ? '#ef4444' : r < 0 ? '#3b82f6' : 'black';
    };
    const getRankStyle = (rank) => {
        const baseStyle = { fontWeight: 'bold', fontSize: '14px', width: '24px', height: '24px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px' };
        if (rank === 1) return { ...baseStyle, backgroundColor: '#FFD700', color: '#fff' };
        if (rank === 2) return { ...baseStyle, backgroundColor: '#C0C0C0', color: '#fff' };
        if (rank === 3) return { ...baseStyle, backgroundColor: '#CD7F32', color: '#fff' };
        return { ...baseStyle, color: '#666' };
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '900px', margin: '0 auto' }}>
            <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
                <button onClick={() => setMarketType('DOMESTIC')} style={{ padding: '10px 20px', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', backgroundColor: marketType === 'DOMESTIC' ? '#222' : '#eee', color: marketType === 'DOMESTIC' ? 'white' : '#333' }}>국내 주식</button>
                <button onClick={() => setMarketType('OVERSEAS')} style={{ padding: '10px 20px', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', backgroundColor: marketType === 'OVERSEAS' ? '#222' : '#eee', color: marketType === 'OVERSEAS' ? 'white' : '#333' }}>해외 주식 (준비중)</button>
            </div>
            <div style={{ marginBottom: '15px', display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom:'5px' }}>
                {[{ id: 'volume', label: '🔥 거래량 상위' }, { id: 'amount', label: '💰 거래대금 상위' }, { id: 'cap', label: '🏢 시가총액 상위' }, { id: 'rise', label: '🚀 급상승' }, { id: 'fall', label: '📉 급하락' }].map(tab => (
                    <button key={tab.id} onClick={() => setRankType(tab.id)} style={{ padding: '8px 16px', borderRadius: '20px', cursor: 'pointer', border: rankType === tab.id ? '2px solid #222' : '1px solid #ddd', backgroundColor: rankType === tab.id ? '#fff' : '#f9f9f9', fontWeight: rankType === tab.id ? 'bold' : 'normal', color: rankType === tab.id ? '#222' : '#666', whiteSpace: 'nowrap' }}>{tab.label}</button>
                ))}
            </div>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                    <thead>
                        <tr style={{ background: '#f8f8f8', color: '#666', fontSize: '13px', borderBottom: '1px solid #ddd' }}><th style={{ padding: '12px', textAlign: 'center', width: '50px' }}>관심</th><th style={{ padding: '12px', textAlign: 'center', width: '50px' }}>순위</th><th style={{ padding: '12px', textAlign: 'left' }}>종목명</th><th style={{ padding: '12px', textAlign: 'right' }}>현재가</th><th style={{ padding: '12px', textAlign: 'right' }}>등락률</th><th style={{ padding: '12px', textAlign: 'right' }}>거래량</th><th style={{ padding: '12px', textAlign: 'right' }}>거래대금</th></tr>
                    </thead>
                    <tbody>
                        {stockList.map((stock, index) => (
                            <tr key={stock.code} onClick={() => navigate(`/stock/${stock.code}`)} style={{ borderBottom: '1px solid #f0f0f0', cursor: 'pointer', height: '60px' }} onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fbfbfb'} onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}>
                                <td style={{ textAlign: 'center' }}><span onClick={(e) => toggleFavorite(e, stock.code)} style={{ fontSize: '20px', color: favorites.has(stock.code) ? '#ff4d4f' : '#e0e0e0', cursor: 'pointer' }}>{favorites.has(stock.code) ? '♥' : '♡'}</span></td>
                                <td style={{ textAlign: 'center' }}><div style={getRankStyle(index + 1)}>{index + 1}</div></td>
                                <td style={{ padding: '12px' }}><div style={{ fontWeight: 'bold', fontSize: '15px' }}>{stock.name}</div><div style={{ fontSize: '12px', color: '#999', marginTop: '2px' }}>{stock.code}</div></td>
                                <td style={{ padding: '12px', textAlign: 'right', fontWeight: '500' }}>{formatNumber(stock.price)}원</td>
                                <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: getColor(stock.change_rate) }}>{stock.change_rate > 0 ? '+' : ''}{parseFloat(stock.change_rate).toFixed(2)}%</td>
                                <td style={{ padding: '12px', textAlign: 'right', color: '#666', fontSize: '13px' }}>{formatNumber(stock.volume)}</td>
                                <td style={{ padding: '12px', textAlign: 'right', color: '#666', fontSize: '13px' }}>{formatAmount(stock.amount)}</td>
                            </tr>
                        ))}
                        {stockList.length === 0 && (<tr><td colSpan="7" style={{ padding: '60px', textAlign: 'center', color: '#999' }}>데이터를 불러오는 중입니다... ⏳</td></tr>)}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default Home;