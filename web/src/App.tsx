import React from 'react';
import { AppHeader } from './ds';
import { SearchScreen } from './screens/SearchScreen';
import { SupplierProfile } from './screens/SupplierProfile';
import { CompareScreen } from './screens/CompareScreen';
import { AboutScreen } from './screens/AboutScreen';
import { api, errorText, relScore, useNarrow } from './lib';
import type { Actual, Item, Lists, LotBrief, NewPurchase, RankedItem, Recommendation, Stats } from './types';

type Screen = 'search' | 'supplier' | 'compare' | 'about';
type NavId = 'search' | 'about';

const hashLot = () => { const m = /lot=(\d+)/.exec(location.hash); return m ? m[1] : null; };
// На телефоне первый раздел называется короче, чтобы оба помещались в шапку без прокрутки.
const nav = (narrow: boolean): { id: NavId; label: string }[] => [{ id: 'search', label: narrow ? 'Подбор' : 'Подбор поставщиков' }, { id: 'about', label: 'Качество и источники' }];
const ranked = (items: Item[], isNew: boolean): RankedItem[] => items.map((it, i) => ({ ...it, rank: i + 1, rel: relScore(it, items), isNew }));

export function App() {
  const [screen, setScreen] = React.useState<Screen>('search');
  const [examples, setExamples] = React.useState<LotBrief[]>([]);
  const [stats, setStats] = React.useState<Stats | null>(null);
  const [data, setData] = React.useState<Recommendation | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [supplierInn, setSupplierInn] = React.useState<string | null>(null);
  const [compare, setCompare] = React.useState<string[]>([]);
  const [headerQuery, setHeaderQuery] = React.useState<{ text: string } | null>(null);
  const req = React.useRef(0);
  const narrow = useNarrow();

  const run = async (promise: Promise<Recommendation>) => {
    const id = ++req.current;
    setScreen('search'); setLoading(true); setError(null); setCompare([]);
    try { const d = await promise; if (id === req.current) setData(d); }
    catch (e) { if (id === req.current) { setData(null); setError(errorText(e)); } }
    if (id === req.current) setLoading(false);
  };
  const fetchLot = (id: number | string) => run(api<Recommendation>('/api/lot/' + id));
  // Ссылка вида /#lot=6008824 сразу открывает закупку; «назад» в браузере возвращает к прежней.
  const loadLot = (id: number | string) => { if (hashLot() === String(id)) fetchLot(id); else location.hash = 'lot=' + id; };
  const recommend = (body: NewPurchase) => {
    history.replaceState(null, '', location.pathname);
    run(api<Recommendation>('/api/recommend', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }));
  };

  React.useEffect(() => {
    api<LotBrief[]>('/api/examples').then(setExamples).catch(() => {});
    api<Stats>('/api/stats').then(setStats).catch(() => {});
    const onHash = () => { const id = hashLot(); if (id) fetchLot(id); };
    window.addEventListener('hashchange', onHash);
    onHash();
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  React.useEffect(() => { window.scrollTo(0, 0); }, [screen, supplierInn]);

  const lists = React.useMemo<Lists | null>(() => data && { known: ranked(data.items, false), new: ranked(data.new_items, true) }, [data]);
  const actual = React.useMemo<Actual>(() => Object.fromEntries((data ? data.lot.participants : []).map((p) => [p.inn, p.won])), [data]);
  const byInn = (inn: string | null) => (lists && inn ? lists.known.find((x) => x.inn === inn) || lists.new.find((x) => x.inn === inn) : undefined);

  const toggleCompare = (inn: string) => setCompare(compare.includes(inn) ? compare.filter((x) => x !== inn) : compare.concat(inn));
  const openSupplier = (inn: string) => { setSupplierInn(inn); setScreen('supplier'); };
  const back = () => setScreen('search');

  return (
    <div style={{ minHeight: '100vh', background: 'var(--surface-page)' }}>
      <AppHeader<NavId> product="Подбор поставщиков" note="АИС ГЗ и электронный магазин" active={screen === 'about' ? 'about' : 'search'} onNav={setScreen} nav={nav(narrow)}
        compareCount={compare.length} onCompare={() => setScreen('compare')} quickSearchPlaceholder="Номер лота или предмет"
        onQuickSearch={(text) => { setScreen('search'); setHeaderQuery({ text }); }} />
      {/* Экран подбора не размонтируется: при возврате из карточки сохраняются фильтры, вкладка и запрос. */}
      <div hidden={screen !== 'search'}>
        <SearchScreen examples={examples} data={data} lists={lists} actual={actual} loading={loading} error={error} headerQuery={headerQuery}
          onLot={loadLot} onRecommend={recommend} compare={compare} setCompare={setCompare} toggleCompare={toggleCompare} openSupplier={openSupplier} />
      </div>
      {screen === 'supplier' ? <SupplierProfile item={byInn(supplierInn)} lot={data ? data.lot : null} mark={supplierInn ? actual[supplierInn] : undefined} back={back} inCompare={!!supplierInn && compare.includes(supplierInn)} toggleCompare={toggleCompare} onLot={loadLot} /> : null}
      {screen === 'compare' ? <CompareScreen items={compare.map(byInn).filter((x): x is RankedItem => !!x)} actual={actual} toggleCompare={toggleCompare} clearCompare={() => setCompare([])} openSupplier={openSupplier} back={back} /> : null}
      {screen === 'about' ? <AboutScreen stats={stats} /> : null}
    </div>
  );
}
