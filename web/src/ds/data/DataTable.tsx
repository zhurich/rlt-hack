import React from 'react';
import { Icon } from '../core/Icon';
import { Checkbox } from '../forms/Checkbox';
const DENS = {
  regular: { pad: '12px 16px', fs: 14, lh: '20px', mono: 13 },
  dense: { pad: '8px 12px', fs: 14, lh: '20px', mono: 13 },
  compact: { pad: '6px 10px', fs: 13, lh: '18px', mono: 12 },
};
/** Реестровая таблица: сортировка, выбор строк, моноширинные колонки для номеров. */
export interface DataTableColumn<T> {
  key: string;
  title: React.ReactNode;
  width?: number | string;
  align?: 'left' | 'right' | 'center';
  mono?: boolean;
  nowrap?: boolean;
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
}
type SortState = { key: string; dir: 'asc' | 'desc' };
export interface DataTableProps<T, K extends string | number> {
  columns: DataTableColumn<T>[];
  rows: T[];
  /** Поле строки с уникальным ключом */
  rowKey?: string;
  selectable?: boolean;
  selected?: K[];
  onSelect?: (keys: K[]) => void;
  sort?: SortState;
  onSort?: (s: SortState) => void;
  onRowClick?: (row: T) => void;
  /** @deprecated используйте density="dense" */
  dense?: boolean;
  /** regular — выдача и профиль; dense — вложенные таблицы; compact — реестры (13/18, строка ≈30px) */
  density?: 'regular' | 'dense' | 'compact';
  /** Чередование фона строк — для длинных реестров */
  zebra?: boolean;
  /** Вертикальные разделители колонок — для реестров с 6+ колонками */
  gridLines?: boolean;
  style?: React.CSSProperties;
}
export function DataTable<T extends object, K extends string | number = string | number>({ columns = [], rows = [], rowKey = 'id', selectable, selected = [], onSelect, sort, onSort, onRowClick, dense, density, zebra, gridLines, style }: DataTableProps<T, K>) {
  const [hoverRow, setHoverRow] = React.useState<K | null>(null);
  const cell = (r: T, key: string) => (r as Record<string, unknown>)[key];
  const keyOf = (r: T) => cell(r, rowKey) as K;
  const d = DENS[density || (dense ? 'dense' : 'regular')] || DENS.regular;
  const pad = d.pad;
  const vline = gridLines ? '1px solid var(--border-subtle)' : 0;
  const allOn = rows.length > 0 && rows.every((r) => selected.includes(keyOf(r)));
  const someOn = rows.some((r) => selected.includes(keyOf(r)));
  const toggle = (k: K) => onSelect && onSelect(selected.includes(k) ? selected.filter((x) => x !== k) : selected.concat(k));
  return (
    <div style={{ overflowX: 'auto', background: 'var(--surface-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)', ...style }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: d.fs, lineHeight: d.lh }}>
        <thead>
          <tr style={{ background: 'var(--surface-sunken)' }}>
            {selectable ? <th style={{ width: 44, padding: pad, borderBottom: '1px solid var(--border-default)' }}><Checkbox checked={allOn} indeterminate={!allOn && someOn} onChange={() => onSelect && onSelect(allOn ? [] : rows.map(keyOf))} /></th> : null}
            {columns.map((c, ci) => {
              const active = sort && sort.key === c.key;
              return (
                <th key={c.key} onClick={c.sortable && onSort ? () => onSort({ key: c.key, dir: sort && active && sort.dir === 'asc' ? 'desc' : 'asc' }) : undefined}
                  style={{ width: c.width, padding: pad, textAlign: c.align || 'left', verticalAlign: 'bottom', fontSize: 12, lineHeight: '16px', fontWeight: 600, color: active ? 'var(--text-primary)' : 'var(--text-secondary)', whiteSpace: 'nowrap', borderBottom: '1px solid var(--border-default)', borderLeft: ci > 0 || selectable ? vline : 0, cursor: c.sortable ? 'pointer' : 'default', userSelect: 'none' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>{c.title}{c.sortable ? <Icon name={sort && active ? (sort.dir === 'asc' ? 'arrow-up' : 'arrow-down') : 'arrow-up-down'} size={14} color={active ? 'var(--blue-600)' : 'var(--gray-300)'} /> : null}</span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const k = keyOf(r);
            const on = selected.includes(k);
            const bb = i < rows.length - 1 ? '1px solid var(--border-subtle)' : 0;
            return (
              <tr key={k} onMouseEnter={() => setHoverRow(k)} onMouseLeave={() => setHoverRow(null)} onClick={onRowClick ? () => onRowClick(r) : undefined}
                style={{ background: on ? 'var(--surface-selected)' : hoverRow === k ? 'var(--surface-hover)' : zebra && i % 2 ? 'var(--gray-25)' : 'transparent', cursor: onRowClick ? 'pointer' : 'default' }}>
                {selectable ? <td style={{ padding: pad, borderBottom: bb }} onClick={(e) => e.stopPropagation()}><Checkbox checked={on} onChange={() => toggle(k)} /></td> : null}
                {columns.map((c, ci) => (
                  <td key={c.key} style={{ padding: pad, textAlign: c.align || 'left', verticalAlign: 'top', fontFamily: c.mono ? 'var(--font-mono)' : 'inherit', fontSize: c.mono ? d.mono : d.fs, borderBottom: bb, borderLeft: ci > 0 || selectable ? vline : 0, whiteSpace: c.nowrap ? 'nowrap' : 'normal' }}>
                    {c.render ? c.render(r) : (cell(r, c.key) as React.ReactNode)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
