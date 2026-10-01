import type { ReactNode } from 'react';
import { Button, IconButton, Badge, Card, MatchScore, EmptyState, Breadcrumbs } from '../ds';
import { StatusChip, RoleChip, ActualChip } from '../components/chips';
import { num, money, date, pct, orgName, hasDebt, inRnp, winRate } from '../lib';
import type { Actual, RankedItem } from '../types';

interface Row {
  label: string;
  render: (s: RankedItem) => ReactNode;
  /** Значение для выбора лучшего в строке; нет — строка не сравнивается */
  value?: (s: RankedItem) => number | null | undefined;
}

export interface CompareScreenProps {
  items: RankedItem[];
  actual: Actual;
  toggleCompare: (inn: string) => void;
  clearCompare: () => void;
  openSupplier: (inn: string) => void;
  back: () => void;
}

export function CompareScreen({ items, actual, toggleCompare, clearCompare, openSupplier, back }: CompareScreenProps) {
  const rows: Row[] = [
    { label: 'Балл', render: (s) => <MatchScore value={s.rel} variant="bar" unit="" label={s.isNew ? 'среди новых компаний' : 'среди поставщиков из истории'} /> },
    { label: 'Статус', render: (s) => <StatusChip company={s.company} size="sm" /> },
    { label: 'Роль', render: (s) => <RoleChip company={s.company} size="sm" /> },
    { label: 'Регион', render: (s) => s.company.place || '—' },
    { label: 'Основной ОКВЭД', render: (s) => (s.company.okved_main ? s.company.okved_main + ' — ' + s.company.okved_main_name : '—') },
    { label: 'Участий', render: (s) => num(s.company.bids), value: (s) => s.company.bids },
    { label: 'Побед', render: (s) => <b>{num(s.company.wins)}</b>, value: (s) => s.company.wins },
    { label: 'Доля побед', render: (s) => { const r = winRate(s.company); return r == null ? '—' : pct(r); }, value: (s) => winRate(s.company) },
    { label: 'Последняя заявка', render: (s) => date(s.company.last_bid) },
    { label: 'Выручка за 2025 год', render: (s) => money(s.company.revenue), value: (s) => s.company.revenue },
    { label: 'Работников', render: (s) => num(s.company.headcount), value: (s) => s.company.headcount },
    { label: 'Долг по налогам', render: (s) => (hasDebt(s.company) ? money(s.company.tax_debt) : 'не числится') },
    { label: 'Признаки', render: (s) => <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{s.company.msp_category ? <Badge size="sm">МСП</Badge> : null}{inRnp(s.company) ? <Badge size="sm" tone="danger" variant="solid">РНП</Badge> : null}<ActualChip mark={actual[s.inn]} size="sm" /></div> },
    { label: 'Главная причина', render: (s) => <span style={{ fontSize: 13 }}>{s.reasons[0] || '—'}</span> },
  ];
  const best = (value: Row['value']) => {
    if (!value || items.length < 2) return null;
    const top = items.reduce((a, b) => ((value(b) || 0) > (value(a) || 0) ? b : a));
    return value(top) ? top.inn : null;
  };
  return (
    <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: '20px var(--gutter) 48px' }}>
      <Breadcrumbs items={[{ label: 'Подбор поставщиков' }, { label: 'Сравнение' }]} onNavigate={back} />
      <div style={{ display: 'flex', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16, margin: '12px 0 20px' }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <h1 style={{ margin: 0, fontSize: 'var(--text-h1)', lineHeight: 'var(--leading-h1)', fontWeight: 700 }}>Сравнение поставщиков</h1>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Лучшее значение в строке выделено. Сравниваются компании из подбора по текущей закупке.</div>
        </div>
        {items.length ? <Button variant="outline" onClick={clearCompare}>Очистить</Button> : null}
      </div>
      {!items.length ? <Card padding={0}><EmptyState icon="git-compare" title="Список сравнения пуст" action={<Button variant="outline" onClick={back}>Перейти к подбору</Button>}>Добавьте поставщиков кнопкой «Сравнить» в выдаче.</EmptyState></Card> : (
        <div style={{ overflowX: 'auto', background: 'var(--surface-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead><tr>
              <th style={{ width: 180, borderBottom: '1px solid var(--border-default)' }} />
              {items.map((s) => (
                <th key={s.inn} style={{ padding: 16, textAlign: 'left', verticalAlign: 'top', borderBottom: '1px solid var(--border-default)', borderLeft: '1px solid var(--border-subtle)', minWidth: 220 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <a href="#" onClick={(e) => { e.preventDefault(); openSupplier(s.inn); }} style={{ flex: 1, fontSize: 15, lineHeight: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>{orgName(s.company)}</a>
                    <IconButton icon="x" label="Убрать из сравнения" size="sm" onClick={() => toggleCompare(s.inn)} />
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 400, color: 'var(--text-tertiary)', marginTop: 2 }}>ИНН {s.inn}</div>
                </th>
              ))}
            </tr></thead>
            <tbody>{rows.map((row, i) => { const b = best(row.value); return (
              <tr key={row.label} style={{ background: i % 2 ? 'var(--surface-page)' : 'transparent' }}>
                <td style={{ padding: '12px 16px', color: 'var(--text-secondary)', fontSize: 13 }}>{row.label}</td>
                {items.map((s) => <td key={s.inn} style={{ padding: '12px 16px', verticalAlign: 'top', borderLeft: '1px solid var(--border-subtle)', background: b === s.inn ? 'var(--match-bg)' : undefined }}>{row.render(s)}</td>)}
              </tr>); })}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
