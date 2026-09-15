"""seats.aero を使ったヨーロッパ特典航空券アラート。

seats.aero の Partner API (要 Pro プラン) を叩いて、羽田・成田から
ヨーロッパ主要都市（ヘルシンキ・コペンハーゲン・ロンドンほか）行きの
マイル特典航空券（ビジネス・ファースト）を横断検索し、お得な空席が
見つかったら LINE に push 通知する。

必要な環境変数
--------------
SEATS_AERO_API_KEY        seats.aero の Partner API キー（Pro プラン必須）
SEATS_AERO_ALERT_USER_ID  通知を送る自分の LINE userId
                           （友だち全員への broadcast にしないため必須）

任意の環境変数（未設定ならデフォルト値を使用）
SEATS_AERO_ORIGIN_AIRPORTS  出発空港（カンマ区切り） 例: "HND,NRT"
SEATS_AERO_DEST_AIRPORTS    到着空港（カンマ区切り） 例: "HEL,CPH,LHR"
SEATS_AERO_CABINS           探すクラス（カンマ区切り） 例: "business,first"
SEATS_AERO_MAX_BUSINESS_MILES  ビジネスの上限マイル数（デフォルト 100000）
SEATS_AERO_MAX_FIRST_MILES     ファーストの上限マイル数（デフォルト 150000）
SEATS_AERO_WINDOW_DAYS      何日先まで探すか（デフォルト 300）
SEATS_AERO_STATE_FILE       既知の空席を記録するJSONのパス
"""
import json
import os
import re
from datetime import date, timedelta

import requests
from linebot.models import TextSendMessage

API_BASE = "https://seats.aero/partnerapi"
SEARCH_WINDOW_MAX_DAYS = 60  # seats.aero 側の1リクエストあたりの上限に合わせて分割する

CABIN_CODES = {
    "economy": "Y",
    "premium": "W",
    "business": "J",
    "first": "F",
}

# 目的地は「フィンランド・デンマーク・イギリスなど」ヨーロッパ主要都市をデフォルトに。
DEFAULT_DESTINATIONS = {
    "HEL": "ヘルシンキ（フィンランド）",
    "CPH": "コペンハーゲン（デンマーク）",
    "LHR": "ロンドン（イギリス）",
    "CDG": "パリ（フランス）",
    "AMS": "アムステルダム（オランダ）",
    "FRA": "フランクフルト（ドイツ）",
    "MUC": "ミュンヘン（ドイツ）",
    "ZRH": "チューリッヒ（スイス）",
    "MAD": "マドリード（スペイン）",
    "FCO": "ローマ（イタリア）",
    "VIE": "ウィーン（オーストリア）",
    "ARN": "ストックホルム（スウェーデン）",
    "OSL": "オスロ（ノルウェー）",
}


def _env_list(name, default_list):
    raw = os.environ.get(name)
    if not raw:
        return list(default_list)
    return [v.strip().upper() for v in raw.split(",") if v.strip()]


def _destinations():
    raw = os.environ.get("SEATS_AERO_DEST_AIRPORTS")
    if not raw:
        return dict(DEFAULT_DESTINATIONS)
    return {code.strip().upper(): code.strip().upper()
            for code in raw.split(",") if code.strip()}


ORIGIN_AIRPORTS = _env_list("SEATS_AERO_ORIGIN_AIRPORTS", ["HND", "NRT"])
DESTINATIONS = _destinations()
CABINS = _env_list("SEATS_AERO_CABINS", ["business", "first"])
MAX_MILES = {
    "business": int(os.environ.get("SEATS_AERO_MAX_BUSINESS_MILES", "100000")),
    "first": int(os.environ.get("SEATS_AERO_MAX_FIRST_MILES", "150000")),
}
WINDOW_DAYS = int(os.environ.get("SEATS_AERO_WINDOW_DAYS", "300"))
STATE_FILE = os.environ.get("SEATS_AERO_STATE_FILE", "seats_aero_seen.json")


class SeatsAeroError(Exception):
    pass


def _parse_miles(value):
    if value in (None, ""):
        return 0
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else 0


def _date_windows(window_days):
    """今日から window_days 日先まで、API制限に合わせて分割した (start, end) を返す。"""
    today = date.today()
    end = today + timedelta(days=window_days)
    windows = []
    cur = today
    while cur < end:
        chunk_end = min(cur + timedelta(days=SEARCH_WINDOW_MAX_DAYS - 1), end)
        windows.append((cur.isoformat(), chunk_end.isoformat()))
        cur = chunk_end + timedelta(days=1)
    return windows


def _fetch_page(params, api_key):
    resp = requests.get(
        f"{API_BASE}/search",
        params=params,
        headers={"Partner-Authorization": api_key, "Accept": "application/json"},
        timeout=30,
    )
    if resp.status_code in (401, 403):
        raise SeatsAeroError(
            "seats.aero API 認証に失敗しました。SEATS_AERO_API_KEY と "
            "Pro プランの契約状況を確認してください。"
        )
    resp.raise_for_status()
    return resp.json()


def _fetch_window(start_date, end_date, api_key):
    params = {
        "origin_airport": ",".join(ORIGIN_AIRPORTS),
        "destination_airport": ",".join(DESTINATIONS.keys()),
        "cabin": ",".join(CABINS),
        "start_date": start_date,
        "end_date": end_date,
        "take": 1000,
        "order_by": "lowest_mileage",
    }
    rows = []
    cursor = None
    while True:
        if cursor is not None:
            params["cursor"] = cursor
        payload = _fetch_page(params, api_key)
        rows.extend(payload.get("data", []))
        if not payload.get("hasMore") or payload.get("cursor") in (None, cursor):
            break
        cursor = payload.get("cursor")
    return rows


def _extract_deals(rows):
    deals = []
    for row in rows:
        route = row.get("Route") or {}
        origin = route.get("OriginAirport") or row.get("OriginAirport")
        dest = route.get("DestinationAirport") or row.get("DestinationAirport")
        flight_date = row.get("Date")
        source = row.get("Source", "?")
        for cabin in CABINS:
            code = CABIN_CODES[cabin]
            if not row.get(f"{code}Available"):
                continue
            miles = _parse_miles(row.get(f"{code}MileageCost"))
            if miles <= 0 or miles > MAX_MILES.get(cabin, 0):
                continue
            deals.append({
                "key": f"{origin}|{dest}|{flight_date}|{source}|{code}",
                "origin": origin,
                "dest": dest,
                "dest_label": DESTINATIONS.get(dest, dest),
                "date": flight_date,
                "source": source,
                "cabin": cabin,
                "miles": miles,
                "direct": bool(row.get(f"{code}Direct")),
            })
    deals.sort(key=lambda d: d["miles"])
    return deals


def find_deals(api_key):
    all_deals = []
    for start_date, end_date in _date_windows(WINDOW_DAYS):
        rows = _fetch_window(start_date, end_date, api_key)
        all_deals.extend(_extract_deals(rows))
    return all_deals


def _load_seen():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False)


def _prune_seen(seen):
    today = date.today().isoformat()
    return {k: v for k, v in seen.items() if v.get("date", "9999-99-99") >= today}


MEDALS = ["🥇", "🥈", "🥉"]


def format_message(deals):
    lines = ["✈️ ヨーロッパ特典航空券アラート", ""]
    for i, d in enumerate(deals):
        rank = MEDALS[i] if i < len(MEDALS) else f"{i + 1}位"
        direct = "直行" if d["direct"] else "経由あり"
        lines.append(
            f"{rank} {d['origin']}→{d['dest']}（{d['dest_label']}）"
            f" {d['date']}\n"
            f"　{d['source']} / {d['cabin']} / {d['miles']:,}マイル / {direct}"
        )
    return "\n".join(lines)


def deals_to_messages(deals, page_size=10, max_messages=5):
    """LINE の1回の送信上限（5通）に収まるように TextSendMessage のリストにする。"""
    pages = [deals[i:i + page_size] for i in range(0, len(deals), page_size)]
    return [TextSendMessage(text=format_message(p)) for p in pages[:max_messages]]


def _push_deals(line_bot_api, user_id, deals, page_size=10):
    for i in range(0, len(deals), page_size * 5):
        chunk = deals[i:i + page_size * 5]
        line_bot_api.push_message(user_id, deals_to_messages(chunk, page_size))


def run_alert(line_bot_api):
    """新しく見つかったお得な空席があれば LINE に push する。戻り値は新規件数。"""
    api_key = os.environ.get("SEATS_AERO_API_KEY")
    user_id = os.environ.get("SEATS_AERO_ALERT_USER_ID")
    if not api_key:
        raise SeatsAeroError("SEATS_AERO_API_KEY が設定されていません。")
    if not user_id:
        raise SeatsAeroError("SEATS_AERO_ALERT_USER_ID が設定されていません。")

    deals = find_deals(api_key)
    seen = _prune_seen(_load_seen())

    new_deals = [d for d in deals if d["key"] not in seen]
    if new_deals:
        _push_deals(line_bot_api, user_id, new_deals)
        for d in new_deals:
            seen[d["key"]] = {"date": d["date"]}
        _save_seen(seen)

    return len(new_deals)
