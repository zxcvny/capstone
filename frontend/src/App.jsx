import { Routes, Route } from 'react-router-dom'
import './styles/App.css'
import Layout from './components/Layout'
import MainPage from './pages/MainPage'
import MarketPage from './pages/MarketPage'
import LoginPage from './pages/LoginPage'
import SignUpPage from './pages/SignupPage'

function App() {

  return (
    <Routes>
      <Route path='/' element={<Layout />}>
        <Route index element={<MainPage />} />
        <Route path='/market' element={<MarketPage />} />    
      </Route>
      <Route path='/login' element={<LoginPage />} />
      <Route path='/signup' element={<SignUpPage />} />
    </Routes>
  )
}

export default App
