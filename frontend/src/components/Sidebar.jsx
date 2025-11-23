import { NavLink } from 'react-router-dom';
import '../styles/Layout.css';
import {
    FaHome,
    FaChartBar,
    FaHeart,
    FaThList,
    FaUser,
    FaAngleDoubleRight
} from 'react-icons/fa';

const menuItems = [
    { key: 'home', path: '/', name: '홈', icon: <FaHome /> },
    { key: 'myinvestlist', path: '/myinvestlist', name: '내 투자 종목', icon: <FaChartBar /> },
    { key: 'myfavorite', path: '/myfavorite', name: '내 관심 종목', icon: <FaHeart /> },
    { key: 'mycategory', path: '/mycategory', name: '내 카테고리', icon: <FaThList /> },
    { key: 'myinfo', path: '/myinfo', name: '내 정보', icon: <FaUser /> },
];

function Sidebar({ isOpen, toggleSidebar }) {
    return(
        <nav className={`sidebar ${isOpen ? 'open':'closed'}`}>
            <button
             onClick={toggleSidebar}
             className='sidebar-toggle-btn'
             aria-label='Toggle sidebar'
            >
                <span className={`tb-icon-wrapper ${isOpen ? 'rotated': ''}`}><FaAngleDoubleRight /></span>
            </button>
            <ul className="sidebar-menu">
                {menuItems.map((item) => (
                    <li key={item.key}>
                        <NavLink
                         to={item.path}
                         className={({ isActive }) => (isActive ? 'active':'')}
                        >
                            <span className="menu-icon">{item.icon}</span>
                            <span className="menu-text">{item.name}</span>
                        </NavLink>
                    </li>
                ))}
            </ul>
        </nav>
    )
}
export default Sidebar;