import React from 'react';
/** Переключатель режима, применяемого сразу (без кнопки «Применить»). */
export interface SwitchProps {
  label?: React.ReactNode;
  checked?: boolean;
  disabled?: boolean;
  onChange?: (checked: boolean) => void;
  style?: React.CSSProperties;
}
export function Switch({ label, checked, disabled, onChange, style }: SwitchProps) {
  const [focus, setFocus] = React.useState(false);
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, cursor: disabled ? 'not-allowed' : 'pointer', fontSize: 14, lineHeight: '20px', color: disabled ? 'var(--text-disabled)' : 'var(--text-primary)', ...style }}>
      <input type="checkbox" role="switch" checked={!!checked} disabled={disabled} onChange={(e) => onChange && onChange(e.target.checked)} onFocus={() => setFocus(true)} onBlur={() => setFocus(false)} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
      <span style={{ position: 'relative', flex: 'none', width: 36, height: 20, borderRadius: 10, background: disabled ? 'var(--gray-200)' : checked ? 'var(--action-primary)' : 'var(--gray-300)', boxShadow: focus ? 'var(--focus-ring)' : 'none', transition: 'background var(--duration-base) var(--ease-standard)' }}>
        <span style={{ position: 'absolute', top: 2, left: checked ? 18 : 2, width: 16, height: 16, borderRadius: '50%', background: '#fff', boxShadow: 'var(--shadow-1)', transition: 'left var(--duration-base) var(--ease-standard)' }} />
      </span>
      {label}
    </label>
  );
}
