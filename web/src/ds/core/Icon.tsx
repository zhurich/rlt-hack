import React from 'react';
// Иконки Lucide (lucide-static@0.469.0) вшиваются в сборку: на защите интернет не нужен.
// Новую иконку добавлять сюда же.
import arrowDown from 'lucide-static/icons/arrow-down.svg?raw';
import arrowUp from 'lucide-static/icons/arrow-up.svg?raw';
import arrowUpDown from 'lucide-static/icons/arrow-up-down.svg?raw';
import building2 from 'lucide-static/icons/building-2.svg?raw';
import check from 'lucide-static/icons/check.svg?raw';
import chevronDown from 'lucide-static/icons/chevron-down.svg?raw';
import chevronRight from 'lucide-static/icons/chevron-right.svg?raw';
import circleAlert from 'lucide-static/icons/circle-alert.svg?raw';
import circleCheck from 'lucide-static/icons/circle-check.svg?raw';
import circleHelp from 'lucide-static/icons/circle-help.svg?raw';
import copy from 'lucide-static/icons/copy.svg?raw';
import database from 'lucide-static/icons/database.svg?raw';
import factory from 'lucide-static/icons/factory.svg?raw';
import gitCompare from 'lucide-static/icons/git-compare.svg?raw';
import info from 'lucide-static/icons/info.svg?raw';
import loaderCircle from 'lucide-static/icons/loader-circle.svg?raw';
import mapPin from 'lucide-static/icons/map-pin.svg?raw';
import minus from 'lucide-static/icons/minus.svg?raw';
import search from 'lucide-static/icons/search.svg?raw';
import searchX from 'lucide-static/icons/search-x.svg?raw';
import shieldCheck from 'lucide-static/icons/shield-check.svg?raw';
import sparkles from 'lucide-static/icons/sparkles.svg?raw';
import triangleAlert from 'lucide-static/icons/triangle-alert.svg?raw';
import trophy from 'lucide-static/icons/trophy.svg?raw';
import truck from 'lucide-static/icons/truck.svg?raw';
import userRound from 'lucide-static/icons/user-round.svg?raw';
import x from 'lucide-static/icons/x.svg?raw';

const prep = (t: string) => t.replace(/<!--[\s\S]*?-->/g, '').replace(/\s(width|height)="\d+"/g, ' width="100%" height="100%"');
const ICONS: Record<string, string> = Object.fromEntries(Object.entries({
  'arrow-down': arrowDown, 'arrow-up': arrowUp, 'arrow-up-down': arrowUpDown, 'building-2': building2, check,
  'chevron-down': chevronDown, 'chevron-right': chevronRight, 'circle-alert': circleAlert, 'circle-check': circleCheck,
  'circle-help': circleHelp, copy, database, factory, 'git-compare': gitCompare, info, 'loader-circle': loaderCircle,
  'map-pin': mapPin, minus, search, 'search-x': searchX, 'shield-check': shieldCheck, sparkles,
  'triangle-alert': triangleAlert, trophy, truck, 'user-round': userRound, x,
}).map(([k, v]) => [k, prep(v)]));

/** Иконка из набора Lucide (контур 2px), окрашивается через currentColor. */
export interface IconProps {
  /** Имя иконки Lucide в kebab-case, напр. "search", "building-2" */
  name: string;
  /** Размер в px: 16 — в тексте и тегах, 20 — в кнопках, 24 — в навигации */
  size?: number;
  color?: string;
  /** Доступное имя; без него иконка декоративная */
  title?: string;
  style?: React.CSSProperties;
}
export function Icon({ name, size = 20, color = 'currentColor', title, style }: IconProps) {
  return (
    <span role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}
      style={{ display: 'inline-flex', flex: 'none', width: size, height: size, color, lineHeight: 0, ...style }}
      dangerouslySetInnerHTML={{ __html: ICONS[name] || '' }} />
  );
}
