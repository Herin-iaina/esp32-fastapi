import { useState, useMemo, useEffect } from 'react'
import { useSensorStore } from '../store/sensorStore'
import { 
  Filter, ArrowUpDown, ArrowUp, ArrowDown, History, Loader2, 
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, 
  CheckSquare, Square, LineChart as LineChartIcon,
  Eye, EyeOff
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import './HistoryTable.css'

type SortField = 'timestamp' | 'sensor' | 'temperature' | 'humidity' | 'avgTemp' | 'avgHumid'
type SortOrder = 'asc' | 'desc'

// Palettes de couleurs pour les capteurs sur le grand graphique
const SENSOR_COLORS: Record<string, { temp: string; humid: string }> = {
  sensor_01: { temp: '#ef4444', humid: '#3b82f6' }, // Rouge / Bleu
  sensor_02: { temp: '#f97316', humid: '#06b6d4' }, // Orange / Cyan
  sensor_03: { temp: '#ec4899', humid: '#8b5cf6' }, // Rose / Violet
  sensor_04: { temp: '#eab308', humid: '#10b981' }, // Jaune / Vert
  sensor_05: { temp: '#f43f5e', humid: '#6366f1' }, // Crimson / Indigo
}

const DEFAULT_COLORS = [
  { temp: '#ef4444', humid: '#3b82f6' },
  { temp: '#f97316', humid: '#06b6d4' },
  { temp: '#ec4899', humid: '#8b5cf6' },
  { temp: '#eab308', humid: '#10b981' },
  { temp: '#f43f5e', humid: '#6366f1' },
]

function getSensorColor(sensorName: string, index: number) {
  if (SENSOR_COLORS[sensorName]) {
    return SENSOR_COLORS[sensorName]
  }
  return DEFAULT_COLORS[index % DEFAULT_COLORS.length]
}

function HistoryTable() {
  const { history, loading, fetchHistory, data } = useSensorStore()
  
  // Filtres
  const [selectedSensors, setSelectedSensors] = useState<string[]>([])
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [hoursFilter, setHoursFilter] = useState<number>(48)
  
  // Tri et pagination
  const [sortField, setSortField] = useState<SortField>('timestamp')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const [rowsPerPage, setRowsPerPage] = useState(10)

  // Options d'affichage du graphique
  const [showTemp, setShowTemp] = useState(true)
  const [showHumid, setShowHumid] = useState(true)

  // Liste des capteurs disponibles dans les données (ou dans history)
  const allSensorNames = useMemo(() => {
    const fromData = data ? Object.keys(data.sensors) : []
    const fromHistory = Array.from(new Set(history.map(h => h.sensor)))
    const combined = Array.from(new Set([...fromData, ...fromHistory])).sort()
    return combined.length > 0 ? combined : ['sensor_01', 'sensor_02', 'sensor_03']
  }, [data, history])

  // Initialiser les capteurs sélectionnés au démarrage (tous par défaut)
  useEffect(() => {
    if (selectedSensors.length === 0 && allSensorNames.length > 0) {
      setSelectedSensors(allSensorNames)
    }
  }, [allSensorNames])

  // Calcul des moyennes globales par timestamp
  const historyWithAverages = useMemo(() => {
    // Groupement par tranche ou timestamp pour calculer les moyennes globales à cet instant
    const timestampGroups: Record<string, { totalTemp: number; totalHumid: number; count: number }> = {}
    
    history.forEach(item => {
      // Normalisation de la date à la minute près
      const key = item.timestamp.substring(0, 16) 
      if (!timestampGroups[key]) {
        timestampGroups[key] = { totalTemp: 0, totalHumid: 0, count: 0 }
      }
      timestampGroups[key].totalTemp += item.temperature
      timestampGroups[key].totalHumid += item.humidity
      timestampGroups[key].count += 1
    })

    return history.map(item => {
      const key = item.timestamp.substring(0, 16)
      const group = timestampGroups[key]
      return {
        ...item,
        avgTemp: group && group.count > 0 ? group.totalTemp / group.count : item.temperature,
        avgHumid: group && group.count > 0 ? group.totalHumid / group.count : item.humidity
      }
    })
  }, [history])

  // Données filtrées par capteurs cochés & dates (sans réinitialiser les filtres au fetch)
  const filteredHistory = useMemo(() => {
    return historyWithAverages.filter(item => {
      // Filtre capteurs (cases à cocher)
      if (selectedSensors.length > 0 && !selectedSensors.includes(item.sensor)) {
        return false
      }
      // Filtre Date Début
      if (startDate) {
        const itemTime = new Date(item.timestamp).getTime()
        const startTime = new Date(startDate).getTime()
        if (itemTime < startTime) return false
      }
      // Filtre Date Fin
      if (endDate) {
        const itemTime = new Date(item.timestamp).getTime()
        const endTime = new Date(endDate).getTime()
        if (itemTime > endTime) return false
      }
      return true
    })
  }, [historyWithAverages, selectedSensors, startDate, endDate])

  // Tri des données
  const sortedHistory = useMemo(() => {
    return [...filteredHistory].sort((a, b) => {
      let comparison = 0
      if (sortField === 'timestamp') {
        comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      } else if (sortField === 'sensor') {
        comparison = a.sensor.localeCompare(b.sensor)
      } else {
        comparison = (a[sortField] as number) - (b[sortField] as number)
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })
  }, [filteredHistory, sortField, sortOrder])

  // Pagination
  const totalPages = Math.max(1, Math.ceil(sortedHistory.length / rowsPerPage))
  const startIndex = (currentPage - 1) * rowsPerPage
  const paginatedHistory = sortedHistory.slice(startIndex, startIndex + rowsPerPage)

  const handleFilterSubmit = () => {
    setCurrentPage(1)
    fetchHistory(hoursFilter, false, {
      start_date: startDate ? new Date(startDate).toISOString() : undefined,
      end_date: endDate ? new Date(endDate).toISOString() : undefined
    })
  }

  const toggleSensorCheck = (sensorName: string) => {
    setCurrentPage(1)
    setSelectedSensors(prev => 
      prev.includes(sensorName) 
        ? prev.filter(s => s !== sensorName)
        : [...prev, sensorName]
    )
  }

  const toggleAllSensors = () => {
    setCurrentPage(1)
    if (selectedSensors.length === allSensorNames.length) {
      setSelectedSensors([])
    } else {
      setSelectedSensors(allSensorNames)
    }
  }

  const toggleSort = (field: SortField) => {
    setCurrentPage(1)
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  // Préparation des données pour le Grand Graphique en courbe (triées par ordre chronologique ascendant)
  const chartData = useMemo(() => {
    const cronoData = [...filteredHistory].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )

    // Formater et grouper par timestamp lisible
    const mapByTime: Record<string, any> = {}

    cronoData.forEach(item => {
      const dateObj = new Date(item.timestamp)
      const formattedTime = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      const formattedDate = dateObj.toLocaleDateString([], { month: 'numeric', day: 'numeric' })
      const label = `${formattedDate} ${formattedTime}`

      if (!mapByTime[label]) {
        mapByTime[label] = {
          timestamp: label,
          rawTimestamp: item.timestamp,
          avgTemp: item.avgTemp,
          avgHumid: item.avgHumid
        }
      }

      // Ajouter les propriétés spécifiques à chaque capteur coché
      mapByTime[label][`${item.sensor}_temp`] = item.temperature
      mapByTime[label][`${item.sensor}_humid`] = item.humidity
    })

    return Object.values(mapByTime)
  }, [filteredHistory])

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown size={14} className="sort-icon-inactive" />
    return sortOrder === 'asc' ? <ArrowUp size={14} /> : <ArrowDown size={14} />
  }

  return (
    <div className="history-table-container">
      {/* En-tête avec Filtres */}
      <div className="history-header">
        <h3>
          <History size={24} /> Historique & Analyse Temporelle
        </h3>
        
        <div className="filter-controls-wrapper">
          {/* Sélection des Capteurs (Cases à Cocher) */}
          <div className="sensor-checkboxes-section">
            <div className="sensor-checkboxes-header">
              <span className="filter-label">Capteurs à afficher :</span>
              <button className="btn-text-action" onClick={toggleAllSensors}>
                {selectedSensors.length === allSensorNames.length ? (
                  <><Square size={14} /> Tout décocher</>
                ) : (
                  <><CheckSquare size={14} /> Tout cocher</>
                )}
              </button>
            </div>
            
            <div className="checkbox-group">
              {allSensorNames.map((sensorName, idx) => {
                const isChecked = selectedSensors.includes(sensorName)
                const colors = getSensorColor(sensorName, idx)
                return (
                  <label key={sensorName} className={`checkbox-chip ${isChecked ? 'active' : ''}`}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleSensorCheck(sensorName)}
                    />
                    <span 
                      className="color-dot" 
                      style={{ backgroundColor: colors.temp }} 
                      title="Couleur Capteur" 
                    />
                    <span>{sensorName}</span>
                  </label>
                )
              })}
            </div>
          </div>

          {/* Filtres de Dates et Période */}
          <div className="filter-bar">
            <div className="filter-group">
              <label>Période</label>
              <select 
                value={hoursFilter} 
                onChange={(e) => {
                  const h = Number(e.target.value)
                  setHoursFilter(h)
                  fetchHistory(h, false, {
                    start_date: startDate ? new Date(startDate).toISOString() : undefined,
                    end_date: endDate ? new Date(endDate).toISOString() : undefined
                  })
                }}
              >
                <option value={12}>Dernières 12h</option>
                <option value={24}>Dernières 24h</option>
                <option value={48}>Dernières 48h (J-1 inclus)</option>
                <option value={168}>Dernière semaine</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Date Début</label>
              <input 
                type="datetime-local" 
                value={startDate} 
                onChange={(e) => setStartDate(e.target.value)} 
              />
            </div>

            <div className="filter-group">
              <label>Date Fin</label>
              <input 
                type="datetime-local" 
                value={endDate} 
                onChange={(e) => setEndDate(e.target.value)} 
              />
            </div>

            <button className="btn-filter" onClick={handleFilterSubmit} disabled={loading}>
              <Filter size={18} />
              Filtrer
            </button>
          </div>
        </div>
      </div>

      {/* Tableau de l'Historique */}
      {loading && history.length === 0 ? (
        <div className="history-loading">
          <Loader2 size={24} className="spin" />
          Chargement de l'historique...
        </div>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th onClick={() => toggleSort('timestamp')} className="sortable">
                    Date / Heure <SortIcon field="timestamp" />
                  </th>
                  <th onClick={() => toggleSort('sensor')} className="sortable">
                    Capteur <SortIcon field="sensor" />
                  </th>
                  <th onClick={() => toggleSort('temperature')} className="sortable">
                    Température (°C) <SortIcon field="temperature" />
                  </th>
                  <th onClick={() => toggleSort('humidity')} className="sortable">
                    Humidité (%) <SortIcon field="humidity" />
                  </th>
                  <th onClick={() => toggleSort('avgTemp')} className="sortable avg-col">
                    Moy. Temp. Globale (°C) <SortIcon field="avgTemp" />
                  </th>
                  <th onClick={() => toggleSort('avgHumid')} className="sortable avg-col">
                    Moy. Humidité Globale (%) <SortIcon field="avgHumid" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedHistory.length > 0 ? (
                  paginatedHistory.map((record, index) => (
                    <tr key={`${record.timestamp}-${record.sensor}-${index}`}>
                      <td className="time-cell">{new Date(record.timestamp).toLocaleString()}</td>
                      <td>
                        <span className="sensor-badge">{record.sensor}</span>
                      </td>
                      <td className="temp-cell">{record.temperature.toFixed(1)} °C</td>
                      <td className="humid-cell">{record.humidity.toFixed(1)} %</td>
                      <td className="avg-temp-cell">{record.avgTemp.toFixed(1)} °C</td>
                      <td className="avg-humid-cell">{record.avgHumid.toFixed(1)} %</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="no-data">
                      Aucun enregistrement ne correspond aux filtres sélectionnés.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {sortedHistory.length > 0 && (
            <div className="pagination-container">
              <div className="pagination-info">
                <span>
                  {startIndex + 1}-{Math.min(startIndex + rowsPerPage, sortedHistory.length)} sur {sortedHistory.length} enregistrement{sortedHistory.length > 1 ? 's' : ''}
                </span>
                {loading && <Loader2 size={14} className="spin" />}
              </div>
              
              <div className="pagination-controls">
                <div className="rows-per-page">
                  <label>Lignes :</label>
                  <select
                    value={rowsPerPage}
                    onChange={(e) => {
                      setRowsPerPage(Number(e.target.value))
                      setCurrentPage(1)
                    }}
                  >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
                
                <div className="pagination-buttons">
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                    title="Première page"
                  >
                    <ChevronsLeft size={18} />
                  </button>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    title="Page précédente"
                  >
                    <ChevronLeft size={18} />
                  </button>
                  <span className="page-indicator">
                    {currentPage} / {totalPages}
                  </span>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    title="Page suivante"
                  >
                    <ChevronRight size={18} />
                  </button>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage(totalPages)}
                    disabled={currentPage === totalPages}
                    title="Dernière page"
                  >
                    <ChevronsRight size={18} />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Grand Graphique en Courbe après le Tableau */}
          <div className="large-chart-section">
            <div className="large-chart-header">
              <h4>
                <LineChartIcon size={20} /> Graphique d'Évolution Temporelle par Capteur
              </h4>

              <div className="chart-series-toggles">
                <button
                  className={`series-toggle-btn ${showTemp ? 'active-temp' : ''}`}
                  onClick={() => setShowTemp(!showTemp)}
                >
                  {showTemp ? <Eye size={16} /> : <EyeOff size={16} />}
                  <span>Température (°C)</span>
                </button>
                
                <button
                  className={`series-toggle-btn ${showHumid ? 'active-humid' : ''}`}
                  onClick={() => setShowHumid(!showHumid)}
                >
                  {showHumid ? <Eye size={16} /> : <EyeOff size={16} />}
                  <span>Humidité (%)</span>
                </button>
              </div>
            </div>

            {chartData.length > 0 && selectedSensors.length > 0 ? (
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={420}>
                  <LineChart data={chartData} margin={{ top: 15, right: 30, left: 10, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                    <XAxis 
                      dataKey="timestamp" 
                      tick={{ fontSize: 11 }} 
                      dy={10} 
                    />
                    <YAxis 
                      yAxisId="left" 
                      orientation="left" 
                      domain={['auto', 'auto']}
                      unit="°C"
                      stroke="#ef4444" 
                      tick={{ fontSize: 12 }} 
                    />
                    <YAxis 
                      yAxisId="right" 
                      orientation="right" 
                      domain={[0, 100]}
                      unit="%"
                      stroke="#3b82f6" 
                      tick={{ fontSize: 12 }} 
                    />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: 'var(--bg-primary, #1e293b)',
                        borderColor: 'var(--border-color, #475569)',
                        borderRadius: '10px',
                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                        color: 'var(--text-primary, #f8fafc)'
                      }}
                    />
                    <Legend verticalAlign="top" height={40} />

                    {/* Générer 2 séries par capteur coché (Température et Humidité) */}
                    {selectedSensors.map((sensorName, idx) => {
                      const colors = getSensorColor(sensorName, idx)
                      return (
                        <g key={sensorName}>
                          {showTemp && (
                            <Line
                              yAxisId="left"
                              type="monotone"
                              dataKey={`${sensorName}_temp`}
                              name={`${sensorName} - Temp (°C)`}
                              stroke={colors.temp}
                              strokeWidth={2.5}
                              dot={false}
                              activeDot={{ r: 6 }}
                            />
                          )}
                          {showHumid && (
                            <Line
                              yAxisId="right"
                              type="monotone"
                              dataKey={`${sensorName}_humid`}
                              name={`${sensorName} - Humidité (%)`}
                              stroke={colors.humid}
                              strokeDasharray="4 4"
                              strokeWidth={2}
                              dot={false}
                              activeDot={{ r: 6 }}
                            />
                          )}
                        </g>
                      )
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="chart-placeholder">
                Veuillez sélectionner au moins un capteur et une série pour afficher le graphique.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default HistoryTable
