import React from 'react';
import { Icon } from '../core/Icon';
/** Сворачиваемая группа фасетного фильтра в боковой панели выдачи. */
export interface FilterGroupProps {
  title: React.ReactNode;
  children?: React.ReactNode;
  defaultOpen?: boolean;
  /** Число выбранных значений — показывается счётчиком */
  selectedCount?: number;
  onReset?: () => void;
  style?: React.CSSProperties;
}
export function FilterGroup({ title, children, defaultOpen = true, selectedCount, onReset, style }: FilterGroupProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <section style={{ padding: '16px 0', borderBottom: '1px solid var(--border-subtle)', ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
          style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, padding: 0, border: 0, background: 'none', cursor: 'pointer', fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', textAlign: 'left' }}>
          {title}
          {selectedCount ? <span style={{ minWidth: 18, height: 18, padding: '0 5px', borderRadius: 9, background: 'var(--action-primary)', color: '#fff', fontSize: 11, lineHeight: '18px', textAlign: 'center' }}>{selectedCount}</span> : null}
          <Icon name="chevron-down" size={16} color="var(--text-tertiary)" style={{ marginLeft: 'auto', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform var(--duration-base)' }} />
        </button>
      </div>
      {open ? <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>{children}</div> : null}
      {open && selectedCount && onReset ? <button type="button" onClick={onReset} style={{ marginTop: 10, padding: 0, border: 0, background: 'none', cursor: 'pointer', fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--text-link)' }}>Сбросить</button> : null}
    </section>
  );
}
