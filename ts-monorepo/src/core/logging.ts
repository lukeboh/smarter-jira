export type LogLevel = "debug" | "info" | "warn" | "error";

export interface Logger {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
}

export function createLogger(level: LogLevel = "info"): Logger {
  const priorities: Record<LogLevel, number> = {
    debug: 10,
    info: 20,
    warn: 30,
    error: 40
  };

  const current = priorities[level];

  function allowed(target: LogLevel): boolean {
    return priorities[target] >= current;
  }

  return {
    debug: (...args: unknown[]) => {
      if (allowed("debug")) console.debug(...args);
    },
    info: (...args: unknown[]) => {
      if (allowed("info")) console.info(...args);
    },
    warn: (...args: unknown[]) => {
      if (allowed("warn")) console.warn(...args);
    },
    error: (...args: unknown[]) => {
      if (allowed("error")) console.error(...args);
    }
  };
}
