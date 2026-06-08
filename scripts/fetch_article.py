import argparse
import json
from pathlib import Path

import requests

ARTICLE_URL = "https://u.geekbang.org/serv/v1/myclass/article"
INFO_URL = "https://u.geekbang.org/serv/v1/myclass/info"

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


config = load_config()
HEADERS = config["headers"]
COOKIES = config["cookies"]


def fetch_article(class_id: int, article_id: int) -> dict:
    payload = {"class_id": class_id, "article_id": article_id}
    response = requests.post(
        ARTICLE_URL,
        headers=HEADERS,
        cookies=COOKIES,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_info(class_id: int) -> dict:
    payload = {"class_id": class_id}
    response = requests.post(
        INFO_URL,
        headers=HEADERS,
        cookies=COOKIES,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def extract_manuscript_text(data: dict) -> str:
    manuscripts = data.get("data", {}).get("manuscripts") or []
    contents = [m.get("content", "").strip() for m in manuscripts]
    return "\n".join(c for c in contents if c)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch data from Geekbang.")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # get 子命令：获取文章
    get_parser = subparsers.add_parser("get", help="获取文章文稿")
    get_parser.add_argument("--class-id", type=int, default=857, help="class id (default: 857)")
    get_parser.add_argument("article_id", type=int, help="article id to fetch")

    # getinfo 子命令：获取课程详情
    getinfo_parser = subparsers.add_parser("getinfo", help="获取课程详情")
    getinfo_parser.add_argument("--class-id", type=int, default=857, help="class id (default: 857)")

    args = parser.parse_args()

    if args.command == "get":
        data = fetch_article(class_id=args.class_id, article_id=args.article_id)
        text = extract_manuscript_text(data)
        print(text)
    elif args.command == "getinfo":
        data = fetch_info(class_id=args.class_id)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
