import { create } from 'zustand'

export interface SensorReading {
  sensor: string
  temperature: number
  humidity: number
  timestamp: string
}

export interface DashboardData {
  average_temperature: number
  average_humidity: number
  fan_status: boolean
  humidifier_status: boolean
  numFailedSensors: number
  sensors: Record<string, { temperature: number; humidity: number }>
}

interface SensorStore {
  data: DashboardData | null
  history: SensorReading[]
  loading: boolean
  error: string | null
  isMockData: boolean
  fetchData: (useMock?: boolean) => Promise<void>
  fetchHistory: (hours?: number, useMock?: boolean) => Promise<void>
  setError: (error: string | null) => void
}

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const useSensorStore = create<SensorStore>((set) => ({
  data: null,
  history: [],
  loading: false,
  error: null,
  isMockData: false,

  fetchData: async (useMock = true) => {
    set({ loading: true, error: null })
    try {
      const mockParam = useMock ? '?mock=true' : ''
      const response = await fetch(`${API_BASE}/sensor/values${mockParam}`)
      if (!response.ok) throw new Error('Erreur lors de la récupération des données')
      const jsonData = await response.json()
      
      // Extraire les données du wrapper APIResponse
      const dashboardData = jsonData.data as DashboardData
      const isMock = jsonData.data?.is_mock || false
      
      set({ 
        data: dashboardData, 
        loading: false,
        isMockData: isMock
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur inconnue'
      set({ error: message, loading: false })
    }
  },

  fetchHistory: async (hours = 24, useMock = true) => {
    set({ loading: true, error: null })
    try {
      const mockParam = useMock ? '&mock=true' : ''
      const response = await fetch(`${API_BASE}/sensor/history?hours=${hours}${mockParam}`)
      if (!response.ok) throw new Error('Erreur lors de la récupération de l\'historique')
      const jsonData = await response.json()
      
      const historyData = jsonData.data?.history || []
      set({ 
        history: historyData, 
        loading: false,
        isMockData: jsonData.data?.is_mock || false
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur inconnue'
      set({ error: message, loading: false })
    }
  },

  setError: (error) => set({ error }),
}))
