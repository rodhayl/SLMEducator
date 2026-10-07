import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
export interface Message { id: number; from_id: number; to_id: number | null; subject: string; content: string; read_at: string | null; sent_at: string; archived_at: string | null; sender_name: string | null; recipient_name: string | null }
export interface Contact { id: number; username: string; full_name: string; role: 'student' | 'teacher' | 'admin' }
export interface MessageInput { recipient_id: number; subject: string; body: string }
export type Folder = 'inbox' | 'sent' | 'archived';
export type MessageAction = 'read' | 'unread' | 'archive' | 'unarchive' | 'delete';
export function record(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value); }
export function invalid(mutation = false): never { throw new ApiError(200, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
const optionalText = (value: unknown) => value === null || typeof value === 'string';
export function parseMessage(value: unknown, mutation = false): Message {
 if (!record(value) || typeof value.id !== 'number' || !positiveId(value.id) || typeof value.from_id !== 'number' || !positiveId(value.from_id) || (value.to_id !== null && (typeof value.to_id !== 'number' || !positiveId(value.to_id))) || typeof value.subject !== 'string' || typeof value.content !== 'string' || typeof value.sent_at !== 'string' || !optionalText(value.read_at) || !optionalText(value.archived_at) || !optionalText(value.sender_name) || !optionalText(value.recipient_name)) return invalid(mutation);
 return value as unknown as Message;
}
export function parseMessages(value: unknown, owner: number, folder: Folder): Message[] {
 if (!Array.isArray(value)) return invalid();
 const messages = value.map(item => parseMessage(item));
 if (new Set(messages.map(item => item.id)).size !== messages.length || messages.some(item => folder === 'inbox' ? item.to_id !== owner || item.archived_at !== null : folder === 'sent' ? item.from_id !== owner || item.archived_at !== null : (item.from_id !== owner && item.to_id !== owner) || item.archived_at === null)) return invalid();
 return messages;
}
export function parseContacts(value: unknown): Contact[] {
 if (!Array.isArray(value) || !value.every(item => record(item) && typeof item.id === 'number' && !!positiveId(item.id) && typeof item.username === 'string' && !!item.username && typeof item.full_name === 'string' && ['student', 'teacher', 'admin'].includes(String(item.role))) || new Set(value.map(item => item.id)).size !== value.length) return invalid();
 return value as Contact[];
}
export function confirmMessage(value: unknown, input: MessageInput, owner: number): Message {
 const message = parseMessage(value, true);
 if (message.from_id !== owner || message.to_id !== input.recipient_id || message.subject !== input.subject || message.content !== input.body) return invalid(true);
 return message;
}
export function confirmMessageAction(value: unknown, action: MessageAction): void {
 if (!record(value) || value.status !== 'ok' || (action === 'delete' ? value.deleted !== true : action === 'read' ? typeof value.read_at !== 'string' : action === 'unread' ? value.read_at !== null : action === 'archive' ? typeof value.archived_at !== 'string' : value.archived_at !== null)) invalid(true);
}
export function messageFolder(value: string | null): Folder { return value === 'sent' || value === 'archived' ? value : 'inbox'; }
export function filterMessages(messages: Message[], query: string): Message[] { const term = query.trim().toLocaleLowerCase(); return messages.filter(message => !term || [message.subject, message.content, message.sender_name, message.recipient_name].some(value => value?.toLocaleLowerCase().includes(term))); }
export function contactLabel(contact: Contact): string { return `${contact.full_name || contact.username} (@${contact.username}) · ID ${contact.id}`; }
