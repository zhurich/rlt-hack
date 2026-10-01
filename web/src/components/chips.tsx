import { Badge, StatusBadge, Tooltip } from '../ds';
import { cap, ROLE_ICON, MSP } from '../lib';
import type { Company } from '../types';

interface ChipProps { company: Company; size?: 'sm' | 'md' }

// Статус — пилюля с точкой; «проверенный» — золотой знак (в системе золото только для него).
export function StatusChip({ company: c, size }: ChipProps) {
  if (!c.status) return null;
  const chip = c.status === 'проверенный'
    ? <Badge tone="verified" icon="shield-check" size={size}>Проверенный</Badge>
    : <StatusBadge status={c.status} size={size} />;
  return <Tooltip content={c.status_reason}>{chip}</Tooltip>;
}

export function RoleChip({ company: c, size }: ChipProps) {
  if (!c.role) return null;
  return <Tooltip content={c.role_reason}><Badge tone="info" icon={ROLE_ICON[c.role] || 'building-2'} size={size}>{cap(c.role)}</Badge></Tooltip>;
}

export function MspChip({ company: c, size }: ChipProps) {
  if (!c.msp_category) return null;
  return <Tooltip content={'Субъект малого и среднего предпринимательства: ' + (MSP[c.msp_category] || '').toLowerCase()}><Badge size={size}>МСП</Badge></Tooltip>;
}

/** mark: true — победил в этой закупке, false — участвовал, undefined — не участвовал. */
export function ActualChip({ mark, size }: { mark: boolean | undefined; size?: 'sm' | 'md' }) {
  if (mark === true) return <Badge tone="success" variant="solid" icon="trophy" size={size}>Победил в этой закупке</Badge>;
  if (mark === false) return <Badge tone="success" icon="check" size={size}>Участвовал в этой закупке</Badge>;
  return null;
}
