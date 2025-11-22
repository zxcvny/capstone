import React, { useState, useEffect, useRef } from 'react';

function Home() {
    const [stockData, setStockData] = useState({});
    const [status, setStatus] = useState("Disconnected");
    const ws = useRef(null);

    useEffect(() => {
        // 실제 백엔드 주소 (포트번호 확인 필요)
        const socketUrl = "ws://localhost:8000/realtime/top-volume";
        ws.current = new WebSocket(socketUrl);

        ws.current.onopen = () => {
            console.log("✅ WebSocket Connected");
            setStatus("Connected 🟢");
        };

        ws.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'ticker') {
                    setStockData(prevData => ({
                        ...prevData,
                        [data.code]: data 
                    }));
                }
            } catch (error) {
                console.error("❌ Data Parsing Error:", error);
            }
        };

        ws.current.onclose = () => {
            console.log("⛔ WebSocket Disconnected");
            setStatus("Disconnected 🔴");
        };

        return () => {
            if (ws.current) ws.current.close();
        };
    }, []);

    const formatNumber = (num) => num ? Number(num).toLocaleString() : '-';

    const getColor = (rate) => {
        if (!rate) return 'black';
        const numRate = parseFloat(rate);
        if (numRate > 0) return '#ef4444';
        if (numRate < 0) return '#3b82f6';
        return 'black';
    };

    return (
        <div className="mainpage-container" style={{ padding: '20px', fontFamily: 'sans-serif' }}>
            <h2 style={{marginBottom:'20px'}}>📊 실시간 거래량 상위 종목 (Live)</h2>
            <div style={{ marginBottom: '10px', fontSize: '14px', color: '#666' }}>
                상태: {status}
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'right', fontSize: '14px' }}>
                <thead>
                    <tr style={{ borderBottom: '2px solid #333', background: '#f4f4f5', color: '#333' }}>
                        <th style={{ padding: '12px', textAlign: 'left' }}>종목명</th>
                        <th style={{ padding: '12px' }}>현재가</th>
                        <th style={{ padding: '12px' }}>등락률</th>
                        <th style={{ padding: '12px' }}>거래량</th>
                        <th style={{ padding: '12px' }}>시간</th>
                    </tr>
                </thead>
                <tbody>
                    {Object.values(stockData).map((stock) => (
                        <tr key={stock.code} style={{ borderBottom: '1px solid #eee' }}>
                            <td style={{ padding: '12px', textAlign: 'left', fontWeight: 'bold' }}>
                                <div style={{ fontSize: '15px' }}>{stock.name || stock.code}</div>
                                <div style={{ fontSize: '12px', color: '#999' }}>{stock.code}</div>
                            </td>
                            <td style={{ padding: '12px', color: getColor(stock.change_rate), fontWeight:'500' }}>
                                {formatNumber(stock.price)}원
                            </td>
                            <td style={{ padding: '12px', color: getColor(stock.change_rate) }}>
                                {stock.change_rate}%
                            </td>
                            <td style={{ padding: '12px' }}>
                                {formatNumber(stock.volume)}
                            </td>
                            <td style={{ padding: '12px', fontSize: '12px', color: '#888' }}>
                                {stock.timestamp}
                            </td>
                        </tr>
                    ))}
                    {Object.keys(stockData).length === 0 ? (
                        <tr>
                            <td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                                데이터 수신 대기중... 📡
                            </td>
                        </tr>
                    ) : null}
                </tbody>
            </table>
        </div>
    );
}

export default Home;