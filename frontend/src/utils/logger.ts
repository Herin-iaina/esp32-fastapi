/**
 * Utilitaire de logging pour déboguer les clics des boutons et les interactions
 */

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  component: string;
  action: string;
  details?: any;
}

class Logger {
  private logs: LogEntry[] = [];
  private maxLogs = 500;

  private formatTimestamp(): string {
    return new Date().toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  }

  private createLogEntry(level: LogLevel, component: string, action: string, details?: any): LogEntry {
    return {
      timestamp: this.formatTimestamp(),
      level,
      component,
      action,
      details
    };
  }

  private logToConsole(entry: LogEntry): void {
    const prefix = `[${entry.timestamp}] [${entry.level}] ${entry.component}`;
    const style = this.getConsoleStyle(entry.level);

    if (entry.details) {
      console.log(`%c${prefix} - ${entry.action}`, style, entry.details);
    } else {
      console.log(`%c${prefix} - ${entry.action}`, style);
    }
  }

  private getConsoleStyle(level: LogLevel): string {
    const styles = {
      DEBUG: 'color: #888; font-weight: bold;',
      INFO: 'color: #0066cc; font-weight: bold;',
      WARN: 'color: #ff9900; font-weight: bold;',
      ERROR: 'color: #cc0000; font-weight: bold;',
    };
    return styles[level];
  }

  private addToLogs(entry: LogEntry): void {
    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }
  }

  /**
   * Log un clic de bouton
   */
  public logButtonClick(buttonName: string, component: string, details?: any): void {
    const entry = this.createLogEntry('INFO', component, `Bouton cliqué: ${buttonName}`, details);
    this.addToLogs(entry);
    this.logToConsole(entry);
  }

  /**
   * Log une action de validation de formulaire
   */
  public logFormSubmit(formName: string, component: string, data?: any): void {
    const entry = this.createLogEntry('INFO', component, `Formulaire soumis: ${formName}`, data);
    this.addToLogs(entry);
    this.logToConsole(entry);
  }

  /**
   * Log un appel API
   */
  public logAPICall(method: string, endpoint: string, status?: string): void {
    const entry = this.createLogEntry('DEBUG', 'API', `${method} ${endpoint}`, { status });
    this.addToLogs(entry);
    this.logToConsole(entry);
  }

  /**
   * Log une erreur
   */
  public logError(component: string, errorMessage: string, error?: any): void {
    const entry = this.createLogEntry('ERROR', component, errorMessage, error);
    this.addToLogs(entry);
    this.logToConsole(entry);
  }

  /**
   * Log une information
   */
  public logInfo(component: string, message: string, details?: any): void {
    const entry = this.createLogEntry('INFO', component, message, details);
    this.addToLogs(entry);
    this.logToConsole(entry);
  }

  /**
   * Log un avertissement
   */
  public logWarn(component: string, message: string, details?: any): void {
    const entry = this.createLogEntry('WARN', component, message, details);
    this.addToLogs(entry);
    this.logToConsole(entry);
  }

  /**
   * Log de débogage
   */
  public logDebug(component: string, message: string, details?: any): void {
    const entry = this.createLogEntry('DEBUG', component, message, details);
    this.addToLogs(entry);
    this.logToConsole(entry);
  }

  /**
   * Obtenir tous les logs
   */
  public getLogs(): LogEntry[] {
    return [...this.logs];
  }

  /**
   * Filtrer les logs par composant
   */
  public getLogsByComponent(component: string): LogEntry[] {
    return this.logs.filter(log => log.component === component);
  }

  /**
   * Filtrer les logs par niveau
   */
  public getLogsByLevel(level: LogLevel): LogEntry[] {
    return this.logs.filter(log => log.level === level);
  }

  /**
   * Exporter les logs en JSON
   */
  public exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  /**
   * Afficher un résumé des logs dans la console
   */
  public printSummary(): void {
    console.log('%c=== RÉSUMÉ DES LOGS ===', 'color: #0066cc; font-weight: bold; font-size: 14px;');
    console.table(this.logs.map(log => ({
      Heure: log.timestamp,
      Niveau: log.level,
      Composant: log.component,
      Action: log.action
    })));
  }

  /**
   * Effacer tous les logs
   */
  public clearLogs(): void {
    this.logs = [];
    console.log('%c🗑️ Logs effacés', 'color: #666; font-weight: bold;');
  }
}

// Créer une instance unique du logger
export const logger = new Logger();

// Rendre disponible globalement dans le window pour accès facile depuis la console
if (typeof window !== 'undefined') {
  (window as any).logger = logger;
}
