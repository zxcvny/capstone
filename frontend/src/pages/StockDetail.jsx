import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { createChart, ColorType, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts';
import '../styles/StockDetail.css';

const StockDetail = () => {
    const { market, symbol } = useParams();
    const [detail, setDetail] = useState(null);
    const [chartData, setChartData] = useState([]);
    const [tradesData, setTradesData] = useState({ trades: [], vol_power: "0.00" });

    const [period, setPeriod] = useState('realtime');
    const [minuteValue, setMinuteValue] = useState('1m');
    const [chartType, setChartType] = useState('candle');

    const chartContainerRef = useRef(null);
    const chartInstanceRef = useRef(null);
    
    // 시리즈 객체를 업데이트하기 위해 ref로 관리
    const mainSeriesRef = useRef(null);
    const volumeSeriesRef = useRef(null);

    // --------------------------------------------------------------------------
    // 1. 초기 데이터 로딩 (REST API - 최초 1회만 실행)
    // --------------------------------------------------------------------------
    useEffect(() => {
        const fetchData = async () => {
            try {
                // 1) 종목 상세
                const infoRes = await fetch(`http://localhost:8000/stocks/${market}/${symbol}/detail`);
                if (infoRes.ok) setDetail(await infoRes.json());

                // 2) 차트 데이터 (과거 데이터 로딩)
                let queryPeriod = period;
                if (period === 'minute') queryPeriod = minuteValue;
                else if (period === 'realtime') queryPeriod = 'realtime';

                const chartRes = await fetch(
                    `http://localhost:8000/stocks/${market}/${symbol}/chart?period=${queryPeriod}`
                );

                if (chartRes.ok) {
                    const rawData = await chartRes.json();
                    const formatted = rawData.map(item => ({
                        time: item.time, 
                        open: item.open, high: item.high, low: item.low, close: item.close, 
                        value: item.close, volume: item.volume
                    }));
                    
                    // 중복 제거 및 정렬
                    const uniqueData = [...new Map(formatted.map(item => [item.time, item])).values()];
                    uniqueData.sort((a, b) => a.time - b.time);
                    setChartData(uniqueData);
                }

                // 3) 체결 내역 (초기 로딩)
                const tradesRes = await fetch(`http://localhost:8000/stocks/${market}/${symbol}/trades`);
                if (tradesRes.ok) setTradesData(await tradesRes.json());

            } catch (err) {
                console.error("API Error:", err);
            }
        };

        fetchData();
        
        // [수정] setInterval(폴링) 삭제됨! 웹소켓이 대신함.

    }, [market, symbol, period, minuteValue]);

    // --------------------------------------------------------------------------
    // 2. 웹소켓 연결 (실시간 데이터 수신) - [신규 추가]
    // --------------------------------------------------------------------------
    useEffect(() => {
        // 실시간 모드가 아니면 웹소켓 연결 안 함
        if (period !== 'realtime') return;

        // [주의] 백엔드 라우터 주소와 맞춰야 함 (/realtime/stocks/...)
        const ws = new WebSocket(`ws://localhost:8000/realtime/stocks/${symbol}`);

        ws.onopen = () => {
            console.log("✅ WebSocket Connected");
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'trade') {
                // 1) 체결 내역 업데이트
                setTradesData(prev => {
                    const newTrade = {
                        time: data.time,
                        price: data.price,
                        diff: data.change,
                        rate: data.rate,
                        volume: data.volume,
                        total_vol: data.acml_vol,
                        vol_power: data.power
                    };
                    return { 
                        trades: [newTrade, ...prev.trades].slice(0, 30), 
                        vol_power: data.power 
                    };
                });

                // 2) 현재가 정보 업데이트
                setDetail(prev => prev ? ({
                    ...prev,
                    price: data.price,
                    diff: data.change,
                    change_rate: data.rate
                }) : null);

                // 3) 차트 실시간 업데이트 (캔들 갱신)
                // chartData State뿐만 아니라 실제 차트 시리즈(update 메서드)를 직접 호출해야 부드러움
                if (mainSeriesRef.current && volumeSeriesRef.current) {
                    const currentPrice = parseFloat(data.price);
                    const currentVol = parseFloat(data.volume); // 순간 체결량 (누적 아님)
                    
                    // 시간 처리 (HHMMSS -> Timestamp)가 필요하지만,
                    // Lightweight Charts는 update() 시 기존 마지막 캔들의 시간과 같으면 갱신, 다르면 추가함.
                    // 정확한 시간 동기화를 위해선 백엔드에서 받은 time을 활용해야 함.
                    // 여기서는 간단히 "마지막 캔들 갱신" 로직 예시:
                    
                    setChartData(prevData => {
                        if (prevData.length === 0) return prevData;
                        
                        const lastCandle = { ...prevData[prevData.length - 1] };
                        // (정교한 시간 비교 로직은 생략, 여기선 단순히 마지막 캔들 값을 갱신한다고 가정)
                        
                        lastCandle.close = currentPrice;
                        lastCandle.high = Math.max(lastCandle.high, currentPrice);
                        lastCandle.low = Math.min(lastCandle.low, currentPrice);
                        lastCandle.volume += currentVol; // 거래량 누적
                        
                        // 차트 라이브러리에 즉시 반영
                        mainSeriesRef.current.update(lastCandle);
                        volumeSeriesRef.current.update({
                            time: lastCandle.time,
                            value: lastCandle.volume,
                            color: (lastCandle.close >= lastCandle.open) ? '#ef5350' : '#26a69a'
                        });

                        // State 업데이트 (React 리렌더링용)
                        const newData = [...prevData];
                        newData[newData.length - 1] = lastCandle;
                        return newData;
                    });
                }
            }
        };

        return () => {
            console.log("🚫 WebSocket Disconnected");
            ws.close();
        };
    }, [symbol, period]);


    // --------------------------------------------------------------------------
    // 3. 차트 생성 및 설정 (가격/거래량 분리)
    // --------------------------------------------------------------------------
    useEffect(() => {
        if (!chartContainerRef.current) return;

        if (chartInstanceRef.current) {
            try { chartInstanceRef.current.remove(); } catch (e) {}
            chartInstanceRef.current = null;
        }

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: 500,
            layout: { background: { type: ColorType.Solid, color: '#ffffff' }, textColor: '#333' },
            timeScale: { 
                borderVisible: false,
                timeVisible: period === 'minute' || period === 'realtime',    
                secondsVisible: false,
                tickMarkFormatter: (time, tickMarkType) => {
                    const date = new Date(time * 1000);
                    const dateStr = date.toLocaleDateString('fr-CA', { timeZone: 'Asia/Seoul' });
                    const timeStr = date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Seoul' });
                    return (tickMarkType < 3) ? dateStr : timeStr;
                }
            },
            localization: {
                locale: 'ko-KR', dateFormat: 'yyyy-MM-dd',
                timeFormatter: (time) => {
                    const date = new Date(time * 1000);
                    const dateStr = date.toLocaleDateString('fr-CA', { timeZone: 'Asia/Seoul' });
                    const timeStr = date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Seoul' });
                    return (period === 'minute' || period === 'realtime') ? `${dateStr} ${timeStr}` : dateStr;
                }
            },
            grid: { vertLines: { color: '#f0f3fa' }, horzLines: { color: '#f0f3fa' } },
        });

        chartInstanceRef.current = chart;

        if (chartData.length > 0) {
            try {
                // 메인 차트 (상단 75%)
                let mainSeries;
                const mainOptions = {
                    priceScaleId: 'right',
                    upColor: '#ef5350', downColor: '#26a69a',
                    borderVisible: false, wickUpColor: '#ef5350', wickDownColor: '#26a69a'
                };
                if (chartType === 'candle') mainSeries = chart.addSeries(CandlestickSeries, mainOptions);
                else mainSeries = chart.addSeries(LineSeries, { ...mainOptions, color: '#2962FF', lineWidth: 2 });
                
                mainSeries.setData(chartData);
                mainSeriesRef.current = mainSeries; // [중요] 웹소켓 업데이트를 위해 저장

                chart.priceScale('right').applyOptions({
                    scaleMargins: { top: 0.1, bottom: 0.25 },
                    borderVisible: false,
                });

                // 거래량 차트 (하단 20%)
                const volumeSeries = chart.addSeries(HistogramSeries, {
                    color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: 'volume',
                });
                
                const volumeData = chartData.map(item => ({
                    time: item.time, value: item.volume,
                    color: (item.close >= item.open) ? '#ef5350' : '#26a69a' 
                }));
                volumeSeries.setData(volumeData);
                volumeSeriesRef.current = volumeSeries; // [중요] 웹소켓 업데이트를 위해 저장

                chart.priceScale('volume').applyOptions({
                    scaleMargins: { top: 0.8, bottom: 0 },
                    borderVisible: false,
                });

                chart.timeScale().fitContent();

            } catch (e) { console.error("Series Error:", e); }
        }
        
        const handleResize = () => {
            if (chartContainerRef.current && chartInstanceRef.current) {
                chartInstanceRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);
        return () => { window.removeEventListener('resize', handleResize); if (chartInstanceRef.current) try { chartInstanceRef.current.remove(); } catch (e) {} };

    }, [chartData, chartType, period]); // chartData가 바뀌면 차트를 다시 그림 (초기 로딩 시)

    if (!detail) return <div style={{ padding: '50px', textAlign: 'center' }}>로딩 중...</div>;

    // 유틸리티 함수
    const safeNum = (val) => { if (!val || val === 'NaN') return 0; const num = parseFloat(val.toString().replace(/,/g, '')); return isNaN(num) ? 0 : num; };
    const formatTime = (t) => { if (!t) return '-'; if (t.includes(':')) return t; return `${t.substr(0, 2)}:${t.substr(2, 2)}:${t.substr(4, 2)}`; };
    const formatMarketCap = (val) => { const num = safeNum(val); if (num === 0) return '-'; if (num >= 10000) { const jo = Math.floor(num / 10000); const eok = Math.floor(num % 10000); return `${jo}조 ${eok}억`; } return `${Math.floor(num)}억`; };
    const getColor = (val) => { const num = parseFloat(val); if (num > 0) return 'up'; if (num < 0) return 'down'; return ''; };
    const getTradeColor = (currentPrice, prevPrice) => { if (!prevPrice) return 'black'; if (currentPrice > prevPrice) return 'up'; if (currentPrice < prevPrice) return 'down'; return 'black'; };

    return (
        <div className="stock-detail-container">
            <header className="detail-header">
                <div className="title-section">
                    <h1>{detail.name || symbol}<span className="market-badge">{detail.market}</span></h1>
                    <p className="stock-code">{detail.code}</p>
                </div>
                <div className="price-section">
                    <h2 className={`price ${getColor(detail.diff)}`}>{safeNum(detail.price).toLocaleString()}원</h2>
                    <span className={`change ${getColor(detail.diff)}`}>
                        <span className="date-label">{detail.prev_date} 기준</span>
                        {safeNum(detail.diff) > 0 ? '▲' : '▼'} {Math.abs(safeNum(detail.diff)).toLocaleString()} ({detail.change_rate}%)
                    </span>
                </div>
            </header>

            <section className="chart-section">
                <div className="chart-controls">
                    <div className="period-btn-group-container">
                        <button className={`period-btn ${period === 'realtime' ? 'active' : ''}`} onClick={() => { setPeriod('realtime'); setMinuteValue('1m'); }}>실시간</button>
                        <div className="period-divider"></div>
                        <select className={`period-select ${period === 'minute' ? 'active' : ''}`} value={minuteValue} onChange={(e) => { setPeriod('minute'); setMinuteValue(e.target.value); }} disabled={period === 'realtime'}>
                            <option value="1m">1분</option><option value="5m">5분</option><option value="10m">10분</option><option value="30m">30분</option><option value="60m">60분</option>
                        </select>
                        <div className="period-divider"></div>
                        <div className="period-btn-group">
                            <button onClick={() => setPeriod('minute')} className={period === 'minute' ? 'active' : ''}>과거</button>
                            {['D', 'W', 'M', 'Y'].map((p) => (
                                <button key={p} onClick={() => setPeriod(p)} className={period === p ? 'active' : ''}>{p}</button>
                            ))}
                        </div>
                    </div>
                    <div className="type-btn-group">
                        <button onClick={() => setChartType('candle')} className={chartType === 'candle' ? 'active' : ''}>봉</button>
                        <button onClick={() => setChartType('line')} className={chartType === 'line' ? 'active' : ''}>라인</button>
                    </div>
                </div>
                <div className="chart-wrapper" ref={chartContainerRef} style={{ position: 'relative', width: '100%' }}>
                    <div className="chart-watermark label-price">가격</div>
                    <div className="chart-watermark label-volume">거래량</div>
                </div>
            </section>

            <section className="trades-section">
                <div className="trades-header-row">
                    <h3>실시간 체결</h3>
                    <span className="vol-power-badge">체결강도: <strong className={getColor(parseFloat(tradesData.vol_power) - 100)}>{tradesData.vol_power}%</strong></span>
                </div>
                <div className="trades-table-header">
                    <span>시간</span><span>체결가</span><span>전일대비</span><span>체결량</span><span>거래량(누적)</span>
                </div>
                <div className="trades-table-body">
                    {tradesData.trades.map((t, i) => {
                        const prevTrade = tradesData.trades[i + 1];
                        const currentPrice = parseInt(t.price);
                        const prevPrice = prevTrade ? parseInt(prevTrade.price) : currentPrice;
                        const tradeColor = getTradeColor(currentPrice, prevPrice);
                        return (
                            <div key={i} className="trade-row">
                                <span className="time">{formatTime(t.time)}</span>
                                <span className={`price ${tradeColor}`}>{currentPrice.toLocaleString()}</span>
                                <span className={`diff ${getColor(t.diff)}`}>{parseInt(t.diff) > 0 ? '+' : ''}{parseInt(t.diff).toLocaleString()} ({t.rate}%)</span>
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