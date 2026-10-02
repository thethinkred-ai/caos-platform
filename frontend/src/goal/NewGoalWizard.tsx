import { FormEvent, useState } from "react";
import { request } from "../api/client";
import { LearningHint } from "../ui/LearningHint";
import type { Goal, Problem } from "../types";

const STEPS = ["Что должно измениться?", "Почему это важно?", "Как поймём, что получилось?"];

/** Progressive goal proposal (critique, sections 66/112): the user answers
 * one question at a time instead of filling a form of technical fields. */
export function NewGoalWizard({
  problems,
  goals,
  onCreated,
  onError,
}: {
  problems: Problem[];
  goals: Goal[];
  onCreated: (goalId: number) => void;
  onError: (message: string) => void;
}) {
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [problemId, setProblemId] = useState("");
  const [parentGoalId, setParentGoalId] = useState("");
  const [criterionName, setCriterionName] = useState("");
  const [criterionTarget, setCriterionTarget] = useState("");
  const [deadline, setDeadline] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (step < STEPS.length - 1) {
      setStep(step + 1);
      return;
    }
    setBusy(true);
    try {
      const goal = await request<Goal>("/goals", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          problem_id: problemId ? Number(problemId) : null,
          parent_goal_id: parentGoalId ? Number(parentGoalId) : null,
          deadline: deadline ? new Date(deadline).toISOString() : null,
        }),
      });
      if (criterionName.trim()) {
        await request(`/goals/${goal.id}/criteria`, {
          method: "POST",
          body: JSON.stringify({ name: criterionName, criterion_type: "quantitative", target_value: criterionTarget }),
        });
      }
      setTitle("");
      setDescription("");
      setProblemId("");
      setParentGoalId("");
      setCriterionName("");
      setCriterionTarget("");
      setDeadline("");
      setStep(0);
      onCreated(goal.id);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось создать цель");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="problem-form" data-tour="goal-wizard">
      <div className="panel-heading" style={{ marginBottom: 8 }}>
        <div>
          <span className="eyebrow">Шаг {step + 1} из {STEPS.length}</span>
          <h2>{STEPS[step]}</h2>
        </div>
      </div>

      {step === 0 && (
        <>
          <input
            placeholder="Например: 100 участников самостоятельно находят цели и присоединяются"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            minLength={3}
            autoFocus
          />
          <textarea
            placeholder="Какое положение дел должно измениться?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
          <LearningHint>
            Цель — не задача и не пожелание, а описание изменения положения дел. «Сделать сайт» — задача;
            «обеспечить 100 участникам доступ к обучению» — цель. Из этой формулировки система дальше
            построит участников, обязательства и проверяемые результаты.
          </LearningHint>
        </>
      )}

      {step === 1 && (
        <>
          <select value={problemId} onChange={(e) => setProblemId(e.target.value)}>
            <option value="">Указать проблему позже</option>
            {problems.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
          <select value={parentGoalId} onChange={(e) => setParentGoalId(e.target.value)}>
            <option value="">Без родительской цели</option>
            {goals.map((g) => (
              <option key={g.id} value={g.id}>
                → {g.title}
              </option>
            ))}
          </select>
          <LearningHint>
            Цель не возникает из воздуха: она вырастает из положения дел, которое вас не устраивает.
            Привязка к проблеме (или родительской цели) — это обоснование, которое потом можно
            проследить в цепочке «Почему эта цель существует».
          </LearningHint>
        </>
      )}

      {step === 2 && (
        <>
          <input
            placeholder="Критерий (например: доля завершивших курс)"
            value={criterionName}
            onChange={(e) => setCriterionName(e.target.value)}
          />
          <input
            placeholder="Целевое значение (78%)"
            value={criterionTarget}
            onChange={(e) => setCriterionTarget(e.target.value)}
          />
          <input
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            title="Срок цели (необязательно)"
          />
          <LearningHint>
            Без проверяемого критерия цель остаётся пожеланием: система не сможет отличить «задачи
            закрыты» от «цель достигнута». Формат: базовое значение → целевое (0 → 6 уроков,
            61% → 78%). Динамику вы будете фиксировать измерениями прямо в рабочем пространстве.
          </LearningHint>
        </>
      )}

      <div className="event-buttons" style={{ marginTop: 8 }}>
        {step > 0 && <button type="button" onClick={() => setStep(step - 1)}>← Назад</button>}
        <button className="primary" type="submit" disabled={busy}>
          {step < STEPS.length - 1 ? "Далее" : busy ? "Создаём…" : "Предложить цель"}
        </button>
      </div>
    </form>
  );
}
