import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import './styles/App.css'
import Layout from './components/Layout'
import Home from './pages/Home'
import MyInvestList from './pages/MyInvestList'
import LoginPage from './pages/LoginPage'
import SignUpPage from './pages/SignUpPage'
import SocialCallbackPage from './pages/SocialCallbackPage'
import StockDetail from './pages/StockDetail';
import MyFavorite from './pages/MyFavorite'
import MyInfo from './pages/MyInfo'

function App() {

  return (
    <AuthProvider>
      <Routes>
        <Route path='/' element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/stock/:market/:symbol" element={<StockDetail />} />
          <Route path='/myinvestlist' element={<MyInvestList />} />
          <Route path='/myfavorite' element={<MyFavorite />} />
          <Route path='/myinfo' element={<MyInfo />} />
        </Route>
        <Route path='/login' element={<LoginPage />} />
        <Route path='/signup' element={<SignUpPage />} />
        <Route path='/social/callback' element={<SocialCallbackPage />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
