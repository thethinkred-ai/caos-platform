"""Russian strings for user-facing backend messages (notifications)."""

GOAL_STATUS = {
    "draft": "черновик", "proposed": "предложена", "under_review": "на рассмотрении",
    "accepted": "принята", "active": "активна", "suspended": "приостановлена",
    "achieved": "достигнута", "verified": "проверена", "closed": "закрыта",
    "rejected": "отклонена", "abandoned": "отменена", "superseded": "заменена",
}

DECISION_EVENT = {
    "proposal": "предложение", "argument": "аргумент", "objection": "возражение",
    "question": "вопрос", "alternative": "альтернатива", "revision": "ревизия",
    "revised": "пересмотрено", "clarification": "уточнение", "evidence": "доказательство",
    "comment": "комментарий", "accepted": "принято", "rejected": "отклонено",
}

PROJECT_STATUS = {
    "planned": "запланирован", "active": "активен", "completed": "завершён", "on_hold": "на паузе",
}

COMMITMENT_STATUS = {
    "open": "взято", "in_progress": "в работе", "fulfilled": "выполнено",
    "failed": "не выполнено", "withdrawn": "снято",
}

RESULT_STATUS = {
    "reported": "сообщён", "under_verification": "на проверке", "verified": "проверен",
    "partially_verified": "частично проверен", "rejected": "отклонён", "disputed": "оспорен",
}


def ru(d: dict, key: str) -> str:
    return d.get(key, key)
