import type { ReactNode } from 'react';
import { Icon, Button, Badge, Card, MatchScore, Requisites, EmptyState, DataTable, Breadcrumbs } from '../ds';
import type { DataTableColumn } from '../ds';
import { StatusChip, RoleChip, MspChip, ActualChip } from '../components/chips';
import { num, money, date, pct, cap, orgName, MSP, hasDebt, inRnp, winRate } from '../lib';
import type { Lot, RankedItem, SimilarLot } from '../types';

function Check({ ok, warn, children }: { ok: boolean; warn?: boolean; children: ReactNode }) {
  const [icon, color] = ok ? ['circle-check', 'var(--green-500)'] : warn ? ['triangle-alert', 'var(--amber-500)'] : ['circle-alert', 'var(--red-500)'];
  return <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}><Icon name={icon} size={16} color={color} style={{ marginTop: 2 }} /><span>{children}</span></div>;
}

const SIMILAR_COLUMNS: DataTableColumn<SimilarLot>[] = [
  { key: 'lot_id', title: '№ лота', mono: true, nowrap: true },
  { key: 'subject', title: 'Предмет закупки' },
  { key: 'won', title: 'Результат', nowrap: true, render: (r) => <Badge size="sm" tone={r.won ? 'success' : 'neutral'}>{r.won ? 'Победил' : 'Участвовал'}</Badge> },
  { key: 'sim', title: 'Близость', align: 'right', render: (r) => <MatchScore value={r.sim * 100} variant="inline" /> },
];

export interface SupplierProfileProps {
  item: RankedItem | undefined;
  lot: Lot | null;
  /** true — победил в этой закупке, false — участвовал, undefined — не участвовал */
  mark: boolean | undefined;
  back: () => void;
  inCompare: boolean;
  toggleCompare: (inn: string) => void;
  onLot: (id: number) => void;
}

export function SupplierProfile({ item, lot, mark, back, inCompare, toggleCompare, onLot }: SupplierProfileProps) {
  if (!item || !lot) return (
    <div style={{ maxWidth: 'var(--container-max)', margin: '24px auto', padding: '0 var(--gutter)' }}>
      <Card padding={0}><EmptyState title="Компания не выбрана" action={<Button variant="outline" onClick={back}>Перейти к подбору</Button>}>Откройте карточку из результатов подбора.</EmptyState></Card>
    </div>
  );
  const c = item.company, name = orgName(c);
  const rel = item.factors.relevance, boosts = item.factors.boosts;
  const sources = c.sources ?? [], licenses = c.licenses ?? [], similar = item.similar_lots ?? [];
  const inRegistries = sources.some((s) => !s.startsWith('История закупок'));
  const rate = winRate(c);
  const tiles: [string, string][] = [['Участий', num(c.bids)], ['Побед', num(c.wins)], ['Доля побед', rate == null ? '—' : pct(rate)], ['Последняя заявка', date(c.last_bid)]];
  if (item.typical_price) tiles.push(['Типичная цена', money(item.typical_price)]);
  return (
    <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: '20px var(--gutter) 48px' }}>
      <Breadcrumbs items={[{ label: 'Подбор поставщиков' }, { label: lot.lot_id ? 'Закупка № ' + lot.lot_id : 'Новая закупка' }, { label: name }]} onNavigate={back} />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'flex-start', marginTop: 16 }}>
        <div style={{ flex: '1 1 480px', minWidth: 0 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
            <RoleChip company={c} /><StatusChip company={c} /><MspChip company={c} />
            {inRnp(c) ? <Badge tone="danger" variant="solid">РНП</Badge> : null}
            <ActualChip mark={mark} />
          </div>
          <h1 style={{ margin: 0, fontSize: 'var(--text-h1)', lineHeight: 'var(--leading-h1)', fontWeight: 700, letterSpacing: 'var(--tracking-tight)', textWrap: 'pretty' }}>{name}</h1>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 20px', marginTop: 6, fontSize: 14, color: 'var(--text-secondary)' }}>
            <span>ИНН <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{item.inn}</span></span>
            {c.place ? <span>{c.place}</span> : null}
            <span>{item.isNew ? 'Новая компания, место в списке — ' : 'Место в подборе — '}{item.rank}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flex: 'none' }}>
          <Button variant={inCompare ? 'secondary' : 'outline'} iconLeft={inCompare ? 'check' : 'git-compare'} onClick={() => toggleCompare(item.inn)}>{inCompare ? 'В сравнении' : 'Сравнить'}</Button>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, marginTop: 24, alignItems: 'flex-start' }}>
        <div style={{ flex: '1 1 520px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Сведения о компании" subtitle="Из открытых реестров, собраны заранее">
            <Requisites columns={2} labelWidth={130} items={[
              { label: 'ИНН', value: item.inn, mono: true, copyable: true },
              { label: 'Вид', value: c.kind === 'ИП' ? 'Индивидуальный предприниматель' : c.kind === 'ЮЛ' ? 'Юридическое лицо' : c.kind || '—' },
              { label: 'Регион', value: c.place || (c.region ? 'код ' + c.region : '—') },
              { label: 'Основной ОКВЭД', value: c.okved_main ? c.okved_main + ' — ' + c.okved_main_name : 'не найден' },
              { label: 'Реестр МСП', value: c.msp_category ? MSP[c.msp_category] + (c.msp_since ? ', с ' + date(c.msp_since) : '') : 'нет в реестре' },
              { label: 'Работников', value: c.headcount ? num(c.headcount) : '—' },
              { label: 'Выручка за 2025', value: c.revenue ? money(c.revenue) : '—' },
              { label: 'Долг по налогам', value: hasDebt(c) ? money(c.tax_debt) : 'не числится' },
            ]} />
            {licenses.length ? (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 6 }}>Лицензии</div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: '20px' }}>{licenses.map((x) => <li key={x}>{x}</li>)}</ul>
              </div>
            ) : null}
          </Card>

          {c.in_history ? (
            <Card title="Показатели в закупках" subtitle="АИС ГЗ и электронный магазин Санкт-Петербурга, 2024–2025">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16 }}>
                {tiles.map(([l, v]) => (
                  <div key={l} style={{ padding: 16, background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)' }}><div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{l}</div><div style={{ fontSize: 'var(--text-h3)', lineHeight: 'var(--leading-h3)', fontWeight: 700, marginTop: 4, whiteSpace: 'nowrap' }}>{v}</div></div>
                ))}
              </div>
            </Card>
          ) : null}

          {similar.length ? (
            <Card title="Похожие закупки с его участием" subtitle="Строка открывает подбор по этой закупке">
              <DataTable density="dense" rowKey="lot_id" rows={similar} onRowClick={(r) => onLot(r.lot_id)} columns={SIMILAR_COLUMNS} />
            </Card>
          ) : null}
        </div>

        <div style={{ flex: '1 1 320px', maxWidth: 400, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Соответствие закупке" padding={20}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <MatchScore value={item.rel} size={72} unit="" title="Балл относительно первого места" />
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', minWidth: 0 }}><div style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>Балл из 100, относительно первого места</div>«{lot.subject}»</div>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: '16px 0 8px' }}>Из чего складывается релевантность</div>
            <div style={{ display: 'grid', gap: 10 }}>
              {rel.map((x) => <MatchScore key={x.label} variant="bar" value={x.share} label={x.label} />)}
            </div>
            {boosts.length ? (
              <div style={{ marginTop: 14 }}>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 6 }}>Надбавки к релевантности</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>{boosts.map((b) => <Badge key={b.label} tone="match">{b.label} +{b.pct}&nbsp;%</Badge>)}</div>
              </div>
            ) : null}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: 'var(--match-fg)', margin: '16px 0 4px' }}><Icon name="sparkles" size={14} />Почему подходит</div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: '20px' }}>{item.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          </Card>

          <Card title="Статус и достоверность" padding={20}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}><StatusChip company={c} /></div>
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-secondary)' }}>{cap(c.status_reason || '')}</div>
            <div style={{ display: 'grid', gap: 8, marginTop: 12, fontSize: 13 }}>
              <Check ok={!inRnp(c)}>{inRnp(c) ? 'Есть в реестре недобросовестных поставщиков: записей — ' + c.rnp_records : 'Нет в реестре недобросовестных поставщиков'}</Check>
              <Check ok={!hasDebt(c)} warn>{hasDebt(c) ? 'Задолженность по налогам — ' + money(c.tax_debt) : 'Долг по налогам не числится (ФНС)'}</Check>
              <Check ok={inRegistries} warn>{inRegistries ? 'Найдена в открытых реестрах ФНС' : 'Не найдена в реестре МСП и отчётности ФНС'}</Check>
            </div>
          </Card>

          <Card title="Роль" padding={20}>
            <RoleChip company={c} />
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-secondary)' }}>{cap(c.role_reason || '')}</div>
            {c.role_source ? <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-tertiary)' }}>Источник: {c.role_source}</div> : null}
          </Card>

          <Card title="Источники" padding={20}>
            <div style={{ display: 'grid', gap: 8, fontSize: 13 }}>
              {sources.map((s) => <div key={s} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}><Icon name="database" size={16} color="var(--text-tertiary)" style={{ marginTop: 2 }} />{s}</div>)}
              {!sources.length ? '—' : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
