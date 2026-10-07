import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
export type Theme = 'light' | 'dark' | 'system';
export type ReadingSize = 16 | 18 | 20 | 24;
interface Appearance { animations: boolean; setAnimations: (value: boolean) => void; theme: Theme; setTheme: (value: Theme) => void; readingSize: ReadingSize; setReadingSize: (value: ReadingSize) => void }
const AppearanceContext = createContext<Appearance>({ animations: true, setAnimations() {}, theme: 'system', setTheme() {}, readingSize: 18, setReadingSize() {} });
export function AppearanceProvider({ children }: { children: ReactNode }) {
 const [animations, setAnimations] = useState(true);
 useEffect(() => { document.documentElement.dataset.motion = animations ? 'system' : 'reduced'; }, [animations]);
 const [theme, setTheme] = useState<Theme>(() => { try { const value = localStorage.getItem('slm-theme'); return value === 'light' || value === 'dark' ? value : 'system'; } catch { return 'system'; } });
 const [readingSize, setReadingSize] = useState<ReadingSize>(() => { try { const value = Number(localStorage.getItem('slm-reading-size')); return [16,18,20,24].includes(value) ? value as ReadingSize : 18; } catch { return 18; } });
 useEffect(() => { const media = matchMedia('(prefers-color-scheme: dark)'); const apply = () => { document.documentElement.dataset.theme = theme === 'system' ? media.matches ? 'dark' : 'light' : theme; }; apply(); media.addEventListener('change', apply); try { localStorage.setItem('slm-theme', theme); } catch { /* Session-only preference. */ } return () => media.removeEventListener('change', apply); }, [theme]);
 useEffect(() => { document.documentElement.style.setProperty('--reading-size', `${readingSize / 16}rem`); try { localStorage.setItem('slm-reading-size', String(readingSize)); } catch { /* Session-only preference. */ } }, [readingSize]);
 return <AppearanceContext.Provider value={{ theme, setTheme, readingSize, setReadingSize, animations, setAnimations }}>{children}</AppearanceContext.Provider>;
}
export function useAppearance() { return useContext(AppearanceContext); }
