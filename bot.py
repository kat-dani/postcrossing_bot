import requests
import os
import time
import re
from datetime import datetime, timedelta, timezone

VK_SERVICE_TOKEN = os.getenv("VK_SERVICE_TOKEN")
VK_COMMUNITY_TOKEN = os.getenv("VK_COMMUNITY_TOKEN")
USER_ID = os.getenv("USER_ID")

API_VERSION = "5.199"

UTC_PLUS_5 = timezone(timedelta(hours=5))

SENT_FILE = "sent_posts.txt"
GROUPS_FILE = "groups.txt"

DAYS_LIMIT = 31

KEYWORDS = [
    "пост для обмена",
    "обмен открыт",
    "обмен открыток",
    "открыт обмен",
    "обменный пост",

    "ищу обмен",
    "ищу обмены",
    "кто на обмен",
    "готова к обмену",
    "готов к обмену",

    "обмен в комментариях",
    "обмены в комментариях",
    "обмены под постом",
    "ищите обмены в комментариях",

    "меняюсь",
    "меняюсь на",
    "обменяю",
    "обменяю на",

    "swap"
]

POST_EXCHANGE_REGEX = re.compile(r"пост\w*\s+обмен\w*", re.IGNORECASE)


def log(message):
    now = datetime.now(UTC_PLUS_5).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_keyword(text):

    text_norm = normalize_text(text)

    if POST_EXCHANGE_REGEX.search(text_norm):
        return True

    for word in KEYWORDS:
        if word in text_norm:
            return True

    return False


def load_groups():
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_sent_posts():
    if not os.path.exists(SENT_FILE):
        return set()

    with open(SENT_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)


def save_sent_posts(posts):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        for p in posts:
            f.write(p + "\n")


def is_recent(post_date):

    post_time = datetime.fromtimestamp(post_date)
    limit = datetime.now() - timedelta(days=DAYS_LIMIT)

    return post_time >= limit


def get_posts(group):

    url = "https://api.vk.com/method/wall.get"

    params = {
        "access_token": VK_SERVICE_TOKEN,
        "v": API_VERSION,
        "count": 30
    }

    if group.isdigit():
        params["owner_id"] = f"-{group}"
    else:
        params["domain"] = group

    response = requests.get(url, params=params).json()

    if "error" in response:
        log(f"Ошибка получения постов из {group}: {response['error']}")
        return None

    return response["response"]["items"]


def get_group_name(group):

    url = "https://api.vk.com/method/groups.getById"

    params = {
        "access_token": VK_SERVICE_TOKEN,
        "v": API_VERSION,
        "group_id": group
    }

    response = requests.get(url, params=params).json()

    if "error" in response:
        return group

    data = response.get("response")

    if isinstance(data, dict):
        groups = data.get("groups", [])
        if groups:
            return groups[0].get("name", group)

    if isinstance(data, list):
        if data:
            return data[0].get("name", group)

    return group


def send_message(text):

    url = "https://api.vk.com/method/messages.send"

    params = {
        "access_token": VK_COMMUNITY_TOKEN,
        "v": API_VERSION,
        "peer_id": USER_ID,
        "random_id": int(time.time() * 1000),
        "message": text
    }

    response = requests.get(url, params=params).json()

    if "error" in response:
        log(f"Ошибка отправки: {response['error']}")

    time.sleep(0.4)


def main():

    start_time = time.time()

    log("🚀 Запуск бота")

    groups = load_groups()
    sent_posts = load_sent_posts()

    intro_sent = False

    total_groups = 0
    error_groups = 0
    found_posts = 0

    for group in groups:

        total_groups += 1

        log(f"🔍 Проверяем группу {group}")

        posts = get_posts(group)

        if posts is None:
            error_groups += 1
            continue

        posts = sorted(posts, key=lambda x: x["date"])

        group_name = None

        for post in posts:

            if not is_recent(post["date"]):
                continue

            post_id = f"{post['owner_id']}_{post['id']}"

            if post_id in sent_posts:
                continue

            text = post.get("text", "")

            if contains_keyword(text):

                if group_name is None:
                    group_name = get_group_name(group)

                if not intro_sent:

                    send_message("Привет! Найдены посты обмена")

                    send_message(
                        "Ищу обмен :)\n"
                        "https://vk.com/club228489482?from=groups&w=wall-228489482_1"
                    )

                    intro_sent = True

                found_posts += 1

                link = f"https://vk.com/wall{post_id}"

                message = (
                    f"📬 Сообщение №{found_posts}\n"
                    f"Группа: {group_name}\n"
                    f"{link}"
                )

                send_message(message)

                sent_posts.add(post_id)

        time.sleep(0.5)

    save_sent_posts(sent_posts)

    log("========== ОТЧЕТ ==========")
    log(f"Проверено групп: {total_groups}")
    log(f"Ошибок доступа: {error_groups}")
    log(f"Найдено новых постов: {found_posts}")

    duration = round(time.time() - start_time, 2)

    log(f"⏱ Время работы: {duration} сек")
    log("🏁 Завершение работы")


if __name__ == "__main__":
    main()
