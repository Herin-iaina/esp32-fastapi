import { useState, useMemo, useEffect, useRef } from 'react'
import { useSensorStore } from '../store/sensorStore'
import { 
  Filter, ArrowUpDown, ArrowUp, ArrowDown, History, Loader2, 
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, 
  CheckSquare, Square, LineChart as LineChartIcon,
  Eye, EyeOff, ChevronDown
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
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
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

  // Fermer la liste déroulante au clic à l'extérieur
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

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
    const bucketSize = 30 * 1000
    const cronoData = [...filteredHistory].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )

    const mapByBucket: Record<number, any> = {}

    cronoData.forEach(item => {
      const dateObj = new Date(item.timestamp)
      const bucketKey = Math.floor(dateObj.getTime() / bucketSize) * bucketSize
      const formattedTime = new Date(bucketKey).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

      if (!mapByBucket[bucketKey]) {
        mapByBucket[bucketKey] = {
          timestamp: formattedTime,
          rawTimestamp: bucketKey,
          avgTempSum: 0,
          avgHumidSum: 0,
          avgCount: 0,
          sensors: {} as Record<string, { sum: number; count: number }>
        }
      }

      const bucket = mapByBucket[bucketKey]
      bucket.avgTempSum += item.temperature
      bucket.avgHumidSum += item.humidity
      bucket.avgCount += 1

      const tempKey = `${item.sensor}_temp`
      const humidKey = `${item.sensor}_humid`

      bucket.sensors[tempKey] = bucket.sensors[tempKey] || { sum: 0, count: 0 }
      bucket.sensors[humidKey] = bucket.sensors[humidKey] || { sum: 0, count: 0 }

      bucket.sensors[tempKey].sum += item.temperature
      bucket.sensors[tempKey].count += 1
      bucket.sensors[humidKey].sum += item.humidity
      bucket.sensors[humidKey].count += 1
    })

    return Object.values(mapByBucket)
      .sort((a, b) => a.rawTimestamp - b.rawTimestamp)
      .map(bucket => {
        const point: Record<string, any> = {
          timestamp: bucket.timestamp,
          rawTimestamp: bucket.rawTimestamp,
          avgTemp: bucket.avgCount > 0 ? Number((bucket.avgTempSum / bucket.avgCount).toFixed(1)) : undefined,
          avgHumid: bucket.avgCount > 0 ? Number((bucket.avgHumidSum / bucket.avgCount).toFixed(1)) : undefined
        }

        Object.entries(bucket.sensors).forEach(([key, value]) => {
          const sensorValue = value as { sum: number; count: number }
          point[key] = sensorValue.count > 0 ? Number((sensorValue.sum / sensorValue.count).toFixed(1)) : undefined
        })

        return point
      })
  }, [filteredHistory])

  const xAxisTicks = useMemo(() => {
    if (!chartData.length) return []
    const values = chartData
      .map(item => item.rawTimestamp)
      .filter((value): value is number => typeof value === 'number')
      .sort((a, b) => a - b)

    if (!values.length) return []

    const min = values[0]
    const max = values[values.length - 1]
    const step = 30 * 1000
    const ticks: number[] = []

    for (let current = min; current <= max; current += step) {
      ticks.push(current)
    }

    if (ticks[ticks.length - 1] !== max) {
      ticks.push(max)
    }

    return ticks
  }, [chartData])

  const formatTickTime = (value: number) => {
    return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

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
          {/* Barre de filtres alignée sur une ligne (optimisation d'espace) */}
          <div className="filter-bar">
            {/* Liste Déroulante Multi-Sélection des Capteurs */}
            <div className="filter-group sensor-dropdown-group" ref={dropdownRef}>
              <label>Capteurs à afficher</label>
              <div className="sensor-dropdown-wrapper">
                <button
                  type="button"
                  className="sensor-dropdown-trigger"
                  onClick={() => setIsDropdownOpen(prev => !prev)}
                >
                  <span className="dropdown-label-text">
                    {selectedSensors.length === 0 
                      ? 'Aucun capteur' 
                      : selectedSensors.length === allSensorNames.length 
                      ? 'Tous les capteurs' 
                      : `${selectedSensors.length} capteur(s)`}
                  </span>
                  <ChevronDown size={16} className={`dropdown-chevron ${isDropdownOpen ? 'open' : ''}`} />
                </button>

                {isDropdownOpen && (
                  <div className="sensor-dropdown-menu">
                    <div className="sensor-dropdown-actions">
                      <button type="button" className="btn-text-action" onClick={toggleAllSensors}>
                        {selectedSensors.length === allSensorNames.length ? (
                          <><Square size={13} /> Tout décocher</>
                        ) : (
                          <><CheckSquare size={13} /> Tout cocher</>
                        )}
                      </button>
                    </div>
                    <div className="sensor-dropdown-list">
                      {allSensorNames.map((sensorName, idx) => {
                        const isChecked = selectedSensors.includes(sensorName)
                        const colors = getSensorColor(sensorName, idx)
                        return (
                          <label key={sensorName} className={`sensor-dropdown-item ${isChecked ? 'active' : ''}`}>
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
                )}
              </div>
            </div>

            {/* Période */}
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

            {/* Date Début */}
            <div className="filter-group">
              <label>Date Début</label>
              <input 
                type="datetime-local" 
                value={startDate} 
                onChange={(e) => setStartDate(e.target.value)} 
              />
            </div>

            {/* Date Fin */}
            <div className="filter-group">
              <label>Date Fin</label>
              <input 
                type="datetime-local" 
                value={endDate} 
                onChange={(e) => setEndDate(e.target.value)} 
              />
            </div>

            {/* Bouton Filtrer */}
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
                <LineChartIcon size={20} /> Courbe continue par capteur (points toutes les 30s)
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
                      dataKey="rawTimestamp"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      ticks={xAxisTicks}
                      tickFormatter={formatTickTime}
                      tick={{ fontSize: 11 }}
                      dy={10}
                      interval={0}
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

                    {/* Générer les séries Line pour chaque capteur coché sans wrapper <g> */}
                    {selectedSensors.flatMap((sensorName, idx) => {
                      const colors = getSensorColor(sensorName, idx)
                      const lines = []
                      if (showTemp) {
                        lines.push(
                          <Line
                            key={`${sensorName}_temp`}
                            yAxisId="left"
                            type="monotone"
                            dataKey={`${sensorName}_temp`}
                            name={`${sensorName} - Temp (°C)`}
                            stroke={colors.temp}
                            strokeWidth={3}
                            dot={false}
                            activeDot={{ r: 6 }}
                            connectNulls
                          />
                        )
                      }
                      if (showHumid) {
                        lines.push(
                          <Line
                            key={`${sensorName}_humid`}
                            yAxisId="right"
                            type="monotone"
                            dataKey={`${sensorName}_humid`}
                            name={`${sensorName} - Humidité (%)`}
                            stroke={colors.humid}
                            strokeDasharray="4 4"
                            strokeWidth={3}
                            dot={false}
                            activeDot={{ r: 6 }}
                            connectNulls
                          />
                        )
                      }
                      return lines
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

