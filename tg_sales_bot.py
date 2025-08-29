#!/usr/bin/env python3
import json, re, os
from pathlib import Path
from decimal import Decimal, InvalidOperation
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

STATE_FILE = Path("tg_sales_state.json")

# ---------- persistence ----------
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}  # chat_id -> {"total": "0", "history": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")

state = load_state()

def get_chat_state(chat_id: int):
    key = str(chat_id)
    if key not in state:
        state[key] = {"total": "0", "history": []}
    return state[key]

def fmt(d: Decimal) -> str:
    return f"{d:.2f}"

def parse_amount(s: str) -> Decimal | None:
    t = s.strip().replace(",", "")
    m = re.fullmatch(r"([+-]?)(\d+(?:\.\d{1,2})?)", t)
    if not m:
        return None
    try:
        amt = Decimal(m.group(2))
        if m.group(1) == "-":
            amt = -amt
        return amt
    except InvalidOperation:
        return None

# ---------- commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Sales Bot ready.\n"
        "Type +500 / -200 to add or subtract.\n"
        "Commands: total, undo, reset (or /total /undo /reset)."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "• +500 / 250 / -75.50 — add/subtract\n"
        "• total — show running total\n"
        "• undo — remove last entry\n"
        "• reset — clear total\n"
        "Slash commands: /total /undo /reset /help"
    )

async def total_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_chat_state(update.effective_chat.id)
    await update.message.reply_text(f"Total: {fmt(Decimal(s['total']))}")

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_chat_state(update.effective_chat.id)
    s["total"] = "0"
    s["history"] = []
    save_state(state)
    await update.message.reply_text("Total reset to 0.00")

async def undo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_chat_state(update.effective_chat.id)
    if not s["history"]:
        await update.message.reply_text("Nothing to undo.")
        return
    last = Decimal(s["history"].pop())
    new_total = Decimal(s["total"]) - last
    s["total"] = str(new_total)
    save_state(state)
    await update.message.reply_text(f"Undid {fmt(last)} — Total: {fmt(new_total)}")

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().lower()
    if text in ("total",):
        return await total_cmd(update, context)
    if text in ("reset",):
        return await reset_cmd(update, context)
    if text in ("undo",):
        return await undo_cmd(update, context)
    if text in ("help",):
        return await help_cmd(update, context)

    amt = parse_amount(text)
    if amt is None:
        return await update.message.reply_text(
            "Unknown input. Try +500, 250, -75.5 or: total, undo, reset, help."
        )

    s = get_chat_state(update.effective_chat.id)
    new_total = Decimal(s["total"]) + amt
    s["total"] = str(new_total)
    s["history"].append(str(amt))
    save_state(state)
    await update.message.reply_text(f"Added {fmt(amt)} — Total: {fmt(new_total)}")

def main():
    # Put your **new** token here or use the TELEGRAM_TOKEN env var
    TOKEN = "8114199493:AAEdd1wZnJvn2EFxUP4J5nEpQfEILM0kOC8"

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("total", total_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("undo", undo_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("Telegram Sales Bot is running (polling). Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
