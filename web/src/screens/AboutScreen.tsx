import type { CSSProperties } from 'react';
import { Icon, Card, MatchScore, Alert } from '../ds';
import { num, pct } from '../lib';
import type { Stats } from '../types';

const Tile = ({ label, value, note }: { label: string; value: string; note?: string }) => (
  <div style={{ padding: 16, background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)' }}>
    <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{label}</div>
    <div style={{ fontSize: 'var(--text-h2)', lineHeight: 'var(--leading-h2)', fontWeight: 700, marginTop: 4 }}>{value}</div>
    {note ? <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{note}</div> : null}
  </div>
);
const grid: CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 };

export function AboutScreen({ stats }: { stats: Stats | null }) {
  const s = stats;
  return (
    <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: '24px var(--gutter) 48px' }}>
      <h1 style={{ margin: '0 0 20px', fontSize: 'var(--text-h1)', lineHeight: 'var(--leading-h1)', fontWeight: 700 }}>Качество и источники</h1>
      {!s ? <Card>Загрузка</Card> : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'flex-start' }}>
          <div style={{ flex: '1 1 520px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Качество подбора" subtitle={'Проверка на ' + num(s.test_lots) + ' отложенных закупках ноября–декабря 2025 года: участники этих закупок от подбора скрыты'}>
              <div style={grid}>
                <Tile label="Реальных участников в первой десятке" value={pct(s.recall10)} note="Recall@10" />
                <Tile label="Победителей в первой десятке" value={pct(s.winner10)} />
                <Tile label="Точность порядка" value={s.map10.toFixed(3).replace('.', ',')} note="MAP@10" />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: '20px 0 8px' }}>Доля реальных участников в первой десятке — в сравнении с простыми способами</div>
              <div style={{ display: 'grid', gap: 12 }}>
                <MatchScore variant="bar" value={s.recall10 * 100} label="Подбор сервиса" />
                <MatchScore variant="bar" value={s.baseline_okpd * 100} label="Только по полному коду ОКПД2" />
                <MatchScore variant="bar" value={s.baseline_popular * 100} label="Десять самых активных поставщиков" />
              </div>
            </Card>
            <Card title="База">
              <div style={grid}>
                <Tile label="Закупок в истории" value={num(s.lots)} note="2024–2025 годы" />
                <Tile label="Поставщиков из истории" value={num(s.known)} />
                <Tile label="Новых компаний" value={num(s.pool)} note="СПб и Ленобласть, в закупках не участвовали" />
                <Tile label="Из них с подтверждённой деятельностью" value={num(s.new_confirmed)} />
              </div>
            </Card>
          </div>
          <div className="neva-side" style={{ flex: '1 1 320px', maxWidth: 400, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Источники данных" subtitle="Собраны заранее; у каждой записи указан источник" padding={20}>
              <div style={{ display: 'grid', gap: 10, fontSize: 13 }}>
                {s.sources.map((x) => <div key={x} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}><Icon name="database" size={16} color="var(--text-tertiary)" style={{ marginTop: 2 }} />{x}</div>)}
              </div>
            </Card>
            <Alert tone="info" title="Без внешних сервисов">Подбор считается на локальных индексах за доли секунды. Нейросети и внешние API при подборе не используются.</Alert>
          </div>
        </div>
      )}
    </div>
  );
}
