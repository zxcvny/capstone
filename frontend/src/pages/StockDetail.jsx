import React, { useEffect, useState, useLayoutEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

function StockDetail() {
    const { code } = useParams(); 
    const navigate = useNavigate();
    const [detail, setDetail] = useState(null);
    const [chartData, setChartData] = useState([]); 
    const [loading, setLoading] = useState(true);
    const [hoveredCandle, setHoveredCandle] = useState(null);
    const [timeframe, setTimeframe] = useState('일'); // 기본값 '일'
    
    // 차트 너비 반응형 관리
    const chartContainerRef = useRef(null);
    const [chartWidth, setChartWidth] = useState(800);

    const marketType = code && code.length === 6 ? 'DOMESTIC' : 'OVERSEAS';

    // 화면 크기 변경 감지
    useLayoutEffect(() => {
        const handleResize = () => {
            if (chartContainerRef.current) {
                setChartWidth(chartContainerRef.current.offsetWidth - 40);
            }
        };
        window.addEventListener('resize', handleResize);
        handleResize();
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // 데이터 조회 (종목코드나 기간이 바뀌면 재조회)
    useEffect(() => {
        if (code) {
            setLoading(true);
            Promise.all([fetchDetail(), fetchChart()])
                .finally(() => setLoading(false));
        }
    }, [code, timeframe]);

    const fetchDetail = async () => {
        try {
            const res = await fetch(`http://localhost:8000/stocks/detail/${code}?market_type=${marketType}`);
            if (res.ok) {
                const data = await res.json();
                setDetail(data && Object.keys(data).length > 0 ? data : null);
            }
        } catch (err) { console.error("상세 에러:", err); }
    };

    const fetchChart = async () => {
        try {
            // 기간 파라미터 추가 (timeframe)
            // 백엔드에서 '일'->D, '주'->W, '월'->M 등으로 처리하도록 보냄
            const mapTime = { '일': 'D', '주': 'W', '월': 'M', '년': 'Y' };
            const period = mapTime[timeframe] || 'D';

            const res = await fetch(`http://localhost:8000/stocks/chart/${code}?market_type=${marketType}&period=${period}`);
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data) && data.length > 0) {
                    const formattedData = data.map(item => ({
                        date: item.date.length === 8 ? `${item.date.slice(4, 6)}/${item.date.slice(6, 8)}` : item.date,
                        fullDate: item.date,
                        open: Number(item.open),
                        high: Number(item.high),
                        low: Number(item.low),
                        close: Number(item.close),
                        volume: Number(item.volume)
                    }));
                    setChartData(formattedData);
                } else {
                    setChartData([]);
                }
            }
        } catch (err) { console.error("차트 에러:", err); }
    };

    // 이동평균선 계산
    const calculateMA = (data, period) => {
        return data.map((item, index) => {
            if (index < period - 1) return null;
            const sum = data.slice(index - period + 1, index + 1).reduce((acc, curr) => acc + curr.close, 0);
            return sum / period;
        });
    };

    const renderCandleChart = () => {
        const height = 400;
        const padding = { top: 40, right: 60, bottom: 30, left: 10 };
        const drawWidth = chartWidth - padding.left - padding.right;
        const drawHeight = height - padding.top - padding.bottom;

        // 가격 범위
        const allPrices = chartData.flatMap(d => [d.high, d.low]);
        const minPrice = Math.min(...allPrices);
        const maxPrice = Math.max(...allPrices);
        const priceRange = maxPrice - minPrice || 1;
        const pricePadding = priceRange * 0.1;

        // 거래량 범위
        const maxVolume = Math.max(...chartData.map(d => d.volume)) || 1;
        const volumeHeight = 80; // 거래량 바 높이

        // MA
        const ma20 = calculateMA(chartData, 20);
        const ma60 = calculateMA(chartData, 60);

        // 좌표 변환
        const getX = (index) => padding.left + (index * drawWidth) / Math.max(chartData.length - 1, 1);
        const getY = (price) => padding.top + ((maxPrice + pricePadding - price) / (priceRange + pricePadding * 2)) * drawHeight;
        const getVolY = (vol) => height - padding.bottom - (vol / maxVolume) * volumeHeight;

        const candleWidth = Math.max(2, (drawWidth / chartData.length) * 0.6);

        // Y축 라벨 (가격)
        const yTicks = 5;
        const yTickValues = Array.from({length: yTicks}, (_, i) => minPrice + (priceRange * i) / (yTicks - 1));

        const createMAPath = (maData) => {
            const points = maData.map((val, i) => val ? [getX(i), getY(val)] : null).filter(p => p);
            if (!points.length) return '';
            return 'M' + points.map(p => `${p[0]},${p[1]}`).join(' L');
        };

        return (
            <svg width={chartWidth} height={height} style={{overflow: 'visible'}}>
                {/* 그리드 & Y축 라벨 */}
                {yTickValues.map((price, i) => (
                    <g key={`grid-${i}`}>
                        <line x1={padding.left} y1={getY(price)} x2={chartWidth - padding.right} y2={getY(price)} stroke="#f0f0f0" strokeWidth="1" />
                        <text x={chartWidth - padding.right + 5} y={getY(price) + 4} fontSize="11" fill="#999">{price.toLocaleString()}</text>
                    </g>
                ))}

                {/* 이동평균선 */}
                <path d={createMAPath(ma20)} stroke="#fb8c00" strokeWidth="1.5" fill="none" />
                <path d={createMAPath(ma60)} stroke="#43a047" strokeWidth="1.5" fill="none" />

                {/* 캔들 & 거래량 */}
                {chartData.map((d, i) => {
                    const x = getX(i);
                    const isUp = d.close >= d.open;
                    const color = isUp ? '#ef4444' : '#3b82f6'; // 한국식: 상승(빨강), 하락(파랑)
                    const yOpen = getY(d.open);
                    const yClose = getY(d.close);
                    const yHigh = getY(d.high);
                    const yLow = getY(d.low);
                    const barH = Math.max(1, Math.abs(yOpen - yClose));

                    return (
                        <g key={`candle-${i}`} 
                           onMouseEnter={() => setHoveredCandle(d)}
                           onMouseLeave={() => setHoveredCandle(null)}>
                            {/* 캔들 심지 */}
                            <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={color} strokeWidth="1" />
                            {/* 캔들 몸통 */}
                            <rect x={x - candleWidth/2} y={Math.min(yOpen, yClose)} width={candleWidth} height={barH} fill={color} />
                            {/* 거래량 바 */}
                            <rect x={x - candleWidth/2} y={getVolY(d.volume)} width={candleWidth} height={height - padding.bottom - getVolY(d.volume)} fill={color} opacity="0.3" />
                        </g>
                    );
                })}

                {/* X축 라벨 (일부만 표시) */}
                {chartData.map((d, i) => {
                    if (i % Math.ceil(chartData.length / 6) === 0) {
                        return <text key={`x-${i}`} x={getX(i)} y={height - 10} fontSize="11" fill="#999" textAnchor="middle">{d.date}</text>;
                    }
                    return null;
                })}
            </svg>
        );
    };

    // --- 숫자 포맷팅 ---
    const fmt = (val) => val ? Number(val).toLocaleString() : '-';
    const formatAmount = (amt) => {
        if (!amt || amt === "0") return '-';
        const num = Number(amt);
        if (num >= 1000000000000) return (num / 1000000000000).toFixed(2) + '조';
        if (num >= 100000000) return (num / 100000000).toFixed(0) + '억';
        return num.toLocaleString();
    };

    if (loading && !detail) return <div style={{padding:'50px', textAlign:'center'}}>로딩중...</div>;
    if (!detail) return <div style={{padding:'50px', textAlign:'center'}}>데이터가 없습니다.</div>;

    const isUp = parseFloat(detail.change_rate) > 0;
    const colorStyle = { color: isUp ? '#ef4444' : '#3b82f6' };

    return (
        <div style={{ maxWidth: '900px', margin: '0 auto', fontFamily: 'sans-serif', backgroundColor: '#fff', minHeight: '100vh', paddingBottom: '50px' }}>
            
            {/* 1. 헤더 영역 (흰색 배경) */}
            <div style={{ padding: '20px 20px 10px', borderBottom: '1px solid #eee' }}>
                <button onClick={() => navigate(-1)} style={{ border: 'none', background: 'none', fontSize: '14px', color: '#666', cursor: 'pointer', marginBottom: '10px' }}>← 뒤로가기</button>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <div>
                        <h1 style={{ margin: '0', fontSize: '26px', color: '#111', fontWeight: '700' }}>
                            {detail.name}
                        </h1>
                        <div style={{ fontSize: '14px', color: '#888', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>{detail.code}</span>
                            {/* KR/US 뱃지 */}
                            <span style={{ 
                                backgroundColor: marketType === 'DOMESTIC' ? '#e0e7ff' : '#fce7f3', 
                                color: marketType === 'DOMESTIC' ? '#3730a3' : '#9d174d',
                                padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold'
                            }}>
                                {marketType === 'DOMESTIC' ? 'KR' : 'US'}
                            </span>
                        </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '32px', fontWeight: 'bold', ...colorStyle }}>
                            {fmt(detail.price)}<span style={{ fontSize: '16px', color: '#333', fontWeight:'normal' }}>원</span>
                        </div>
                        <div style={{ fontSize: '15px', fontWeight: '500', ...colorStyle }}>
                            {isUp ? '▲' : '▼'} {fmt(Math.abs(detail.change_amt))} ({parseFloat(detail.change_rate).toFixed(2)}%)
                        </div>
                    </div>
                </div>
            </div>

            {/* 2. 차트 컨트롤 & 차트 영역 */}
            <div style={{ padding: '20px' }}>
                <div style={{ display: 'flex', gap: '5px', marginBottom: '10px' }}>
                    {['일', '주', '월', '년'].map((tf) => (
                        <button 
                            key={tf} 
                            onClick={() => setTimeframe(tf)}
                            style={{
                                padding: '6px 12px', borderRadius: '20px', border: '1px solid #ddd', cursor: 'pointer', fontSize: '13px',
                                backgroundColor: timeframe === tf ? '#333' : '#fff',
                                color: timeframe === tf ? '#fff' : '#555',
                                fontWeight: timeframe === tf ? 'bold' : 'normal'
                            }}
                        >
                            {tf}
                        </button>
                    ))}
                </div>

                {/* 호버 정보 표시 */}
                <div style={{ height: '20px', fontSize: '13px', color: '#555', marginBottom: '5px', display: 'flex', gap: '15px' }}>
                    {hoveredCandle ? (
                        <>
                            <span>일자: {hoveredCandle.date}</span>
                            <span>시가: <b style={{color:'#333'}}>{fmt(hoveredCandle.open)}</b></span>
                            <span>종가: <b style={{color:'#333'}}>{fmt(hoveredCandle.close)}</b></span>
                            <span>거래량: {fmt(hoveredCandle.volume)}</span>
                        </>
                    ) : (
                        <span style={{color:'#aaa'}}>차트 위로 마우스를 올려보세요</span>
                    )}
                </div>

                {/* 차트 컨테이너 */}
                <div ref={chartContainerRef} style={{ height: '400px', border: '1px solid #f5f5f5', borderRadius: '8px', padding: '10px' }}>
                    {chartData.length > 0 ? renderCandleChart() : <div style={{height:'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'#ccc'}}>데이터 없음</div>}
                </div>
            </div>

            {/* 3. 상세 지표 그리드 */}
            <div style={{ padding: '0 20px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#333', marginBottom: '15px' }}>투자 정보</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', borderTop: '2px solid #333' }}>
                    <InfoRow label="시가" value={fmt(detail.open)} />
                    <InfoRow label="고가" value={fmt(detail.high)} color="#ef4444" />
                    <InfoRow label="저가" value={fmt(detail.low)} color="#3b82f6" />
                    <InfoRow label="52주 최고" value={fmt(detail.high52)} />
                    <InfoRow label="52주 최저" value={fmt(detail.low52)} />
                    <InfoRow label="거래량" value={fmt(detail.volume)} />
                    <InfoRow label="거래대금" value={formatAmount(detail.amount)} />
                    <InfoRow label="시가총액" value={formatAmount(detail.market_cap)} />
                    <InfoRow label="PER" value={detail.per} />
                    <InfoRow label="PBR" value={detail.pbr} />
                </div>
            </div>
        </div>
    );
}

const InfoRow = ({ label, value, color }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #eee', fontSize: '14px' }}>
        <span style={{ color: '#888' }}>{label}</span>
        <span style={{ fontWeight: '600', color: color || '#333' }}>{value}</span>
    </div>
);

function formatAmount(amt) {
    if (!amt || amt === "0") return '-';
    const num = Number(amt);
    if (num >= 1000000000000) return (num / 1000000000000).toFixed(2) + '조';
    if (num >= 100000000) return (num / 100000000).toFixed(0) + '억';
    return num.toLocaleString();
}

export default StockDetail;