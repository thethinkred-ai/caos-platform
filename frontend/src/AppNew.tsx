import { FormEvent, useEffect, useState } from "react";
import { MyActivity } from "./activity/MyActivity";
import { KnowledgeSection } from "./knowledge/KnowledgeSection";
import { ProfileSection } from "./profile/ProfileSection";
import { NotificationsPanel } from "./notifications/NotificationsPanel";
import { OverviewPanel } from "./overview/OverviewPanel";
import { DecisionProcess } from "./decisions/DecisionProcess";
import { useHashRoute } from "./app/useHashRoute";
import { API_URL, request } from "./api/client";
import { GoalWorkspace } from "./goal/GoalWorkspace";
import { NewGoalWizard } from "./goal/NewGoalWizard";
import { OnboardingTour } from "./OnboardingTour";
import type {
  AuditEvent, Competence, Decision, DecisionEvent, Goal, KnowledgeItem, NextAction,
  Notification, Problem, Project, SearchResults, Section, Task, Team, User,
} from "./types";

const labels: Record<Section, string> = {
  overview: "Обзор",
  activity: "Моя деятельность",
  problems: "Проблемы",
  goals: "Цели",
  projects: "Проекты",
  teams: "Команды",
  decisions: "Решения",
  knowledge: "База знаний",
  profile: "Профиль",
  notifications: "Уведомления",
  audit: "Журнал",
  competences: "Компетенции",
};

export default function AppNew() {
  const [user, setUser] = useState<User | null>(null);
  const [route, navigate] = useHashRoute();
  const section = route.section;
  const workspaceGoalId = route.goalId;
  const goSection = (target: Section) => navigate(target);
  const goGoal = (goalId: number) => navigate("goals", goalId);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [nextAction, setNextAction] = useState<NextAction | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResults | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [competences, setCompetences] = useState<Competence[]>([]);
  const [compName, setCompName] = useState("");
  const [compLevel, setCompLevel] = useState(1);
  const [compDesc, setCompDesc] = useState("");
  const [projectTasks, setProjectTasks] = useState<Record<number, Task[]>>({});
  const [expandedProjectId, setExpandedProjectId] = useState<number | null>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDesc, setTaskDesc] = useState("");
  const [aiStatus, setAiStatus] = useState<{ llm_available: boolean; model: string | null; base_url: string | null } | null>(null);
  const [selectedDecisionId, setSelectedDecisionId] = useState<number | null>(null);
  const [decisionEvents, setDecisionEvents] = useState<DecisionEvent[]>([]);
  const [decisionMethod, setDecisionMethod] = useState("majority");
  const [decisionGoalId, setDecisionGoalId] = useState("");
  const [eventContent, setEventContent] = useState("");
  const [parentGoalId, setParentGoalId] = useState<number | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"login" | "register">("register");
  const [stepikCourses, setStepikCourses] = useState<{ id: number; title: string; slug: string; url: string; learners_count: number; sections_count: number }[]>([]);
  const [aiRecommendation, setAiRecommendation] = useState<{ goalId: number; suggestion: string; source: string; confidence: number } | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAction, setAiAction] = useState("");

  const callAi = async (endpoint: string, goalId: number, label: string) => {
    setAiLoading(true);
    setAiAction(label);
    setAiRecommendation(null);
    try {
      const rec = await request<{ suggestion: string; source: string; confidence: number }>(
        `/recommendations/${endpoint}/${goalId}`
      );
      setAiRecommendation({ goalId, ...rec });
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI недоступен");
    } finally {
      setAiLoading(false);
      setAiAction("");
    }
  };

  const loadData = async () => {
    try {
      const [problemData, goalData, projectData, teamData, decisionData, knowledgeData, actionData, notifData, auditData, compData] =
        await Promise.all([
          request<Problem[]>("/problems"),
          request<Goal[]>("/goals"),
          request<Project[]>("/projects"),
          request<Team[]>("/teams"),
          request<Decision[]>("/decisions"),
          request<KnowledgeItem[]>("/knowledge"),
          request<NextAction>("/next-action"),
          request<Notification[]>("/notifications"),
          request<AuditEvent[]>("/audit"),
          request<Competence[]>("/competences"),
        ]);
      setProblems(problemData);
      setGoals(goalData);
      setProjects(projectData);
      setTeams(teamData);
      setDecisions(decisionData);
      setKnowledge(knowledgeData);
      setNextAction(actionData);
      setNotifications(notifData);
      setAuditEvents(auditData);
      setCompetences(compData);
      try {
        const ai = await request<{ llm_available: boolean; model: string | null; base_url: string | null }>("/ai/status");
        setAiStatus(ai);
      } catch {
        setAiStatus({ llm_available: false, model: null, base_url: null });
      }
      try {
        const courses = await request<{ courses: typeof stepikCourses }>("/auth/stepik/courses");
        setStepikCourses(courses.courses);
      } catch {
        setStepikCourses([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки данных");
    }
  };

  useEffect(() => {
    const path = window.location.pathname;
    if (path === "/auth/callback") {
      window.history.replaceState({}, document.title, "/");
      request<User>("/auth/me")
        .then((current) => {
          setUser(current);
          return loadData();
        })
        .catch(() => {
          setError("Не удалось войти через OAuth. Попробуйте ещё раз.");
        });
      return;
    }
    if (path === "/auth/verify") {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("token");
      if (token) {
        request<{ message: string }>(`/auth/verify?token=${encodeURIComponent(token)}`)
          .then(() => {
            window.history.replaceState({}, document.title, "/");
            setError("Email подтверждён. Теперь вы можете войти.");
          })
          .catch(() => {
            window.history.replaceState({}, document.title, "/");
            setError("Ссылка подтверждения недействительна или истекла.");
          });
      } else {
        window.history.replaceState({}, document.title, "/");
      }
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const errorParam = params.get("error");
    if (errorParam) {
      window.history.replaceState({}, document.title, window.location.pathname);
      setError("Не удалось войти. Попробуйте другой способ.");
      return;
    }
    request<User>("/auth/me")
      .then((current) => {
        setUser(current);
        return loadData();
      })
      .catch(() => {});
  }, []);

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
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
      setUser(data.user);
      await loadData();
    } catch (e) {
      const message = e instanceof Error ? e.message : "Ошибка авторизации";
      setError(message);
    }
  };

  const createItem = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    const endpoint = section === "problems" ? "/problems" : section === "goals" ? "/goals" : "/projects";
    try {
      await request(endpoint, { method: "POST", body: JSON.stringify({ title, description }) });
      setTitle("");
      setDescription("");
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать запись");
    }
  };

  const createTeam = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      await request("/teams", { method: "POST", body: JSON.stringify({ name: title, description }) });
      setTitle("");
      setDescription("");
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать команду");
    }
  };

  const createDecision = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      await request("/decisions", {
        method: "POST",
        body: JSON.stringify({
          title,
          proposal: description,
          decision_method: decisionMethod,
          goal_id: decisionGoalId ? Number(decisionGoalId) : null,
        }),
      });
      setTitle("");
      setDescription("");
      setDecisionGoalId("");
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать решение");
    }
  };


  const doSearch = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (searchQuery.trim().length < 2) return;
    try {
      const results = await request<SearchResults>(`/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchResults(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось выполнить поиск");
    }
  };


  const loadDecisionEvents = async (decisionId: number) => {
    setSelectedDecisionId(decisionId);
    try {
      const events = await request<DecisionEvent[]>(`/decisions/${decisionId}/events`);
      setDecisionEvents(events);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить события");
    }
  };

  const addDecisionEvent = async (eventType: string) => {
    if (!selectedDecisionId || !eventContent.trim()) return;
    try {
      await request(`/decisions/${selectedDecisionId}/events`, {
        method: "POST",
        body: JSON.stringify({ event_type: eventType, content: eventContent }),
      });
      setEventContent("");
      await loadDecisionEvents(selectedDecisionId);
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить событие");
    }
  };

  const updateProjectStatus = async (projectId: number, newStatus: string) => {
    try {
      await request(`/projects/${projectId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось изменить статус");
    }
  };

  const markNotificationRead = async (notificationId: number) => {
    try {
      await request(`/notifications/${notificationId}/read`, { method: "PATCH" });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  const markAllNotificationsRead = async () => {
    try {
      await request("/notifications/read-all", { method: "PATCH" });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };



  const createCompetence = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      await request("/competences", {
        method: "POST",
        body: JSON.stringify({ name: compName, level: compLevel, description: compDesc }),
      });
      setCompName("");
      setCompLevel(1);
      setCompDesc("");
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить компетенцию");
    }
  };

  const deleteCompetence = async (competenceId: number) => {
    try {
      await request(`/competences/${competenceId}`, { method: "DELETE" });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  const loadProjectTasks = async (projectId: number) => {
    if (expandedProjectId === projectId) {
      setExpandedProjectId(null);
      return;
    }
    try {
      const tasks = await request<Task[]>(`/projects/${projectId}/tasks`);
      setProjectTasks((prev) => ({ ...prev, [projectId]: tasks }));
      setExpandedProjectId(projectId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить задачи");
    }
  };

  const assignTaskToSelf = async (taskId: number) => {
    try {
      await request(`/tasks/${taskId}/assign`, {
        method: "PATCH",
        body: JSON.stringify({ assignee_id: user?.id ?? null }),
      });
      if (expandedProjectId) {
        const tasks = await request<Task[]>(`/projects/${expandedProjectId}/tasks`);
        setProjectTasks((prev) => ({ ...prev, [expandedProjectId]: tasks }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  const unassignTask = async (taskId: number) => {
    try {
      await request(`/tasks/${taskId}/assign`, {
        method: "PATCH",
        body: JSON.stringify({ assignee_id: null }),
      });
      if (expandedProjectId) {
        const tasks = await request<Task[]>(`/projects/${expandedProjectId}/tasks`);
        setProjectTasks((prev) => ({ ...prev, [expandedProjectId]: tasks }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    }
  };

  const createTask = async (projectId: number) => {
    if (!taskTitle.trim()) return;
    try {
      await request(`/projects/${projectId}/tasks`, {
        method: "POST",
        body: JSON.stringify({ title: taskTitle, description: taskDesc }),
      });
      setTaskTitle("");
      setTaskDesc("");
      const tasks = await request<Task[]>(`/projects/${projectId}/tasks`);
      setProjectTasks((prev) => ({ ...prev, [projectId]: tasks }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать задачу");
    }
  };

  const completeTask = async (taskId: number) => {
    try {
      await request(`/tasks/${taskId}/complete`, { method: "PATCH" });
      if (expandedProjectId) {
        const tasks = await request<Task[]>(`/projects/${expandedProjectId}/tasks`);
        setProjectTasks((prev) => ({ ...prev, [expandedProjectId]: tasks }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось завершить задачу");
    }
  };

  if (!user)
    return (
      <main className="auth-page">
        <div className="auth-card">
          <span className="eyebrow">CAOS / MVP 0.1</span>
          <h1>Деятельность начинается с проблемы.</h1>
          <p className="muted">
            Находите общие задачи, формулируйте цели и превращайте их в совместные проекты.
          </p>
          <div className="stepik-login-section">
            <a
              className="stepik-login-btn"
              href={`${API_URL}/auth/stepik`}
            >
              <span className="stepik-icon">S</span>
              Войти через Stepik
            </a>
            <a
              className="google-login-btn"
              href={`${API_URL}/auth/google`}
            >
              <span className="google-icon">G</span>
              Войти через Google
            </a>
          </div>
          <div className="auth-divider"><span>или</span></div>
          <form onSubmit={submitAuth} className="auth-form">
            <h2>{mode === "register" ? "Создать аккаунт" : "Войти"}</h2>
            {mode === "register" && (
              <input
                placeholder="Ваше имя"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                minLength={2}
              />
            )}
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Пароль (минимум 12 символов)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={12}
            />
            {error && <p className="error">{error}</p>}
            <button type="submit" className="primary">
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

  const isCatalog = section === "problems" || section === "goals" || section === "projects";
  const items = section === "problems" ? problems : section === "goals" ? goals : projects;

  return (
    <div className="app-shell">
      <OnboardingTour onComplete={() => {}} />
      <aside>
        <div className="brand">
          <span className="brand-mark">C</span>
          <span>CAOS</span>
        </div>
        <p className="side-caption">Collective Activity Operating System</p>
        <nav>
          {(Object.keys(labels) as Section[]).map((key) => {
            const unreadCount = key === "notifications" ? notifications.filter((n) => !n.is_read).length : 0;
            return (
              <button
                key={key}
                className={section === key ? "active" : ""}
                onClick={() => {
                  goSection(key);
                  setError("");
                }}
              >
                {labels[key]}
                {unreadCount > 0 && <span className="nav-badge">{unreadCount}</span>}
              </button>
            );
          })}
        </nav>
        <button
          className="logout"
          onClick={() => {
            request("/auth/logout", { method: "POST" }).catch(() => {});
            setUser(null);
          }}
        >
          Выйти
        </button>
      </aside>
      <main className="content">
        <header>
          <div>
            <span className="eyebrow">Рабочее пространство</span>
            <h1>{labels[section]}</h1>
          </div>
          <div className="avatar">{user.display_name.slice(0, 1).toUpperCase()}</div>
        </header>

        {section === "overview" && (
          <>
            <section className="hero">
              <div>
                <span className="eyebrow">Главный цикл</span>
                <h2>Положение дел → Проблема → Цель → Действие → Результат</h2>
                <p>Выберите раздел слева или зафиксируйте проблему, чтобы начать коллективный цикл.</p>
              </div>
              <span className="hero-number">01</span>
            </section>

            {nextAction && (
              <section className="panel next-action-panel">
                <div>
                  <span className="eyebrow">Чем помочь сегодня</span>
                  <h2>{nextAction.label}</h2>
                  <p className="muted">{nextAction.reason}</p>
                  <button className="primary" onClick={() => goSection(nextAction.section as Section)}>
                    Перейти →
                  </button>
                </div>
              </section>
            )}

            {user && (
              <OverviewPanel
                goals={goals}
                notifications={notifications}
                auditEvents={auditEvents}
                onOpenGoal={(id) => goGoal(id)}
                onGoSection={(target) => goSection(target)}
              />
            )}

            <div className="grid">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">Активность</span>
                    <h2>Ваше пространство</h2>
                  </div>
                </div>
                <div className="stats">
                  <button onClick={() => goSection("problems")}>
                    <strong>{problems.length}</strong>
                    <span>Проблемы</span>
                  </button>
                  <button onClick={() => goSection("goals")}>
                    <strong>{goals.length}</strong>
                    <span>Цели</span>
                  </button>
                  <button onClick={() => goSection("projects")}>
                    <strong>{projects.length}</strong>
                    <span>Проекты</span>
                  </button>
                </div>
              </section>

              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">Поиск</span>
                    <h2>Найти по ключевому слову</h2>
                  </div>
                </div>
                <form onSubmit={doSearch} className="problem-form">
                  <input
                    placeholder="Введите запрос (минимум 2 символа)"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    required
                    minLength={2}
                  />
                  <button type="submit">Искать</button>
                </form>
                {searchResults && (
                  <div className="search-results">
                    {searchResults.problems.length > 0 && (
                      <>
                        <h3>Проблемы</h3>
                        {searchResults.problems.map((p) => (
                          <article key={p.id}>
                            <div>
                              <h4>{p.title}</h4>
                              <p>{p.description}</p>
                            </div>
                          </article>
                        ))}
                      </>
                    )}
                    {searchResults.goals.length > 0 && (
                      <>
                        <h3>Цели</h3>
                        {searchResults.goals.map((g) => (
                          <article key={g.id}>
                            <div>
                              <h4>{g.title}</h4>
                              <p>{g.description}</p>
                            </div>
                          </article>
                        ))}
                      </>
                    )}
                    {searchResults.projects.length > 0 && (
                      <>
                        <h3>Проекты</h3>
                        {searchResults.projects.map((pr) => (
                          <article key={pr.id}>
                            <div>
                              <h4>{pr.title}</h4>
                              <p>{pr.description}</p>
                            </div>
                          </article>
                        ))}
                      </>
                    )}
                    {searchResults.knowledge.length > 0 && (
                      <>
                        <h3>База знаний</h3>
                        {searchResults.knowledge.map((k) => (
                          <article key={k.id}>
                            <div>
                              <h4>{k.title}</h4>
                              <p>{k.content.slice(0, 120)}</p>
                            </div>
                          </article>
                        ))}
                      </>
                    )}
                    {searchResults.decisions.length > 0 && (
                      <>
                        <h3>Решения</h3>
                        {searchResults.decisions.map((d) => (
                          <article key={d.id}>
                            <div>
                              <h4>{d.title}</h4>
                              <p>{d.proposal.slice(0, 120)}</p>
                            </div>
                          </article>
                        ))}
                      </>
                    )}
                    {searchResults.problems.length === 0 &&
                      searchResults.goals.length === 0 &&
                      searchResults.projects.length === 0 &&
                      searchResults.knowledge.length === 0 &&
                      searchResults.decisions.length === 0 && <p className="muted">Ничего не найдено.</p>}
                  </div>
                )}
                {error && <p className="error">{error}</p>}
              </section>

              <section className="panel">
                <span className="eyebrow">Следующий шаг</span>
                <h2>Начните с проблемы</h2>
                <p className="muted">
                  Проблема помогает найти общую задачу, сформулировать цель и объединить людей вокруг проекта.
                </p>
                <button className="primary" onClick={() => goSection("problems")}>
                  Зафиксировать проблему
                </button>
              </section>

              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">AI</span>
                    <h2>AI-ассистент</h2>
                  </div>
                </div>
                {aiStatus ? (
                  aiStatus.llm_available ? (
                    <p>LLM подключён: <strong>{aiStatus.model}</strong></p>
                  ) : (
                    <p className="muted">LLM не настроен. AI-эндпоинты работают в режиме заглушек. Добавьте AI_API_KEY в .env для подключения.</p>
                  )
                ) : (
                  <p className="muted">Проверка статуса…</p>
                )}
              </section>
            </div>
          </>
        )}

        {section === "activity" && (
        <MyActivity
          onOpenGoal={(id) => {
            goSection("goals");
            goGoal(id);
            setError("");
          }}
        />
      )}
      {section === "goals" && workspaceGoalId !== null && user && (
        <GoalWorkspace
          goalId={workspaceGoalId}
          goals={goals}
          user={user}
          onBack={() => goSection("goals")}
        />
      )}
      {isCatalog && !(section === "goals" && workspaceGoalId !== null) && (
          <div className="catalog-layout">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">
                    {section === "problems" ? "Проблема" : section === "goals" ? "Цель" : "Проект"}
                  </span>
                  <h2>Новая запись</h2>
                </div>
              </div>
              {section === "goals" ? (
                <NewGoalWizard
                  problems={problems}
                  goals={goals}
                  onCreated={(goalId) => goGoal(goalId)}
                  onError={(message) => setError(message)}
                />
              ) : (
                <form onSubmit={createItem} className="problem-form">
                  <input
                    placeholder="Название"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    minLength={3}
                  />
                  <textarea
                    placeholder="Описание"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                  />
                  <button className="primary" type="submit">
                    Создать
                  </button>
                </form>
              )}
              {error && <p className="error">{error}</p>}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Все записи</span>
                  <h2>{labels[section]}</h2>
                </div>
                <span className="count">{items.length}</span>
              </div>
              {items.length === 0 ? (
                <p className="muted empty">Записей пока нет.</p>
              ) : (
                <div className="problem-list">
                  {items.map((item: Problem | Goal | Project) => (
                    <article key={item.id}>
                      <span className="problem-icon">●</span>
                      <div>
                        <h3>{item.title}</h3>
                        <p>{item.description}</p>
                        <small>
                          {item.status} · #{item.id}
                          {"parent_goal_id" in item && item.parent_goal_id && ` · sub-goal of #${item.parent_goal_id}`}
                        </small>
                        {section === "goals" && (
                          <div className="status-buttons" style={{ marginTop: 6 }}>
                            <button className="primary" onClick={() => goGoal(item.id)}>
                              Открыть рабочее пространство
                            </button>
                          </div>
                        )}
                        {section === "goals" && (
                          <div className="ai-section">
                            <div className="ai-buttons">
                              <button className="ai-btn" onClick={() => callAi("decompose", item.id, "декомпозиция")} disabled={aiLoading}>
                                {aiLoading && aiAction === "декомпозиция" ? "..." : "Декомпозиция"}
                              </button>
                              <button className="ai-btn" onClick={() => callAi("similar-goals", item.id, "совпадения")} disabled={aiLoading}>
                                {aiLoading && aiAction === "совпадения" ? "..." : "Совпадения"}
                              </button>
                              <button className="ai-btn" onClick={() => callAi("duplicate-goals", item.id, "дубликаты")} disabled={aiLoading}>
                                {aiLoading && aiAction === "дубликаты" ? "..." : "Дубликаты"}
                              </button>
                              <button className="ai-btn" onClick={() => callAi("missing-competences", item.id, "компетенции")} disabled={aiLoading}>
                                {aiLoading && aiAction === "компетенции" ? "..." : "Компетенции"}
                              </button>
                              <button className="ai-btn" onClick={() => callAi("goal-context", item.id, "контекст")} disabled={aiLoading}>
                                {aiLoading && aiAction === "контекст" ? "..." : "Контекст"}
                              </button>
                            </div>
                            {aiRecommendation && aiRecommendation.goalId === item.id && (
                              <div className="ai-recommendation">
                                <div className="ai-rec-header">
                                  <span className="ai-badge">AI · {aiRecommendation.source}</span>
                                  <span className="ai-confidence">{Math.round(aiRecommendation.confidence * 100)}%</span>
                                </div>
                                <p>{aiRecommendation.suggestion}</p>
                              </div>
                            )}
                          </div>
                        )}
                        {section === "projects" && (
                          <div className="status-buttons">
                            {item.status !== "active" && (
                              <button onClick={() => updateProjectStatus(item.id, "active")}>→ Активен</button>
                            )}
                            {item.status !== "completed" && (
                              <button onClick={() => updateProjectStatus(item.id, "completed")}>→ Завершён</button>
                            )}
                            {item.status !== "on_hold" && (
                              <button onClick={() => updateProjectStatus(item.id, "on_hold")}>→ На паузе</button>
                            )}
                          </div>
                        )}
                        {section === "projects" && (
                          <div className="project-meta">
                            <small className="knowledge-badge">
                              {"knowledge_count" in item ? item.knowledge_count : 0} в базе знаний
                            </small>
                            <button className="link-button" onClick={() => loadProjectTasks(item.id)}>
                              {expandedProjectId === item.id ? "Скрыть задачи" : "Показать задачи"}
                            </button>
                          </div>
                        )}
                        {section === "projects" && expandedProjectId === item.id && (
                          <div className="task-list">
                            {(projectTasks[item.id] || []).length === 0 ? (
                              <p className="muted">Задач пока нет.</p>
                            ) : (
                              projectTasks[item.id].map((t) => (
                                <div key={t.id} className="task-item">
                                  <span className={`task-status ${t.status}`}>{t.status === "done" ? "✓" : "○"}</span>
                                  <div>
                                    <strong>{t.title}</strong>
                                    {t.description && <p className="muted">{t.description}</p>}
                                    <small>
                                      {t.assignee_name ? `@${t.assignee_name}` : "не назначен"}
                                      {t.status === "done" && " · выполнена"}
                                    </small>
                                  </div>
                                  {t.status !== "done" && (
                                    <div className="task-actions">
                                      {t.assignee_id ? (
                                        <button className="link-button" onClick={() => unassignTask(t.id)}>Снять</button>
                                      ) : (
                                        <button className="link-button" onClick={() => assignTaskToSelf(t.id)}>Взять себе</button>
                                      )}
                                      <button className="link-button" onClick={() => completeTask(t.id)}>✓ Завершить</button>
                                    </div>
                                  )}
                                </div>
                              ))
                            )}
                            <div className="task-create-form">
                              <input
                                placeholder="Новая задача…"
                                value={taskTitle}
                                onChange={(e) => setTaskTitle(e.target.value)}
                                minLength={3}
                              />
                              <input
                                placeholder="Описание (необязательно)"
                                value={taskDesc}
                                onChange={(e) => setTaskDesc(e.target.value)}
                              />
                              <button className="primary" onClick={() => createTask(item.id)}>
                                + Добавить задачу
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {section === "teams" && (
          <div className="catalog-layout">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Команда</span>
                  <h2>Новая команда</h2>
                </div>
              </div>
              <form onSubmit={createTeam} className="problem-form">
                <input
                  placeholder="Название команды"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  minLength={2}
                />
                <textarea
                  placeholder="Описание"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
                <button className="primary" type="submit">
                  Создать команду
                </button>
              </form>
              {error && <p className="error">{error}</p>}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Ваши команды</span>
                  <h2>Команды</h2>
                </div>
                <span className="count">{teams.length}</span>
              </div>
              {teams.length === 0 ? (
                <p className="muted empty">Создайте первую команду для совместной работы.</p>
              ) : (
                <div className="problem-list">
                  {teams.map((team) => (
                    <article key={team.id}>
                      <span className="problem-icon">✦</span>
                      <div>
                        <h3>{team.name}</h3>
                        <p>{team.description || "Описание пока не добавлено."}</p>
                        <small>Команда · #{team.id}</small>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {section === "decisions" && (
          <div className="catalog-layout">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Goal Alignment</span>
                  <h2>Новое предложение</h2>
                </div>
              </div>
              <form onSubmit={createDecision} className="problem-form">
                <input
                  placeholder="Название решения"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  minLength={3}
                />
                <textarea
                  placeholder="Предложение и основания"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />
                <select value={decisionGoalId} onChange={(e) => setDecisionGoalId(e.target.value)}>
                  <option value="">Без привязки к цели</option>
                  {goals.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.title}
                    </option>
                  ))}
                </select>
                <select value={decisionMethod} onChange={(e) => setDecisionMethod(e.target.value)}>
                  <option value="majority">Большинство</option>
                  <option value="supermajority">Супербольшинство (2/3)</option>
                  <option value="unanimity">Единогласие</option>
                  <option value="consent">Консент (без возражений)</option>
                </select>
                <button className="primary" type="submit">
                  Предложить решение
                </button>
              </form>
              {error && <p className="error">{error}</p>}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">История согласования</span>
                  <h2>Решения</h2>
                </div>
                <span className="count">{decisions.length}</span>
              </div>
              {decisions.length === 0 ? (
                <p className="muted empty">Предложений пока нет.</p>
              ) : (
                <div className="problem-list">
                  {decisions.map((decision) => (
                    <article
                      key={decision.id}
                      className={selectedDecisionId === decision.id ? "selected" : ""}
                      onClick={() => loadDecisionEvents(decision.id)}
                    >
                      <span className="problem-icon">→</span>
                      <div>
                        <h3>{decision.title}</h3>
                        <p>{decision.proposal}</p>
                        <small>
                          {decision.status} · #{decision.id}
                        </small>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              {selectedDecisionId && decisions.find((d) => d.id === selectedDecisionId) && user && (
                <DecisionProcess
                  decision={decisions.find((d) => d.id === selectedDecisionId)!}
                  user={user}
                  onReload={loadData}
                />
              )}
              {selectedDecisionId && decisionEvents.length > 0 && (
                <div className="decision-events inline-events">
                  <h3>События решения #{selectedDecisionId}</h3>
                  <div className="event-timeline">
                    {decisionEvents.map((ev) => (
                      <div key={ev.id} className={`event-timeline-item event-type-${ev.event_type}`}>
                        <span className="event-type-badge">{ev.event_type}</span>
                        <p>{ev.content}</p>
                        <small>{new Date(ev.created_at).toLocaleString("ru-RU")}</small>
                      </div>
                    ))}
                  </div>
                  <div className="event-actions">
                    <textarea
                      placeholder="Комментарий к событию"
                      value={eventContent}
                      onChange={(e) => setEventContent(e.target.value)}
                    />
                    <div className="event-buttons">
                      <button onClick={() => addDecisionEvent("accepted")}>Принять</button>
                      <button onClick={() => addDecisionEvent("rejected")}>Отклонить</button>
                      <button onClick={() => addDecisionEvent("revised")}>Пересмотреть</button>
                      <button onClick={() => addDecisionEvent("comment")}>Комментарий</button>
                    </div>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {section === "knowledge" && (
          <KnowledgeSection
            knowledge={knowledge}
            projects={projects}
            goals={goals}
            onReload={loadData}
            onError={(message) => setError(message)}
          />
        )}

        {section === "profile" && user && (
          <ProfileSection
            user={user}
            stepikCourses={stepikCourses}
            onUpdated={(updated) => setUser(updated)}
            onError={(message) => setError(message)}
          />
        )}

        {section === "audit" && (
          <div className="catalog-layout">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Audit trail</span>
                  <h2>Журнал действий</h2>
                </div>
                <span className="count">{auditEvents.length}</span>
              </div>
              {auditEvents.length === 0 ? (
                <p className="muted empty">Записей в журнале пока нет.</p>
              ) : (
                <div className="problem-list">
                  {auditEvents.map((ev) => (
                    <article key={ev.id} className="audit-entry">
                      <span className="problem-icon">◇</span>
                      <div>
                        <h3>{ev.action}</h3>
                        <p>{ev.detail}</p>
                        <small>
                          {ev.entity_type} #{ev.entity_id} · {new Date(ev.created_at).toLocaleString("ru-RU")}
                        </small>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {section === "competences" && (
          <div className="catalog-layout">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Навыки</span>
                  <h2>Добавить компетенцию</h2>
                </div>
              </div>
              <form onSubmit={createCompetence} className="problem-form">
                <input
                  placeholder="Название (например, фасилитация)"
                  value={compName}
                  onChange={(e) => setCompName(e.target.value)}
                  required
                  minLength={2}
                />
                <select value={compLevel} onChange={(e) => setCompLevel(Number(e.target.value))}>
                  <option value={1}>Уровень 1 — новичок</option>
                  <option value={2}>Уровень 2 — базовый</option>
                  <option value={3}>Уровень 3 — уверенный</option>
                  <option value={4}>Уровень 4 — продвинутый</option>
                  <option value={5}>Уровень 5 — эксперт</option>
                </select>
                <textarea
                  placeholder="Описание (контекст, опыт применения)"
                  value={compDesc}
                  onChange={(e) => setCompDesc(e.target.value)}
                />
                <button className="primary" type="submit">
                  Добавить
                </button>
              </form>
              {error && <p className="error">{error}</p>}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Ваши навыки</span>
                  <h2>Компетенции</h2>
                </div>
                <span className="count">{competences.length}</span>
              </div>
              {competences.length === 0 ? (
                <p className="muted empty">Добавьте первую компетенцию, чтобы отметить свои навыки.</p>
              ) : (
                <div className="problem-list">
                  {competences.map((c) => (
                    <article key={c.id} className="competence-entry">
                      <span className="problem-icon">★</span>
                      <div>
                        <h3>{c.name}</h3>
                        {c.description && <p>{c.description}</p>}
                        <small>
                          Уровень {c.level}/5 · #{c.id}
                        </small>
                        <button className="link-button" onClick={() => deleteCompetence(c.id)}>
                          Удалить
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
