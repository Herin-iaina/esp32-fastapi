import './SensorCard.css'

interface SensorCardProps {
  sensor: {
    name: string
    temperature: number
    humidity: number
  }
}

function SensorCard({ sensor }: SensorCardProps) {
  const getTempStatus = (temp: number) => {
    if (temp < 15) return 'cold'
    if (temp > 30) return 'hot'
    return 'normal'
  }

  const getHumidStatus = (humid: number) => {
    if (humid < 30) return 'dry'
    if (humid > 70) return 'wet'
    return 'normal'
  }

  return (
    <div className={`sensor-card ${getTempStatus(sensor.temperature)}`}>
      <h4>{sensor.name}</h4>
      <div className="sensor-values">
        <div className="value-block temperature">
          <span className="label">🌡️ Temp</span>
          <span className="value">{sensor.temperature.toFixed(1)}°C</span>
        </div>
        <div className={`value-block humidity ${getHumidStatus(sensor.humidity)}`}>
          <span className="label">💧 Humidité</span>
          <span className="value">{sensor.humidity.toFixed(1)}%</span>
        </div>
      </div>
      <div className="sensor-status">
        <div className="status-indicator"></div>
        <span>Actif</span>
      </div>
    </div>
  )
}

export default SensorCard
