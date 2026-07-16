import { useState, useEffect } from "react";

export interface TipStep {
  id: string;
  title: string;
  body: string;
  highlight?: string;
  articleUrl: string;
  articleTitle: string;
}

export const ONBOARDING_TIPS: TipStep[] = [
  {
    id: "welcome",
    title: "Добро пожаловать в CAOS",
    body: "CAOS — это платформа коллективного целеполагания. Здесь люди объединяются не вокруг организаций, а вокруг целей. Вы присоединяетесь к конкретной цели, а не «вступаете в организацию».",
    articleUrl: "https://thinkred.ru/blog/crisis-of-self-organization.html",
    articleTitle: "Кризис самоорганизации XXI века",
  },
  {
    id: "goal-primary",
    title: "Цель — первичная единица",
    body: "В традиционной организации первичная единица — человек. В CAOS первичная единица — цель. Каждая цель имеет цифровой паспорт: описание, причину возникновения, подцели, участников, критерии достижения и историю решений.",
    highlight: "goals",
    articleUrl: "https://thinkred.ru/blog/goal-as-primary-unit.html",
    articleTitle: "Цель как первичная единица",
  },
  {
    id: "concretization",
    title: "Закон конкретизации",
    body: "Любая цель должна отвечать на вопрос «Что необходимо сделать прямо сейчас?». Если ответа нет — цель слишком абстрактна. Используйте кнопку «Декомпозиция», чтобы AI помог разбить цель на конкретные подзадачи.",
    highlight: "goals",
    articleUrl: "https://thinkred.ru/blog/dialectical-goal-tree.html",
    articleTitle: "Диалектическое дерево целей",
  },
  {
    id: "problems-first",
    title: "Проблема — источник цели",
    body: "Цель не возникает из воздуха. Она появляется как решение конкретной проблемы. Сначала сформулируйте проблему, затем поставьте цель, которая её решает. Раздел «Проблемы» — отправная точка всей работы.",
    highlight: "problems",
    articleUrl: "https://thinkred.ru/blog/dialectical-goal-tree.html",
    articleTitle: "Диалектическое дерево целей",
  },
  {
    id: "graph-not-departments",
    title: "Граф целей вместо отделов",
    body: "В CAOS нет отделов и начальников. Вместо этого — граф связанных целей. Вы можете участвовать в нескольких целях одновременно, в разных ролях. Координатор цели — не начальник, а хранитель процедуры.",
    highlight: "projects",
    articleUrl: "https://thinkred.ru/blog/goal-graph-instead-of-departments.html",
    articleTitle: "Граф целей вместо отделов",
  },
  {
    id: "digital-twin",
    title: "Ваш цифровой двойник",
    body: "Ваш профиль — это цифровой двойник. Заполните компетенции: навыки, уровень владения, описание. Это позволяет AI находить вас как подходящего участника для целей, где нужны ваши умения.",
    highlight: "profile",
    articleUrl: "https://thinkred.ru/blog/digital-twin-membership.html",
    articleTitle: "Цифровой двойник и членство",
  },
  {
    id: "membership",
    title: "Три принципа членства",
    body: "1. Временность — вы участвуете, пока цель актуальна. 2. Множественность — вы можете быть в нескольких целях сразу. 3. Компетентность — вас оценивают по навыкам, а не по статусу.",
    articleUrl: "https://thinkred.ru/blog/digital-twin-membership.html",
    articleTitle: "Цифровой двойник и членство",
  },
  {
    id: "ai-assistant",
    title: "AI-ассистент",
    body: "AI помогает, но не решает за вас. Он может: найти совпадающие цели, выявить дубликаты, предложить декомпозицию, найти недостающие компетенции, восстановить контекст цели. Все предложения AI требуют вашего подтверждения.",
    highlight: "goals",
    articleUrl: "https://thinkred.ru/blog/role-of-ai-in-collective-goal-setting.html",
    articleTitle: "Роль ИИ в коллективном целеполагании",
  },
  {
    id: "knowledge-base",
    title: "База знаний",
    body: "Каждая цель накапливает коллективное знание. Материалы, выводы, решения — всё сохраняется в истории цели. Когда новые участники присоединяются, им не нужно спрашивать «что было до меня» — контекст уже есть.",
    highlight: "knowledge",
    articleUrl: "https://thinkred.ru/blog/goal-graph-instead-of-departments.html",
    articleTitle: "Граф целей вместо отделов",
  },
  {
    id: "scale",
    title: "От кружка к сети",
    body: "CAOS растёт от одного человека до сети в 100 000 участников. Вы начинаете с личных целей, затем объединяетесь с другими в кружок, клуб, практический центр. Граф целей позволяет масштабироваться без бюрократии.",
    articleUrl: "https://thinkred.ru/blog/goal-graph-to-scale.html",
    articleTitle: "Масштабирование: от кружка к сети",
  },
];

interface OnboardingProps {
  onComplete: () => void;
}

export function OnboardingTour({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const tip = ONBOARDING_TIPS[step];
  const isLast = step === ONBOARDING_TIPS.length - 1;

  useEffect(() => {
    const seen = localStorage.getItem("caos_onboarding_done");
    if (seen === "1") {
      setDismissed(true);
    }
  }, []);

  if (dismissed) return null;

  const next = () => {
    if (isLast) {
      localStorage.setItem("caos_onboarding_done", "1");
      onComplete();
    } else {
      setStep(step + 1);
    }
  };

  const skip = () => {
    localStorage.setItem("caos_onboarding_done", "1");
    setDismissed(true);
    onComplete();
  };

  return (
    <>
      <div className="onboarding-overlay" onClick={skip} />
      <div className="onboarding-popover">
        <div className="onboarding-header">
          <span className="onboarding-step">
            {step + 1} / {ONBOARDING_TIPS.length}
          </span>
          <button className="onboarding-skip" onClick={skip}>
            Пропустить
          </button>
        </div>
        <h3>{tip.title}</h3>
        <p>{tip.body}</p>
        <a
          href={tip.articleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="onboarding-article-link"
        >
          📖 {tip.articleTitle}
        </a>
        <div className="onboarding-footer">
          <div className="onboarding-dots">
            {ONBOARDING_TIPS.map((_, i) => (
              <span
                key={i}
                className={`onboarding-dot ${i === step ? "active" : ""}`}
                onClick={() => setStep(i)}
              />
            ))}
          </div>
          <button className="onboarding-next" onClick={next}>
            {isLast ? "Готово" : "Далее →"}
          </button>
        </div>
      </div>
    </>
  );
}
