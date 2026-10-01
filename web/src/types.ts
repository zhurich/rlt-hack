// Типы ответов API (app/main.py → recsys/service.py). Менять вместе с Service._build и CARD_COLUMNS.

export type Role = 'производитель' | 'дистрибьютор' | 'поставщик';
export type Status = 'проверенный' | 'участник' | 'новый, подтверждён' | 'новый' | 'требует проверки' | 'риск';

/** Карточка компании из таблицы companies. Для ИНН, которого в таблице нет, приходит только inn. */
export interface Company {
  inn: string;
  kind?: string | null;
  name?: string | null;
  region?: string | null;
  place?: string | null;
  in_history?: boolean;
  bids?: number;
  wins?: number;
  last_bid?: string | null;
  status?: Status | null;
  status_reason?: string | null;
  role?: Role | null;
  role_reason?: string | null;
  role_source?: string | null;
  okved_main?: string | null;
  okved_main_name?: string | null;
  /** 1 — микро, 2 — малое, 3 — среднее */
  msp_category?: number | null;
  msp_since?: string | null;
  headcount?: number | null;
  revenue?: number | null;
  tax_debt?: number | null;
  rnp_records?: number | null;
  licenses?: string[] | null;
  sources?: string[] | null;
}

export interface Factors {
  relevance: { label: string; share: number }[];
  boosts: { label: string; pct: number }[];
}

export interface SimilarLot {
  lot_id: number;
  sim: number;
  won: boolean;
  subject: string | null;
}

/** Строка выдачи: поставщик из истории или новая компания из реестров. */
export interface Item {
  inn: string;
  score: number;
  company: Company;
  reasons: string[];
  factors: Factors;
  /** Только у поставщиков из истории */
  similar_lots?: SimilarLot[];
  typical_price?: number | null;
}

/** Строка выдачи с местом и баллом относительно первого места — считается на фронте. */
export interface RankedItem extends Item {
  rank: number;
  rel: number;
  isNew: boolean;
}

export interface Participant {
  inn: string;
  won: boolean;
  name: string | null;
  /** Место в нашей выдаче; null — в выдачу не попал */
  place: number | null;
}

export interface Lot {
  lot_id: number | null;
  publish_date?: string | null;
  source: string | null;
  price: number | null;
  subject: string | null;
  is_smp: boolean;
  customer_inn: string | null;
  positions: { name: string; code: string; n: number }[];
  participants: Participant[];
}

export interface Recommendation {
  lot: Lot;
  codes: { code: string; share: number }[];
  codes_inferred: boolean;
  items: Item[];
  new_items: Item[];
  elapsed_ms: number;
}

/** Строка поиска закупок и пример для показа. */
export interface LotBrief {
  lot_id: number;
  publish_date: string;
  source: string;
  price: number | null;
  subject: string;
  participants: number;
}

export interface Stats {
  lots: number;
  known: number;
  new_total: number;
  new_confirmed: number;
  known_named: number;
  pool: number;
  recall10: number;
  winner10: number;
  map10: number;
  test_lots: number;
  baseline_okpd: number;
  baseline_popular: number;
  sources: string[];
}

/** Тело POST /api/recommend. */
export interface NewPurchase {
  text: string;
  codes: string[];
  price: number | null;
  source: string | null;
  is_smp: boolean;
}

/** ИНН → победил ли в этой закупке; ключа нет — не участвовал. */
export type Actual = Record<string, boolean>;
export type Lists = { known: RankedItem[]; new: RankedItem[] };
