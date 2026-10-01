import React from 'react';
// Статусы контрагента — из docs/statuses.md (считаются в enrich/companies.py).
// «Проверенный» показывается золотым Badge (см. components/StatusChip.jsx), остальные — пилюлей с точкой.
type StatusTone = 'neutral' | 'info' | 'warning' | 'success' | 'danger';
const MAP: Record<string, [StatusTone, string]> = {
  'участник': ['info', 'Участник'], 'новый, подтверждён': ['success', 'Новый, подтверждён'], 'новый': ['neutral', 'Новый'],
  'требует проверки': ['warning', 'Требует проверки'], 'риск': ['danger', 'Риск'], 'проверенный': ['success', 'Проверенный'],
};
/** Статус контрагента: пилюля с точкой. */
export interface StatusBadgeProps {
  /** Предопределённый статус; подпись подставляется автоматически */
  status?: string;
  /** Переопределить тон для произвольного статуса */
  tone?: StatusTone;
  /** sm — для плотных реестров */
  size?: 'sm' | 'md';
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export function StatusBadge({ status, tone, children, size = 'md', style }: StatusBadgeProps) {
  const m = (status && MAP[status]) || ([tone || 'neutral', status] as const);
  const t = tone || m[0];
  const sm = size === 'sm';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: sm ? 20 : 24, padding: sm ? '0 8px' : '0 10px', borderRadius: 'var(--radius-pill)', whiteSpace: 'nowrap',
      background: 'var(--status-' + t + '-bg)', color: 'var(--status-' + t + '-fg)', fontSize: sm ? 11 : 12, fontWeight: 500, lineHeight: 1, ...style }}>
      <span style={{ width: 6, height: 6, flex: 'none', borderRadius: '50%', background: 'var(--status-' + t + '-solid)' }} />
      {children || m[1]}
    </span>
  );
}
