// Запросы к API и форматы чисел/дат по правилам дизайн-системы
// (разряды через неразрывный пробел, десятичная запятая, «₽» после суммы, даты ДД.ММ.ГГГГ).
import React from 'react';
import type { Company, Item, Role, Status } from './types';

// Узкий экран (телефон): та же граница, что у правил @media в ds/styles.css.
const NARROW = '(max-width: 640px)';
export function useNarrow(): boolean {
  const [narrow, setNarrow] = React.useState(() => window.matchMedia(NARROW).matches);
  React.useEffect(() => {
    const mq = window.matchMedia(NARROW);
    const on = () => setNarrow(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return narrow;
}

export async function api<T>(url: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Ошибка ' + r.status);
  return r.json();
}
export const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

type Num = number | null | undefined;
const NBSP = ' ';
export const num = (x: Num) => (x == null ? '—' : Math.round(x).toLocaleString('ru-RU'));
export const rub = (x: Num) => (x == null ? '—' : x.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + NBSP + '₽');
const dec = (x: number) => x.toFixed(1).replace('.', ',');
export const money = (x: Num) => (x == null ? '—'
  : x >= 1e9 ? dec(x / 1e9) + NBSP + 'млрд' + NBSP + '₽'
  : x >= 1e6 ? dec(x / 1e6) + NBSP + 'млн' + NBSP + '₽'
  : x >= 1e3 ? Math.round(x / 1e3) + NBSP + 'тыс.' + NBSP + '₽'
  : Math.round(x) + NBSP + '₽');
export const date = (s: string | null | undefined) => (s ? s.slice(0, 10).split('-').reverse().join('.') : '—');
export const pct = (x: number) => Math.round(x * 100) + NBSP + '%';
export const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

// Названия организаций — с кавычками-ёлочками.
export const orgName = (c: { name?: string | null }) => (c.name ? c.name.replace(/\s+/g, ' ').replace(/"([^"]*)"/g, '«$1»') : 'Название не найдено в реестрах');

export const ROLES: Role[] = ['производитель', 'дистрибьютор', 'поставщик'];
export const ROLE_ICON: Record<Role, string> = { 'производитель': 'factory', 'дистрибьютор': 'truck', 'поставщик': 'building-2' };
export const STATUSES: Status[] = ['проверенный', 'участник', 'новый, подтверждён', 'новый', 'требует проверки', 'риск'];
export const MSP: Record<number, string> = { 1: 'Микропредприятие', 2: 'Малое предприятие', 3: 'Среднее предприятие' };

// Балл показывается относительно первого места в списке.
export const relScore = (it: Item, items: Item[]) => (items.length ? Math.round((100 * it.score) / items[0].score) : 0);

// Признаки компании: поля из реестров бывают пустыми.
export const hasDebt = (c: Company) => (c.tax_debt ?? 0) > 0;
export const inRnp = (c: Company) => (c.rnp_records ?? 0) > 0;
export const winRate = (c: Company) => (c.bids ? (c.wins ?? 0) / c.bids : null);
