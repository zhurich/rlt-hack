import React from 'react';
import { Icon } from '../core/Icon';
/** Навигационная цепочка над заголовком страницы. */
export interface BreadcrumbItem { label: string; href?: string; }
export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  onNavigate?: (item: BreadcrumbItem, index: number) => void;
  style?: React.CSSProperties;
}
export function Breadcrumbs({ items = [], onNavigate, style }: BreadcrumbsProps) {
  return (
    <nav aria-label="Навигационная цепочка" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, fontSize: 13, lineHeight: '20px', ...style }}>
      {items.map((it, i) => { const last = i === items.length - 1; return (
        <React.Fragment key={i}>
          {last ? <span style={{ color: 'var(--text-secondary)' }} aria-current="page">{it.label}</span>
            : <a href={it.href || '#'} onClick={(e) => { if (onNavigate) { e.preventDefault(); onNavigate(it, i); } }} style={{ color: 'var(--text-link)' }}>{it.label}</a>}
          {!last ? <Icon name="chevron-right" size={14} color="var(--text-tertiary)" /> : null}
        </React.Fragment>); })}
    </nav>
  );
}
