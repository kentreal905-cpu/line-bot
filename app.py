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
    "PwCコンサルティング": "https://docs.google.com/presentation/d/19HQGyT5S00O673_ZLg5ljxr1giCD19ZbPjnds8Zbhqs/edit?usp=drivesdk",
    "三井不動産": "https://docs.google.com/presentation/d/1asUnoECkc34wu3HNfJ-Z7CYBhOKOuWLPd7hYZpb_VRw/edit?usp=drivesdk",
    "日本生命保険": "https://docs.google.com/presentation/d/1hrRt-A351y8WPOsX3XfweTIzh9yKgpTXlEYE7e_BEco/edit?usp=drivesdk",
}

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

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
