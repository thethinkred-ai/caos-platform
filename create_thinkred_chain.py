import urllib.request, urllib.parse, json, sys

TOKEN = open('/tmp/caos_token').read().strip()
API = "https://api-caos.thinkred.ru/api/v1"
AUTH = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def post(path, data):
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(data).encode(), headers=AUTH, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=15).read())

# Decision
d = post("/decisions", {"title":"Контент-пайплайн ThinkRed","proposal":"Генерация → рецензия → доработка → публикация. Hermes Agent + gbrain + контент-борд. Каналы: сайт, Telegram, VK, YouTube.","goal_id":1})
print(f"Decision #{d['id']}")

# Team
t = post("/teams", {"name":"ThinkRed Contributors","description":"Авторы, редакторы, разработчики. Координация через Telegram и контент-борд."})
print(f"Team #{t['id']}")

# Project
p = post("/projects", {"title":"thinkred.ru — сайт и контент","description":"Сайт с блогом, курсы Stepik, YouTube. Контент-пайплайн, мониторинг, SEO, Telegram/VK.","goal_id":1})
print(f"Project #{p['id']}")

# Tasks
for tname in ["Разработка контент-пайплайна","Написание статей и аналитики","Курсы на Stepik (Гегель, Капитал)","Мониторинг и дайджест новостей","Публикация в Telegram и VK","SEO и продвижение"]:
    tk = post(f"/projects/{p['id']}/tasks", {"title": tname, "description": ""})
    print(f"  Task #{tk['id']}: {tname}")

# Knowledge
k = post("/knowledge", {"title":"Контент-пайплайн ThinkRed","content":"gen → red1 → red2 → rework → prepub → ready. Hermes Agent + gbrain. board.html + reviews-data.json. Каналы: thinkred.ru, @thinkred_marx, vk.com/thinkred_marx","project_id": p['id']})
print(f"Knowledge #{k['id']}")

# Competences
for cname in ["Марксистская теория","Редактура текстов","FastAPI и веб-стек","Linux и VPS","SEO и продвижение","Видеопроизводство"]:
    c = post("/competences", {"name":cname,"level":3,"description":"Компетенция ThinkRed"})
    print(f"  Competence #{c['id']}: {cname}")

print("\n✅ CHAIN: Problem #1 → Goal #1 → Decision → Team → Project → 6 Tasks → Knowledge → 6 Competences")
