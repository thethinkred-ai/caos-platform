import { FormEvent, useEffect, useState } from "react";

type Problem = { id: number; title: string; description: string; status: string; author_id: number };
type User = { id: number; email: string; display_name: string; bio: string };

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("caos_token");
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
  } catch (error) {
    if (error instanceof TypeError) throw new Error("API недоступен. Запустите backend на порту 8000.");
    throw error;
  }
  if (!response.ok) throw new Error((await response.json()).detail ?? "Не удалось выполнить запрос");
  return response.json();
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"login" | "register">("register");

  const loadProblems = async () => {
    try { setProblems(await request<Problem[]>("/problems")); } catch (e) { setError(e instanceof Error ? e.message : "Ошибка загрузки"); }
  };

  useEffect(() => {
    const token = localStorage.getItem("caos_token");
    if (token) request<User>("/auth/me").then(setUser).then(loadProblems).catch(() => localStorage.removeItem("caos_token"));
  }, []);

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault(); setError("");
    try {
      const data = await request<{ access_token: string; user: User }>(`/auth/${mode}`, { method: "POST", body: JSON.stringify(mode === "register" ? { email, password, display_name: displayName } : { email, password }) });
      localStorage.setItem("caos_token", data.access_token); setUser(data.user); await loadProblems();
    } catch (e) {
    const message = e instanceof Error ? e.message : "Ошибка авторизации";
    if (message === "Email already registered") {
      setMode("login");
      setError("Этот email уже зарегистрирован. Введите пароль и войдите.");
    } else {
      setError(message);
    }
  }
  };

  const createProblem = async (event: FormEvent) => {
    event.preventDefault(); setError("");
    try { await request<Problem>("/problems", { method: "POST", body: JSON.stringify({ title: newTitle, description: newDescription }) }); setNewTitle(""); setNewDescription(""); await loadProblems(); }
    catch (e) { setError(e instanceof Error ? e.message : "Ошибка создания"); }
  };

  if (!user) return <main className="auth-page"><div className="auth-card"><span className="eyebrow">CAOS / MVP 0.1</span><h1>Деятельность начинается с проблемы.</h1><p className="muted">Находите общие задачи, формулируйте цели и превращайте их в совместные проекты.</p><form onSubmit={submitAuth}><h2>{mode === "register" ? "Создать аккаунт" : "Войти"}</h2>{mode === "register" && <input placeholder="Ваше имя" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required minLength={2} />}<input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required /><input type="password" placeholder="Пароль (не менее 8 символов)" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} /><button type="submit">{mode === "register" ? "Начать работу" : "Войти"}</button></form>{error && <p className="error">{error}</p>}<button className="link-button" onClick={() => setMode(mode === "register" ? "login" : "register")}>{mode === "register" ? "Уже есть аккаунт? Войти" : "Создать новый аккаунт"}</button></div></main>;

  return <div className="app-shell"><aside><div className="brand"><span className="brand-mark">C</span><span>CAOS</span></div><p className="side-caption">Collective Activity Operating System</p><nav><a className="active">Обзор</a><a>Проблемы</a><a>Цели</a><a>Проекты</a><a>База знаний</a></nav><button className="logout" onClick={() => { localStorage.removeItem("caos_token"); setUser(null); }}>Выйти</button></aside><main className="content"><header><div><span className="eyebrow">Рабочее пространство</span><h1>Добрый день, {user.display_name}</h1></div><div className="avatar">{user.display_name.slice(0, 1).toUpperCase()}</div></header><section className="hero"><div><span className="eyebrow">Главный цикл</span><h2>Проблема → цель → проект → результат</h2><p>Зафиксируйте проблему, чтобы найти людей и знания для совместного действия.</p></div><span className="hero-number">01</span></section><div className="grid"><section className="panel"><div className="panel-heading"><div><span className="eyebrow">Шаг 1</span><h2>Создать проблему</h2></div><span className="status-dot" /></div><form onSubmit={createProblem} className="problem-form"><input placeholder="Что нужно изменить?" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} required /><textarea placeholder="Опишите контекст и желаемый результат" value={newDescription} onChange={(e) => setNewDescription(e.target.value)} required /><button type="submit">Добавить проблему</button></form>{error && <p className="error">{error}</p>}</section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">Ваше пространство</span><h2>Открытые проблемы</h2></div><span className="count">{problems.length}</span></div>{problems.length === 0 ? <p className="muted empty">Пока нет проблем. Создайте первую, чтобы начать коллективный цикл.</p> : <div className="problem-list">{problems.map((problem) => <article key={problem.id}><span className="problem-icon">↗</span><div><h3>{problem.title}</h3><p>{problem.description}</p><small>Открыта · #{problem.id}</small></div></article>)}</div>}</section></div></main></div>;
}
