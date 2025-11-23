import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { createChart, ColorType, CandlestickSeries, LineSeries } from 'lightweight-charts';
import '../styles/StockDetail.css';

const StockDetail = () => {
    const { market, symbol } = useParams();
    const [detail, setDetail] = useState(null);
    const [chartData, setChartData] = useState([]);
    const [tradesData, setTradesData] = useState({ trades: [], vol_power: "0.00" }); 
    
    // 차트 설정 상태
    const [period, setPeriod] = useState('D'); 
    const [minuteValue, setMinuteValue] = useState('1m'); 
    const [chartType, setChartType] = useState('candle');
    
    const chartContainerRef = useRef(null);
    const chartInstanceRef = useRef(null);

    // 1. 데이터 로딩
    useEffect(() => {
        const fetchData = async () => {
            try {
                // 상세 정보
                const infoRes = await fetch(`http://localhost:8000/stocks/${market}/${symbol}/detail`);
                if (infoRes.ok) setDetail(await infoRes.json());

                // 차트 데이터
                const queryPeriod = period === 'minute' ? minuteValue : period;
                const chartRes = await fetch(`http://localhost:8000/stocks/${market}/${symbol}/chart?period=${queryPeriod}`);
                if (chartRes.ok) {
                    const rawData = await chartRes.json();
                    const formatted = rawData.map(item => {
                        let timeVal;
                        if (period === 'minute' || (item.time && item.time.includes(':'))) {
                            timeVal = new Date(item.time).getTime() / 1000; 
                        } else {
                            timeVal = item.time;
                        }
                        return {
                            time: timeVal,
                            open: item.open, high: item.high, low: item.low, close: item.close,
                            value: item.close
                        };
                    });
                    const uniqueData = [...new Map(formatted.map(item => [item.time, item])).values()];
                    uniqueData.sort((a, b) => (a.time > b.time ? 1 : -1));
                    setChartData(uniqueData);
                }

                // 체결 내역 (시세)
                const tradesRes = await fetch(`http://localhost:8000/stocks/${market}/${symbol}/trades`);
                if (tradesRes.ok) setTradesData(await tradesRes.json());

            } catch (err) {
                console.error("API Error:", err);
            }
        };
        fetchData();
    }, [market, symbol, period, minuteValue]);

    // 2. 차트 생성
    useEffect(() => {
        if (!chartContainerRef.current) return;

        if (chartInstanceRef.current) {
            try { chartInstanceRef.current.remove(); } catch (e) {}
            chartInstanceRef.current = null;
        }

        const chart = createChart(chartContainerRef.current, {
            layout: { background: { type: ColorType.Solid, color: 'white' } },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            rightPriceScale: { borderVisible: false },
            timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
            grid: { vertLines: { color: '#f0f3fa' }, horzLines: { color: '#f0f3fa' } },
        });

        chartInstanceRef.current = chart;

        if (chartData.length > 0) {
            try {
                let series;
                if (chartType === 'candle') {
                    series = chart.addSeries(CandlestickSeries, {
                        upColor: '#ef5350', downColor: '#26a69a',
                        borderVisible: false, wickUpColor: '#ef5350', wickDownColor: '#26a69a',
                    });
                } else {
                    series = chart.addSeries(LineSeries, { color: '#2962FF', lineWidth: 2 });
                }
                series.setData(chartData);
                chart.timeScale().fitContent();
            } catch (e) {
                console.error("Series Error:", e);
            }
        }

        const handleResize = () => {
            if (chartContainerRef.current && chartInstanceRef.current) {
                chartInstanceRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (chartInstanceRef.current) {
                try { chartInstanceRef.current.remove(); } catch (e) {}
                chartInstanceRef.current = null;
            }
        };
    }, [chartData, chartType]);

    if (!detail) return <div style={{padding:'50px', textAlign:'center'}}>로딩 중...</div>;

    const safeNum = (val) => {
        if (!val || val === 'NaN') return 0;
        const num = parseFloat(val.toString().replace(/,/g, ''));
        return isNaN(num) ? 0 : num;
    };

    const formatTime = (t) => {
        if (!t) return '-';
        if (t.includes(':')) return t; 
        return `${t.substr(0,2)}:${t.substr(2,2)}:${t.substr(4,2)}`;
    };

    const formatMarketCap = (val) => {
        const num = safeNum(val);
        if (num === 0) return '-';
        if (num >= 10000) {
            const jo = Math.floor(num / 10000);
            const eok = Math.floor(num % 10000);
            return `${jo}조 ${eok}억`;
        } else {
            return `${Math.floor(num)}억`;
        }
    };

    // 전일대비 색상 (등락률 기준)
    const getColor = (val) => {
        const num = parseFloat(val);
        if (num > 0) return 'up';
        if (num < 0) return 'down';
        return '';
    };

    // [신규] 체결가 색상 (직전 체결가 대비)
    const getTradeColor = (currentPrice, prevPrice) => {
        if (!prevPrice) return 'black';
        if (currentPrice > prevPrice) return 'up';
        if (currentPrice < prevPrice) return 'down';
        return 'black';
    };

    return (
        <div className="stock-detail-container">
            <header className="detail-header">
                <div className="title-section">
                    <h1>{detail.name || symbol} <span className="market-badge">{detail.market}</span></h1>
                    <p className="stock-code">{detail.code}</p>
                </div>
                <div className="price-section">
                    <h2 className={`price ${getColor(detail.diff)}`}>
                        {safeNum(detail.price).toLocaleString()}원
                    </h2>
                    <span className={`change ${getColor(detail.diff)}`}>
                        <span className="date-label">{detail.date}</span>
                        {safeNum(detail.diff) > 0 ? '▲' : '▼'} {Math.abs(safeNum(detail.diff)).toLocaleString()} ({detail.change_rate}%)
                    </span>
                </div>
            </header>

            <section className="chart-section">
                <div className="chart-controls">
                    <div className="period-btn-group-container">
                        <select 
                            className={`period-select ${period === 'minute' ? 'active' : ''}`}
                            value={period === 'minute' ? minuteValue : ''}
                            onChange={(e) => { setPeriod('minute'); setMinuteValue(e.target.value); }}
                        >
                            <option value="" disabled>분봉</option>
                            <option value="1m">1분</option><option value="5m">5분</option>
                            <option value="10m">10분</option><option value="30m">30분</option><option value="60m">60분</option>
                        </select>
                        <div className="period-divider"></div>
                        <div className="period-btn-group">
                            {['D', 'W', 'M', 'Y'].map((p) => <button key={p} onClick={() => setPeriod(p)} className={period === p ? 'active' : ''}>{p}</button>)}
                        </div>
                    </div>
                    <div className="type-btn-group">
                        <button onClick={() => setChartType('candle')} className={chartType === 'candle' ? 'active' : ''}>봉</button>
                        <button onClick={() => setChartType('line')} className={chartType === 'line' ? 'active' : ''}>라인</button>
                    </div>
                </div>
                <div className="chart-wrapper" ref={chartContainerRef} style={{ position: 'relative', width: '100%' }}></div>
            </section>

            <section className="trades-section">
                <div className="trades-header-row">
                    <h3>실시간 체결</h3>
                    {/* 체결강도는 여기 한 번만 표시 */}
                    <span className="vol-power-badge">체결강도: <strong className={getColor(parseFloat(tradesData.vol_power) - 100)}>{tradesData.vol_power}%</strong></span>
                </div>
                <div className="trades-table-header">
                    <span>시간</span>
                    <span>체결가</span>
                    <span>전일대비</span>
                    <span>체결량</span>
                    <span>거래량(누적)</span>
                </div>
                <div className="trades-table-body">
                    {tradesData.trades.map((t, i) => {
                        // 직전 체결가 (리스트의 다음 항목이 시간상 이전임)
                        const prevTrade = tradesData.trades[i + 1];
                        const currentPrice = parseInt(t.price);
                        const prevPrice = prevTrade ? parseInt(prevTrade.price) : currentPrice;
                        const tradeColor = getTradeColor(currentPrice, prevPrice);

                        return (
                            <div key={i} className="trade-row">
                                <span className="time">{formatTime(t.time)}</span>
                                {/* 체결가는 직전대비 색상 */}
                                <span className={`price ${tradeColor}`}>
                                    {currentPrice.toLocaleString()}
                                </span>
                                {/* 등락률은 전일대비 색상 */}
                                <span className={`diff ${getColor(t.diff)}`}>
                                    {parseInt(t.diff) > 0 ? '+' : ''}{parseInt(t.diff).toLocaleString()} ({t.rate}%)
                                </span>
                                <span className={`vol ${tradeColor}`}>{parseInt(t.volume).toLocaleString()}</span>
                                <span className="total-vol">{t.total_vol !== '-' ? parseInt(t.total_vol).toLocaleString() : '-'}</span>
                            </div>
                        );
                    })}
                </div>
            </section>

            <section className="financial-grid">
                <InfoCard title="시가총액" value={formatMarketCap(detail.market_cap)} />
                <InfoCard title="PER" value={`${detail.per}배`} />
                <InfoCard title="PBR" value={`${detail.pbr}배`} />
                <InfoCard title="EPS" value={`${safeNum(detail.eps).toLocaleString()}원`} />
                <InfoCard title="ROE" value={`${detail.roe}%`} />
                <InfoCard title="상장주식수" value={safeNum(detail.shares_outstanding).toLocaleString()} />
            </section>
        </div>
    );
};

const InfoCard = ({ title, value }) => (
    <div className="info-card"><span className="label">{title}</span><span className="value">{value}</span></div>
);

export default StockDetail;