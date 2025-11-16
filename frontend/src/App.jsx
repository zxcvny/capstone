import { Routes, Route } from 'react-router-dom'
import './styles/App.css'
import Layout from './components/Layout'
import MainPage from './pages/MainPage'
import MarketPage from './pages/MarketPage'

function App() {

  return (
    <Routes>
      <Route path='/' element={<Layout />}>
        <Route index element={<MainPage />} />
        <Route path='/market' element={<MarketPage />} />
      </Route>
    </Routes>
  )
}

export default App
