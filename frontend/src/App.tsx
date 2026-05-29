import { useEffect, useState } from 'react'
import './App.css'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import DebugPanel from './components/DebugPanel'
import { useSensorStore } from './store/sensorStore'
import { useAppStore } from './store/appStore'
import { AlertCircle } from 'lucide-react'
import { logger } from './utils/logger'

function App() {
  const [currentPage, setCurrentPage] = useState<'dashboard' | 'settings'>('dashboard')
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const { error } = useSensorStore()
  const { isDarkMode } = useAppStore()

  useEffect(() => {
    logger.logInfo('App', 'Application démarrée')
  }, [])

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      logger.logInfo('App', 'Application en ligne')
    }
    const handleOffline = () => {
      setIsOnline(false)
      logger.logWarn('App', 'Application hors ligne')
    }

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
              onClick={() => {
                logger.logButtonClick('Tableau de Bord', 'App')
                setCurrentPage('dashboard')
              }}
            >
              Tableau de Bord
            </button>
            <button
              className={`nav-btn ${currentPage === 'settings' ? 'active' : ''}`}
              onClick={() => {
                logger.logButtonClick('Paramètres', 'App')
                setCurrentPage('settings')
              }}
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
        {currentPage === 'settings' && <Settings />}
      </main>

      <footer className="footer">
        <p>Système de Surveillance des Capteurs ESP32 v2.0</p>
      </footer>

      <DebugPanel />
    </div>
  )
}

export default App
