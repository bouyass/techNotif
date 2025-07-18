import smtplib
import ssl
import random
import requests
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Charge les variables d’environnement depuis un fichier .env

# === Configuration utilisateur ===
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

SUJETS = [
    "javascript", "typescript", "angular", "react", "vue",
    "machine learning", "AI", "cloud", "microservices",
    ".NET", "C#", "architecture logicielle", "sécurité",
    "DevOps", "CI/CD"
]

# === Fonctions de récupération ===

def get_articles_from_devto():
    res = requests.get("https://dev.to/api/articles?per_page=100")
    if res.status_code != 200:
        return []
    articles = res.json()
    return [
        {
            "title": a["title"],
            "url": a["url"],
            "source": "Dev.to",
            "summary": a.get("description", ""),
            "score": a.get("positive_reactions_count", 0)
        }
        for a in articles
        if any(s.lower() in a["title"].lower() for s in SUJETS) and a.get("positive_reactions_count", 0) >= 30
    ]

def get_articles_from_hackernews():
    res = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    if res.status_code != 200:
        return []
    ids = res.json()[:50]
    articles = []
    for id in ids:
        item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{id}.json").json()
        if not item or "title" not in item or "url" not in item or "score" not in item:
            continue
        if any(s.lower() in item["title"].lower() for s in SUJETS) and item["score"] >= 50:
            articles.append({
                "title": item["title"],
                "url": item["url"],
                "source": "Hacker News",
                "summary": "",
                "score": item["score"]
            })
    return articles

def get_articles_from_reddit():
    headers = {"User-agent": "tech-bot"}
    res = requests.get("https://www.reddit.com/r/programming/top.json?limit=50&t=day", headers=headers)
    if res.status_code != 200:
        return []
    posts = res.json()["data"]["children"]
    return [
        {
            "title": post["data"]["title"],
            "url": "https://reddit.com" + post["data"]["permalink"],
            "source": "Reddit",
            "summary": "",
            "score": post["data"]["ups"]
        }
        for post in posts
        if any(s.lower() in post["data"]["title"].lower() for s in SUJETS) and post["data"]["ups"] >= 50
    ]

# === Email ===

def format_email(article):
    content = f"""
    <h2>{article['title']}</h2>
    <p><strong>Source :</strong> {article['source']}</p>
    <p>{article['summary']}</p>
    <a href="{article['url']}">Lire l'article</a>
    """
    return content

def send_email(subject, html_content):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    part = MIMEText(html_content, "html")
    msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())


LAST_TOPIC_FILE = ".last_topic"

def detect_topic(title):
    for sujet in SUJETS:
        if sujet.lower() in title.lower():
            return sujet.lower()
    return "inconnu"


def load_last_topic():
    if os.path.exists(LAST_TOPIC_FILE):
        with open(LAST_TOPIC_FILE, "r") as f:
            return f.read().strip().lower()
    return None

def save_last_topic(topic):
    with open(LAST_TOPIC_FILE, "w") as f:
        f.write(topic)

# === Main ===

def main():
    print(f"🔍 {datetime.now()} - Recherche de sujets tech populaires...")

    articles = get_articles_from_devto() + get_articles_from_hackernews() + get_articles_from_reddit()

    if not articles:
        print("⚠️ Aucun article trouvé aujourd'hui.")
        return

    random.shuffle(articles) 

    last_topic = load_last_topic()

    filtered = [
        a for a in articles
        if detect_topic(a['title']) != last_topic
    ]

    candidates = filtered if filtered else articles

    top_articles = sorted(candidates, key=lambda a: a["score"], reverse=True)[:5]
    chosen = random.choice(top_articles)

    topic_of_the_day = detect_topic(chosen['title'])
    save_last_topic(topic_of_the_day)

    html = format_email(chosen)
    send_email(f"📰 Sujet tech du jour : {chosen['title']}", html)
    print(f"✅ Article envoyé : {chosen['title']} ({chosen['source']}) - Sujet : {topic_of_the_day}")


    

if __name__ == "__main__":
    main()
