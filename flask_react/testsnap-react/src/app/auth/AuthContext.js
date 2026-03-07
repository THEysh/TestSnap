import { createContext } from 'react';

export const AuthContext = createContext({
  user: null,
  loading: true,
  signIn: async () => ({ ok: false, error: 'not_ready' }),
  signUp: async () => ({ ok: false, error: 'not_ready' }),
  signOut: () => ({ ok: true })
});

