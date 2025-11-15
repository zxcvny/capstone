import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar'
import '../styles/Layout.css';

function Layout() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen)
    }

    return(
        <div className="layout-container">
            <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
            <main className={`content-area ${isSidebarOpen ? 'sidebar-open':'sidebar-closed'}`}>
                <div className="page-content">
                    <Outlet />
                </div>
            </main>
        </div>
    )
}
export default Layout;