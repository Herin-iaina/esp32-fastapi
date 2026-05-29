import { useState, useEffect } from 'react'
import { logger } from '../utils/logger'
import './DebugPanel.css'
import { ChevronDown, X, RotateCcw, Copy, Download } from 'lucide-react'

interface DebugPanelProps {
  isOpen?: boolean
}

function DebugPanel({ isOpen: initialOpen = false }: DebugPanelProps) {
  const [isOpen, setIsOpen] = useState(initialOpen)
  const [logs, setLogs] = useState(logger.getLogs())
  const [filter, setFilter] = useState<'ALL' | 'INFO' | 'DEBUG' | 'WARN' | 'ERROR'>('ALL')
  const [filterComponent, setFilterComponent] = useState<string>('ALL')

  // Mettre à jour les logs toutes les secondes
  useEffect(() => {
    const interval = setInterval(() => {
      setLogs([...logger.getLogs()])
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  // Filtrer les logs
  const filteredLogs = logs.filter(log => {
    const levelMatch = filter === 'ALL' || log.level === filter
    const componentMatch = filterComponent === 'ALL' || log.component === filterComponent
    return levelMatch && componentMatch
  })

  // Obtenir les composants uniques
  const components = ['ALL', ...new Set(logs.map(log => log.component))]

  const handleCopyLogs = () => {
    const logsJSON = JSON.stringify(logs, null, 2)
    navigator.clipboard.writeText(logsJSON)
    alert('Logs copiés dans le presse-papiers!')
  }

  const handleDownloadLogs = () => {
    const logsJSON = JSON.stringify(logs, null, 2)
    const blob = new Blob([logsJSON], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs_${new Date().toISOString().slice(0, 19)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleClearLogs = () => {
    logger.clearLogs()
    setLogs([])
  }

  if (!isOpen) {
    return (
      <button
        className="debug-panel-toggle"
        onClick={() => setIsOpen(true)}
        title="Ouvrir le panneau de débogage"
      >
        🐛
      </button>
    )
  }

  return (
    <div className="debug-panel">
      <div className="debug-panel-header">
        <h3>🐛 Panneau de Débogage</h3>
        <button
          className="debug-close"
          onClick={() => setIsOpen(false)}
          title="Fermer"
        >
          <X size={18} />
        </button>
      </div>

      <div className="debug-panel-controls">
        <div className="control-group">
          <label>Niveau:</label>
          <select value={filter} onChange={(e) => setFilter(e.target.value as any)}>
            <option value="ALL">Tous</option>
            <option value="INFO">Info</option>
            <option value="DEBUG">Debug</option>
            <option value="WARN">Avertissement</option>
            <option value="ERROR">Erreur</option>
          </select>
        </div>

        <div className="control-group">
          <label>Composant:</label>
          <select value={filterComponent} onChange={(e) => setFilterComponent(e.target.value)}>
            {components.map(comp => (
              <option key={comp} value={comp}>{comp}</option>
            ))}
          </select>
        </div>

        <div className="control-buttons">
          <button
            className="btn-action"
            onClick={handleCopyLogs}
            title="Copier les logs"
          >
            <Copy size={16} />
          </button>
          <button
            className="btn-action"
            onClick={handleDownloadLogs}
            title="Télécharger les logs"
          >
            <Download size={16} />
          </button>
          <button
            className="btn-action btn-danger"
            onClick={handleClearLogs}
            title="Effacer les logs"
          >
            <RotateCcw size={16} />
          </button>
        </div>

        <div className="log-count">
          {filteredLogs.length}/{logs.length} logs
        </div>
      </div>

      <div className="debug-logs-container">
        {filteredLogs.length === 0 ? (
          <div className="debug-empty">Aucun log à afficher</div>
        ) : (
          <div className="debug-logs">
            {filteredLogs.map((log, idx) => (
              <div key={idx} className={`debug-log debug-log-${log.level.toLowerCase()}`}>
                <div className="log-meta">
                  <span className="log-time">{log.timestamp}</span>
                  <span className={`log-level log-level-${log.level.toLowerCase()}`}>
                    {log.level}
                  </span>
                  <span className="log-component">{log.component}</span>
                </div>
                <div className="log-action">{log.action}</div>
                {log.details && (
                  <div className="log-details">
                    {typeof log.details === 'string' ? (
                      log.details
                    ) : (
                      JSON.stringify(log.details, null, 2)
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default DebugPanel
