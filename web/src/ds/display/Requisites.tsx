import React from 'react';
import { Icon } from '../core/Icon';
function Copy({ text }: { text: React.ReactNode }) {
  const [ok, setOk] = React.useState(false);
  return <button type="button" aria-label="Скопировать" title="Скопировать" onClick={() => { try { navigator.clipboard.writeText(String(text)); } catch (e) {} setOk(true); setTimeout(() => setOk(false), 1200); }}
    style={{ display: 'inline-flex', padding: 2, border: 0, background: 'none', cursor: 'pointer', color: ok ? 'var(--green-500)' : 'var(--text-tertiary)' }}><Icon name={ok ? 'check' : 'copy'} size={14} /></button>;
}
/** Список «параметр — значение» для реквизитов организации и сведений о закупке. */
export interface RequisiteItem { label: string; value: React.ReactNode; mono?: boolean; copyable?: boolean; }
export interface RequisitesProps {
  items: RequisiteItem[];
  columns?: 1 | 2 | 3;
  labelWidth?: number;
  style?: React.CSSProperties;
}
export function Requisites({ items = [], columns = 1, labelWidth = 160, style }: RequisitesProps) {
  return (
    <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: columns > 1 ? 'repeat(auto-fit, minmax(280px, 1fr))' : 'minmax(0,1fr)', columnGap: 32, rowGap: 10, ...style }}>
      {items.map((it) => (
        <div key={it.label} style={{ display: 'grid', gridTemplateColumns: labelWidth + 'px minmax(0,1fr)', gap: 12, fontSize: 14, lineHeight: '20px' }}>
          <dt style={{ color: 'var(--text-tertiary)' }}>{it.label}</dt>
          <dd style={{ margin: 0, display: 'flex', alignItems: 'flex-start', gap: 4, minWidth: 0, fontFamily: it.mono ? 'var(--font-mono)' : 'inherit', color: 'var(--text-primary)' }}>
            <span style={{ minWidth: 0, overflowWrap: it.mono ? 'normal' : 'break-word', whiteSpace: it.mono ? 'nowrap' : 'normal' }}>{it.value}</span>{it.copyable ? <Copy text={it.value} /> : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}
