import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui';
import { useResource } from '@/lib/query';

/** One account-scoped cache entry is shared by desktop and mobile navigation. */
export function UnreadMessagesBadge() {
 const { t } = useTranslation();
 const unread = useResource<unknown>(['messages', 'unread-count'], '/api/classroom/messages/unread-count');
 const count = unread.data && typeof unread.data === 'object' && 'unread_count' in unread.data ? unread.data.unread_count : null;
 const valid = typeof count === 'number' && Number.isSafeInteger(count) && count >= 0;
 if (unread.error || !unread.isPending && !valid) return <span aria-label={t('unreadUnavailable')} title={t('unreadUnavailable')}>?</span>;
 return valid && count > 0 ? <span aria-label={t('unreadMessages', { count })}><Badge tone="warning">{count}</Badge></span> : null;
}
