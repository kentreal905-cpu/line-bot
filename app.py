from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET", "1e6a5d46d13166cd0277d9e1252efb15")
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN", "ufTFLX4SsJV5y10ZpALAy1p5Lj2NJNL92q3p0IWd9F20tLdiFntfy9eSvDSogk5T6aug0qsc2u9ULeD1DD4LteDpPzfP6xyYEjBS41kzpe6P8+aoVTpgxeRGO0Uy3spU1u7S0Z3wMbPlxwgmndaRBAdB04t89/1O/w1cDnyilFU=")

# 会社名 → GoogleスライドURL
SLIDES = {
    "ソフトバンク": "https://docs.google.com/presentation/d/1TqYwnS9dmQ0UT_4qP4LuGMZH7Ai6_cgVdJhGKdt4kjM/edit?usp=drivesdk",
    "PwCコンサルティング": "https://docs.google.com/presentation/d/1zKZRWIN03wyZU9_TCqnvZlh1glPEbUOCi4zGL5-jSHk/edit?usp=drivesdk",
    "PwC": "https://docs.google.com/presentation/d/1zKZRWIN03wyZU9_TCqnvZlh1glPEbUOCi4zGL5-jSHk/edit?usp=drivesdk",
    "三井不動産": "https://docs.google.com/presentation/d/1asUnoECkc34wu3HNfJ-Z7CYBhOKOuWLPd7hYZpb_VRw/edit?usp=drivesdk",
    "日本生命保険": "https://docs.google.com/presentation/d/1hrRt-A351y8WPOsX3XfweTIzh9yKgpTXlEYE7e_BEco/edit?usp=drivesdk",
    "ニデック": "https://docs.google.com/presentation/d/1bbeNHSdq45Lxyyk8DaYjXS7tsEDZQWgM5SDPfwjR9As/edit?usp=drivesdk",
    "PayPay": "https://docs.google.com/presentation/d/1lkpNlJLE61Ifl-uohmGNW-Em-F0TW07C7CKV2A-Im5s/edit?usp=drivesdk",
    "デロイトトーマツ": "https://docs.google.com/presentation/d/1dhwtNCA4PKHl1FC8_AYgT5je4tFo4lBcfaW4DfMcLeE/edit?usp=drivesdk",
    "三菱電機": "https://docs.google.com/presentation/d/1OtQNI_ow98u9pBD4ZyGfKDSmC7WBmyx7xf1nt-ps7bc/edit?usp=drivesdk",
    "楽天": "https://docs.google.com/presentation/d/1KvnZT8GnUMX0TS1g4wQjBfWrLFXla2L22VfwhBG0vgE/edit?usp=drivesdk",
    "楽天グループ": "https://docs.google.com/presentation/d/1KvnZT8GnUMX0TS1g4wQjBfWrLFXla2L22VfwhBG0vgE/edit?usp=drivesdk",
    "M&A総合研究所": "https://docs.google.com/presentation/d/1uvwJSeDHOwt5WeyxNXXVRx1ktIFCOQKN2DuC-vN84fc/edit?usp=drivesdk",
    "プルデンシャル": "https://docs.google.com/presentation/d/1Cje0fnNYLXAz2UHm5OM_r_I1CUewVDIKxRhzFjh4V9E/edit?usp=drivesdk",
    "プルデンシャル生命": "https://docs.google.com/presentation/d/1Cje0fnNYLXAz2UHm5OM_r_I1CUewVDIKxRhzFjh4V9E/edit?usp=drivesdk",
    "DeNA": "https://docs.google.com/presentation/d/1YI5cKciModIrQNydgiutprVOuMkPRXXtW5KBQF5bmUQ/edit?usp=drivesdk",
    "ベイカレント": "https://docs.google.com/presentation/d/1WQp9gM-cX3BE1n3tl_VpuDhiDA1XlFhNMOBfeG-QCNs/edit?usp=drivesdk",
    "ベイカレントコンサルティング": "https://docs.google.com/presentation/d/1WQp9gM-cX3BE1n3tl_VpuDhiDA1XlFhNMOBfeG-QCNs/edit?usp=drivesdk",
    "サイバーエージェント": "https://docs.google.com/presentation/d/1phWS2r6IZLBOF4ynmTdjUcjEvTpwzbCFCIK-VaWQcAU/edit?usp=drivesdk",
    "任天堂": "https://docs.google.com/presentation/d/1oI3oMci7JACLD8_H9qMTvtSDQDcoxc9urK8IuT-za-0/edit?usp=drivesdk",
    "フジテレビ": "https://docs.google.com/presentation/d/1AlE_XNoFzNlzwKIWRCNo1R1DAbCyt8Myv0DnEAkbHuA/edit?usp=drivesdk",
    "オープンハウス": "https://docs.google.com/presentation/d/1NPnP0ADfNJAFIydsVTkn2lQWl6K8yBoUtKzwaHRaCuI/edit?usp=drivesdk",
    "ANA": "https://docs.google.com/presentation/d/1_J3C4OB839YhIgIVwMzFoB8AUfHHtTbb7jFjNCamgCQ/edit?usp=drivesdk",
    "JAL": "https://docs.google.com/presentation/d/14JwkftTFl18mkI1kBdaXTsnE1NyBfux47zm3rwnaVkA/edit?usp=drivesdk",
    "サントリー": "https://docs.google.com/presentation/d/1nvIYT1A7VV4-5UfbRvV59UfJmWLxj8i1QjKVLxh4SS0/edit?usp=drivesdk",
    "ニトリ": "https://docs.google.com/presentation/d/1VQREcuN6DvkwEDs48j4QlDCIFFpWF_j8U6bBh5cOG-o/edit?usp=drivesdk",
    "資生堂": "https://docs.google.com/presentation/d/1sbn17FI-5o8oAuUTcW9qirJZSfZodvQXxWYiBOHz2BI/edit?usp=drivesdk",
    "伊藤忠商事": "https://docs.google.com/presentation/d/1FC_plmFQtksFuo1dyJzmTD5dKhqkmK69hYvTBiwc2CY/edit?usp=drivesdk",
    "三井住友銀行": "https://docs.google.com/presentation/d/15hr0Tz8qxBD1ofUWOAkM2NFtC7Li3rtVndJP__1oCrw/edit?usp=drivesdk",
    "丸紅": "https://docs.google.com/presentation/d/1BsRc-4fdv7kF8hc3gUyiuoE-UuJ5IxeQGVFHDMPnTlI/edit?usp=drivesdk",
    "トヨタ": "https://docs.google.com/presentation/d/1OTV_5CyXe_fVE1Ad2R3ISOKCHpAYdOEX20Jimno51NQ/edit?usp=drivesdk",
    "トヨタ自動車": "https://docs.google.com/presentation/d/1OTV_5CyXe_fVE1Ad2R3ISOKCHpAYdOEX20Jimno51NQ/edit?usp=drivesdk",
    "みずほ銀行": "https://docs.google.com/presentation/d/14I91ygSfxjzqUQEgqNCGGZ7W5Cn2QZGA4b9Bp1QRB6g/edit?usp=drivesdk",
    "味の素": "https://docs.google.com/presentation/d/1LgcsXwvH6Sk17IDJAjOKKZhQNO1fpS7N0P7dLN5oYhU/edit?usp=drivesdk",
    "ソニー": "https://docs.google.com/presentation/d/15ull55Ng-atp18epttAAhsJ0NlZot2y1edMJrIKpF_s/edit?usp=drivesdk",
    "ソニーグループ": "https://docs.google.com/presentation/d/15ull55Ng-atp18epttAAhsJ0NlZot2y1edMJrIKpF_s/edit?usp=drivesdk",
    "NTTデータ": "https://docs.google.com/presentation/d/1LKibQfAiFAefqhq0WCzNoE9kML-xPLRG75EJh8xUK3E/edit?usp=drivesdk",
    "キーエンス": "https://docs.google.com/presentation/d/1f1RBRptrK4t-77AKTAJmQ5icCw8ze03ERDld8AHcbg8/edit?usp=drivesdk",
    "パナソニック": "https://docs.google.com/presentation/d/1xdVEP-Q2fJAU6L-3PYwi7xIrNh5poYC32XE2f9fXQUQ/edit?usp=drivesdk",
    "東京海上日動": "https://docs.google.com/presentation/d/1t61hlIGjFGfwVhiQRHqnPzH81abbOfwKy9djRCA2C3k/edit?usp=drivesdk",
    "三菱UFJ銀行": "https://docs.google.com/presentation/d/1uCVILEta-EjN4nxr-i9U-4rF2Ael8RUZwInd8Rxd4TQ/edit?usp=drivesdk",
    "アクセンチュア": "https://docs.google.com/presentation/d/1QW9hwGiC0AG-tjBboK32mu3_12vqTaYDRiVQXvaeny0/edit?usp=drivesdk",
    "住友商事": "https://docs.google.com/presentation/d/1sFM-o2XtC84fs_6lPehs9gbiUwigS0yativhShZi9uw/edit?usp=drivesdk",
    "大和ハウス工業": "https://docs.google.com/presentation/d/11dotzh2c1RCtfT2pCeFODYaFkqTyeFStHK1weIKkkIE/edit?usp=drivesdk",
    "大和ハウス": "https://docs.google.com/presentation/d/11dotzh2c1RCtfT2pCeFODYaFkqTyeFStHK1weIKkkIE/edit?usp=drivesdk",
    "第一生命保険": "https://docs.google.com/presentation/d/14NiPRwQ3RTmuk0cvtsl8D1Z1kc9urGXzTMvJGXAy8DY/edit?usp=drivesdk",
    "第一生命": "https://docs.google.com/presentation/d/14NiPRwQ3RTmuk0cvtsl8D1Z1kc9urGXzTMvJGXAy8DY/edit?usp=drivesdk",
    "博報堂": "https://docs.google.com/presentation/d/1jsaCT8PR-3zY92MMgvE0TZeb4uJwXx2izatjQJ9rzSw/edit?usp=drivesdk",
    "三井物産": "https://docs.google.com/presentation/d/18iG6s1O8Ie3MjN-m8Me1gLRXQ0TohcqPJI9ZLQTaF1A/edit?usp=drivesdk",
    "三菱地所": "https://docs.google.com/presentation/d/1h9EC2ZbXDdqq57cWsw0T9wlF5mw_9nxLbZnesT2iJ5s/edit?usp=drivesdk",
}

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    url = SLIDES.get(text)

    if url:
        reply = f"プレゼントはこちらです！\n\n{url}"
    else:
        companies = "\n".join(f"・{c}" for c in SLIDES.keys())
        reply = f"会社名を送ってください。\n\n対応している会社一覧：\n{companies}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run(port=8000)
