/**
 * Structured Logger for Frontend
 *
 * Provides consistent logging across the frontend with:
 * - Log levels (debug, info, warn, error)
 * - Structured context metadata
 * - Environment-aware filtering
 * - Timestamp formatting
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  level: LogLevel
  message: string
  timestamp: string
  context?: Record<string, unknown>
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
}

class Logger {
  private minLevel: LogLevel
  private name: string

  constructor(
    name: string = 'app',
    minLevel: LogLevel = process.env.NODE_ENV === 'production' ? 'warn' : 'debug'
  ) {
    this.name = name
    this.minLevel = minLevel
  }

  private log(level: LogLevel, message: string, context?: Record<string, unknown>) {
    if (LOG_LEVELS[level] < LOG_LEVELS[this.minLevel]) return

    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      context,
    }

    const prefix = `[${entry.timestamp.substring(11, 23)}] [${this.name}] [${level.toUpperCase()}]`
    const consoleMethod = level === 'debug' ? 'log' : level

    if (context && Object.keys(context).length > 0) {
      console[consoleMethod](prefix, message, context)
    } else {
      console[consoleMethod](prefix, message)
    }

    // In production, could send errors to a logging service
    if (level === 'error' && process.env.NODE_ENV === 'production') {
      // Future: Send to error tracking service
      // sendToErrorService(entry)
    }
  }

  debug = (msg: string, ctx?: Record<string, unknown>) => this.log('debug', msg, ctx)
  info = (msg: string, ctx?: Record<string, unknown>) => this.log('info', msg, ctx)
  warn = (msg: string, ctx?: Record<string, unknown>) => this.log('warn', msg, ctx)
  error = (msg: string, ctx?: Record<string, unknown>) => this.log('error', msg, ctx)

  /**
   * Create a child logger with a specific name prefix
   */
  child(name: string): Logger {
    return new Logger(`${this.name}.${name}`, this.minLevel)
  }
}

/**
 * Default logger instance
 */
export const logger = new Logger('gamed-ai')

/**
 * Create a named logger for a specific module
 *
 * @example
 * const logger = createLogger('pipeline')
 * logger.info('Pipeline started', { runId: '123' })
 */
export function createLogger(name: string): Logger {
  return new Logger(`gamed-ai.${name}`)
}

/**
 * Common logging contexts
 */
export const LogContext = {
  pipeline: (runId: string, extra?: Record<string, unknown>) => ({
    runId,
    ...extra,
  }),
  stage: (stageName: string, status?: string, extra?: Record<string, unknown>) => ({
    stageName,
    status,
    ...extra,
  }),
  api: (endpoint: string, method: string, extra?: Record<string, unknown>) => ({
    endpoint,
    method,
    ...extra,
  }),
  game: (processId: string, extra?: Record<string, unknown>) => ({
    processId,
    ...extra,
  }),
}

export default logger
