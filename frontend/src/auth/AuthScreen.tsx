import { FormEvent, useState } from "react";
import { API_URL, request } from "../api/client";
import type { User } from "../types";

/** Entry screen: OAuth (Stepik/Google) or email+password. The 0.2 message
 * asks what should change instead of starting from a problem. */
export function AuthScreen({ notice, onAuthenticated }: { notice?: string; onAuthenticated: (user: User) => void }) {
  const [mode, setMode] = useState<"register" | "login">("login");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await request<{ message: string }>(`/auth/register`, {
          method: "POST",
          body: JSON.stringify({ email, password, display_name: displayName, consent_accepted: true }),
        });
        setMode("login");
        setError("Аккаунт создан. Проверьте email для подтверждения, затем войдите.");
        return;
      }
      const data = await request<{ user: User }>(`/auth/login`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      onAuthenticated(data.user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка авторизации");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <div className="auth-card">
        <span className="eyebrow">CAOS 0.2</span>
        <h1>Что вы хотите изменить?</h1>
        <p className="muted">Формулируйте цели, присоединяйтесь к целям других и доказывайте результат.</p>
        <div className="stepik-login-section">
          <a className="stepik-login-btn" href={`${API_URL}/auth/stepik`}>
            <span className="stepik-icon">S</span>
            Войти через Stepik
          </a>
          <a className="google-login-btn" href={`${API_URL}/auth/google`}>
            <span className="google-icon">G</span>
            Войти через Google
          </a>
        </div>
        <div className="auth-divider"><span>или</span></div>
        <form onSubmit={submitAuth} className="auth-form">
          <h2>{mode === "register" ? "Создать аккаунт" : "Войти"}</h2>
          {mode === "register" && (
            <input placeholder="Ваше имя" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required minLength={2} />
          )}
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="password" placeholder="Пароль (минимум 12 символов)" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={12} />
          {(error || notice) && <p className="error">{error || notice}</p>}
          <button type="submit" className="primary" disabled={busy}>
            {mode === "register" ? "Начать работу" : "Войти"}
          </button>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              setMode(mode === "register" ? "login" : "register");
              setError("");
            }}
          >
            {mode === "register" ? "Уже есть аккаунт? Войти" : "Нет аккаунта? Зарегистрироваться"}
          </button>
        </form>
        <div className="stepik-courses-preview">
          <h3>Наши курсы на Stepik:</h3>
          <a className="course-link" href="https://stepik.org/course/288738" target="_blank" rel="noopener">
            <span className="course-icon">H</span>
            Наука логики Гегеля
          </a>
          <a className="course-link" href="https://stepik.org/course/288774" target="_blank" rel="noopener">
            <span className="course-icon">K</span>
            Капитал Маркса
          </a>
          <a className="course-link" href="https://stepik.org/course/285340" target="_blank" rel="noopener">
            <span className="course-icon">L</span>
            Ленин «Карл Маркс»
          </a>
        </div>
      </div>
    </main>
  );
}
