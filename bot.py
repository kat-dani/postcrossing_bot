import requests
import os
import time
import re
from datetime import datetime, timedelta

# =======================
# НАСТРОЙКИ
# =======================

VK_SERVICE_TOKEN = os.getenv("VK_SERVICE_TOKEN")
VK_COMMUNITY_TOKEN = os.getenv("VK_COMMUNITY_TOKEN")
USER_ID = os.getenv("USER_ID")

API_VERSION = "5.199"
KEYWORD = "пост обмена"
SENT_FILE = "sent_posts.txt"
DAYS_LIMIT = 31

# =======================
# ВСПОМОГАТЕЛЬНОЕ
# =======================

def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")


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
        for post_id in sorted(sent_posts):
            f.write(post_id + "\n")


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_keyword(text):
    return KEYWORD in normalize_text(text)


def is_recent(post_date):
    post_datetime = datetime.fromtimestamp(post_date)
    limit_date = datetime.now() - timedelta(days=DAYS_LIMIT)
    return post_datetime >= limit_date


# =======================
# VK API
# =======================

def get_group_info(group):
    """Получаем реальное название группы"""
    url = "https://api.vk.com/method/groups.getById"

    params = {
        "access_token": VK_SERVICE_TOKEN,
        "v": API_VERSION
    }

    if group.isdigit():
        params["group_id"] = group
    else:
        params["group_id"] = group

    response = requests.get(url, params=params).json()

    if "error" in response:
        return group  # fallback — используем то, что есть

    return response["response"][0]["name"]


def get_posts(group):
    url = "https://api.vk.com/method/wall.get"

    params = {
        "access_token": VK_SERVICE_TOKEN,
        "v": API_VERSION,
        "count": 10
    }

    if group.isdigit():
        params["owner_id"] = f"-{group}"
    else:
        params["domain"] = group

    response = requests.get(url, params=params).json()

    if "error" in response:
        log(f"❌ Ошибка получения постов из {group}: {response['error']['error_msg']}")
        return None

    return response.get("response", {}).get("items", [])


def send_message(text):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_COMMUNITY_TOKEN,
        "v": API_VERSION,
        "peer_id": USER_ID,
        "random_id": int(time.time()),
        "message": text
    }

    response = requests.get(url, params=params).json()

    if "error" in response:
        log(f"❌ Ошибка отправки сообщения: {response['error']['error_msg']}")
        return False

    return True


# =======================
# ОСНОВНАЯ ЛОГИКА
# =======================

def main():
    start_time = time.time()
    log("🚀 Запуск бота")

    groups = load_groups()
    sent_posts = load_sent_posts()

    total_groups = 0
    error_groups = 0
    sent_count = 0

    for group in groups:
        total_groups += 1
        group_start = time.time()

        log(f"🔍 Проверяем группу: {group}")

        posts = get_posts(group)

        if posts is None:
            error_groups += 1
            continue

        group_name = get_group_info(group)

        posts = sorted(posts, key=lambda x: x["date"])

        for post in posts:
            if not is_recent(post["date"]):
                continue

            post_global_id = f"{post['owner_id']}_{post['id']}"
            text = post.get("text", "")

            if contains_keyword(text) and post_global_id not in sent_posts:
                sent_count += 1
                link = f"https://vk.com/wall{post_global_id}"

                message = (
                    f"📬 Сообщение №{sent_count} \n"
                    f"Группа: {group_name}\n\n"
                    f"{link}"
                )

                if send_message(message):
                    sent_posts.add(post_global_id)
                    time.sleep(0.5)

        group_time = round(time.time() - group_start, 2)
        log(f"⏱ Группа обработана за {group_time} сек")

    if sent_count > 0:
        save_sent_posts(sent_posts)
        log("💾 sent_posts.txt обновлён")

    total_time = round(time.time() - start_time, 2)

    log("========== ОТЧЁТ ==========")
    log(f"Всего групп проверено: {total_groups}")
    log(f"Групп с ошибками: {error_groups}")
    log(f"Новых постов отправлено: {sent_count}")
    log(f"Общее время работы: {total_time} сек")
    log("===========================")


if __name__ == "__main__":
    main()
