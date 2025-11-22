import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';

function StockDetail() {
    const { code } = useParams();
    const navigate = useNavigate();

    return (
        <div style={{ padding: '20px' }}>
            <button onClick={() => navigate(-1)} style={{ marginBottom: '20px' }}>
                &larr; 뒤로가기
            </button>
            <h2>종목 상세 페이지</h2>
            <p>종목 코드: <strong>{code}</strong></p>
            <div style={{ 
                padding: '40px', 
                background: '#f5f5f5', 
                borderRadius: '8px', 
                textAlign: 'center',
                color: '#666'
            }}>
                차트 및 상세 호가 정보가 여기에 표시됩니다.
            </div>
        </div>
    );
}

export default StockDetail;