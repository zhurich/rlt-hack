import React from 'react';
function tone(v: number) { return v >= 80 ? 'var(--match-solid)' : v >= 60 ? 'var(--blue-500)' : 'var(--gray-400)'; }
/** Индикатор релевантности (0–100). ≥80 — бирюзовый, 60–79 — синий, ниже — серый. */
export interface MatchScoreProps {
  value: number;
  variant?: 'ring' | 'bar' | 'inline';
  /** Диаметр кольца, px */
  size?: number;
  label?: string;
  /** Единица после числа; пустая строка — балл без знака процента */
  unit?: string;
  /** Подсказка при наведении на кольцо */
  title?: string;
  style?: React.CSSProperties;
}
export function MatchScore({ value = 0, variant = 'ring', size = 56, label = 'совпадение', unit = '%', title, style }: MatchScoreProps) {
  const v = Math.max(0, Math.min(100, Math.round(value)));
  const c = tone(v);
  if (variant === 'bar') {
    return (
      <div style={{ minWidth: 120, ...style }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, lineHeight: '16px', marginBottom: 4 }}>
          <span style={{ color: 'var(--text-secondary)' }}>{label}</span><span style={{ fontWeight: 600, color: v >= 80 ? 'var(--match-fg)' : 'var(--text-primary)' }}>{v}{unit ? <>&nbsp;{unit}</> : null}</span>
        </div>
        <div style={{ height: 6, borderRadius: 3, background: 'var(--gray-100)', overflow: 'hidden' }}><div style={{ width: v + '%', height: '100%', background: c, borderRadius: 3 }} /></div>
      </div>
    );
  }
  if (variant === 'inline') {
    return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600, color: v >= 80 ? 'var(--match-fg)' : 'var(--text-primary)', ...style }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: c }} />{v}{unit ? <>&nbsp;{unit}</> : null}</span>;
  }
  const r = (size - 6) / 2, L = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', width: size, height: size, flex: 'none', ...style }} title={title || 'Релевантность ' + v + unit}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--gray-100)" strokeWidth="5" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={c} strokeWidth="5" strokeLinecap="round" strokeDasharray={L} strokeDashoffset={L * (1 - v / 100)} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', lineHeight: 1 }}>
        <span style={{ fontSize: size >= 56 ? 17 : 13, fontWeight: 700, color: 'var(--text-primary)' }}>{v}{unit ? <span style={{ fontSize: size >= 56 ? 11 : 9, fontWeight: 600, color: 'var(--text-tertiary)' }}>{unit}</span> : null}</span>
      </div>
    </div>
  );
}
