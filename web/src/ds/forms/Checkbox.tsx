import React from 'react';
import { Icon } from '../core/Icon';

/** Флажок; в фильтрах показывает счётчик найденных записей справа. */
export interface CheckboxProps {
  label?: React.ReactNode;
  description?: string;
  checked?: boolean;
  indeterminate?: boolean;
  disabled?: boolean;
  /** Количество записей для фасетного фильтра */
  count?: number | string;
  onChange?: (checked: boolean, e: React.ChangeEvent<HTMLInputElement>) => void;
  name?: string;
  value?: string;
  style?: React.CSSProperties;
}
export function Checkbox({ label, checked, indeterminate, disabled, count, onChange, name, value, style, description }: CheckboxProps) {
  const [focus, setFocus] = React.useState(false);
  const [hover, setHover] = React.useState(false);
  const on = checked || indeterminate;
  return (
    <label onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: disabled ? 'not-allowed' : 'pointer', color: disabled ? 'var(--text-disabled)' : 'var(--text-primary)', fontSize: 14, lineHeight: '20px', ...style }}>
      <input type="checkbox" name={name} value={value} checked={!!checked} disabled={disabled} onChange={(e) => onChange && onChange(e.target.checked, e)}
        onFocus={() => setFocus(true)} onBlur={() => setFocus(false)} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
      <span style={{ flex: 'none', width: 18, height: 18, marginTop: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        borderRadius: 'var(--radius-xs)', background: disabled ? 'var(--surface-sunken)' : on ? 'var(--action-primary)' : 'var(--surface-card)',
        border: '1.5px solid ' + (disabled ? 'var(--border-default)' : on ? 'var(--action-primary)' : hover ? 'var(--blue-400)' : 'var(--border-strong)'),
        boxShadow: focus ? 'var(--focus-ring)' : 'none', transition: 'all var(--duration-fast)' }}>
        {on ? <Icon name={indeterminate ? 'minus' : 'check'} size={14} color="#fff" /> : null}
      </span>
      <span style={{ flex: 1, minWidth: 0 }}>
        {label}
        {description ? <span style={{ display: 'block', fontSize: 12, lineHeight: '16px', color: 'var(--text-tertiary)' }}>{description}</span> : null}
      </span>
      {count != null ? <span style={{ flex: 'none', fontSize: 12, color: 'var(--text-tertiary)' }}>{count}</span> : null}
    </label>
  );
}
