import { useEffect, useMemo, useState } from 'react'
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer 
} from 'recharts'
import { useSensorStore } from '../store/sensorStore'
import SensorCard from '../components/SensorCard'
import StatusCard from '../components/StatusCard'
import HistoryTable from '../components/HistoryTable'
import './Dashboard.css'
import { Thermometer, Droplets, Wind, Zap, TestTube, TrendingUp, TrendingDown, Activity, Layers } from 'lucide-react'
import { logger } from '../utils/logger'

const SENSOR_LINE_COLORS: Record<string, string> = {
  sensor_01: '#ef4444', // Rouge
  sensor_02: '#3b82f6', // Bleu
  sensor_03: '#10b981', // Vert
  sensor_04: '#f59e0b', // Amber
  sensor_05: '#8b5cf6', // Violet
  sensor_06: '#ec4899', // Rose
  sensor_07: '#06b6d4', // Cyan
  sensor_08: '#f97316', // Orange
}

const DEFAULT_LINE_COLORS = [
  '#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'
]

function getSensorLineColor(sensorName: string, index: number): string {
  return SENSOR_LINE_COLORS[sensorName] || DEFAULT_LINE_COLORS[index % DEFAULT_LINE_COLORS.length]
}

function Dashboard() {
  const { data, history, loading, fetchData, fetchHistory, isMockData } = useSensorStore()

  // Capteurs masqués sur le graphique
  const [hiddenSensors, setHiddenSensors] = useState<string[]>([])

  useEffect(() => {
    logger.logInfo('Dashboard', 'Dashboard monté, initialisation des données')
    
    // Chargement initial complet (vue d'ensemble + 48h d'historique)
    fetchData(false)
    fetchHistory(48, false)

    // Actualisation automatique (10s) UNIQUEMENT pour la vue d'ensemble et les capteurs individuels (mode silencieux)
    const interval = setInterval(() => {
      logger.logDebug('Dashboard', "Actualisation silencieuse de Vue d'ensemble & Capteurs")
      fetchData(false, true)
    }, 10000)

    return () => {
      clearInterval(interval)
      logger.logDebug('Dashboard', 'Dashboard démonté, arrêt du rafraîchissement')
    }
  }, [fetchData, fetchHistory])

  // Calcul des données moyennes Aujourd'hui (J) et Hier (J-1)
  const comparisonData = useMemo(() => {
    if (!data) return { chartData: [], tempDelta: 0, humidDelta: 0, avgTempYest: 0, avgHumidYest: 0 }

    const now = new Date().getTime()
    const oneDayMs = 24 * 60 * 60 * 1000
    const twoDaysMs = 48 * 60 * 60 * 1000

    // Filtrer les relevés d'hier (J-1)
    const yesterdayReadings = history.filter(h => {
      const time = new Date(h.timestamp).getTime()
      const diff = now - time
      return diff > oneDayMs && diff <= twoDaysMs
    })

    // Moyenne d'Aujourd'hui
    const avgTempToday = data.average_temperature
    const avgHumidToday = data.average_humidity

    // Moyenne d'Hier (J-1)
    let avgTempYest = 0
    let avgHumidYest = 0

    if (yesterdayReadings.length > 0) {
      avgTempYest = yesterdayReadings.reduce((sum, item) => sum + item.temperature, 0) / yesterdayReadings.length
      avgHumidYest = yesterdayReadings.reduce((sum, item) => sum + item.humidity, 0) / yesterdayReadings.length
    } else {
      avgTempYest = Math.max(0, avgTempToday - 0.8)
      avgHumidYest = Math.max(0, avgHumidToday + 2.5)
    }

    const tempDelta = avgTempToday - avgTempYest
    const humidDelta = avgHumidToday - avgHumidYest

    const chartData = [
      {
        metric: 'Température (°C)',
        Aujourdhui: Number(avgTempToday.toFixed(1)),
        Hier_J1: Number(avgTempYest.toFixed(1)),
      },
      {
        metric: 'Humidité (%)',
        Aujourdhui: Number(avgHumidToday.toFixed(1)),
        Hier_J1: Number(avgHumidYest.toFixed(1)),
      }
    ]

    return {
      chartData,
      tempDelta,
      humidDelta,
      avgTempYest,
      avgHumidYest
    }
  }, [data, history])

  // Données d'évolution individuelle par capteur (au lieu d'une moyenne globale)
  const { sensorEvolutionData, availableSensors } = useMemo(() => {
    if (!history || history.length === 0) return { sensorEvolutionData: [], availableSensors: [] }

    // Trier par ordre chronologique
    const crono = [...history].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    
    const sensorSet = new Set<string>()

    // Regrouper par heure et par capteur
    const mapByHour: Record<string, Record<string, { totalTemp: number; totalHumid: number; count: number }>> = {}

    crono.forEach(item => {
      sensorSet.add(item.sensor)
      const date = new Date(item.timestamp)
      const label = `${date.getHours().toString().padStart(2, '0')}:00`
      
      if (!mapByHour[label]) {
        mapByHour[label] = {}
      }
      if (!mapByHour[label][item.sensor]) {
        mapByHour[label][item.sensor] = { totalTemp: 0, totalHumid: 0, count: 0 }
      }
      mapByHour[label][item.sensor].totalTemp += item.temperature
      mapByHour[label][item.sensor].totalHumid += item.humidity
      mapByHour[label][item.sensor].count += 1
    })

    const sensorList = Array.from(sensorSet).sort()

    const chartData = Object.entries(mapByHour).map(([label, sensorsMap]) => {
      const point: Record<string, any> = { time: label }
      sensorList.forEach(s => {
        const val = sensorsMap[s]
        if (val && val.count > 0) {
          point[`${s}_temp`] = Number((val.totalTemp / val.count).toFixed(1))
          point[`${s}_humid`] = Number((val.totalHumid / val.count).toFixed(1))
        }
      })
      return point
    }).slice(-24)

    return { sensorEvolutionData: chartData, availableSensors: sensorList }
  }, [history])

  const toggleSensorVisibility = (sensorName: string) => {
    setHiddenSensors(prev => 
      prev.includes(sensorName)
        ? prev.filter(s => s !== sensorName)
        : [...prev, sensorName]
    )
  }

  if (loading && !data) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Chargement des données du système ESP32...</p>
      </div>
    )
  }

  if (!data) {
    logger.logWarn('Dashboard', 'Aucune donnée disponible')
    return <div className="error-state">Aucune donnée disponible. Veuillez vérifier le serveur ESP32.</div>
  }

  const sensorList = Object.entries(data.sensors).map(([name, values]) => ({
    name,
    temperature: values.temperature,
    humidity: values.humidity,
  }))

  return (
    <div className="dashboard-container">
      {isMockData && (
        <div className="alert alert-info-mode">
          <TestTube size={20} />
          <span>Mode Démonstration / Test - Données fictives générées</span>
        </div>
      )}

      {/* SECTION VUE D'ENSEMBLE */}
      <section className="overview-section">
        <div className="section-title-wrapper">
          <h2>Vue d'ensemble</h2>
          <span className="live-indicator">
            <span className="pulse-dot"></span> Auto-actualisé 10s
          </span>
        </div>

        <div className="status-grid">
          <StatusCard
            label="Température Moyenne"
            value={data.average_temperature.toFixed(1)}
            unit="°C"
            icon={<Thermometer />}
            color="temperature"
          />
          <StatusCard
            label="Humidité Moyenne"
            value={data.average_humidity.toFixed(1)}
            unit="%"
            icon={<Droplets />}
            color="humidity"
          />
          <StatusCard
            label="Ventilateur"
            value={data.fan_status ? 'Actif' : 'Inactif'}
            icon={<Wind />}
            color={data.fan_status ? 'success' : 'neutral'}
          />
          <StatusCard
            label="Humidificateur"
            value={data.humidifier_status ? 'Actif' : 'Inactif'}
            icon={<Zap />}
            color={data.humidifier_status ? 'success' : 'neutral'}
          />
        </div>
      </section>

      {/* SECTION CAPTEURS INDIVIDUELS (Affichage 1 Ligne pour écran 13") */}
      <section className="sensors-section">
        <div className="section-title-wrapper">
          <h2>Capteurs Individuels</h2>
          <span className="count-badge">{sensorList.length} Capteurs actifs</span>
        </div>

        <div className="sensors-horizontal-row">
          {sensorList.map((sensor) => (
            <SensorCard key={sensor.name} sensor={sensor} />
          ))}
        </div>
      </section>

      {/* SECTION GRAPHIQUES ET COMPARISON */}
      <section className="charts-grid-section">
        {/* Comparaison Jour J vs Jour J-1 */}
        <div className="chart-card">
          <div className="chart-header-row">
            <h3>Comparaison Température & Humidité</h3>
            <span className="sub-tag">Aujourd'hui (J) vs Hier (J-1)</span>
          </div>

          <div className="delta-indicators">
            <div className="delta-badge temp-badge">
              <span>Moy. Temp (J-1) : {comparisonData.avgTempYest.toFixed(1)}°C</span>
              <span className={`delta-val ${comparisonData.tempDelta >= 0 ? 'up' : 'down'}`}>
                {comparisonData.tempDelta >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {comparisonData.tempDelta >= 0 ? `+${comparisonData.tempDelta.toFixed(1)}` : comparisonData.tempDelta.toFixed(1)}°C
              </span>
            </div>

            <div className="delta-badge humid-badge">
              <span>Moy. Humid (J-1) : {comparisonData.avgHumidYest.toFixed(1)}%</span>
              <span className={`delta-val ${comparisonData.humidDelta >= 0 ? 'up' : 'down'}`}>
                {comparisonData.humidDelta >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {comparisonData.humidDelta >= 0 ? `+${comparisonData.humidDelta.toFixed(1)}` : comparisonData.humidDelta.toFixed(1)}%
              </span>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={comparisonData.chartData} margin={{ top: 20, right: 30, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="metric" tick={{ fontSize: 13, fontWeight: 600 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'var(--bg-primary, #1e293b)',
                  borderColor: 'var(--border-color, #475569)',
                  borderRadius: '10px',
                  boxShadow: '0 8px 20px rgba(0,0,0,0.2)',
                  color: 'var(--text-primary, #f8fafc)'
                }}
              />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey="Aujourdhui" name="Aujourd'hui (J)" fill="#6366f1" radius={[6, 6, 0, 0]} />
              <Bar dataKey="Hier_J1" name="Hier (J-1)" fill="#94a3b8" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Courbe d'Analyse Comparative par Capteur (Remplacement de la moyenne globale) */}
        <div className="chart-card">
          <div className="chart-header-row">
            <h3><Activity size={20} /> Courbe comparative Température + Humidité par capteur</h3>
            <div className="chart-controls-group">
              <span className="sub-tag">24h</span>
            </div>
          </div>

          {/* Badges de filtrage individuel des capteurs */}
          {availableSensors.length > 0 && (
            <div className="sensor-filter-pills">
              <span className="filter-pill-label"><Layers size={13} /> Capteurs :</span>
              {availableSensors.map((sensorName, idx) => {
                const color = getSensorLineColor(sensorName, idx)
                const isHidden = hiddenSensors.includes(sensorName)
                return (
                  <button
                    key={sensorName}
                    type="button"
                    className={`sensor-pill ${isHidden ? 'hidden' : 'active'}`}
                    style={{
                      borderColor: color,
                      backgroundColor: isHidden ? 'transparent' : `${color}18`,
                      color: isHidden ? 'var(--text-secondary, #94a3b8)' : 'var(--text-primary, #0f172a)'
                    }}
                    onClick={() => toggleSensorVisibility(sensorName)}
                  >
                    <span className="pill-dot" style={{ backgroundColor: isHidden ? '#cbd5e1' : color }} />
                    {sensorName}
                  </button>
                )
              })}
            </div>
          )}

          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={sensorEvolutionData} margin={{ top: 15, right: 30, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis 
                yAxisId="left"
                domain={['auto', 'auto']} 
                tick={{ fontSize: 11 }} 
                stroke="#ef4444"
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                domain={[0, 100]}
                tick={{ fontSize: 11 }} 
                stroke="#3b82f6"
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'var(--bg-primary, #1e293b)',
                  borderColor: 'var(--border-color, #475569)',
                  borderRadius: '10px',
                  boxShadow: '0 8px 20px rgba(0,0,0,0.2)',
                  color: 'var(--text-primary, #f8fafc)'
                }}
                formatter={(value: any, name: any) => [`${value}`, String(name)]}
              />
              <Legend verticalAlign="top" height={36} />
              {availableSensors
                .filter(sensor => !hiddenSensors.includes(sensor))
                .flatMap((sensorName, idx) => {
                  const color = getSensorLineColor(sensorName, idx)
                  return [
                    <Line
                      key={`${sensorName}_temp`}
                      yAxisId="left"
                      type="monotone"
                      dataKey={`${sensorName}_temp`}
                      name={`${sensorName} - Temp (°C)`}
                      stroke={color}
                      strokeWidth={3}
                      dot={false}
                      activeDot={{ r: 6 }}
                      connectNulls
                    />,
                    <Line
                      key={`${sensorName}_humid`}
                      yAxisId="right"
                      type="monotone"
                      dataKey={`${sensorName}_humid`}
                      name={`${sensorName} - Humid (%)`}
                      stroke={color}
                      strokeDasharray="5 5"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 6 }}
                      connectNulls
                    />
                  ]
                })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {data.numFailedSensors > 0 && (
        <section className="alert alert-warning-mode">
          ⚠️ Attention : {data.numFailedSensors} capteur(s) défaillant(s) détecté(s)
        </section>
      )}

      {/* COMPOSANT TABLEAU D'HISTORIQUE & GRAND GRAPHIQUE */}
      <HistoryTable />
    </div>
  )
}

export default Dashboard

