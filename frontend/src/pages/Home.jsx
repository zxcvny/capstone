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
        // 주말 제외
        if (day === 0 || day === 6) return false;
        
        const currentTime = hours * 100 + minutes;
        
        if (marketType === 'DOMESTIC') {
            // 국내장: 09:00 ~ 16:00
            return currentTime >= 900 && currentTime < 1600;
        } else {
            // 미국장(서머타임 고려 등 복잡하지만 단순화): 한국시간 밤 22:30 ~ 05:00 
            // (간단히 밤 시간대에는 갱신하도록 설정)
            return (currentTime >= 2230 || currentTime < 500);
        }
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
            // 백엔드에 market_type 파라미터 추가 전송
            const res = await fetch(`http://localhost:8000/stocks/rank/${rankType}?market_type=${marketType}`);
            if (res.ok) {
                const data = await res.json();
                setStockList(data);
            } else {
                setStockList([]); // 에러 시 빈 배열
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
        // 장 운영 시간일 때만 주기적 갱신 (옵션)
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

    // 포맷팅 함수들
    const formatNumber = (num) => num ? Number(num).toLocaleString() : '-';
    const formatAmount = (amt) => {
        if (!amt) return '-';
        const num = Number(amt);
        
        // 해외 주식은 단위가 다를 수 있으나 일단 동일 로직 적용
        // (해외 API가 달러 단위로 주면 환율 계산된 원화값인지 확인 필요 - 백엔드에서 원화 변환함)
        if (num >= 100000000) return (num / 100000000).toFixed(1) + '억'; 
        if (num >= 10000) return (num / 10000).toFixed(0) + '만';
        return num.toLocaleString();
    };
    const getColor = (rate) => {
        const r = parseFloat(rate);
        // 해외 주식도 빨강(상승) / 파랑(하락) 기준 동일
        return r > 0 ? '#ef4444' : r < 0 ? '#3b82f6' : 'black';
    };
    
    const getRankStyle = (rank) => {
        const baseStyle = { fontWeight: 'bold', fontSize: '14px', width: '24px', height: '24px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px' };
        if (rank === 1) return { ...baseStyle, backgroundColor: '#FFD700', color: '#fff' };
        if (rank === 2) return { ...baseStyle, backgroundColor: '#C0C0C0', color: '#fff' };
        if (rank === 3) return { ...baseStyle, backgroundColor: '#CD7F32', color: '#fff' };
        return { ...baseStyle, color: '#666' };
    };

    // 탭 설정 (해외주식 API 매핑 고려)
    const tabs = [
        { id: 'volume', label: '🔥 거래량' },
        { id: 'amount', label: '💰 거래대금' },
        { id: 'cap', label: '🏢 시가총액' }, // 해외: market_cap
        { id: 'rise', label: '🚀 급상승' },
        { id: 'fall', label: '📉 급하락' }
    ];

    // 탭 클릭 핸들러 (백엔드 키값 매핑 보정)
    const handleRankTypeChange = (type) => {
        // 백엔드에서 해외 시가총액은 'market_cap'을 사용하므로 변환 필요할 수 있음
        // 하지만 백엔드 kis_data.get_overseas_ranking_data에서 'market_cap' 처리를 'cap'으로 받게 하거나,
        // 여기서 변환해서 보내야 함. 
        // *백엔드 코드에서 rank_type == "market_cap"일때 처리하므로, 
        // 프론트에서는 "cap" 대신 "market_cap"을 보내는게 좋음.
        
        if(marketType === 'OVERSEAS' && type === 'cap') {
             setRankType('market_cap');
        } else {
             setRankType(type);
        }
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '900px', margin: '0 auto' }}>
            {/* 상단 시장 선택 버튼 */}
            <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
                <button onClick={() => { setMarketType('DOMESTIC'); setRankType('volume'); }} 
                    style={{ padding: '10px 20px', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', backgroundColor: marketType === 'DOMESTIC' ? '#222' : '#eee', color: marketType === 'DOMESTIC' ? 'white' : '#333' }}>
                    국내 주식
                </button>
                <button onClick={() => { setMarketType('OVERSEAS'); setRankType('volume'); }} 
                    style={{ padding: '10px 20px', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', backgroundColor: marketType === 'OVERSEAS' ? '#222' : '#eee', color: marketType === 'OVERSEAS' ? 'white' : '#333' }}>
                    해외 주식 (나스닥)
                </button>
            </div>

            {/* 순위 탭 버튼 */}
            <div style={{ marginBottom: '15px', display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom:'5px' }}>
                {tabs.map(tab => {
                    // 실제 상태값과 비교를 위한 키 로직 (해외 시총 예외처리)
                    const isActive = rankType === tab.id || (rankType === 'market_cap' && tab.id === 'cap');
                    
                    return (
                        <button key={tab.id} 
                            onClick={() => handleRankTypeChange(tab.id)} 
                            style={{ padding: '8px 16px', borderRadius: '20px', cursor: 'pointer', border: isActive ? '2px solid #222' : '1px solid #ddd', backgroundColor: isActive ? '#fff' : '#f9f9f9', fontWeight: isActive ? 'bold' : 'normal', color: isActive ? '#222' : '#666', whiteSpace: 'nowrap' }}>
                            {tab.label}
                        </button>
                    )
                })}
            </div>

            {/* 리스트 테이블 */}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                    <thead>
                        <tr style={{ background: '#f8f8f8', color: '#666', fontSize: '13px', borderBottom: '1px solid #ddd' }}>
                            <th style={{ padding: '12px', textAlign: 'center', width: '50px' }}>관심</th>
                            <th style={{ padding: '12px', textAlign: 'center', width: '50px' }}>순위</th>
                            <th style={{ padding: '12px', textAlign: 'left' }}>종목명</th>
                            <th style={{ padding: '12px', textAlign: 'right' }}>현재가</th>
                            <th style={{ padding: '12px', textAlign: 'right' }}>등락률</th>
                            <th style={{ padding: '12px', textAlign: 'right' }}>거래량</th>
                            <th style={{ padding: '12px', textAlign: 'right' }}>거래대금</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stockList.map((stock, index) => (
                            <tr key={stock.code} onClick={() => navigate(`/stock/${stock.code}`)} style={{ borderBottom: '1px solid #f0f0f0', cursor: 'pointer', height: '60px' }} onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fbfbfb'} onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}>
                                <td style={{ textAlign: 'center' }}>
                                    <span onClick={(e) => toggleFavorite(e, stock.code)} style={{ fontSize: '20px', color: favorites.has(stock.code) ? '#ff4d4f' : '#e0e0e0', cursor: 'pointer' }}>
                                        {favorites.has(stock.code) ? '♥' : '♡'}
                                    </span>
                                </td>
                                <td style={{ textAlign: 'center' }}><div style={getRankStyle(index + 1)}>{index + 1}</div></td>
                                <td style={{ padding: '12px' }}>
                                    <div style={{ fontWeight: 'bold', fontSize: '15px' }}>{stock.name}</div>
                                    <div style={{ fontSize: '12px', color: '#999', marginTop: '2px' }}>{stock.code}</div>
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', fontWeight: '500' }}>{formatNumber(stock.price)}원</td>
                                <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: getColor(stock.change_rate) }}>
                                    {stock.change_rate > 0 ? '+' : ''}{parseFloat(stock.change_rate).toFixed(2)}%
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', color: '#666', fontSize: '13px' }}>{formatNumber(stock.volume)}</td>
                                <td style={{ padding: '12px', textAlign: 'right', color: '#666', fontSize: '13px' }}>{formatAmount(stock.amount)}</td>
                            </tr>
                        ))}
                        {stockList.length === 0 && (
                            <tr><td colSpan="7" style={{ padding: '60px', textAlign: 'center', color: '#999' }}>
                                {marketType === 'OVERSEAS' ? '해외 주식 데이터를 불러오는 중...' : '데이터를 불러오는 중입니다... ⏳'}
                            </td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default Home;