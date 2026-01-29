import { useState, useEffect } from 'react'
import './Settings.css'
import { Settings as SettingsIcon, Save, LogOut, Moon, Sun, User, Lock, LogIn } from 'lucide-react'
import { useAppStore } from '../store/appStore'

interface IncubatorSettings {
  temperature: number
  humidity: number
  start_date: string
  stat_stepper: boolean
  number_stepper: number
  espece: 'poule' | 'canne' | 'dinde' | 'autre'
  timetoclose: number | null
  temp_incubation: number
  humidity_target: number
  rotation_count: number
  user_id: number | null
}

function Settings() {
  const { isDarkMode, toggleDarkMode, isAuthenticated, username } = useAppStore()
  
  const [loginData, setLoginData] = useState({
    username: '',
    password: '',
  })
  
  const [settings, setSettings] = useState<IncubatorSettings>({
    temperature: 25,
    humidity: 60,
    start_date: new Date().toISOString(),
    stat_stepper: false,
    number_stepper: 3,
    espece: 'poule',
    timetoclose: 21,
    temp_incubation: 37.5,
    humidity_target: 60,
    rotation_count: 5,
    user_id: null,
  })

  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Charger les paramètres
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch('/api/parameter')
        if (response.ok) {
          const data = await response.json()
          setSettings(data)
        }
      } catch (err) {
        console.error('Erreur chargement paramètres:', err)
      }
    }
    fetchSettings()
  }, [])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData),
      })

      if (response.ok) {
        const data = await response.json()
        // Utiliser le store Zustand
        const { login } = useAppStore.getState()
        login(data.username)
        localStorage.setItem('auth_token', data.access_token)
        setLoginData({ username: '', password: '' })
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Identifiants invalides')
      }
    } catch (err) {
      setError('Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    const { logout } = useAppStore.getState()
    logout()
    localStorage.removeItem('auth_token')
  }

  const handleChange = (key: keyof IncubatorSettings, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    if (!isAuthenticated) {
      setError('Vous devez être connecté pour modifier les paramètres')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/parameter', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}` 
        },
        body: JSON.stringify(settings),
      })

      if (response.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Erreur lors de la sauvegarde')
      }
    } catch (err) {
      setError('Erreur serveur')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <div className="header-left">
          <SettingsIcon size={32} />
          <h2>Paramètres Incubateur</h2>
        </div>
        <div className="header-right">
          <button 
            className="btn-theme"
            onClick={toggleDarkMode}
            title={isDarkMode ? 'Mode clair' : 'Mode sombre'}
          >
            {isDarkMode ? <Sun size={24} /> : <Moon size={24} />}
          </button>
        </div>
      </div>

      {/* Section Authentification */}
      {!isAuthenticated ? (
        <div className="login-container">
          <div className="login-card">
            <div className="login-header">
              <div className="login-icon">
                <User size={32} />
              </div>
              <h3>Connexion</h3>
              <p className="login-subtitle">Connectez-vous pour modifier les paramètres</p>
            </div>
            <form onSubmit={handleLogin} className="login-form">
              <div className="input-group">
                <User size={20} className="input-icon" />
                <input
                  type="text"
                  placeholder="Nom d'utilisateur"
                  value={loginData.username}
                  onChange={(e) => setLoginData(prev => ({ ...prev, username: e.target.value }))}
                  disabled={loading}
                />
              </div>
              <div className="input-group">
                <Lock size={20} className="input-icon" />
                <input
                  type="password"
                  placeholder="Mot de passe"
                  value={loginData.password}
                  onChange={(e) => setLoginData(prev => ({ ...prev, password: e.target.value }))}
                  disabled={loading}
                />
              </div>
              <button type="submit" className="btn-login" disabled={loading}>
                {loading ? (
                  <span className="btn-loading">Connexion en cours...</span>
                ) : (
                  <>
                    <LogIn size={20} />
                    Se connecter
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      ) : (
        <div className="auth-status">
          <div className="user-info">
            <div className="user-avatar">
              <User size={24} />
            </div>
            <div className="user-details">
              <span className="user-label">Connecté en tant que</span>
              <strong className="user-name">{username}</strong>
            </div>
          </div>
          <button className="btn-logout" onClick={handleLogout}>
            <LogOut size={20} /> Déconnexion
          </button>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}
      {saved && <div className="success-message">✓ Paramètres sauvegardés avec succès !</div>}

      <div className="settings-grid">
        {/* Incubation */}
        <section className="settings-section">
          <h3>⏰ Paramètres d'Incubation</h3>
          <div className="form-group">
            <label>Espèce</label>
            <select 
              value={settings.espece}
              onChange={(e) => handleChange('espece', e.target.value)}
              disabled={!isAuthenticated}
            >
              <option value="poule">Poule (21 jours)</option>
              <option value="cannecanard">Canard (28 jours)</option>
              <option value="dinde">Dinde (28 jours)</option>
              <option value="autre">Autre</option>
            </select>
          </div>
          <div className="form-group">
            <label>Durée d'éclosion (jours)</label>
            <input
              type="number"
              min="1"
              max="30"
              value={settings.timetoclose || 21}
              onChange={(e) => handleChange('timetoclose', parseInt(e.target.value))}
              disabled={!isAuthenticated}
            />
          </div>
          <div className="form-group">
            <label>Rotations par jour</label>
            <input
              type="number"
              min="0"
              max="24"
              value={settings.rotation_count}
              onChange={(e) => handleChange('rotation_count', parseInt(e.target.value))}
              disabled={!isAuthenticated}
            />
          </div>
        </section>

        {/* Température */}
        <section className="settings-section">
          <h3>🌡️ Température</h3>
          <div className="form-group">
            <label>Température d'incubation (°C)</label>
            <input
              type="number"
              step="0.1"
              min="35"
              max="40"
              value={settings.temp_incubation}
              onChange={(e) => handleChange('temp_incubation', parseFloat(e.target.value))}
              disabled={!isAuthenticated}
            />
            <small>Poule: 37.5°C, Canard: 37.2°C</small>
          </div>
          <div className="form-group">
            <label>Température Actuelle (°C)</label>
            <input
              type="number"
              step="0.1"
              value={settings.temperature}
              onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
              disabled={!isAuthenticated}
            />
          </div>
        </section>

        {/* Humidité */}
        <section className="settings-section">
          <h3>💧 Humidité</h3>
          <div className="form-group">
            <label>Humidité Cible (%)</label>
            <input
              type="number"
              min="30"
              max="90"
              value={settings.humidity_target}
              onChange={(e) => handleChange('humidity_target', parseInt(e.target.value))}
              disabled={!isAuthenticated}
            />
            <small>J1-J18: 40-50%, J19+: 70-75%</small>
          </div>
          <div className="form-group">
            <label>Humidité Actuelle (%)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={settings.humidity}
              onChange={(e) => handleChange('humidity', parseInt(e.target.value))}
              disabled={!isAuthenticated}
            />
          </div>
        </section>

        {/* Équipements */}
        <section className="settings-section">
          <h3>⚙️ Équipements</h3>
          <div className="form-group checkbox">
            <input
              type="checkbox"
              checked={settings.stat_stepper}
              onChange={(e) => handleChange('stat_stepper', e.target.checked)}
              disabled={!isAuthenticated}
            />
            <label>Moteur de rotation actif</label>
          </div>
          <div className="form-group">
            <label>Nombre de tourneurs</label>
            <input
              type="number"
              min="1"
              max="10"
              value={settings.number_stepper}
              onChange={(e) => handleChange('number_stepper', parseInt(e.target.value))}
              disabled={!isAuthenticated}
            />
          </div>
        </section>

        {/* Date de démarrage */}
        <section className="settings-section">
          <h3>📅 Cycle d'Incubation</h3>
          <div className="form-group">
            <label>Date de démarrage</label>
            <input
              type="datetime-local"
              value={settings.start_date.slice(0, 16)}
              onChange={(e) => handleChange('start_date', new Date(e.target.value).toISOString())}
              disabled={!isAuthenticated}
            />
          </div>
        </section>
      </div>

      <div className="settings-actions">
        <button 
          className="btn-save" 
          onClick={handleSave}
          disabled={!isAuthenticated || loading}
        >
          <Save size={20} />
          {loading ? 'Sauvegarde...' : 'Sauvegarder les paramètres'}
        </button>
      </div>
    </div>
  )
}

export default Settings
