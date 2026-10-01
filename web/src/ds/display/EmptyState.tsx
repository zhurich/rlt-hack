import React from 'react';
import { Icon } from '../core/Icon';
/** Пустое состояние: ничего не найдено, список пуст. */
export interface EmptyStateProps {
  icon?: string;
  title: React.ReactNode;
  children?: React.ReactNode;
  action?: React.ReactNode;
  style?: React.CSSProperties;
}
export function EmptyState({ icon = 'search-x', title, children, action, style }: EmptyStateProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '48px 24px', ...style }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 56, height: 56, borderRadius: '50%', background: 'var(--surface-sunken)', color: 'var(--text-tertiary)' }}><Icon name={icon} size={24} /></span>
      <div style={{ marginTop: 16, fontSize: 'var(--text-h4)', lineHeight: 'var(--leading-h4)', fontWeight: 600 }}>{title}</div>
      {children ? <div style={{ marginTop: 6, maxWidth: 420, fontSize: 14, color: 'var(--text-secondary)', textWrap: 'pretty' }}>{children}</div> : null}
      {action ? <div style={{ marginTop: 20 }}>{action}</div> : null}
    </div>
  );
}
