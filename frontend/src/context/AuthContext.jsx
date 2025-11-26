import { createContext, useContext, useState, useEffect } from "react";
import axios from "../lib/axios";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // 사용자 정보 가져오기
    const fetchUser = async () => {
        try {
            const response = await axios.get("/users/me");
            setUser(response.data)
        } catch (error) {
            console.error("사용자 정보 로드 실패:", error);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    // 로그인
    const login = (token) => {
        localStorage.setItem("access_token", token);
        fetchUser();
    };

    // 로그아웃
    const logout = () => {
        localStorage.removeItem("access_token");
        setUser(null);
        window.location.href = "/";
    };

    // 토큰으로 사용자 정보 가져오기
    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (token) {
            fetchUser();
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