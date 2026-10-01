import React from 'react';
import { Icon } from '../core/Icon';
function Label({ children, required, htmlFor }: { children: React.ReactNode; required?: boolean; htmlFor?: string }) {
  return <label htmlFor={htmlFor} style={{ display: 'block', marginBottom: 6, fontSize: 13, lineHeight: '16px', fontWeight: 500, color: 'var(--text-primary)' }}>{children}{required ? <span style={{ color: 'var(--red-500)', marginLeft: 2 }}>*</span> : null}</label>;
}
function Help({ error, hint }: { error?: string; hint?: string }) {
  if (!error && !hint) return null;
  return <div style={{ marginTop: 6, fontSize: 12, lineHeight: '16px', color: error ? 'var(--red-700)' : 'var(--text-tertiary)' }}>{error || hint}</div>;
}
/** Текстовое поле с подписью, подсказкой и ошибкой. */
export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  hint?: string;
  /** Текст ошибки — поле подсвечивается красным */
  error?: string;
  required?: boolean;
  iconLeft?: string;
  /** Единица измерения или текст справа: «₽», «шт.» */
  suffix?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  /** Моноширинный ввод для ИНН, ОГРН, кодов */
  mono?: boolean;
  inputStyle?: React.CSSProperties;
}
export function Input({ label, hint, error, required, iconLeft, suffix, size = 'md', mono, disabled, id, style, inputStyle, ...rest }: InputProps) {
  const [focus, setFocus] = React.useState(false);
  const h = { sm: 32, md: 36, lg: 44 }[size] || 36;
  const fid = id || (label ? 'in-' + String(label).replace(/\s+/g, '-') : undefined);
  return (
    <div style={{ minWidth: 0, ...style }}>
      {label ? <Label required={required} htmlFor={fid}>{label}</Label> : null}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, height: h, padding: '0 12px', background: disabled ? 'var(--surface-sunken)' : 'var(--surface-card)',
        border: '1px solid ' + (error ? 'var(--red-500)' : focus ? 'var(--border-focus)' : 'var(--border-default)'), borderRadius: 'var(--radius-sm)',
        boxShadow: focus ? (error ? 'var(--focus-ring-danger)' : 'var(--focus-ring)') : 'none', transition: 'border-color var(--duration-fast)' }}>
        {iconLeft ? <Icon name={iconLeft} size={18} color="var(--text-tertiary)" /> : null}
        <input id={fid} disabled={disabled} {...rest} onFocus={(e) => { setFocus(true); rest.onFocus && rest.onFocus(e); }} onBlur={(e) => { setFocus(false); rest.onBlur && rest.onBlur(e); }}
          style={{ flex: 1, minWidth: 0, height: '100%', border: 0, outline: 'none', background: 'transparent', padding: 0, fontFamily: mono ? 'var(--font-mono)' : 'var(--font-sans)', fontSize: size === 'lg' ? 16 : 14, color: disabled ? 'var(--text-disabled)' : 'var(--text-primary)', ...inputStyle }} />
        {suffix ? <span style={{ color: 'var(--text-tertiary)', fontSize: 13, flex: 'none' }}>{suffix}</span> : null}
      </div>
      <Help error={error} hint={hint} />
    </div>
  );
}
