const unavailable: Storage = {
 get length(): number { throw new Error('Storage unavailable'); },
 clear() { throw new Error('Storage unavailable'); },
 getItem() { throw new Error('Storage unavailable'); },
 key() { throw new Error('Storage unavailable'); },
 removeItem() { throw new Error('Storage unavailable'); },
 setItem() { throw new Error('Storage unavailable'); },
};
/** Some browsers throw when the localStorage property itself is read. */
export function browserStorage(read: () => Storage = () => window.localStorage): Storage {
 try { return read(); } catch { return unavailable; }
}
