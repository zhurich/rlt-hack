import React from 'react';
import { Icon } from '../core/Icon';
/** Интерактивный чип: применённые фильтры (с крестиком). */
export interface TagProps {
  children?: React.ReactNode;
  selected?: boolean;
  onClick?: () => void;
  /** Показывает крестик удаления */
  onRemove?: () => void;
  count?: number | string;
  icon?: string;
  size?: 'sm' | 'md';
  style?: React.CSSProperties;
}
export function Tag({ children, selected, onClick, onRemove, count, icon, size = 'md', style }: TagProps) {
  const [hover, setHover] = React.useState(false);
  const interactive = !!onClick;
  const h = size === 'sm' ? 28 : 32;
  return (
    <span onClick={onClick} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)} role={interactive ? 'button' : undefined} aria-pressed={interactive ? !!selected : undefined}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: h, padding: '0 ' + (onRemove ? 6 : 12) + 'px 0 12px', borderRadius: 'var(--radius-pill)', whiteSpace: 'nowrap',
        fontSize: size === 'sm' ? 12 : 13, fontWeight: 500, cursor: interactive ? 'pointer' : 'default', transition: 'all var(--duration-fast)',
        background: selected ? 'var(--surface-selected)' : hover && interactive ? 'var(--surface-hover)' : 'var(--surface-card)',
        color: selected ? 'var(--blue-700)' : 'var(--text-primary)', border: '1px solid ' + (selected ? 'var(--blue-300)' : 'var(--border-default)'), ...style }}>
      {icon ? <Icon name={icon} size={14} /> : null}
      {children}
      {count != null ? <span style={{ color: selected ? 'var(--blue-600)' : 'var(--text-tertiary)', fontWeight: 400 }}>{count}</span> : null}
      {onRemove ? (
        <button type="button" aria-label="Убрать" onClick={(e) => { e.stopPropagation(); onRemove(); }}
          style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 20, height: 20, padding: 0, border: 0, borderRadius: '50%', cursor: 'pointer', background: 'transparent', color: 'inherit' }}>
          <Icon name="x" size={14} />
        </button>
      ) : null}
    </span>
  );
}
