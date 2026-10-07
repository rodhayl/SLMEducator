import { createContext, useContext } from 'react';
import type { AuthStatus } from './auth-controller';
/** Portals render outside the visual shell, but share this privacy context. */
export const PrivacyContext = createContext<AuthStatus>('authenticated');
export function usePrivacyStatus() { return useContext(PrivacyContext); }
