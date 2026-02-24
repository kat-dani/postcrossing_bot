import requests
import os
import time
import re

VK_TOKEN = os.getenv("VK_TOKEN")
USER_ID = os.getenv("USER_ID")
API_VERSION = "5.199"

KEYWORD = "пост обмена"
SENT_FILE = "sent_posts.txt"


def load_groups():
    with open("groups.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_sent_posts():
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)


def save_sent_posts(sent_posts):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        for post_id in sent_posts:
            f.write(post_id + "\n")


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)  # убираем лишние пробелы
    return text.strip()


def contains_keyword(text):
    normalized = normalize_text(text)
    return KEYWORD in normalized


def get_posts(group):
    url = "https://api.vk.com/method/wall.get"
    params = {
        "access_token": VK_TOKEN,
        "v": API_VERSION,
        "domain": group,
        "count": 5
    }
    response = requests.get(url, params=params).json()
    return response.get("response", {}).get("items", [])


def send_message(text):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "v": API_VERSION,
        "user_id": USER_ID,
        "random_id": int(time.time()),
        "message": text
    }
    requests.get(url, params=params)


def main():
    groups = load_groups()
    sent_posts = load_sent_posts()
    updated = False

    for group in groups:
        posts = get_posts(group)

        for post in posts:
            post_global_id = f"{post['owner_id']}_{post['id']}"
            text = post.get("text", "")

            if contains_keyword(text) and post_global_id not in sent_posts:
                link = f"https://vk.com/wall{post_global_id}"
                send_message(f"Найден пост обмена:\n{link}")

                sent_posts.add(post_global_id)
                updated = True

    if updated:
        save_sent_posts(sent_posts)


if __name__ == "__main__":
    main()
