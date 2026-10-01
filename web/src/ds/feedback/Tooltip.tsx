import React from 'react';
/** Подсказка при наведении: расшифровка аббревиатур и причин статуса. */
export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  placement?: 'top' | 'bottom';
  style?: React.CSSProperties;
}
export function Tooltip({ content, children, placement = 'top', style }: TooltipProps) {
  const [open, setOpen] = React.useState(false);
  const pos = placement === 'bottom' ? { top: '100%', marginTop: 6 } : { bottom: '100%', marginBottom: 6 };
  return (
    <span onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} style={{ position: 'relative', display: 'inline-flex', ...style }}>
      {children}
      {open && content ? <span role="tooltip" style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', ...pos, zIndex: 'var(--z-dropdown)', width: 'max-content', maxWidth: 280, padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--gray-800)', color: '#fff', fontSize: 12, lineHeight: '16px', fontWeight: 400, textAlign: 'left', whiteSpace: 'normal', boxShadow: 'var(--shadow-2)', pointerEvents: 'none' }}>{content}</span> : null}
    </span>
  );
}
