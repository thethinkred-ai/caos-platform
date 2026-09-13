import { FormEvent, useState } from "react";
import { request } from "../api/client";
import type { User } from "../types";

export type StepikCourse = { id: number; title: string; slug: string; url: string; learners_count: number; sections_count: number };

/** Own profile: edit identity fields, see current data, Stepik courses. */
export function ProfileSection({
  user,
  stepikCourses,
  onUpdated,
  onError,
}: {
  user: User;
  stepikCourses: StepikCourse[];
  onUpdated: (user: User) => void;
  onError: (message: string) => void;
}) {
  const [displayName, setDisplayName] = useState(user.display_name);
  const [bio, setBio] = useState(user.bio);
  const [busy, setBusy] = useState(false);

  const patchPrivacy = async (params: { visibility?: string; consent?: boolean }) => {
    setBusy(true);
    try {
      if (params.visibility !== undefined) {
        await request(`/profile/visibility?visibility=${encodeURIComponent(params.visibility)}`, { method: "PATCH" });
      } else if (params.consent !== undefined) {
        await request(`/profile/ai-consent?consent=${params.consent}`, { method: "PATCH" });
      }
      onUpdated(await request<User>("/auth/me"));
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось изменить настройки");
    } finally {
      setBusy(false);
    }
  };

  const updateProfile = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const updated = await request<User>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ display_name: displayName, bio }),
      });
      onUpdated(updated);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось обновить профиль");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="catalog-layout">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Аккаунт</span>
            <h2>Редактировать профиль</h2>
          </div>
        </div>
        <form onSubmit={updateProfile} className="problem-form">
          <input placeholder="Отображаемое имя" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required minLength={2} />
          <textarea placeholder="О себе (био)" value={bio} onChange={(e) => setBio(e.target.value)} />
          <button className="primary" type="submit" disabled={busy}>
            Сохранить
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Текущие данные</span>
            <h2>Профиль</h2>
          </div>
        </div>
        <div className="profile-info">
          <p>
            <strong>Имя:</strong> {user.display_name}
          </p>
          <p>
            <strong>Email:</strong> {user.email}
          </p>
          <p>
            <strong>Био:</strong> {user.bio || "Не заполнено"}
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Приватность</span>
            <h2>Кто видит мой профиль и данные</h2>
          </div>
        </div>
        <div className="problem-form">
          <select
            value={user.profile_visibility}
            onChange={(e) => void patchPrivacy({ visibility: e.target.value })}
          >
            <option value="private">Приватный — только я</option>
            <option value="members">Участники общих проектов</option>
            <option value="public">Публичный</option>
          </select>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={user.ai_consent}
              onChange={(e) => void patchPrivacy({ consent: e.target.checked })}
            />
            <span>Согласие на AI-анализ моих данных (без него AI-рекомендации недоступны)</span>
          </label>
        </div>
      </section>

      {stepikCourses.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Stepik</span>
              <h2>Наши курсы</h2>
            </div>
          </div>
          <div className="stepik-courses-list">
            {stepikCourses.map((c) => (
              <a key={c.id} className="course-link" href={c.url} target="_blank" rel="noopener">
                <span className="course-icon">{c.slug ? c.slug[0].toUpperCase() : "S"}</span>
                <div>
                  <div>{c.title}</div>
                  <div className="course-meta">
                    {c.learners_count} студентов · {c.sections_count} разделов
                  </div>
                </div>
              </a>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
