import { useState } from 'react'
import { useSensorStore } from '../store/sensorStore'
import { Filter, ArrowUpDown, ArrowUp, ArrowDown, History, Loader2 } from 'lucide-react'
import './HistoryTable.css'

type SortField = 'timestamp' | 'sensor' | 'temperature' | 'humidity'
type SortOrder = 'asc' | 'desc'

function HistoryTable() {
    const { history, loading, fetchHistory, data } = useSensorStore()
    const [sensorFilter, setSensorFilter] = useState('')
    const [startDate, setStartDate] = useState('')
    const [endDate, setEndDate] = useState('')
    const [sortField, setSortField] = useState<SortField>('timestamp')
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

    // Lister les capteurs uniques pour le filtre
    const sensorNames = data ? Object.keys(data.sensors) : []

    const handleFilter = () => {
        fetchHistory(24, false, {
            sensor: sensorFilter || undefined,
            start_date: startDate ? new Date(startDate).toISOString() : undefined,
            end_date: endDate ? new Date(endDate).toISOString() : undefined
        })
    }

    const toggleSort = (field: SortField) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        } else {
            setSortField(field)
            setSortOrder('desc')
        }
    }

    const sortedHistory = [...history].sort((a, b) => {
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

    const SortIcon = ({ field }: { field: SortField }) => {
        if (sortField !== field) return <ArrowUpDown size={14} className="sort-icon-inactive" />
        return sortOrder === 'asc' ? <ArrowUp size={14} /> : <ArrowDown size={14} />
    }

    return (
        <div className="history-table-container">
            <div className="history-header">
                <h3><History size={24} /> Historique des relevés</h3>
                <div className="filter-bar">
                    <div className="filter-group">
                        <label>Capteur</label>
                        <select value={sensorFilter} onChange={(e) => setSensorFilter(e.target.value)}>
                            <option value="">Tous les capteurs</option>
                            {sensorNames.map(name => (
                                <option key={name} value={name}>{name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="filter-group">
                        <label>Début</label>
                        <input type="datetime-local" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                    </div>
                    <div className="filter-group">
                        <label>Fin</label>
                        <input type="datetime-local" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                    </div>
                    <button className="btn-filter" onClick={handleFilter} disabled={loading}>
                        <Filter size={18} />
                        Filtrer
                    </button>
                </div>
            </div>

            {loading && sortedHistory.length === 0 ? (
                <div className="history-loading">
                    <Loader2 size={20} />
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
                                </tr>
                            </thead>
                            <tbody>
                                {sortedHistory.length > 0 ? (
                                    sortedHistory.map((record, index) => (
                                        <tr key={`${record.timestamp}-${index}`}>
                                            <td>{new Date(record.timestamp).toLocaleString()}</td>
                                            <td>{record.sensor}</td>
                                            <td className="temp-cell">{record.temperature.toFixed(1)}</td>
                                            <td className="humid-cell">{record.humidity.toFixed(1)}</td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={4} className="no-data">Aucun historique disponible</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                    {sortedHistory.length > 0 && (
                        <div className="history-stats">
                            <span>{sortedHistory.length} enregistrement{sortedHistory.length > 1 ? 's' : ''}</span>
                            {loading && <Loader2 size={14} className="spin" />}
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

export default HistoryTable
