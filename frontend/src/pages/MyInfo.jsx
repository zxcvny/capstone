import { useAuth } from "../context/AuthContext";
import NotLogin from "../components/NotLogin";

function MyInfo() {
    const { user } = useAuth();
    
    return (
        <div>
            {user ? (
                // user 정보 있을 때 (로그인 상태일 때)
                <div></div>
            ): (
                // user 정보 없을 때 (비로그인 상태일 때)
                <NotLogin />
            )}
        </div>
    )
}
export default MyInfo