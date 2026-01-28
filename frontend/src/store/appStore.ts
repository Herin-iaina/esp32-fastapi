import { create } from 'zustand'

interface AuthState {
  isAuthenticated: boolean
  username: string | null
  login: (username: string) => void
  logout: () => void
}

interface ThemeState {
  isDarkMode: boolean
  toggleDarkMode: () => void
}

interface AppState extends AuthState, ThemeState {}

export const useAppStore = create<AppState>((set) => ({
  // Auth
  isAuthenticated: false,
  username: null,
  login: (username: string) => {
    set({ isAuthenticated: true, username })
    localStorage.setItem('username', username)
  },
  logout: () => {
    set({ isAuthenticated: false, username: null })
    localStorage.removeItem('username')
  },

  // Theme
  isDarkMode: localStorage.getItem('darkMode') === 'true' || false,
  toggleDarkMode: () => set((state) => {
    const newValue = !state.isDarkMode
    localStorage.setItem('darkMode', String(newValue))
    if (newValue) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    return { isDarkMode: newValue }
  }),
}))
