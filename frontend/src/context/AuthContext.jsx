import { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // 백엔드에서 사용자 정보 가져오기
    const fetchUser = async (token) => {
        try {
            const response = await fetch("http://localhost:8000/users/me", {
                headers: {
                    "Authorization": `Bearer ${token}` // JWT 헤더에 포함
                }
            });

            if (response.ok) {
                const userData = await response.json();
                setUser(userData); // { user_id, username, email, name, ... }
            } else {
                // 토큰이 만료되었거나 유효하지 않으면 로그아웃 처리
                console.log("토큰 만료 또는 유효하지 않음");
                logout();
            }
        } catch (error) {
            console.error("사용자 정보 로드 실패:", error);
            logout();
        } finally {
            setLoading(false);
        }
    };

    // 로그인: 토큰을 localStorage에 저장하고 사용자 정보 가져오기
    const login = (token) => {
        localStorage.setItem("access_token", token);
        fetchUser(token);
    };

    // 로그아웃: 토큰 삭제 및 상태 초기화
    const logout = () => {
        localStorage.removeItem("access_token");
        setUser(null);
    };

    // 앱 실행 시 localStorage에 토큰이 있다면 로그인 유지 시도
    useEffect(() => {
        const storedToken = localStorage.getItem("access_token");
        if (storedToken) {
            fetchUser(storedToken);
        } else {
            setLoading(false);
        }
    }, []);

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);