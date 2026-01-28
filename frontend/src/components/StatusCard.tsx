import { ReactNode } from 'react'
import './StatusCard.css'

interface StatusCardProps {
  label: string
  value: string
  unit?: string
  icon?: ReactNode
  color?: 'temperature' | 'humidity' | 'success' | 'neutral'
}

function StatusCard({ label, value, unit = '', icon, color = 'neutral' }: StatusCardProps) {
  return (
    <div className={`status-card status-${color}`}>
      {icon && <div className="status-icon">{icon}</div>}
      <div className="status-content">
        <p className="status-label">{label}</p>
        <p className="status-value">
          {value}
          {unit && <span className="status-unit">{unit}</span>}
        </p>
      </div>
    </div>
  )
}

export default StatusCard
