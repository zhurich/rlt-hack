import React from 'react';
import { Icon } from '../core/Icon';
function Label({ children, required, htmlFor }: { children: React.ReactNode; required?: boolean; htmlFor?: string }) {
  return <label htmlFor={htmlFor} style={{ display: 'block', marginBottom: 6, fontSize: 13, lineHeight: '16px', fontWeight: 500, color: 'var(--text-primary)' }}>{children}{required ? <span style={{ color: 'var(--red-500)', marginLeft: 2 }}>*</span> : null}</label>;
}
function Help({ error, hint }: { error?: string; hint?: string }) {
  if (!error && !hint) return null;
  return <div style={{ marginTop: 6, fontSize: 12, lineHeight: '16px', color: error ? 'var(--red-700)' : 'var(--text-tertiary)' }}>{error || hint}</div>;
}
/** Выпадающий список на базе нативного select. */
export interface SelectOption { value: string; label: string; }
export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  options?: Array<SelectOption | string>;
  placeholder?: string;
  size?: 'sm' | 'md' | 'lg';
}
export function Select({ label, hint, error, required, options = [], placeholder, size = 'md', disabled, id, style, ...rest }: SelectProps) {
  const [focus, setFocus] = React.useState(false);
  const h = { sm: 32, md: 36, lg: 44 }[size] || 36;
  const fid = id || (label ? 'sel-' + String(label).replace(/\s+/g, '-') : undefined);
  return (
    <div style={{ minWidth: 0, ...style }}>
      {label ? <Label required={required} htmlFor={fid}>{label}</Label> : null}
      <div style={{ position: 'relative' }}>
        <select id={fid} disabled={disabled} {...rest} onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
          style={{ appearance: 'none', WebkitAppearance: 'none', width: '100%', height: h, padding: '0 36px 0 12px', fontFamily: 'var(--font-sans)', fontSize: 14,
            color: disabled ? 'var(--text-disabled)' : 'var(--text-primary)', background: disabled ? 'var(--surface-sunken)' : 'var(--surface-card)',
            border: '1px solid ' + (error ? 'var(--red-500)' : focus ? 'var(--border-focus)' : 'var(--border-default)'), borderRadius: 'var(--radius-sm)',
            boxShadow: focus ? 'var(--focus-ring)' : 'none', outline: 'none', cursor: disabled ? 'not-allowed' : 'pointer' }}>
          {placeholder ? <option value="">{placeholder}</option> : null}
          {options.map((o) => { const v = typeof o === 'string' ? o : o.value; const l = typeof o === 'string' ? o : o.label; return <option key={v} value={v}>{l}</option>; })}
        </select>
        <Icon name="chevron-down" size={18} color="var(--text-tertiary)" style={{ position: 'absolute', right: 10, top: '50%', marginTop: -9, pointerEvents: 'none' }} />
      </div>
      <Help error={error} hint={hint} />
    </div>
  );
}
