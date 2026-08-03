import { Thermometer, Droplets } from 'lucide-react'
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
      <div className="sensor-card-header">
        <h4>{sensor.name}</h4>
        <div className="sensor-status-pill">
          <span className="status-dot"></span>
          <span>En ligne</span>
        </div>
      </div>

      <div className="sensor-values-grid">
        <div className="value-block temperature-block">
          <div className="value-header">
            <Thermometer size={16} />
            <span>Température</span>
          </div>
          <span className="value-number">{sensor.temperature.toFixed(1)}°C</span>
        </div>

        <div className={`value-block humidity-block ${getHumidStatus(sensor.humidity)}`}>
          <div className="value-header">
            <Droplets size={16} />
            <span>Humidité</span>
          </div>
          <span className="value-number">{sensor.humidity.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  )
}

export default SensorCard
