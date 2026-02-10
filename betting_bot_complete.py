import os
import json
import re
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from PIL import Image
import io
from sports_api import get_nba_player_id
print("BDL test - player id:", get_nba_player_id("LeBron James"))


# Configurazione
TELEGRAM_TOKEN = "IL_TUO_TOKEN_QUI"  # Sostituisci con il tuo token da @BotFather
GEMINI_API_KEY = "LA_TUA_API_KEY_GEMINI"  # API key gratuita da https://makersuite.google.com/app/apikey

# File per salvare lo storico
HISTORY_FILE = "betting_history.json"

# Configura Gemini per OCR (gratuito, 60 richieste/minuto)
genai.configure(api_key=GEMINI_API_KEY)

class BettingAnalyzer:
    def __init__(self):
        self.history = self.load_history()
    
    def load_history(self):
        """Carica lo storico delle scommesse"""
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"bets": [], "stats_by_sport": {}}
    
    def save_history(self):
        """Salva lo storico"""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def extract_bet_info(self, image_bytes):
        """Estrae informazioni dalla scommessa usando Gemini Vision"""
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Converti bytes in Image PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            prompt = """Analizza questo screenshot di scommessa e restituisci SOLO un JSON valido con questa struttura:
{
    "sport": "NBA" oppure "Calcio" oppure "Tennis" oppure altro sport,
    "match": "Squadra1 vs Squadra2 o Giocatore1 vs Giocatore2",
    "bet_type": "descrizione esatta della scommessa (es: OVER 1.5 tiri da 3, Vincente, Under 2.5 gol, ecc)",
    "player": "nome completo del giocatore se la scommessa riguarda un giocatore specifico, altrimenti null",
    "quota": 1.75,
    "importo": 250.00,
    "vincita_potenziale": 437.50,
    "date": "05/02/2026 02:10"
}

REGOLE:
- Estrai TUTTI i dettagli visibili
- Per le quote usa il punto decimale (es: 1.75 non 1,75)
- Per date usa formato DD/MM/YYYY HH:MM
- Se un campo non è visibile metti null
- Per il calcio scrivi "Calcio" non "Football" o "Soccer"
- Rispondi SOLO con il JSON, niente testo aggiuntivo"""

            response = model.generate_content([prompt, image])
            
            # Estrai il JSON dalla risposta
            text = response.text.strip()
            # Rimuovi eventuali markdown code blocks
            text = re.sub(r'```json\s*|\s*```', '', text).strip()
            
            bet_info = json.loads(text)
            return bet_info
            
        except Exception as e:
            print(f"Errore nell'estrazione: {e}")
            return None
    
    def search_match_result_nba(self, match, player=None, bet_type="", date=""):
        """Cerca risultati NBA usando ricerca web simulata"""
        # Questa funzione sarà implementata con vere API o web scraping
        # Per ora ritorna un placeholder
        
        # Esempio di integrazione con API-Basketball (gratuita)
        # https://www.api-football.com/documentation-v3
        
        return {
            "found": False,
            "result": "⏳ Partita non ancora conclusa o in attesa di verifica",
            "bet_won": None,
            "details": ""
        }
    
    def search_match_result_football(self, match, bet_type, date):
        """Cerca risultati calcio"""
        return {
            "found": False,
            "result": "⏳ Partita non ancora conclusa o in attesa di verifica",
            "bet_won": None,
            "details": ""
        }
    
    def search_match_result_tennis(self, match, bet_type, date):
        """Cerca risultati tennis"""
        return {
            "found": False,
            "result": "⏳ Partita non ancora conclusa o in attesa di verifica",
            "bet_won": None,
            "details": ""
        }
    
    def get_match_result(self, sport, match, date, bet_type, player=None):
        """Router per cercare risultati in base allo sport"""
        sport_lower = sport.lower()
        
        if sport_lower == "nba":
            return self.search_match_result_nba(match, player, bet_type, date)
        elif sport_lower in ["calcio", "football", "soccer"]:
            return self.search_match_result_football(match, bet_type, date)
        elif sport_lower == "tennis":
            return self.search_match_result_tennis(match, bet_type, date)
        else:
            return {
                "found": False,
                "result": f"⏳ Sport {sport} - verifica manuale necessaria",
                "bet_won": None,
                "details": ""
            }
    
    def calculate_profit_loss(self, bet_info, bet_won):
        """Calcola profitto o perdita"""
        if bet_won is None:
            return None
        
        importo = float(bet_info.get('importo', 0))
        vincita = float(bet_info.get('vincita_potenziale', 0))
        
        if bet_won:
            return vincita - importo  # Profitto netto
        else:
            return -importo  # Perdita totale
    
    def add_bet(self, bet_info, result_info):
        """Aggiunge una scommessa allo storico"""
        profit_loss = self.calculate_profit_loss(bet_info, result_info['bet_won'])
        
        bet_record = {
            **bet_info,
            "result": result_info['result'],
            "result_details": result_info.get('details', ''),
            "won": result_info['bet_won'],
            "profit_loss": profit_loss,
            "analyzed_at": datetime.now().isoformat()
        }
        
        self.history["bets"].append(bet_record)
        
        # Aggiorna statistiche per sport
        sport = bet_info['sport']
        if sport not in self.history["stats_by_sport"]:
            self.history["stats_by_sport"][sport] = {
                "total_bets": 0,
                "won": 0,
                "lost": 0,
                "pending": 0,
                "total_profit_loss": 0.0,
                "total_staked": 0.0
            }
        
        stats = self.history["stats_by_sport"][sport]
        stats["total_bets"] += 1
        stats["total_staked"] += float(bet_info['importo'])
        
        if result_info['bet_won'] is True:
            stats["won"] += 1
            stats["total_profit_loss"] += profit_loss
        elif result_info['bet_won'] is False:
            stats["lost"] += 1
            stats["total_profit_loss"] += profit_loss
        else:
            stats["pending"] += 1
        
        self.save_history()
        return bet_record
    
    def get_stats_summary(self):
        """Ritorna un riepilogo delle statistiche"""
        if not self.history["stats_by_sport"]:
            return "Nessuna scommessa analizzata ancora!"
        
        summary = []
        total_profit = 0.0
        total_staked = 0.0
        
        sport_icons = {
            "NBA": "🏀",
            "Calcio": "⚽",
            "Tennis": "🎾",
            "Football": "🏈",
            "Baseball": "⚾",
            "Hockey": "🏒",
            "Basket": "🏀"
        }
        
        for sport, stats in sorted(self.history["stats_by_sport"].items()):
            icon = sport_icons.get(sport, "🎯")
            profit = stats["total_profit_loss"]
            staked = stats["total_staked"]
            total_profit += profit
            total_staked += staked
            
            # Calcola ROI se ci sono scommesse concluse
            concluded = stats["won"] + stats["lost"]
            roi = (profit / staked * 100) if staked > 0 and concluded > 0 else 0
            
            sign = "+" if profit >= 0 else ""
            summary.append(
                f"{icon} *{sport}*: {sign}{profit:.2f}€ "
                f"({stats['won']}V-{stats['lost']}P-{stats['pending']}In corso)"
            )
            if concluded > 0:
                summary.append(f"   ROI: {roi:+.1f}%")
        
        # Totale generale
        summary.append("\n" + "─" * 30)
        sign = "+" if total_profit >= 0 else ""
        total_roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
        summary.append(f"💰 *TOTALE*: {sign}{total_profit:.2f}€")
        summary.append(f"📊 ROI Totale: {total_roi:+.1f}%")
        summary.append(f"💵 Investito: {total_staked:.2f}€")
        
        return "\n".join(summary)


# Inizializza analyzer
analyzer = BettingAnalyzer()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_text = """
🎯 *Bot Analisi Scommesse Sportive*

Benvenuto! Sono il tuo assistente per analizzare le scommesse.

*Come funziona:*
📸 Invia uno screenshot della tua scommessa
🔍 Analizzerò automaticamente tutti i dettagli
✅/❌ Ti dirò se hai vinto o perso
💰 Calcolerò il tuo profitto/perdita

*Comandi disponibili:*
/stats - Visualizza statistiche complete
/reset - Azzera tutto lo storico
/help - Mostra questo messaggio

*Sport supportati:*
🏀 NBA Basketball
⚽ Calcio
🎾 Tennis
...e molti altri!

Invia il tuo primo screenshot per iniziare! 🚀
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    await start(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra statistiche complete"""
    summary = analyzer.get_stats_summary()
    
    header = "📊 *STATISTICHE COMPLETE*\n\n"
    total_bets = sum(s['total_bets'] for s in analyzer.history['stats_by_sport'].values())
    header += f"Scommesse analizzate: {total_bets}\n\n"
    
    await update.message.reply_text(header + summary, parse_mode='Markdown')

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset storico con conferma"""
    total_bets = sum(s['total_bets'] for s in analyzer.history['stats_by_sport'].values())
    
    if total_bets == 0:
        await update.message.reply_text("📊 Lo storico è già vuoto!")
        return
    
    # Salva backup
    backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(analyzer.history, f, ensure_ascii=False, indent=2)
    
    # Reset
    analyzer.history = {"bets": [], "stats_by_sport": {}}
    analyzer.save_history()
    
    await update.message.reply_text(
        f"🗑️ *Storico azzerato!*\n\n"
        f"Backup salvato in: `{backup_file}`\n"
        f"Scommesse cancellate: {total_bets}",
        parse_mode='Markdown'
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce gli screenshot ricevuti"""
    processing_msg = await update.message.reply_text("🔍 Analizzo lo screenshot...")
    
    try:
        # Scarica l'immagine
        photo = update.message.photo[-1]  # Risoluzione più alta
        file = await context.bot.get_file(photo.file_id)
        
        # Download bytes
        image_bytes = await file.download_as_bytearray()
        
        # Estrai info dalla scommessa usando Gemini Vision
        await processing_msg.edit_text("🤖 Leggo i dettagli della scommessa...")
        bet_info = analyzer.extract_bet_info(bytes(image_bytes))
        
        if not bet_info:
            await processing_msg.edit_text(
                "❌ *Errore nella lettura*\n\n"
                "Non riesco a leggere lo screenshot.\n"
                "Assicurati che l'immagine sia:\n"
                "✓ Nitida e ben illuminata\n"
                "✓ Contenga tutti i dettagli della scommessa\n"
                "✓ Non sia ritagliata",
                parse_mode='Markdown'
            )
            return
        
        # Cerca il risultato della partita
        await processing_msg.edit_text("🔎 Cerco il risultato della partita...")
        result_info = analyzer.get_match_result(
            bet_info['sport'],
            bet_info['match'],
            bet_info.get('date', ''),
            bet_info['bet_type'],
            bet_info.get('player')
        )
        
        # Salva nello storico
        bet_record = analyzer.add_bet(bet_info, result_info)
        
        # Prepara risposta dettagliata
        sport_icons = {
            "NBA": "🏀",
            "Calcio": "⚽",
            "Tennis": "🎾",
            "Football": "🏈"
        }
        icon = sport_icons.get(bet_info['sport'], "🎯")
        
        response = f"{icon} *{bet_info['sport'].upper()}*\n\n"
        response += f"⚡ *{bet_info['match']}*\n"
        response += f"📋 {bet_info['bet_type']}\n"
        
        if bet_info.get('player'):
            response += f"👤 Giocatore: {bet_info['player']}\n"
        
        response += f"\n💰 Quota: *{bet_info['quota']}*\n"
        response += f"💵 Puntata: {bet_info['importo']:.2f}€\n"
        response += f"🎯 Vincita pot.: {bet_info['vincita_potenziale']:.2f}€\n"
        
        response += "\n" + "─" * 30 + "\n\n"
        
        # Risultato
        if result_info['bet_won'] is True:
            profit = bet_record['profit_loss']
            response += f"✅ *SCOMMESSA VINTA!*\n"
            response += f"💚 Profitto: +{profit:.2f}€"
        elif result_info['bet_won'] is False:
            loss = bet_record['profit_loss']
            response += f"❌ *Scommessa persa*\n"
            response += f"💔 Perdita: {loss:.2f}€"
        else:
            response += f"⏳ *{result_info['result']}*"
        
        if result_info.get('details'):
            response += f"\n\n📊 {result_info['details']}"
        
        await processing_msg.edit_text(response, parse_mode='Markdown')
        
        # Mostra stats aggiornate dopo 1 secondo
        import asyncio
        await asyncio.sleep(1)
        
        summary = analyzer.get_stats_summary()
        await update.message.reply_text(
            f"📊 *RIEPILOGO AGGIORNATO*\n\n{summary}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = f"❌ *Errore imprevisto*\n\n`{str(e)}`\n\nRiprova o contatta il supporto."
        await processing_msg.edit_text(error_msg, parse_mode='Markdown')
        print(f"Errore completo: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Avvia il bot"""
    print("🚀 Inizializzazione bot...")
    
    # Verifica configurazione
    if TELEGRAM_TOKEN == "IL_TUO_TOKEN_QUI":
        print("❌ ERRORE: Imposta il TELEGRAM_TOKEN nel file!")
        return
    
    if GEMINI_API_KEY == "LA_TUA_API_KEY_GEMINI":
        print("❌ ERRORE: Imposta la GEMINI_API_KEY nel file!")
        print("   Ottienila gratis su: https://makersuite.google.com/app/apikey")
        return
    
    # Crea application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Aggiungi handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Avvia
    print("✅ Bot attivo e in ascolto!")
    print("📱 Invia screenshot su Telegram per iniziare.")
    print("\n🛑 Premi CTRL+C per fermare il bot.\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
