import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AuthContext } from './AuthContext';
import { getCurrentUser, signIn, signOut, signUp } from './authStorage';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const u = getCurrentUser();
    setUser(u);
    setLoading(false);
  }, []);

  const doSignIn = useCallback(async (payload) => {
    const res = await signIn(payload);
    if (res.ok) setUser(res.user);
    return res;
  }, []);

  const doSignUp = useCallback(async (payload) => {
    const res = await signUp(payload);
    if (res.ok) setUser(res.user);
    return res;
  }, []);

  const doSignOut = useCallback(() => {
    const res = signOut();
    setUser(null);
    return res;
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    signIn: doSignIn,
    signUp: doSignUp,
    signOut: doSignOut
  }), [user, loading, doSignIn, doSignUp, doSignOut]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
