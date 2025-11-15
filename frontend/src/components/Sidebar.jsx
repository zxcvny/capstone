import { NavLink } from 'react-router-dom';
import '../styles/Layout.css';
import {
    FaChartBar,
    FaBullhorn,
    FaRobot,
    FaAngleDoubleRight
} from 'react-icons/fa';

const menuItems = [
    { key: 'market', path: '/market', name: '시장현황', icon: <FaChartBar /> },
    { key: 'signal', path: '/signal', name: '매매신호', icon: <FaBullhorn /> },
    { key: 'auto-trade', path: '/auto-trade', name: '자동매매', icon: <FaRobot /> },
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