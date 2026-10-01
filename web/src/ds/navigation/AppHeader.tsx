import React from 'react';
import { Icon } from '../core/Icon';
import { IconButton } from '../core/IconButton';
import { Input } from '../forms/Input';
// Отличие от исходника дизайн-системы: «Справка», пользователь и уведомления показываются только
// когда переданы — в сервисе нет ни авторизации, ни уведомлений, и пустых кнопок быть не должно.
/**
 * Шапка в два яруса: тёмная служебная строка (система, регион) прокручивается,
 * светлая основная (сервис, разделы, быстрый поиск) остаётся закреплённой.
 */
export interface AppHeaderNavItem<I extends string = string> { id: I; label: string; }
export interface AppHeaderProps<I extends string = string> {
  system?: string;
  product?: string;
  /** Регион в служебной строке */
  region?: string;
  nav?: AppHeaderNavItem<I>[];
  active?: I;
  onNav?: (id: I) => void;
  user?: string;
  /** Организация заказчика */
  org?: string;
  /** Пояснение в служебной строке */
  note?: string;
  /** Число поставщиков в сравнении; null — скрыть кнопку */
  compareCount?: number | null;
  onCompare?: () => void;
  /** Поле быстрого поиска */
  quickSearch?: boolean;
  quickSearchPlaceholder?: string;
  onQuickSearch?: (q: string) => void;
  style?: React.CSSProperties;
}
export function AppHeader<I extends string = string>({ system = 'АИС ГЗ Санкт-Петербурга', product = 'Поиск поставщиков', region = 'Санкт-Петербург', nav = [], active, onNav, user, org, note, compareCount, onCompare, quickSearch = true, quickSearchPlaceholder = '№ извещения, ИНН, ОКПД2', onQuickSearch, style }: AppHeaderProps<I>) {
  const [hover, setHover] = React.useState<I | null>(null);
  const [q, setQ] = React.useState('');
  const top: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap', color: 'var(--blue-100)' };
  return (
    <header style={{ position: 'sticky', top: 'calc(var(--header-top-h) * -1)', zIndex: 'var(--z-sticky)', ...style }}>
      <div style={{ height: 'var(--header-top-h)', background: 'var(--surface-header)', color: '#fff', fontSize: 12 }}>
        <div style={{ height: '100%', maxWidth: 'var(--container-max)', margin: '0 auto', padding: '0 var(--gutter)', display: 'flex', alignItems: 'center', gap: 20 }}>
          <span style={{ ...top, fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0 }}>{system}</span>
          <span style={{ flex: 1 }} />
          {note ? <span style={{ ...top, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{note}</span> : null}
          {region ? <span style={top}><Icon name="map-pin" size={14} />{region}</span> : null}
          {user ? <span style={{ ...top, color: '#fff', minWidth: 0, overflow: 'hidden' }}><Icon name="user-round" size={14} /><span style={{ fontWeight: 600 }}>{user}</span>{org ? <span style={{ color: 'var(--blue-200)', overflow: 'hidden', textOverflow: 'ellipsis' }}>· {org}</span> : null}</span> : null}
        </div>
      </div>
      <div style={{ height: 'var(--header-main-h)', background: 'var(--surface-header-main)', borderBottom: '1px solid var(--border-default)' }}>
        <div style={{ height: '100%', maxWidth: 'var(--container-max)', margin: '0 auto', padding: '0 var(--gutter)', display: 'flex', alignItems: 'stretch', gap: 24 }}>
          <a href="#" onClick={(e) => { e.preventDefault(); onNav && nav[0] && onNav(nav[0].id); }} style={{ flex: 'none', display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
            <span style={{ width: 4, alignSelf: 'stretch', margin: '14px 0', background: 'var(--blue-600)' }} />
            <span style={{ fontSize: 17, lineHeight: '20px', fontWeight: 700, color: 'var(--blue-700)', whiteSpace: 'nowrap' }}>{product}</span>
          </a>
          <nav style={{ display: 'flex', alignItems: 'stretch', flex: 1, minWidth: 0, overflowX: 'auto', scrollbarWidth: 'none' }}>
            {nav.map((n) => { const on = n.id === active; return (
              <a key={n.id} href="#" onClick={(e) => { e.preventDefault(); onNav && onNav(n.id); }} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
                style={{ display: 'flex', alignItems: 'center', padding: '0 12px', whiteSpace: 'nowrap', fontSize: 14, fontWeight: on ? 600 : 500, textDecoration: 'none',
                  color: on ? 'var(--blue-700)' : hover === n.id ? 'var(--blue-600)' : 'var(--text-primary)', boxShadow: on ? 'inset 0 -3px 0 var(--blue-600)' : 'none', background: hover === n.id && !on ? 'var(--surface-hover)' : 'transparent' }}>
                {n.label}
              </a>); })}
          </nav>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flex: '0 1 auto', minWidth: 0 }}>
            {quickSearch ? <form onSubmit={(e) => { e.preventDefault(); if (q.trim() && onQuickSearch) { onQuickSearch(q.trim()); setQ(''); } }} style={{ flex: '0 1 240px', minWidth: 140, marginRight: 8 }}>
              <Input size="sm" iconLeft="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={quickSearchPlaceholder} aria-label="Быстрый поиск" />
            </form> : null}
            {compareCount != null ? <IconButton icon="git-compare" label="Сравнение" badge={compareCount || undefined} onClick={onCompare} /> : null}
          </div>
        </div>
      </div>
    </header>
  );
}
