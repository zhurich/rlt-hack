import React from 'react';
/** Контейнер-карточка: белый фон, граница 1px, без тени в покое. */
export interface CardProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  padding?: number;
  /** Подсветка границы и тень при наведении */
  interactive?: boolean;
  selected?: boolean;
  onClick?: () => void;
  style?: React.CSSProperties;
}
export function Card({ title, subtitle, actions, children, padding = 20, interactive, selected, onClick, style }: CardProps) {
  const [hover, setHover] = React.useState(false);
  return (
    <div onClick={onClick} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid ' + (selected ? 'var(--blue-400)' : hover && interactive ? 'var(--border-strong)' : 'var(--border-default)'),
        boxShadow: selected ? '0 0 0 1px var(--blue-400)' : hover && interactive ? 'var(--shadow-1)' : 'none', cursor: interactive || onClick ? 'pointer' : 'default',
        transition: 'border-color var(--duration-fast), box-shadow var(--duration-fast)', ...style }}>
      {title || actions ? (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, padding: padding + 'px ' + padding + 'px 0' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            {title ? <div style={{ fontSize: 'var(--text-h4)', lineHeight: 'var(--leading-h4)', fontWeight: 600 }}>{title}</div> : null}
            {subtitle ? <div style={{ marginTop: 2, fontSize: 13, color: 'var(--text-secondary)' }}>{subtitle}</div> : null}
          </div>
          {actions ? <div style={{ display: 'flex', gap: 8, flex: 'none' }}>{actions}</div> : null}
        </div>
      ) : null}
      <div style={{ padding }}>{children}</div>
    </div>
  );
}
