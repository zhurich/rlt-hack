import React from 'react';
import { Icon, Button, Input, Select, Checkbox, Switch, Alert, Badge, Tag, Card, MatchScore, Requisites, EmptyState, DataTable, Tabs, FilterGroup, Tooltip } from '../ds';
import type { BadgeProps, DataTableColumn, RequisiteItem } from '../ds';
import { SupplierCard } from '../components/SupplierCard';
import { StatusChip, ActualChip } from '../components/chips';
import { api, errorText, useNarrow, num, rub, money, date, cap, orgName, ROLES, STATUSES } from '../lib';
import type { Actual, Lists, LotBrief, NewPurchase, Participant, RankedItem, Recommendation, Role, Status } from '../types';

type Mode = 'lot' | 'new';
type ListTab = keyof Lists;
type View = 'list' | 'table';
interface Filters { role: Role[]; status: Status[]; msp: boolean }
type Applied = { key: 'role'; value: Role } | { key: 'status'; value: Status } | { key: 'msp' };

const NO_FILTERS: Filters = { role: [], status: [], msp: false };
const HINTS: Record<ListTab, string> = {
  known: 'Поставщики из истории закупок. Балл — относительно первого места.',
  new: 'Компании Санкт-Петербурга и Ленобласти из открытых реестров, которые в этих закупках ещё не участвовали.',
};
const toggled = <T,>(arr: T[], v: T) => (arr.includes(v) ? arr.filter((x) => x !== v) : arr.concat(v));

interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder: string;
  button: string;
  busy?: boolean;
  examples?: LotBrief[];
  onExample?: (ex: LotBrief) => void;
}

// Строка поиска — по образцу SmartSearch из дизайн-системы, без переключателя «ИИ-подбор»:
// подбор работает на локальных индексах, нейросети в нём нет.
function SearchBar({ value, onChange, onSubmit, placeholder, button, busy, examples, onExample }: SearchBarProps) {
  const [focus, setFocus] = React.useState(false);
  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }} style={{ display: 'flex', alignItems: 'center', gap: 8, height: 56, padding: '0 6px 0 16px', background: 'var(--surface-card)',
        border: '1px solid ' + (focus ? 'var(--border-focus)' : 'var(--border-strong)'), borderRadius: 'var(--radius-md)', boxShadow: focus ? 'var(--focus-ring)' : 'var(--shadow-1)' }}>
        <Icon name="search" size={20} color="var(--text-tertiary)" />
        <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} onFocus={() => setFocus(true)} onBlur={() => setFocus(false)} autoComplete="off"
          style={{ flex: 1, minWidth: 0, height: '100%', border: 0, outline: 'none', background: 'transparent', fontFamily: 'var(--font-sans)', fontSize: 16, color: 'var(--text-primary)' }} />
        <Button type="submit" loading={busy}>{button}</Button>
      </form>
      {([['Тестовый набор:', (examples || []).filter((ex) => ex.test)], ['Из истории:', (examples || []).filter((ex) => !ex.test)]] as const).map(([label, group]) => group.length ? (
        <div key={label} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px 14px', marginTop: 10 }}>
          <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{label}</span>
          {group.map((ex) => (
            <button key={ex.lot_id} type="button" title={ex.subject} onClick={() => onExample && onExample(ex)}
              style={{ border: 0, background: 'none', padding: 0, cursor: 'pointer', fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--text-link)', textDecoration: 'underline', textDecorationStyle: 'dotted', textUnderlineOffset: 3,
                maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ex.subject}</button>
          ))}
        </div>
      ) : null)}
    </div>
  );
}

const Code = ({ children }: { children: React.ReactNode }) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, padding: '2px 6px', borderRadius: 'var(--radius-xs)', background: 'var(--surface-sunken)', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{children}</span>;

function LotCard({ data }: { data: Recommendation }) {
  const l = data.lot;
  const items: RequisiteItem[] = [];
  if (l.publish_date) items.push({ label: 'Дата', value: date(l.publish_date) });
  items.push({ label: 'Площадка', value: (l.source || 'не указана') + (l.is_smp ? ' · для СМП' : '') });
  items.push({ label: 'Цена', value: rub(l.price) });
  if (l.customer_inn) items.push({ label: 'Заказчик', value: l.customer_inn, mono: true, copyable: true });
  return (
    <Card title={'Закупка' + (l.lot_id ? ' № ' + l.lot_id : '')} padding={20}>
      <div style={{ fontSize: 15, lineHeight: '22px', fontWeight: 600, marginBottom: 12, textWrap: 'pretty' }}>{l.subject || 'Предмет не указан'}</div>
      <Requisites labelWidth={84} items={items} />
      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text-tertiary)' }}>ОКПД2{data.codes_inferred ? ' — определены по похожим закупкам' : ''}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
        {data.codes.length ? data.codes.map((c) => <Code key={c.code}>{c.code} · {Math.round(c.share * 100)}&nbsp;%</Code>) : '—'}
      </div>
      {l.positions.length ? (
        <ul style={{ listStyle: 'none', margin: '14px 0 0', padding: 0, maxHeight: 168, overflowY: 'auto', fontSize: 13, lineHeight: '18px' }}>
          {l.positions.map((p, i) => (
            <li key={i} style={{ display: 'flex', gap: 8, justifyContent: 'space-between', padding: '6px 0', borderTop: '1px solid var(--border-subtle)' }}>
              <span style={{ minWidth: 0 }}>{p.name}{p.n > 1 ? ' ×' + p.n : ''}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>{p.code}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

function ActualCard({ participants }: { participants: Participant[] }) {
  return (
    <Card title="Кто участвовал на самом деле" padding={20}>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 8 }}>
        {participants.map((p) => {
          const tone: BadgeProps['tone'] = p.place == null ? 'neutral' : p.place <= 10 ? 'success' : p.place <= 50 ? 'warning' : 'neutral';
          return (
            <li key={p.inn} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 13, lineHeight: '20px' }}>
              <Badge size="sm" tone={tone} style={{ minWidth: 48, justifyContent: 'center' }}>{p.place == null ? '—' : '№ ' + p.place}</Badge>
              <span style={{ minWidth: 0 }}>{p.name ? orgName(p) : 'ИНН ' + p.inn}{p.won ? <Icon name="trophy" size={14} color="var(--green-500)" title="Победитель" style={{ marginLeft: 6, verticalAlign: '-2px' }} /> : null}</span>
            </li>
          );
        })}
      </ul>
      <div style={{ marginTop: 12, fontSize: 12, lineHeight: '16px', color: 'var(--text-tertiary)' }}>Место в нашей выдаче. Подбор видит только историю до даты этой закупки — участники самого лота ему неизвестны.</div>
    </Card>
  );
}

function FiltersPanel({ items, f, setF }: { items: RankedItem[]; f: Filters; setF: (f: Filters) => void }) {
  const roleCount = (v: Role) => items.filter((it) => it.company.role === v).length;
  const statusCount = (v: Status) => items.filter((it) => it.company.status === v).length;
  return (
    <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)', padding: '4px 20px 4px' }}>
      <FilterGroup title="Роль" selectedCount={f.role.length} onReset={() => setF({ ...f, role: [] })}>
        {ROLES.filter((v) => roleCount(v) || f.role.includes(v)).map((v) => <Checkbox key={v} label={cap(v)} count={roleCount(v)} checked={f.role.includes(v)} onChange={() => setF({ ...f, role: toggled(f.role, v) })} />)}
      </FilterGroup>
      <FilterGroup title="Статус" selectedCount={f.status.length} onReset={() => setF({ ...f, status: [] })}>
        {STATUSES.filter((v) => statusCount(v) || f.status.includes(v)).map((v) => <Checkbox key={v} label={cap(v)} count={statusCount(v)} checked={f.status.includes(v)} onChange={() => setF({ ...f, status: toggled(f.status, v) })} />)}
      </FilterGroup>
      <FilterGroup title="Размер бизнеса" style={{ borderBottom: 0 }}>
        <Switch label="Только субъекты МСП" checked={f.msp} onChange={(v) => setF({ ...f, msp: v })} />
      </FilterGroup>
    </div>
  );
}

const FOUND_COLUMNS: DataTableColumn<LotBrief>[] = [
  { key: 'lot_id', title: '№ лота', mono: true, nowrap: true },
  { key: 'subject', title: 'Предмет закупки' },
  { key: 'publish_date', title: 'Дата', nowrap: true, render: (r) => date(r.publish_date) },
  { key: 'source', title: 'Площадка', nowrap: true },
  { key: 'price', title: 'Цена', align: 'right', nowrap: true, render: (r) => money(r.price) },
  { key: 'participants', title: 'Участников', align: 'right' },
];
// На телефоне в таблицах остаются только главные колонки — остальное есть в карточке.
const FOUND_NARROW = ['lot_id', 'subject', 'publish_date'];
const RANKED_NARROW = ['rank', 'name', 'rel'];

export interface SearchScreenProps {
  examples: LotBrief[];
  data: Recommendation | null;
  lists: Lists | null;
  actual: Actual;
  loading: boolean;
  error: string | null;
  /** Запрос из быстрого поиска в шапке; новый объект — новый поиск */
  headerQuery: { text: string } | null;
  onLot: (id: number | string) => void;
  onRecommend: (body: NewPurchase) => void;
  compare: string[];
  setCompare: (inns: string[]) => void;
  toggleCompare: (inn: string) => void;
  openSupplier: (inn: string) => void;
}

export function SearchScreen({ examples, data, lists, actual, loading, error, headerQuery, onLot, onRecommend, compare, setCompare, toggleCompare, openSupplier }: SearchScreenProps) {
  const [mode, setMode] = React.useState<Mode>('lot');
  const [q, setQ] = React.useState('');
  const [found, setFound] = React.useState<LotBrief[] | null>(null);
  const [searching, setSearching] = React.useState(false);
  const [searchErr, setSearchErr] = React.useState<string | null>(null);
  const [nw, setNw] = React.useState({ text: '', codes: '', price: '', source: '', is_smp: false });
  const [tab, setTab] = React.useState<ListTab>('known');
  const [view, setView] = React.useState<View>('list');
  const [f, setF] = React.useState<Filters>(NO_FILTERS);
  const narrow = useNarrow();

  React.useEffect(() => {
    setTab('known'); setF(NO_FILTERS); setFound(null);
    if (data && data.lot.lot_id) { setMode('lot'); setQ(String(data.lot.lot_id)); }
  }, [data]);
  React.useEffect(() => { if (loading) setFound(null); }, [loading]);

  const searchText = async (text: string) => {
    setSearching(true); setSearchErr(null);
    try { setFound(await api<LotBrief[]>('/api/search?q=' + encodeURIComponent(text))); }
    catch (e) { setFound(null); setSearchErr(errorText(e)); }
    setSearching(false);
  };
  const submitLot = (text = q) => {
    const t = text.trim();
    if (!t) return;
    if (/^\d+$/.test(t)) onLot(t); else searchText(t);
  };
  // Быстрый поиск из шапки.
  React.useEffect(() => { if (headerQuery) { setMode('lot'); setQ(headerQuery.text); submitLot(headerQuery.text); } }, [headerQuery]);

  const submitNew = () => {
    if (!nw.text.trim() && !nw.codes.trim()) { setSearchErr('Укажите предмет закупки или коды ОКПД2.'); return; }
    setSearchErr(null);
    onRecommend({ text: nw.text, codes: nw.codes.split(/[,;\s]+/).filter(Boolean), price: parseFloat(nw.price.replace(/\s/g, '').replace(',', '.')) || null, source: nw.source || null, is_smp: nw.is_smp });
  };

  const all = lists ? lists[tab] : [];
  const list = all.filter((it) => (!f.role.length || (it.company.role != null && f.role.includes(it.company.role)))
    && (!f.status.length || (it.company.status != null && f.status.includes(it.company.status)))
    && (!f.msp || !!it.company.msp_category));
  const applied: Applied[] = [...f.role.map((value): Applied => ({ key: 'role', value })), ...f.status.map((value): Applied => ({ key: 'status', value })), ...(f.msp ? [{ key: 'msp' } as const] : [])];
  const drop = (a: Applied) => setF(a.key === 'role' ? { ...f, role: f.role.filter((x) => x !== a.value) } : a.key === 'status' ? { ...f, status: f.status.filter((x) => x !== a.value) } : { ...f, msp: false });

  const allColumns: DataTableColumn<RankedItem>[] = [
    { key: 'rank', title: '№', align: 'right', width: narrow ? 28 : 44 },
    { key: 'name', title: 'Организация', render: (r) => <div><div style={{ fontWeight: 600 }}>{orgName(r.company)}</div><div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{[r.company.role ? cap(r.company.role) : null, r.company.place].filter(Boolean).join(' · ')}</div>{actual[r.inn] != null ? <div style={{ marginTop: 4 }}><ActualChip mark={actual[r.inn]} size="sm" /></div> : null}</div> },
    { key: 'inn', title: 'ИНН', mono: true, nowrap: true },
    { key: 'status', title: 'Статус', render: (r) => <StatusChip company={r.company} size="sm" /> },
    ...(tab === 'known'
      ? [{ key: 'bids', title: 'Участий', align: 'right', render: (r) => num(r.company.bids) }, { key: 'wins', title: 'Побед', align: 'right', render: (r) => num(r.company.wins) }] satisfies DataTableColumn<RankedItem>[]
      : [{ key: 'revenue', title: 'Выручка', align: 'right', nowrap: true, render: (r) => money(r.company.revenue) }, { key: 'headcount', title: 'Работников', align: 'right', render: (r) => num(r.company.headcount) }] satisfies DataTableColumn<RankedItem>[]),
    { key: 'rel', title: 'Балл', align: 'right', render: (r) => <MatchScore value={r.rel} variant="inline" unit="" /> },
  ];
  const columns = narrow ? allColumns.filter((c) => RANKED_NARROW.includes(c.key)) : allColumns;
  const foundColumns = narrow ? FOUND_COLUMNS.filter((c) => FOUND_NARROW.includes(c.key)) : FOUND_COLUMNS;

  return (
    <div>
      <div style={{ background: 'var(--surface-card)', borderBottom: '1px solid var(--border-default)' }}>
        <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: '24px var(--gutter) 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 16, marginBottom: 16 }}>
            <h1 style={{ margin: 0, flex: 1, fontSize: 'var(--text-h2)', lineHeight: 'var(--leading-h2)', fontWeight: 700 }}>Подбор поставщиков</h1>
            <Tabs<Mode> variant="segmented" value={mode} onChange={(m) => { setMode(m); setFound(null); setSearchErr(null); }} items={[{ id: 'lot', label: 'Закупка из истории' }, { id: 'new', label: 'Новая закупка' }]} />
          </div>
          {mode === 'lot' ? (
            <SearchBar value={q} onChange={setQ} onSubmit={() => submitLot()} button="Найти" busy={searching} placeholder="Номер лота или слова из предмета закупки"
              examples={examples} onExample={(ex) => onLot(ex.lot_id)} />
          ) : (
            <div>
              <SearchBar value={nw.text} onChange={(v) => setNw({ ...nw, text: v })} onSubmit={submitNew} button="Подобрать" placeholder="Предмет закупки, например: поставка бумаги для офисной техники А4" />
              <div className="app-form-row" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: 12, marginTop: 12 }}>
                <Input label="ОКПД2" mono placeholder="17.12.14.110, 17.23" hint="Необязательно, через запятую" value={nw.codes} onChange={(e) => setNw({ ...nw, codes: e.target.value })} style={{ flex: '1 1 240px' }} />
                <Input label="Начальная цена" placeholder="300 000" suffix="₽" inputMode="decimal" hint="Необязательно" value={nw.price} onChange={(e) => setNw({ ...nw, price: e.target.value })} style={{ flex: '0 1 180px' }} />
                <Select label="Площадка" placeholder="Не указана" hint="Необязательно" options={['ЭМ', 'АИС ГЗ']} value={nw.source} onChange={(e) => setNw({ ...nw, source: e.target.value })} style={{ flex: '0 1 180px' }} />
                <Checkbox label="Закупка для СМП" checked={nw.is_smp} onChange={(v) => setNw({ ...nw, is_smp: v })} style={{ paddingBottom: 30 }} />
              </div>
            </div>
          )}
          {searchErr ? <Alert tone="danger" style={{ marginTop: 12 }} onClose={() => setSearchErr(null)}>{searchErr}</Alert> : null}
          {found ? (found.length
            ? <DataTable density="compact" style={{ marginTop: 12 }} rowKey="lot_id" rows={found} onRowClick={(r) => onLot(r.lot_id)} columns={foundColumns} />
            : <Alert tone="info" style={{ marginTop: 12 }}>Закупки не найдены. Опишите предмет другими словами или введите номер лота.</Alert>) : null}
        </div>
      </div>

      <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: '24px var(--gutter) 48px' }}>
        {loading ? (
          <Card padding={0}><div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 56, color: 'var(--text-secondary)' }}><Icon name="loader-circle" size={20} style={{ animation: 'neva-spin 0.8s linear infinite' }} />Подбираем поставщиков</div></Card>
        ) : error ? (
          <Alert tone="danger" title="Не удалось выполнить подбор">{error}</Alert>
        ) : !data || !lists ? (
          <Card padding={0}><EmptyState icon="search" title="Закупка не выбрана">Выберите пример, найдите закупку по номеру или словам либо опишите новую.</EmptyState></Card>
        ) : (
          <div className="neva-split">
            <aside style={{ position: 'sticky', top: 'calc(var(--header-main-h) + 16px)', maxHeight: 'calc(100vh - var(--header-main-h) - 32px)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
              <LotCard data={data} />
              {data.lot.participants.length ? <ActualCard participants={data.lot.participants} /> : null}
              <FiltersPanel items={all} f={f} setF={setF} />
            </aside>
            <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="app-tabs-row" style={{ display: 'flex', alignItems: 'flex-end', gap: narrow ? 4 : 16, flexWrap: 'wrap', borderBottom: '1px solid var(--border-default)' }}>
                <Tabs<ListTab> style={{ flex: 1, borderBottom: 0 }} value={tab} onChange={setTab} items={[{ id: 'known', label: narrow ? 'Рекомендуемые' : 'Рекомендуемые поставщики', count: lists.known.length }, { id: 'new', label: narrow ? 'Новые компании' : 'Новые компании из реестров', count: lists.new.length }]} />
                <Tabs<View> variant="segmented" style={{ marginBottom: 6 }} value={view} onChange={setView} items={[{ id: 'list', label: 'Карточки' }, { id: 'table', label: 'Таблица' }]} />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 0, fontSize: 13, color: 'var(--text-secondary)' }}>{applied.length ? 'Показано ' + list.length + ' из ' + all.length + '. ' : ''}{HINTS[tab]}</div>
                <Tooltip content="Подбор считается на локальных индексах, без внешних сервисов"><span style={{ fontSize: 12, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>Ответ за {num(data.elapsed_ms)}&nbsp;мс</span></Tooltip>
              </div>
              {applied.length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
                  {applied.map((a) => <Tag key={a.key + (a.key === 'msp' ? '' : a.value)} size="sm" onRemove={() => drop(a)}>{a.key === 'msp' ? 'МСП' : cap(a.value)}</Tag>)}
                  <a href="#" onClick={(e) => { e.preventDefault(); setF(NO_FILTERS); }} style={{ fontSize: 13 }}>Сбросить все</a>
                </div>
              ) : null}
              {data.codes_inferred ? <Alert tone="match" title="Коды ОКПД2 определены по похожим закупкам">{data.codes.map((c) => c.code).join(', ')} — по предметам закупок из истории, наиболее близких к описанию.</Alert> : null}
              {list.length === 0 ? (
                <Card padding={0}>{all.length
                  ? <EmptyState title="Под фильтры никто не подошёл" action={<Button variant="outline" onClick={() => setF(NO_FILTERS)}>Сбросить фильтры</Button>}>Уберите часть фильтров.</EmptyState>
                  : <EmptyState title="Подходящих компаний не нашлось">Опишите предмет закупки другими словами или уточните коды ОКПД2.</EmptyState>}</Card>
              ) : view === 'list' ? (
                list.map((it) => <SupplierCard key={it.inn} item={it} mark={actual[it.inn]} inCompare={compare.includes(it.inn)} onOpen={() => openSupplier(it.inn)} onCompare={() => toggleCompare(it.inn)} />)
              ) : (
                <DataTable<RankedItem, string> density={narrow ? 'compact' : 'regular'} selectable={!narrow} selected={compare} onSelect={setCompare} rowKey="inn" rows={list} onRowClick={(r) => openSupplier(r.inn)} columns={columns} />
              )}
            </main>
          </div>
        )}
      </div>
    </div>
  );
}
