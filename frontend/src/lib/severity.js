export const SEV_LABEL = { low: 'норма', medium: 'внимание', critical: 'критично' }
export function sevLabel(level) { return SEV_LABEL[level] || level }
export function sevColor(level) {
  return level === 'critical' ? 'var(--sev-crit)' : level === 'medium' ? 'var(--sev-med)' : 'var(--accent)'
}
