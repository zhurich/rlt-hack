import React from 'react';
/** Вкладки разделов (line) или переключатель вида (segmented). */
export interface TabItem<I extends string = string> { id: I; label: React.ReactNode; count?: number | string; }
export interface TabsProps<I extends string = string> {
  items: TabItem<I>[];
  value: I;
  onChange?: (id: I) => void;
  variant?: 'line' | 'segmented';
  style?: React.CSSProperties;
}
export function Tabs<I extends string = string>({ items = [], value, onChange, variant = 'line', style }: TabsProps<I>) {
  const [hover, setHover] = React.useState<I | null>(null);
  if (variant === 'segmented') {
    return (
      <div role="tablist" style={{ display: 'inline-flex', gap: 2, padding: 2, background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)', ...style }}>
        {items.map((it) => { const on = it.id === value; return (
          <button key={it.id} role="tab" aria-selected={on} type="button" onClick={() => onChange && onChange(it.id)}
            style={{ height: 32, padding: '0 14px', border: 0, borderRadius: 'var(--radius-sm)', background: on ? 'var(--surface-card)' : 'transparent', boxShadow: on ? 'var(--shadow-1)' : 'none', color: on ? 'var(--text-primary)' : 'var(--text-secondary)', fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
            {it.label}{it.count != null ? <span style={{ marginLeft: 6, color: 'var(--text-tertiary)', fontWeight: 400 }}>{it.count}</span> : null}
          </button>); })}
      </div>
    );
  }
  return (
    <div role="tablist" style={{ display: 'flex', gap: 24, borderBottom: '1px solid var(--border-default)', overflowX: 'auto', overflowY: 'hidden', scrollbarWidth: 'none', ...style }}>
      {items.map((it) => { const on = it.id === value; return (
        <button key={it.id} role="tab" aria-selected={on} type="button" onClick={() => onChange && onChange(it.id)} onMouseEnter={() => setHover(it.id)} onMouseLeave={() => setHover(null)}
          style={{ position: 'relative', height: 44, padding: 0, border: 0, background: 'none', whiteSpace: 'nowrap', fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: on ? 600 : 500, cursor: 'pointer',
            color: on ? 'var(--text-primary)' : hover === it.id ? 'var(--blue-600)' : 'var(--text-secondary)' }}>
          {it.label}
          {it.count != null ? <span style={{ marginLeft: 6, padding: '1px 6px', borderRadius: 10, background: on ? 'var(--blue-50)' : 'var(--surface-sunken)', color: on ? 'var(--blue-700)' : 'var(--text-tertiary)', fontSize: 12, fontWeight: 500 }}>{it.count}</span> : null}
          <span style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 2, background: on ? 'var(--action-primary)' : 'transparent' }} />
        </button>); })}
    </div>
  );
}
