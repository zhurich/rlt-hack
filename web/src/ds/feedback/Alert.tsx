import React from 'react';
import { Icon } from '../core/Icon';
const T = { info: ['info', 'info'], success: ['success', 'circle-check'], warning: ['warning', 'triangle-alert'], danger: ['danger', 'circle-alert'], match: ['match', 'sparkles'] };
/** Встроенное сообщение в потоке страницы: предупреждение, результат проверки, подсказка подбора. */
export interface AlertProps {
  tone?: 'info' | 'success' | 'warning' | 'danger' | 'match';
  title?: React.ReactNode;
  children?: React.ReactNode;
  action?: React.ReactNode;
  onClose?: () => void;
  style?: React.CSSProperties;
}
export function Alert({ tone = 'info', title, children, action, onClose, style }: AlertProps) {
  const [k, icon] = T[tone] || T.info;
  const bg = k === 'match' ? 'var(--match-bg)' : 'var(--status-' + k + '-bg)';
  const fg = k === 'match' ? 'var(--match-fg)' : 'var(--status-' + k + '-fg)';
  const solid = k === 'match' ? 'var(--match-solid)' : 'var(--status-' + k + '-solid)';
  return (
    <div role={tone === 'danger' ? 'alert' : 'status'} style={{ display: 'flex', gap: 12, padding: '12px 16px', borderRadius: 'var(--radius-md)', background: bg, color: 'var(--text-primary)', ...style }}>
      <Icon name={icon} size={20} color={solid} style={{ marginTop: 0 }} />
      <div style={{ flex: 1, minWidth: 0, fontSize: 14, lineHeight: '20px' }}>
        {title ? <div style={{ fontWeight: 600, color: fg }}>{title}</div> : null}
        {children ? <div style={{ marginTop: title ? 2 : 0, color: 'var(--text-secondary)', textWrap: 'pretty' }}>{children}</div> : null}
        {action ? <div style={{ marginTop: 10 }}>{action}</div> : null}
      </div>
      {onClose ? <button type="button" aria-label="Закрыть" onClick={onClose} style={{ alignSelf: 'flex-start', display: 'inline-flex', padding: 2, border: 0, background: 'none', cursor: 'pointer', color: 'var(--text-tertiary)' }}><Icon name="x" size={18} /></button> : null}
    </div>
  );
}
