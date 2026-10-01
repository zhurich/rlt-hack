import React from 'react';
import { Icon } from './Icon';
/** Квадратная кнопка с иконкой; обязательна подпись label для доступности. */
export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: string;
  label: string;
  variant?: 'ghost' | 'outline' | 'primary' | 'inverse';
  size?: 'sm' | 'md' | 'lg';
  /** Нажатое/выбранное состояние */
  active?: boolean;
  /** Счётчик в правом верхнем углу */
  badge?: number | string;
}
export function IconButton({ icon, label, variant = 'ghost', size = 'md', active, disabled, badge, style, ...rest }: IconButtonProps) {
  const [hover, setHover] = React.useState(false);
  const [focus, setFocus] = React.useState(false);
  const d = { sm: 32, md: 36, lg: 44 }[size] || 36;
  const ic = { sm: 16, md: 20, lg: 24 }[size] || 20;
  const onDark = variant === 'inverse';
  const bg = disabled ? 'transparent' : active ? (onDark ? 'rgba(255,255,255,.16)' : 'var(--surface-selected)') : hover ? (onDark ? 'rgba(255,255,255,.10)' : variant === 'primary' ? 'var(--action-primary-hover)' : 'var(--surface-hover)') : variant === 'primary' ? 'var(--action-primary)' : variant === 'outline' ? 'var(--surface-card)' : 'transparent';
  const fg = disabled ? 'var(--text-disabled)' : onDark ? 'var(--text-inverse)' : variant === 'primary' ? 'var(--text-inverse)' : active ? 'var(--blue-600)' : 'var(--text-secondary)';
  return (
    <button type="button" aria-label={label} title={label} disabled={disabled} {...rest}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)} onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: d, height: d, padding: 0, flex: 'none',
        background: bg, color: fg, border: '1px solid ' + (variant === 'outline' ? 'var(--border-strong)' : 'transparent'), borderRadius: 'var(--radius-sm)',
        cursor: disabled ? 'not-allowed' : 'pointer', outline: 'none', boxShadow: focus ? 'var(--focus-ring)' : 'none', transition: 'background var(--duration-fast)', ...style }}>
      <Icon name={icon} size={ic} />
      {badge ? <span style={{ position: 'absolute', top: 4, right: 4, minWidth: 16, height: 16, padding: '0 4px', borderRadius: 8, background: 'var(--red-500)', color: '#fff', fontSize: 10, fontWeight: 600, lineHeight: '16px', textAlign: 'center' }}>{badge}</span> : null}
    </button>
  );
}
