import { useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'
import { useSensorStore } from '../store/sensorStore'
import SensorCard from '../components/SensorCard'
import StatusCard from '../components/StatusCard'
import HistoryTable from '../components/HistoryTable'
import './Dashboard.css'
import { Thermometer, Droplets, Wind, Zap, TestTube } from 'lucide-react'

function Dashboard() {
  const { data, loading, fetchData, fetchHistory, isMockData } = useSensorStore()

  useEffect(() => {
    // Ne plus forcer les données fictives
    const load = () => {
      fetchData(false)
      fetchHistory(24, false)
    }

    load()
    const interval = setInterval(load, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [fetchData, fetchHistory])

  if (loading && !data) {
    return <div className="loading">Chargement des données...</div>
  }

  if (!data) {
    return <div className="error">Aucune donnée disponible</div>
  }

  // Préparer les données pour les graphiques
  const sensorData = Object.entries(data.sensors).map(([name, values]) => ({
    name,
    temperature: values.temperature,
    humidity: values.humidity,
  }))

  const chartData = [
    { name: 'Temp', value: data.average_temperature, fill: '#ef4444' },
    { name: 'Humid', value: data.average_humidity, fill: '#3b82f6' },
  ]

  return (
    <div className="dashboard">
      {isMockData && (
        <div className="alert alert-info">
          <TestTube size={20} />
          <span>🧪 Mode Test - Données fictives en cours d'utilisation</span>
        </div>
      )}

      <section className="overview-section">
        <h2>Vue d'ensemble</h2>
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

      <section className="sensors-section">
        <h2>Capteurs Individuels</h2>
        <div className="sensors-grid">
          {sensorData.map((sensor) => (
            <SensorCard key={sensor.name} sensor={sensor} />
          ))}
        </div>
      </section>

      <section className="charts-section">
        <div className="chart-container">
          <h3>Comparaison Température/Humidité</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#8884d8" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Analyse des Capteurs (Radar)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={sensorData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="name" />
              <PolarRadiusAxis angle={90} domain={[0, 100]} />
              <Radar name="Température" dataKey="temperature" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} />
              <Radar name="Humidité" dataKey="humidity" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
              <Legend />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {data.numFailedSensors > 0 && (
        <section className="alert alert-warning">
          ⚠️ {data.numFailedSensors} capteur(s) défaillant(s) détecté(s)
        </section>
      )}

      <HistoryTable />
    </div>
  )
}

export default Dashboard
