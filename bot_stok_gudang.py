"""
Bot Telegram Stok Gudang Pabrik
Fitur:
- Catat Barang Masuk (Bal + Pres)
- Catat Barang Keluar (Bal + Pres)
- Lihat Rekap Stok
- Transaksi Terakhir
"""

import logging
import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# KONFIGURASI
# ============================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8935195516:AAFu7ksERLDJEeszN3DHGBrFE8OrEZv98RY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1q6WUYGOjoLQBWq2royMH7BEi63kdBKgG0g-enUg59dA")
SERVICE_ACCOUNT_FILE = os.environ.get("SERVICE_ACCOUNT_FILE", "bot-keuangan-497306-45e4e92ece26.json")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")

# Daftar barang
DAFTAR_BARANG = ["BERLIAN", "JB ICCE", "MARBOL", "GM", "NA", "L300", "R7", "JBR", "KING"]

# Daftar tukang pak
DAFTAR_TUKANG_PAK = ["LULUK", "PUTAT", "YONO"]

# Daftar seles
DAFTAR_SELES = ["RIZAL", "NOR HASAN", "SOL", "DAYAT", "LAINNYA"]

# State untuk ConversationHandler
(MASUK_BARANG, MASUK_BAL, MASUK_PRES, MASUK_TUKANG,
 KELUAR_BARANG, KELUAR_BAL, KELUAR_PRES, KELUAR_SELES) = range(8)

# ============================================
# KONEKSI GOOGLE SHEETS
# ============================================
def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    if GOOGLE_CREDENTIALS_JSON:
        import json
        creds_json = GOOGLE_CREDENTIALS_JSON.replace('\\n', '\n')
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet

def init_headers():
    """Inisialisasi header di semua sheet"""
    try:
        spreadsheet = get_sheet()
        
        # Sheet BARANG MASUK
        sheet_masuk = spreadsheet.worksheet("BARANG MASUK")
        if sheet_masuk.row_values(1) == []:
            sheet_masuk.update('A1:E1', [["TANGGAL", "BARANG", "MASUK (Bal)", "PRES (Slop)", "TUKANG PAK"]])
        
        # Sheet BARANG KELUAR
        sheet_keluar = spreadsheet.worksheet("BARANG KELUAR")
        if sheet_keluar.row_values(1) == []:
            sheet_keluar.update('A1:E1', [["TANGGAL", "NAMA BARANG", "KELUAR (Bal)", "PRES (Slop)", "SELES"]])
        
        # Sheet REKAP BARANG
        sheet_rekap = spreadsheet.worksheet("REKAP BARANG")
        if sheet_rekap.row_values(1) == []:
            sheet_rekap.update('A1:E1', [["NAMA BARANG", "SISA PRES", "LULUK", "PUTAT", "YONO"]])
            # Isi nama barang
            for i, barang in enumerate(DAFTAR_BARANG, start=2):
                sheet_rekap.update(f'A{i}', barang)
        
        logging.info("Header berhasil diinisialisasi")
    except Exception as e:
        logging.error(f"Error init headers: {e}")

# ============================================
# KEYBOARD
# ============================================
def main_keyboard():
    keyboard = [
        ["📦 Barang Masuk", "📤 Barang Keluar"],
        ["📊 Rekap Stok", "📋 Transaksi Terakhir"],
        ["❓ Bantuan"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def barang_keyboard():
    rows = []
    for i in range(0, len(DAFTAR_BARANG), 2):
        row = DAFTAR_BARANG[i:i+2]
        rows.append(row)
    rows.append(["❌ Batal"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def tukang_keyboard():
    keyboard = [[t] for t in DAFTAR_TUKANG_PAK]
    keyboard.append(["❌ Batal"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def seles_keyboard():
    keyboard = [[s] for s in DAFTAR_SELES]
    keyboard.append(["❌ Batal"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================
# HANDLERS UTAMA
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bot Stok Gudang Pabrik — Aktif!*\n\n"
        "📦 Catat Barang Masuk\n"
        "📤 Catat Barang Keluar\n"
        "📊 Rekap Stok Terkini\n"
        "📋 Transaksi Terakhir",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ *BANTUAN*\n\n"
        "📦 *Barang Masuk* — Catat barang masuk dari supplier\n"
        "📤 *Barang Keluar* — Catat barang keluar ke seles\n"
        "📊 *Rekap Stok* — Lihat stok semua barang\n"
        "📋 *Transaksi Terakhir* — 10 transaksi terakhir\n\n"
        "Satuan:\n"
        "• 1 Bal = 200 pack = 20 slop\n"
        "• 1 Pres/Slop = 10 pack",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

# ============================================
# BARANG MASUK
# ============================================
async def masuk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 *CATAT BARANG MASUK*\n\nPilih nama barang:",
        parse_mode="Markdown",
        reply_markup=barang_keyboard()
    )
    return MASUK_BARANG

async def masuk_barang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    if text not in DAFTAR_BARANG:
        await update.message.reply_text("⚠️ Pilih barang dari daftar!")
        return MASUK_BARANG
    
    context.user_data['masuk_barang'] = text
    await update.message.reply_text(
        f"Barang: *{text}*\n\nMasukkan jumlah *Bal* (ketik angka, 0 jika tidak ada):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True)
    )
    return MASUK_BAL

async def masuk_bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    try:
        bal = int(text)
        context.user_data['masuk_bal'] = bal
        await update.message.reply_text(
            f"Bal: *{bal}*\n\nMasukkan jumlah *Pres/Slop* (ketik angka, 0 jika tidak ada):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True)
        )
        return MASUK_PRES
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka yang valid!")
        return MASUK_BAL

async def masuk_pres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    try:
        pres = int(text)
        context.user_data['masuk_pres'] = pres
        await update.message.reply_text(
            f"Pres: *{pres}*\n\nPilih *Tukang Pak*:",
            parse_mode="Markdown",
            reply_markup=tukang_keyboard()
        )
        return MASUK_TUKANG
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka yang valid!")
        return MASUK_PRES

async def masuk_tukang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    if text not in DAFTAR_TUKANG_PAK:
        await update.message.reply_text("⚠️ Pilih tukang pak dari daftar!")
        return MASUK_TUKANG
    
    # Simpan ke Google Sheets
    barang = context.user_data['masuk_barang']
    bal = context.user_data['masuk_bal']
    pres = context.user_data['masuk_pres']
    tukang = text
    tanggal = datetime.now().strftime("%d/%m/%Y")
    
    try:
        spreadsheet = get_sheet()
        sheet = spreadsheet.worksheet("BARANG MASUK")
        sheet.append_row([tanggal, barang, bal, pres, tukang])
        
        await update.message.reply_text(
            f"✅ *Barang Masuk Tersimpan!*\n\n"
            f"📅 Tanggal : {tanggal}\n"
            f"📦 Barang  : {barang}\n"
            f"🔢 Masuk   : {bal} Bal\n"
            f"📌 Pres    : {pres} Slop\n"
            f"👷 Tukang  : {tukang}",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal menyimpan: {e}", reply_markup=main_keyboard())
    
    return ConversationHandler.END

# ============================================
# BARANG KELUAR
# ============================================
async def keluar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📤 *CATAT BARANG KELUAR*\n\nPilih nama barang:",
        parse_mode="Markdown",
        reply_markup=barang_keyboard()
    )
    return KELUAR_BARANG

async def keluar_barang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    if text not in DAFTAR_BARANG:
        await update.message.reply_text("⚠️ Pilih barang dari daftar!")
        return KELUAR_BARANG
    
    context.user_data['keluar_barang'] = text
    await update.message.reply_text(
        f"Barang: *{text}*\n\nMasukkan jumlah *Bal* keluar (ketik angka, 0 jika tidak ada):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True)
    )
    return KELUAR_BAL

async def keluar_bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    try:
        bal = int(text)
        context.user_data['keluar_bal'] = bal
        await update.message.reply_text(
            f"Bal: *{bal}*\n\nMasukkan jumlah *Pres/Slop* keluar (ketik angka, 0 jika tidak ada):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True)
        )
        return KELUAR_PRES
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka yang valid!")
        return KELUAR_BAL

async def keluar_pres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    try:
        pres = int(text)
        context.user_data['keluar_pres'] = pres
        await update.message.reply_text(
            f"Pres: *{pres}*\n\nPilih *Seles*:",
            parse_mode="Markdown",
            reply_markup=seles_keyboard()
        )
        return KELUAR_SELES
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka yang valid!")
        return KELUAR_PRES

async def keluar_seles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Batal":
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    if text not in DAFTAR_SELES:
        await update.message.reply_text("⚠️ Pilih seles dari daftar!")
        return KELUAR_SELES
    
    # Simpan ke Google Sheets
    barang = context.user_data['keluar_barang']
    bal = context.user_data['keluar_bal']
    pres = context.user_data['keluar_pres']
    seles = text
    tanggal = datetime.now().strftime("%d/%m/%Y")
    
    try:
        spreadsheet = get_sheet()
        sheet = spreadsheet.worksheet("BARANG KELUAR")
        sheet.append_row([tanggal, barang, bal, pres, seles])
        
        await update.message.reply_text(
            f"✅ *Barang Keluar Tersimpan!*\n\n"
            f"📅 Tanggal : {tanggal}\n"
            f"📦 Barang  : {barang}\n"
            f"🔢 Keluar  : {bal} Bal\n"
            f"📌 Pres    : {pres} Slop\n"
            f"🧑 Seles   : {seles}",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal menyimpan: {e}", reply_markup=main_keyboard())
    
    return ConversationHandler.END

# ============================================
# REKAP STOK
# ============================================
async def rekap_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Memuat rekap stok...")
    
    try:
        spreadsheet = get_sheet()
        sheet_masuk = spreadsheet.worksheet("BARANG MASUK")
        sheet_keluar = spreadsheet.worksheet("BARANG KELUAR")
        
        data_masuk = sheet_masuk.get_all_values()[1:]  # skip header
        data_keluar = sheet_keluar.get_all_values()[1:]  # skip header
        
        # Hitung stok per barang
        stok = {}
        for barang in DAFTAR_BARANG:
            stok[barang] = {'masuk_bal': 0, 'masuk_pres': 0, 'keluar_bal': 0, 'keluar_pres': 0}
        
        for row in data_masuk:
            if len(row) >= 4 and row[1] in stok:
                try:
                    stok[row[1]]['masuk_bal'] += int(row[2]) if row[2] else 0
                    stok[row[1]]['masuk_pres'] += int(row[3]) if row[3] else 0
                except:
                    pass
        
        for row in data_keluar:
            if len(row) >= 4 and row[1] in stok:
                try:
                    stok[row[1]]['keluar_bal'] += int(row[2]) if row[2] else 0
                    stok[row[1]]['keluar_pres'] += int(row[3]) if row[3] else 0
                except:
                    pass
        
        # Format pesan
        msg = "📊 *REKAP STOK GUDANG*\n"
        msg += f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        msg += "─────────────────\n"
        
        for barang in DAFTAR_BARANG:
            s = stok[barang]
            sisa_bal = s['masuk_bal'] - s['keluar_bal']
            sisa_pres = s['masuk_pres'] - s['keluar_pres']
            
            # Konversi pres negatif ke bal
            if sisa_pres < 0:
                kurang_bal = (-sisa_pres + 19) // 20
                sisa_bal -= kurang_bal
                sisa_pres += kurang_bal * 20
            
            if s['masuk_bal'] > 0 or s['masuk_pres'] > 0:
                msg += f"📦 *{barang}*\n"
                msg += f"   Sisa: {sisa_bal} Bal + {sisa_pres} Slop\n"
        
        msg += "─────────────────\n"
        msg += "1 Bal = 20 Slop = 200 Pack"
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal memuat rekap: {e}", reply_markup=main_keyboard())

# ============================================
# TRANSAKSI TERAKHIR
# ============================================
async def transaksi_terakhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Memuat transaksi terakhir...")
    
    try:
        spreadsheet = get_sheet()
        sheet_masuk = spreadsheet.worksheet("BARANG MASUK")
        sheet_keluar = spreadsheet.worksheet("BARANG KELUAR")
        
        data_masuk = sheet_masuk.get_all_values()[1:]
        data_keluar = sheet_keluar.get_all_values()[1:]
        
        msg = "📋 *TRANSAKSI TERAKHIR*\n"
        msg += "─────────────────\n"
        
        # 5 masuk terakhir
        msg += "📦 *Barang Masuk (5 Terakhir):*\n"
        for row in data_masuk[-5:]:
            if len(row) >= 5:
                msg += f"• {row[0]} | {row[1]} | {row[2]}Bal {row[3]}Slop | {row[4]}\n"
        
        msg += "\n📤 *Barang Keluar (5 Terakhir):*\n"
        for row in data_keluar[-5:]:
            if len(row) >= 5:
                msg += f"• {row[0]} | {row[1]} | {row[2]}Bal {row[3]}Slop | {row[4]}\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal memuat transaksi: {e}", reply_markup=main_keyboard())

async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Dibatalkan.", reply_markup=main_keyboard())
    return ConversationHandler.END

# ============================================
# MAIN
# ============================================
def main():
    logging.basicConfig(level=logging.INFO)
    
    # Init headers
    init_headers()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # ConversationHandler Barang Masuk
    conv_masuk = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📦 Barang Masuk"), masuk_start)],
        states={
            MASUK_BARANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, masuk_barang)],
            MASUK_BAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, masuk_bal)],
            MASUK_PRES: [MessageHandler(filters.TEXT & ~filters.COMMAND, masuk_pres)],
            MASUK_TUKANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, masuk_tukang)],
        },
 fallbacks=[CommandHandler("batal", batal), CommandHandler("start", start)]
    )
    # ConversationHandler Barang Keluar
    conv_keluar = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📤 Barang Keluar"), keluar_start)],
        states={
            KELUAR_BARANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, keluar_barang)],
            KELUAR_BAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, keluar_bal)],
            KELUAR_PRES: [MessageHandler(filters.TEXT & ~filters.COMMAND, keluar_pres)],
            KELUAR_SELES: [MessageHandler(filters.TEXT & ~filters.COMMAND, keluar_seles)],
        },
   fallbacks=[CommandHandler("batal", batal), CommandHandler("start", start)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(conv_masuk)
    app.add_handler(conv_keluar)
    app.add_handler(MessageHandler(filters.Regex("📊 Rekap Stok"), rekap_stok))
    app.add_handler(MessageHandler(filters.Regex("📋 Transaksi Terakhir"), transaksi_terakhir))
    app.add_handler(MessageHandler(filters.Regex("❓ Bantuan"), bantuan))
    
    print("🏭 Bot Stok Gudang Pabrik aktif!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
