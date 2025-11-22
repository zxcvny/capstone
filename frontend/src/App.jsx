import { Routes, Route } from 'react-router-dom'
import './styles/App.css'
import Layout from './components/Layout'
import Home from './pages/Home'
import MyInvestList from './pages/MyInvestList'
import LoginPage from './pages/LoginPage'
import SignUpPage from './pages/SignupPage'

function App() {

  return (
    <Routes>
      <Route path='/' element={<Layout />}>
        <Route index element={<Home />} />
        <Route path='/myinvestlist' element={<MyInvestList />} />    
      </Route>
      <Route path='/login' element={<LoginPage />} />
      <Route path='/signup' element={<SignUpPage />} />
    </Routes>
  )
}

export default App
