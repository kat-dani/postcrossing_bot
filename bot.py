import requests
import time
import os

VK_TOKEN = os.getenv("VK_TOKEN")
USER_ID = os.getenv("USER_ID")  # Куда отправлять сообщения
API_VERSION = "5.199"

KEYWORD = "пост обмена"
STATE_FILE = "last_checked.txt"


def load_groups():
    with open("groups.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    state = {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            group, post_id = line.strip().split(":")
            state[group] = int(post_id)
    return state


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        for group, post_id in state.items():
            f.write(f"{group}:{post_id}\n")


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
    state = load_state()

    for group in groups:
        print(f"Проверяем {group}")
        posts = get_posts(group)

        if not posts:
            continue

        last_saved = state.get(group, 0)

        for post in posts:
            post_id = post["id"]
            text = post.get("text", "").lower()

            if post_id <= last_saved:
                continue

            if KEYWORD in text:
                link = f"https://vk.com/{group}?w=wall-{post['owner_id']}_{post_id}"
                send_message(f"Найден пост обмена:\n{link}")

        state[group] = max(post["id"] for post in posts)

    save_state(state)


if __name__ == "__main__":
    main()