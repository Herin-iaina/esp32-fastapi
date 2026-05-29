/**
 * Hook personnalisé pour utiliser le logger facilement dans les composants React
 */

import { useCallback } from 'react'
import { logger } from '../utils/logger'

export function useLogger(componentName: string) {
  /**
   * Logger un clic de bouton
   */
  const logButtonClick = useCallback(
    (buttonName: string, details?: any) => {
      logger.logButtonClick(buttonName, componentName, details)
    },
    [componentName]
  )

  /**
   * Logger une soumission de formulaire
   */
  const logFormSubmit = useCallback(
    (formName: string, data?: any) => {
      logger.logFormSubmit(formName, componentName, data)
    },
    [componentName]
  )

  /**
   * Logger un appel API
   */
  const logAPI = useCallback(
    (method: string, endpoint: string, status?: string) => {
      logger.logAPICall(method, endpoint, status)
    },
    []
  )

  /**
   * Logger une erreur
   */
  const logError = useCallback(
    (message: string, error?: any) => {
      logger.logError(componentName, message, error)
    },
    [componentName]
  )

  /**
   * Logger une information
   */
  const logInfo = useCallback(
    (message: string, details?: any) => {
      logger.logInfo(componentName, message, details)
    },
    [componentName]
  )

  /**
   * Logger un avertissement
   */
  const logWarn = useCallback(
    (message: string, details?: any) => {
      logger.logWarn(componentName, message, details)
    },
    [componentName]
  )

  /**
   * Logger de débogage
   */
  const logDebug = useCallback(
    (message: string, details?: any) => {
      logger.logDebug(componentName, message, details)
    },
    [componentName]
  )

  return {
    logButtonClick,
    logFormSubmit,
    logAPI,
    logError,
    logInfo,
    logWarn,
    logDebug,
  }
}

/**
 * Exemple d'utilisation dans un composant:
 *
 * function MyComponent() {
 *   const { logButtonClick, logInfo, logError } = useLogger('MyComponent')
 *
 *   const handleClick = () => {
 *     logButtonClick('Mon Bouton', { id: 123 })
 *   }
 *
 *   const handleSubmit = async () => {
 *     try {
 *       logInfo('Envoi des données')
 *       // ... code
 *       logInfo('Données envoyées avec succès')
 *     } catch (err) {
 *       logError('Erreur lors de l\'envoi', err)
 *     }
 *   }
 *
 *   return (
 *     <button onClick={handleClick}>Cliquez-moi</button>
 *   )
 * }
 */
