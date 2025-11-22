import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import './styles/App.css'
import Layout from './components/Layout'
import MainPage from './pages/MainPage'
import MarketPage from './pages/MarketPage'
import LoginPage from './pages/LoginPage'
import SignUpPage from './pages/SignUpPage'
import SocialCallbackPage from './pages/SocialCallbackPage'

function App() {

  return (
    <AuthProvider>
      <Routes>
        <Route path='/' element={<Layout />}>
          <Route index element={<MainPage />} />
          <Route path='/market' element={<MarketPage />} />    
        </Route>
        <Route path='/login' element={<LoginPage />} />
        <Route path='/signup' element={<SignUpPage />} />
        <Route path='/social/callback' element={<SocialCallbackPage />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
