import React from 'react';
import { Icon, Button, Badge, MatchScore } from '../ds';
import { StatusChip, RoleChip, MspChip, ActualChip } from './chips';
import { num, money, date, orgName, inRnp } from '../lib';
import type { RankedItem } from '../types';

interface SupplierCardProps {
  item: RankedItem;
  /** true — победил в этой закупке, false — участвовал, undefined — не участвовал */
  mark: boolean | undefined;
  inCompare: boolean;
  onOpen: () => void;
  onCompare: () => void;
}

const Stat = ({ label, value }: { label: string; value: string }) => (
  <div style={{ minWidth: 0 }}><div style={{ fontSize: 12, lineHeight: '16px', color: 'var(--text-tertiary)' }}>{label}</div><div style={{ fontSize: 14, lineHeight: '20px', fontWeight: 600, whiteSpace: 'nowrap' }}>{value}</div></div>
);

// Карточка контрагента в выдаче: раскладка SupplierCard из дизайн-системы, поля — из ответа подбора.
export function SupplierCard({ item, mark, inCompare, onOpen, onCompare }: SupplierCardProps) {
  const c = item.company;
  const [hover, setHover] = React.useState(false);
  const hit = mark != null;
  return (
    <article onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid ' + (inCompare ? 'var(--blue-400)' : hover ? 'var(--border-strong)' : 'var(--border-default)'),
        boxShadow: [hit ? 'inset 3px 0 0 var(--green-500)' : null, inCompare ? '0 0 0 1px var(--blue-400)' : hover ? 'var(--shadow-1)' : null].filter(Boolean).join(', ') || 'none',
        transition: 'border-color var(--duration-fast), box-shadow var(--duration-fast)' }}>
      <div style={{ display: 'flex', gap: 20, padding: '20px 20px 16px' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
            <RoleChip company={c} />
            <StatusChip company={c} />
            <MspChip company={c} />
            {inRnp(c) ? <Badge tone="danger" variant="solid">РНП</Badge> : null}
            <ActualChip mark={mark} />
          </div>
          <a href="#" onClick={(e) => { e.preventDefault(); onOpen(); }} style={{ display: 'block', fontSize: 'var(--text-h4)', lineHeight: 'var(--leading-h4)', fontWeight: 600, color: 'var(--text-primary)', textDecoration: 'none' }}>
            <span style={{ color: 'var(--text-tertiary)', fontWeight: 500, marginRight: 8 }}>{item.rank}.</span>{orgName(c)}
          </a>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 16px', marginTop: 4, fontSize: 13, color: 'var(--text-secondary)' }}>
            <span>ИНН <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{item.inn}</span></span>
            {c.place ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Icon name="map-pin" size={14} />{c.place}</span> : c.region ? <span>Регион {c.region}</span> : null}
            {c.okved_main ? <span>ОКВЭД <span style={{ fontFamily: 'var(--font-mono)' }}>{c.okved_main}</span></span> : null}
          </div>
          {c.status_reason ? <div style={{ marginTop: 6, fontSize: 13, color: 'var(--text-tertiary)' }}>Статус: {c.status_reason}</div> : null}
        </div>
        <MatchScore value={item.rel} size={60} unit="" title={'Балл ' + item.rel + ' из 100 — относительно первого места'} />
      </div>
      {item.reasons.length ? (
        <div style={{ margin: '0 20px', padding: '10px 12px', borderRadius: 'var(--radius-md)', background: 'var(--match-bg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: 'var(--match-fg)', marginBottom: 4 }}><Icon name="sparkles" size={14} />Почему подходит</div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: '20px', color: 'var(--text-primary)' }}>{item.reasons.slice(0, 3).map((r, i) => <li key={i}>{r}</li>)}</ul>
        </div>
      ) : null}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 16, padding: '16px 20px', marginTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', gap: '12px 28px', flex: '1 1 320px', minWidth: 0, flexWrap: 'wrap' }}>
          {c.in_history ? <Stat label="Участий" value={num(c.bids)} /> : null}
          {c.in_history ? <Stat label="Побед" value={num(c.wins)} /> : null}
          {c.in_history && c.last_bid ? <Stat label="Последняя заявка" value={date(c.last_bid)} /> : null}
          {c.revenue ? <Stat label="Выручка за 2025 год" value={money(c.revenue)} /> : null}
          {c.headcount ? <Stat label="Работников" value={num(c.headcount)} /> : null}
          {!c.in_history && c.msp_since ? <Stat label="В реестре МСП" value={'с ' + c.msp_since.slice(0, 4) + ' года'} /> : null}
        </div>
        <div style={{ display: 'flex', gap: 8, flex: 'none' }}>
          <Button variant={inCompare ? 'secondary' : 'outline'} iconLeft={inCompare ? 'check' : 'git-compare'} onClick={onCompare}>{inCompare ? 'В сравнении' : 'Сравнить'}</Button>
          <Button iconRight="chevron-right" onClick={onOpen}>Подробнее</Button>
        </div>
      </div>
    </article>
  );
}
