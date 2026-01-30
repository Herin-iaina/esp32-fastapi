import { useEffect, useState } from 'react'
import './App.css'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import CRMDashboard from './pages/CRMDashboard'
import { useSensorStore } from './store/sensorStore'
import { useAppStore } from './store/appStore'
import { AlertCircle } from 'lucide-react'

function App() {
  const [currentPage, setCurrentPage] = useState<'dashboard' | 'settings' | 'crm'>('dashboard')
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const { error } = useSensorStore()
  const { isDarkMode } = useAppStore()

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Appliquer le dark mode globalement
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="nav-content">
          <h1 className="logo">🌡️ Monitoring ESP32</h1>
          <div className="nav-buttons">
            <button
              className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentPage('dashboard')}
            >
              Tableau de Bord
            </button>
            <button
              className={`nav-btn ${currentPage === 'crm' ? 'active' : ''}`}
              onClick={() => setCurrentPage('crm')}
            >
              CRM & Analytics
            </button>
            <button
              className={`nav-btn ${currentPage === 'settings' ? 'active' : ''}`}
              onClick={() => setCurrentPage('settings')}
            >
              Paramètres
            </button>
          </div>
        </div>
      </nav>

      <main className="main-content">
        {!isOnline && (
          <div className="alert alert-warning">
            <AlertCircle size={20} />
            Vous êtes actuellement hors ligne
          </div>
        )}

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'crm' && <CRMDashboard />}
        {currentPage === 'settings' && <Settings />}
      </main>

      <footer className="footer">
        <p>Système de Surveillance des Capteurs ESP32 v2.0</p>
      </footer>
    </div>
  )
}

export default App
