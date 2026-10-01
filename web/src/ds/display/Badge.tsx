import React from 'react';
import { Icon } from '../core/Icon';
const TONES = {
  neutral: ['var(--status-neutral-bg)', 'var(--status-neutral-fg)', 'var(--status-neutral-solid)'],
  info: ['var(--status-info-bg)', 'var(--status-info-fg)', 'var(--status-info-solid)'],
  success: ['var(--status-success-bg)', 'var(--status-success-fg)', 'var(--status-success-solid)'],
  warning: ['var(--status-warning-bg)', 'var(--status-warning-fg)', 'var(--status-warning-solid)'],
  danger: ['var(--status-danger-bg)', 'var(--status-danger-fg)', 'var(--status-danger-solid)'],
  match: ['var(--match-bg)', 'var(--match-fg)', 'var(--match-solid)'],
  verified: ['var(--verified-bg)', 'var(--verified-fg)', 'var(--verified-solid)'],
};
/** Короткая неинтерактивная метка: роль, признак МСП, проверка. */
export interface BadgeProps {
  tone?: 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'match' | 'verified';
  variant?: 'soft' | 'solid' | 'outline';
  size?: 'sm' | 'md';
  icon?: string;
  dot?: boolean;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export function Badge({ tone = 'neutral', variant = 'soft', size = 'md', icon, dot, children, style }: BadgeProps) {
  const [bg, fg, solid] = TONES[tone] || TONES.neutral;
  const h = size === 'sm' ? 20 : 24;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: h, padding: '0 ' + (size === 'sm' ? 6 : 8) + 'px', borderRadius: 'var(--radius-sm)',
      fontSize: size === 'sm' ? 11 : 12, lineHeight: 1, fontWeight: 500, whiteSpace: 'nowrap',
      background: variant === 'solid' ? solid : variant === 'outline' ? 'transparent' : bg, color: variant === 'solid' ? '#fff' : fg,
      border: '1px solid ' + (variant === 'outline' ? solid : 'transparent'), ...style }}>
      {dot ? <span style={{ width: 6, height: 6, borderRadius: '50%', background: variant === 'solid' ? '#fff' : solid }} /> : null}
      {icon ? <Icon name={icon} size={size === 'sm' ? 12 : 14} /> : null}
      {children}
    </span>
  );
}
