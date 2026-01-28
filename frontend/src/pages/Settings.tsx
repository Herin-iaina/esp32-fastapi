import React, { useState } from 'react'
import './Settings.css'
import { Settings as SettingsIcon, Save } from 'lucide-react'

function Settings() {
  const [settings, setSettings] = useState({
    tempMin: -50,
    tempMax: 100,
    humidMin: 0,
    humidMax: 100,
    sensorRefreshRate: 10,
    fanThreshold: 25,
    humidifierThreshold: 60,
    notificationsEnabled: true,
    darkMode: false,
  })

  const [saved, setSaved] = useState(false)

  const handleChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    try {
      // Appel API pour sauvegarder les paramètres
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })

      if (response.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (err) {
      console.error('Erreur lors de la sauvegarde:', err)
    }
  }

  return (
    <div className="settings-container">
      <header className="settings-header">
        <SettingsIcon size={32} />
        <h2>Paramètres Système</h2>
      </header>

      <div className="settings-grid">
        <section className="settings-section">
          <h3>Limites de Température</h3>
          <div className="form-group">
            <label>Température Minimale (°C)</label>
            <input
              type="number"
              value={settings.tempMin}
              onChange={(e) => handleChange('tempMin', parseInt(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label>Température Maximale (°C)</label>
            <input
              type="number"
              value={settings.tempMax}
              onChange={(e) => handleChange('tempMax', parseInt(e.target.value))}
            />
          </div>
        </section>

        <section className="settings-section">
          <h3>Limites d'Humidité</h3>
          <div className="form-group">
            <label>Humidité Minimale (%)</label>
            <input
              type="number"
              value={settings.humidMin}
              onChange={(e) => handleChange('humidMin', parseInt(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label>Humidité Maximale (%)</label>
            <input
              type="number"
              value={settings.humidMax}
              onChange={(e) => handleChange('humidMax', parseInt(e.target.value))}
            />
          </div>
        </section>

        <section className="settings-section">
          <h3>Seuils des Équipements</h3>
          <div className="form-group">
            <label>Seuil Ventilateur (°C)</label>
            <input
              type="number"
              value={settings.fanThreshold}
              onChange={(e) => handleChange('fanThreshold', parseInt(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label>Seuil Humidificateur (%)</label>
            <input
              type="number"
              value={settings.humidifierThreshold}
              onChange={(e) => handleChange('humidifierThreshold', parseInt(e.target.value))}
            />
          </div>
        </section>

        <section className="settings-section">
          <h3>Comportement</h3>
          <div className="form-group">
            <label>Fréquence de Rafraîchissement (sec)</label>
            <input
              type="number"
              value={settings.sensorRefreshRate}
              onChange={(e) => handleChange('sensorRefreshRate', parseInt(e.target.value))}
            />
          </div>
          <div className="form-group checkbox">
            <input
              type="checkbox"
              checked={settings.notificationsEnabled}
              onChange={(e) => handleChange('notificationsEnabled', e.target.checked)}
            />
            <label>Activer les notifications</label>
          </div>
          <div className="form-group checkbox">
            <input
              type="checkbox"
              checked={settings.darkMode}
              onChange={(e) => handleChange('darkMode', e.target.checked)}
            />
            <label>Mode sombre (à implémenter)</label>
          </div>
        </section>
      </div>

      <div className="settings-actions">
        <button className="btn-save" onClick={handleSave}>
          <Save size={20} />
          Sauvegarder les paramètres
        </button>
        {saved && <div className="success-message">✓ Paramètres sauvegardés avec succès !</div>}
      </div>
    </div>
  )
}

export default Settings
