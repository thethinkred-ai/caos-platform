import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../api/client";
import type { Goal } from "../types";

type Step = {
  title: string;
  body: string;
  target?: string; // CSS selector of the element to spotlight
  route?: string; // hash to navigate to before showing
  before?: () => Promise<string>; // dynamic route
  centered?: boolean;
  link?: { url: string; title: string };
};

const Z_INDEX_BLOCKER = 9000;
const Z_INDEX_SPOT = 9001;
const Z_INDEX_POPOVER = 9002;

async function firstGoalRoute(): Promise<string> {
  try {
    const goals = await request<Goal[]>("/goals");
    if (goals.length > 0) return `#/goals/${goals[0].id}`;
  } catch {
    /* fall through to the catalog */
  }
  return "#/goals";
}

/** Interactive interface training (mobile-game style): a spotlight
 * highlights the real element, a nearby coach bubble explains what it
 * is for and how to use it, and the tour walks the user through the
 * whole product. */
const STEPS: Step[] = [
  {
    centered: true,
    title: "Обучение интерфейсу",
    body: "Как в игре: подсветим каждый важный элемент и объясним, зачем он нужен и как им пользоваться. займёт пару минут. Esc — выйти в любой момент.",
  },
  {
    target: "[data-tour='nav']",
    route: "#/overview",
    title: "Разделы системы",
    body: "Слева — разделы. «Обзор» — карта вашего дня. «Моя деятельность» — ваши обязательства. «Цели» — ядро системы. Дальше — решения, знания, профиль.",
  },
  {
    target: "[data-tour='ai-proposals']",
    route: "#/overview",
    title: "AI предлагает — вы решаете",
    body: "Каждая AI-рекомендация попадает сюда и ждёт вашего решения: принять или отклонить. AI ничего не меняет в системе сам.",
  },
  {
    target: "[data-tour='my-activity']",
    route: "#/activity",
    title: "Моя деятельность",
    body: "Что вы взяли на себя по всем целям. Кнопки двигают обязательство: «Начать работу» → «Выполнено». Клик по названию цели ведёт в её рабочее пространство.",
  },
  {
    target: "[data-tour='goal-wizard']",
    route: "#/goals",
    title: "Создание цели",
    body: "Не анкета, а три вопроса: что должно измениться → почему важно (связь с проблемой) → как поймём, что получилось (критерий).",
  },
  {
    target: "[data-tour='goal-card']",
    title: "Карточка цели",
    body: "Статус и номер цели. Клик по карточке открывает рабочее пространство — всё о жизни цели в одном месте.",
  },
  {
    target: "[data-tour='goal-header']",
    before: firstGoalRoute,
    title: "Рабочее пространство цели",
    body: "Мы внутри цели. Здесь её статус, участники, обязательства, результаты и история — «мини-организация» вокруг одной цели.",
  },
  {
    target: "[data-tour='goal-lifecycle']",
    title: "Жизненный цикл",
    body: "Статус меняется только этими кнопками: черновик → предложена → принята → активна → достигнута. Перепрыгнуть процедуру нельзя — а цель с участниками принимается только коллективным решением.",
  },
  {
    target: "[data-tour='goal-explain']",
    title: "Обоснование",
    body: "«Почему эта цель существует»: проблема → решения → обязательства → задачи → результаты. Цепочка собирается из реальных данных, а не из памяти.",
  },
  {
    target: "[data-tour='goal-impact']",
    title: "Влияние",
    body: "«Что остановится, если цель провалится»: кто зависит напрямую и транзитивно, кто поддерживает, с кем конфликт. Оценка последствий перед решением.",
  },
  {
    target: "[data-tour='goal-relations']",
    title: "Граф целей",
    body: "Связи между целями: «зависит от», «поддерживает», «конфликтует с»… У каждой связи — обязательное обоснование. Это граф, а не дерево.",
  },
  {
    target: "[data-tour='goal-participation']",
    title: "Участие",
    body: "Люди присоединяются к цели с контекстной ролью: участник, координатор, эксперт… Роль действует только здесь — «временно присоединился к цели», а не «вступил в организацию».",
  },
  {
    target: "[data-tour='goal-commitments']",
    title: "Обязательства",
    body: "Добровольный вклад: «я беру на себя…». Статусы: взято → в работе → выполнено. Задачи привязываются к целям через обязательства — бесхозной работы не бывает.",
  },
  {
    target: "[data-tour='goal-criteria']",
    title: "Критерии и измерения",
    body: "Проверяемость: базовая линия → цель (например, 0 → 6 уроков). Кнопка «Записать измерение» фиксирует динамику — видно движение к цели.",
  },
  {
    target: "[data-tour='goal-results']",
    title: "Результаты",
    body: "Результат — изменение положения дел, а не «задача закрыта». Сообщите факт, прикрепите доказательство. Проверить может только другой участник: свою работу верифицировать нельзя.",
  },
  {
    target: "[data-tour='goal-challenge']",
    title: "Возражения",
    body: "Любой участник может оспорить цель: утверждение + аргумент. Возражение нельзя потерять — владелец обязан ответить резолюцией.",
  },
  {
    target: "[data-tour='goal-delegations']",
    title: "Полномочия",
    body: "Передача власти с гарантиями: только то, чем владеешь, всегда со сроком, отзыв — в один клик. Никаких вечных «замов».",
  },
  {
    target: "[data-tour='goal-activities']",
    title: "Деятельность",
    body: "Не всё — чекбокс: встречи, исследования, обсуждения, внешние действия. У каждой формы свой жизненный цикл.",
  },
  {
    target: "[data-tour='goal-timeline']",
    title: "Хронология",
    body: "Вся история цели в одной ленте: кто присоединился, какие решения приняты, что проверено. Нажмите, чтобы раскрыть.",
  },
  {
    target: "[data-tour='notifications']",
    route: "#/notifications",
    title: "Уведомления",
    body: "Каждое уведомление кликабельно — ведёт туда, где произошло событие. Фильтр «непрочитанные» помогает не потерять важное.",
  },
  {
    target: "[data-tour='privacy']",
    route: "#/profile",
    title: "Приватность",
    body: "Вы управляете, кто видит ваш профиль, и даёте (или нет) согласие на AI-анализ своих данных. По умолчанию — закрыто.",
  },
  {
    centered: true,
    title: "Основное вы знаете",
    body: "Дальше — практика: создайте цель через три вопроса, возьмите обязательство и сообщите первый результат. Обучение можно пройти заново кнопкой в меню.",
    link: { url: "https://thinkred.ru/blog/goal-as-primary-unit.html", title: "Цикл статей о философии CAOS" },
  },
];

export function CoachTour({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [node, setNode] = useState<HTMLElement | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const step = STEPS[Math.min(index, STEPS.length - 1)];
  const isLast = index >= STEPS.length - 1;

  // Resolve the route and wait for the target element.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setNode(null);
    setRect(null);
    void (async () => {
      let hash: string | null = null;
      if (step.before) hash = await step.before();
      else if (step.route) hash = step.route;
      if (hash && window.location.hash !== hash) {
        window.location.hash = hash;
      }
      if (!step.target || step.centered) return;
      const deadline = Date.now() + 5000;
      const timer = window.setInterval(() => {
        if (cancelled) {
          window.clearInterval(timer);
          return;
        }
        const found = document.querySelector(step.target as string) as HTMLElement | null;
        if (found) {
          window.clearInterval(timer);
          found.scrollIntoView({ block: "center", behavior: "smooth" });
          window.setTimeout(() => {
            if (!cancelled) setNode(found);
          }, 400);
        } else if (Date.now() > deadline) {
          window.clearInterval(timer);
        }
      }, 200);
    })();
    return () => {
      cancelled = true;
    };
  }, [index, open, step]);

  // Track the element position while the page scrolls or resizes.
  useEffect(() => {
    if (!node) {
      setRect(null);
      return;
    }
    const measure = () => setRect(node.getBoundingClientRect());
    measure();
    window.addEventListener("scroll", measure, true);
    window.addEventListener("resize", measure);
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => {
      window.removeEventListener("scroll", measure, true);
      window.removeEventListener("resize", measure);
      observer.disconnect();
    };
  }, [node]);

  const finish = useCallback(() => {
    localStorage.setItem("caos_tour_done", "1");
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") finish();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, finish]);

  if (!open) return null;

  const spotlighted = rect !== null && !step.centered && rect.width > 0;
  const pad = 6;

  // Popover placement: below the target when there is room, else above.
  let popoverStyle: React.CSSProperties = {
    position: "fixed",
    left: "50%",
    top: "50%",
    transform: "translate(-50%, -50%)",
    width: "min(360px, calc(100vw - 24px))",
    zIndex: Z_INDEX_POPOVER,
  };
  if (spotlighted && rect) {
    const below = rect.bottom + 16;
    const fitsBelow = below + 190 < window.innerHeight;
    const top = fitsBelow ? below : Math.max(16, rect.top - 200);
    const left = Math.min(Math.max(12, rect.left), Math.max(12, window.innerWidth - 372));
    popoverStyle = { position: "fixed", left, top, width: "min(360px, calc(100vw - 24px))", zIndex: Z_INDEX_POPOVER };
  }

  return (
    <>
      {/* click blocker: the tour locks the interface like a game tutorial */}
      <div
        onClick={(event) => event.stopPropagation()}
        style={{ position: "fixed", inset: 0, zIndex: Z_INDEX_BLOCKER }}
      />
      {spotlighted && rect && (
        <div
          style={{
            position: "fixed",
            left: rect.left - pad,
            top: rect.top - pad,
            width: rect.width + pad * 2,
            height: rect.height + pad * 2,
            borderRadius: 10,
            border: "2px solid var(--primary)",
            boxShadow: "0 0 0 9999px rgba(8, 12, 24, 0.72)",
            zIndex: Z_INDEX_SPOT,
            pointerEvents: "none",
            transition: "all 0.3s ease",
          }}
        />
      )}
      {!spotlighted && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(8, 12, 24, 0.72)", zIndex: Z_INDEX_SPOT }} />
      )}
      <div ref={popoverRef} className="panel" style={{ ...popoverStyle, padding: 16, background: "var(--surface)" }}>
        <span className="eyebrow" style={{ fontSize: "var(--font-meta)" }}>
          Шаг {index + 1} из {STEPS.length}
        </span>
        <h3 style={{ margin: "4px 0 6px", font: "600 18px 'Space Grotesk'" }}>{step.title}</h3>
        <p style={{ margin: 0, fontSize: "var(--font-small)", lineHeight: 1.55 }}>{step.body}</p>
        {step.link && (
          <p style={{ margin: "8px 0 0" }}>
            <a href={step.link.url} target="_blank" rel="noopener">
              {step.link.title} →
            </a>
          </p>
        )}
        <div className="event-buttons" style={{ marginTop: 12, justifyContent: "space-between" }}>
          <button className="link-button" onClick={finish}>
            Пропустить
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            {index > 0 && <button onClick={() => setIndex(index - 1)}>← Назад</button>}
            <button className="primary" onClick={() => (isLast ? finish() : setIndex(index + 1))}>
              {isLast ? "Завершить" : "Далее →"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
