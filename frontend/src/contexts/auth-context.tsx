"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { api } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (
    email: string,
    password: string,
    inviteToken?: string
  ) => Promise<void>;
  loginWithGoogle: (credential: string, inviteToken?: string) => Promise<void>;
  register: (
    email: string,
    name: string,
    password: string,
    inviteToken?: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const authenticateWithToken = useCallback(async (accessToken: string) => {
    localStorage.setItem("token", accessToken);
    const nextUser = await api.auth.me();
    setUser(nextUser);
  }, []);

  const fetchUser = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setLoading(false);
        return;
      }
      const u = await api.auth.me();
      setUser(u);
    } catch {
      localStorage.removeItem("token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = async (
    email: string,
    password: string,
    inviteToken?: string
  ) => {
    const res = await api.auth.login({
      email,
      password,
      invite_token: inviteToken,
    });
    await authenticateWithToken(res.access_token);
  };

  const loginWithGoogle = async (credential: string, inviteToken?: string) => {
    const res = await api.auth.google({
      credential,
      invite_token: inviteToken,
    });
    await authenticateWithToken(res.access_token);
  };

  const register = async (
    email: string,
    name: string,
    password: string,
    inviteToken?: string
  ) => {
    const res = await api.auth.register({
      email,
      name,
      password,
      invite_token: inviteToken,
    });
    await authenticateWithToken(res.access_token);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, loginWithGoogle, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
