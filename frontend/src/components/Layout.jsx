import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar'
import Header from './Header';
import '../styles/Layout.css';

function Layout() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen)
    }

    return(
        <div className="layout-container">
            <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
            <div className={`main-content-container ${isSidebarOpen ? 'sidebar-open':'sidebar-closed'}`}>
                <Header />
                <main className="content-area">
                    <div className="page-content">
                        <Outlet />
                    </div>
                </main>
            </div>
        </div>
    )
}
export default Layout;