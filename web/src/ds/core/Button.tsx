import React from 'react';
import { Icon } from './Icon';
const VARIANTS = {
  primary: { bg: 'var(--action-primary)', h: 'var(--action-primary-hover)', a: 'var(--action-primary-active)', fg: 'var(--text-inverse)', bd: 'transparent' },
  secondary: { bg: 'var(--action-secondary-bg)', h: 'var(--action-secondary-hover)', a: 'var(--blue-200)', fg: 'var(--blue-700)', bd: 'transparent' },
  outline: { bg: 'var(--surface-card)', h: 'var(--surface-hover)', a: 'var(--gray-100)', fg: 'var(--text-primary)', bd: 'var(--border-strong)' },
  ghost: { bg: 'transparent', h: 'var(--surface-hover)', a: 'var(--gray-100)', fg: 'var(--blue-600)', bd: 'transparent' },
  danger: { bg: 'var(--red-500)', h: 'var(--red-700)', a: 'var(--red-700)', fg: 'var(--text-inverse)', bd: 'transparent' },
};
const SIZES = { sm: { h: 32, px: 12, fs: 13, ic: 16 }, md: { h: 36, px: 14, fs: 14, ic: 16 }, lg: { h: 44, px: 20, fs: 15, ic: 18 } };
/** Кнопка действия. Одна primary на экран/блок; остальное — secondary/outline/ghost. */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  /** Имя иконки Lucide слева */
  iconLeft?: string;
  iconRight?: string;
  loading?: boolean;
  fullWidth?: boolean;
  children?: React.ReactNode;
}
export function Button({ variant = 'primary', size = 'md', iconLeft, iconRight, loading, disabled, fullWidth, type = 'button', children, style, ...rest }: ButtonProps) {
  const [hover, setHover] = React.useState(false);
  const [active, setActive] = React.useState(false);
  const [focus, setFocus] = React.useState(false);
  const v = VARIANTS[variant] || VARIANTS.primary;
  const s = SIZES[size] || SIZES.md;
  const off = disabled || loading;
  const bg = off ? (variant === 'ghost' ? 'transparent' : 'var(--gray-100)') : active ? v.a : hover ? v.h : v.bg;
  return (
    <button type={type} disabled={off} {...rest}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => { setHover(false); setActive(false); }}
      onMouseDown={() => setActive(true)} onMouseUp={() => setActive(false)}
      onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: s.h, padding: '0 ' + s.px + 'px',
        width: fullWidth ? '100%' : undefined, fontFamily: 'var(--font-sans)', fontSize: s.fs, fontWeight: 500, lineHeight: 1, whiteSpace: 'nowrap',
        color: off ? 'var(--text-disabled)' : v.fg, background: bg, border: '1px solid ' + (off && variant === 'outline' ? 'var(--border-default)' : v.bd),
        borderRadius: 'var(--radius-sm)', cursor: off ? 'not-allowed' : 'pointer', boxShadow: focus ? 'var(--focus-ring)' : 'none', outline: 'none',
        transition: 'background var(--duration-fast) var(--ease-standard)', ...style }}>
      {loading ? <Icon name="loader-circle" size={s.ic} style={{ animation: 'neva-spin 0.8s linear infinite' }} /> : iconLeft ? <Icon name={iconLeft} size={s.ic} /> : null}
      {children}
      {iconRight && !loading ? <Icon name={iconRight} size={s.ic} /> : null}
    </button>
  );
}
