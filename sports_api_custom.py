"""
Modulo API Sportive - BallDontLie (NBA) + LiveScore (Calcio)
Ottimizzato per le API che hai già
"""

import os
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class SportsAPIManager:
    """
    Gestore per BallDontLie (NBA) e LiveScore (Calcio)
    """
    
    def __init__(self):
        # API Keys dalle variabili d'ambiente
        self.balldontlie_key = os.getenv("BALLDONTLIE_API_KEY", "")
        self.livescore_key = os.getenv("LIVESCORE_API_KEY", "")
        
        # Base URLs
        self.nba_url = "https://api.balldontlie.io/v1"
        self.livescore_url = "https://livescore-api.com/api-client"
        
    def parse_date(self, date_string: str) -> str:
        """Converte data in formato YYYY-MM-DD"""
        try:
            if not date_string:
                return datetime.now().strftime('%Y-%m-%d')
            
            # Da "05/02/2026 02:10" a "2026-02-05"
            if '/' in date_string:
                parts = date_string.split()[0].split('/')
                if len(parts) == 3:
                    return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            
            return datetime.now().strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def normalize_name(self, name: str) -> str:
        """Normalizza nomi per matching"""
        name = name.strip().lower()
        name = re.sub(r'\s+', ' ', name)
        # Rimuovi caratteri speciali
        name = re.sub(r'[^\w\s]', '', name)
        return name
    
    def extract_teams(self, match: str) -> Tuple[str, str]:
        """Estrae le due squadre dalla stringa match"""
        if ' vs ' in match.lower():
            parts = match.lower().split(' vs ')
        elif ' - ' in match:
            parts = match.split(' - ')
        else:
            return "", ""
        
        if len(parts) == 2:
            return self.normalize_name(parts[0]), self.normalize_name(parts[1])
        return "", ""
    
    # ==================== NBA - BALLDONTLIE ====================
    
    def get_nba_player_id(self, player_name: str) -> Optional[int]:
        """Trova ID giocatore NBA da nome"""
        try:
            url = f"{self.nba_url}/players"
            
            headers = {
                "Authorization": self.balldontlie_key
            }
            
            # Cerca per nome
            params = {
                "search": player_name.split()[0]  # Primo nome o cognome
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"BallDontLie error: {response.status_code}")
                return None
            
            data = response.json()
            players = data.get('data', [])
            
            # Cerca match esatto o parziale
            player_lower = self.normalize_name(player_name)
            
            for player in players:
                first = player.get('first_name', '').lower()
                last = player.get('last_name', '').lower()
                full = f"{first} {last}"
                
                # Match trovato
                if player_lower in full or full in player_lower or \
                   last in player_lower or player_lower in last:
                    return player.get('id')
            
            return None
            
        except Exception as e:
            print(f"Errore get_nba_player_id: {e}")
            return None
    
    def get_nba_game_id(self, team1: str, team2: str, date: str) -> Optional[int]:
        """Trova ID partita NBA"""
        try:
            game_date = self.parse_date(date)
            
            url = f"{self.nba_url}/games"
            
            headers = {
                "Authorization": self.balldontlie_key
            }
            
            params = {
                "dates[]": game_date
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            games = data.get('data', [])
            
            # Normalizza team names
            team1_norm = self.normalize_name(team1)
            team2_norm = self.normalize_name(team2)
            
            for game in games:
                home = self.normalize_name(game['home_team']['full_name'])
                away = self.normalize_name(game['visitor_team']['full_name'])
                
                # Match trovato
                if (team1_norm in home or team1_norm in away) and \
                   (team2_norm in home or team2_norm in away):
                    return game.get('id')
            
            return None
            
        except Exception as e:
            print(f"Errore get_nba_game_id: {e}")
            return None
    
    def get_nba_player_stats(self, game_id: int, player_id: int) -> Optional[Dict]:
        """Ottiene stats giocatore NBA in una partita specifica"""
        try:
            url = f"{self.nba_url}/stats"
            
            headers = {
                "Authorization": self.balldontlie_key
            }
            
            params = {
                "game_ids[]": game_id,
                "player_ids[]": player_id
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            stats = data.get('data', [])
            
            if stats and len(stats) > 0:
                return stats[0]
            
            return None
            
        except Exception as e:
            print(f"Errore get_nba_player_stats: {e}")
            return None
    
    def check_nba_player_bet(self, match: str, player_name: str, bet_type: str, date: str) -> Dict:
        """Verifica scommessa giocatore NBA con BallDontLie"""
        
        team1, team2 = self.extract_teams(match)
        
        if not team1 or not team2:
            return {
                'found': False,
                'result': '⏳ Impossibile identificare le squadre',
                'bet_won': None,
                'details': ''
            }
        
        # Trova game ID
        game_id = self.get_nba_game_id(team1, team2, date)
        
        if not game_id:
            return {
                'found': False,
                'result': '⏳ Partita non trovata o non ancora conclusa',
                'bet_won': None,
                'details': 'Verifica che la partita sia terminata'
            }
        
        # Trova player ID
        player_id = self.get_nba_player_id(player_name)
        
        if not player_id:
            return {
                'found': False,
                'result': f'⚠️ Giocatore {player_name} non trovato',
                'bet_won': None,
                'details': 'Controlla il nome del giocatore'
            }
        
        # Ottieni stats
        stats = self.get_nba_player_stats(game_id, player_id)
        
        if not stats:
            return {
                'found': True,
                'result': f'⚠️ Statistiche di {player_name} non disponibili',
                'bet_won': None,
                'details': 'Il giocatore potrebbe non aver giocato'
            }
        
        # Analizza bet type
        over_under, threshold, stat_type = self.parse_nba_bet_type(bet_type)
        
        if not stat_type:
            return {
                'found': True,
                'result': '⚠️ Tipo di scommessa non riconosciuto',
                'bet_won': None,
                'details': f'Bet: {bet_type}'
            }
        
        # Ottieni valore statistica
        stat_value = self.get_stat_value_from_balldontlie(stats, stat_type)
        
        if stat_value is None:
            return {
                'found': True,
                'result': f'⚠️ Statistica {stat_type} non disponibile',
                'bet_won': None,
                'details': ''
            }
        
        # Calcola risultato
        if over_under == 'over':
            bet_won = stat_value > threshold
        else:
            bet_won = stat_value < threshold
        
        stat_name = self.get_stat_display_name(stat_type)
        
        return {
            'found': True,
            'result': f'{player_name}: {stat_value} {stat_name}',
            'bet_won': bet_won,
            'details': f'Soglia: {over_under.upper()} {threshold} | Risultato: {stat_value}'
        }
    
    def parse_nba_bet_type(self, bet_type: str) -> Tuple[str, float, str]:
        """Analizza tipo scommessa NBA"""
        bet_lower = bet_type.lower()
        
        # OVER o UNDER
        over_under = 'over' if 'over' in bet_lower else 'under'
        
        # Estrai threshold
        numbers = re.findall(r'\d+\.?\d*', bet_type)
        threshold = float(numbers[0]) if numbers else 0
        
        # Identifica statistica
        if 'tiri da 3' in bet_lower or 'tiri da tre' in bet_lower or 'three' in bet_lower or '3pt' in bet_lower:
            return over_under, threshold, 'fg3m'
        elif 'punti' in bet_lower or 'points' in bet_lower or 'pts' in bet_lower:
            return over_under, threshold, 'pts'
        elif 'assist' in bet_lower or 'ast' in bet_lower:
            return over_under, threshold, 'ast'
        elif 'rimbalz' in bet_lower or 'rebound' in bet_lower or 'reb' in bet_lower:
            return over_under, threshold, 'reb'
        elif 'stoppat' in bet_lower or 'block' in bet_lower or 'blk' in bet_lower:
            return over_under, threshold, 'blk'
        elif 'rub' in bet_lower or 'steal' in bet_lower or 'stl' in bet_lower:
            return over_under, threshold, 'stl'
        
        return over_under, threshold, None
    
    def get_stat_value_from_balldontlie(self, stats: Dict, stat_type: str) -> Optional[float]:
        """Estrae valore da stats BallDontLie"""
        try:
            # BallDontLie usa questi nomi:
            # pts, ast, reb, fg3m (3-pointers made), blk, stl
            value = stats.get(stat_type)
            
            if value is not None:
                return float(value)
            
            return None
        except:
            return None
    
    def get_stat_display_name(self, stat_type: str) -> str:
        """Nome display statistiche"""
        names = {
            'fg3m': 'tiri da 3',
            'pts': 'punti',
            'ast': 'assist',
            'reb': 'rimbalzi',
            'blk': 'stoppate',
            'stl': 'palle rubate'
        }
        return names.get(stat_type, stat_type)
    
    # ==================== CALCIO - LIVESCORE ====================
    
    def get_football_match(self, team1: str, team2: str, date: str) -> Optional[Dict]:
        """Trova partita calcio su LiveScore"""
        try:
            game_date = self.parse_date(date)
            
            # LiveScore API endpoint (adatta in base alla loro documentazione)
            url = f"{self.livescore_url}/scores/live.json"
            
            params = {
                "key": self.livescore_key,
                "secret": self.livescore_key  # Se richiesto
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"LiveScore error: {response.status_code}")
                return None
            
            data = response.json()
            
            # Cerca la partita (adatta in base alla struttura risposta LiveScore)
            team1_norm = self.normalize_name(team1)
            team2_norm = self.normalize_name(team2)
            
            # Nota: Adatta questa parte alla struttura specifica di LiveScore
            matches = data.get('data', {}).get('match', [])
            
            for match in matches:
                home = self.normalize_name(match.get('home_name', ''))
                away = self.normalize_name(match.get('away_name', ''))
                
                if (team1_norm in home or team1_norm in away) and \
                   (team2_norm in home or team2_norm in away):
                    return match
            
            return None
            
        except Exception as e:
            print(f"Errore LiveScore: {e}")
            return None
    
    def check_football_bet(self, match: str, bet_type: str, date: str) -> Dict:
        """Verifica scommessa calcio con LiveScore"""
        team1, team2 = self.extract_teams(match)
        
        if not team1 or not team2:
            return {
                'found': False,
                'result': '⏳ Impossibile identificare le squadre',
                'bet_won': None
            }
        
        match_data = self.get_football_match(team1, team2, date)
        
        if not match_data:
            return {
                'found': False,
                'result': '⏳ Partita non trovata o non ancora conclusa',
                'bet_won': None
            }
        
        # Controlla se finita
        status = match_data.get('status', '')
        if status not in ['finished', 'FT', '90']:
            return {
                'found': True,
                'result': '⏳ Partita ancora in corso',
                'bet_won': None
            }
        
        # Ottieni risultato
        goals_home = int(match_data.get('home_score', 0))
        goals_away = int(match_data.get('away_score', 0))
        total_goals = goals_home + goals_away
        
        home_team = match_data.get('home_name', team1)
        away_team = match_data.get('away_name', team2)
        
        # Valuta scommessa
        bet_won = self.evaluate_football_bet(bet_type, goals_home, goals_away, total_goals)
        
        return {
            'found': True,
            'result': f'{home_team} {goals_home}-{goals_away} {away_team}',
            'bet_won': bet_won,
            'details': f'Gol totali: {total_goals}'
        }
    
    def evaluate_football_bet(self, bet_type: str, home_goals: int, away_goals: int, total: int) -> Optional[bool]:
        """Valuta scommessa calcio"""
        bet_lower = bet_type.lower()
        
        # 1X2
        if bet_lower in ['1', 'home', 'casa']:
            return home_goals > away_goals
        elif bet_lower in ['x', 'draw', 'pareggio']:
            return home_goals == away_goals
        elif bet_lower in ['2', 'away', 'trasferta']:
            return away_goals > home_goals
        
        # Over/Under
        if 'over' in bet_lower or 'under' in bet_lower:
            numbers = re.findall(r'\d+\.?\d*', bet_type)
            if numbers:
                threshold = float(numbers[0])
                if 'over' in bet_lower:
                    return total > threshold
                else:
                    return total < threshold
        
        # GG/NG
        if 'gg' in bet_lower or 'goal' in bet_lower:
            if 'no' in bet_lower or 'ng' in bet_lower:
                return home_goals == 0 or away_goals == 0
            else:
                return home_goals > 0 and away_goals > 0
        
        return None
    
    # ==================== ROUTER PRINCIPALE ====================
    
    def check_bet(self, sport: str, match: str, bet_type: str, date: str, player: Optional[str] = None) -> Dict:
        """Router principale per tutte le scommesse"""
        sport_lower = sport.lower()
        
        if sport_lower in ['nba', 'basket', 'basketball']:
            if player:
                return self.check_nba_player_bet(match, player, bet_type, date)
            else:
                return {
                    'found': False,
                    'result': '⏳ Scommesse su risultato NBA non ancora supportate',
                    'bet_won': None
                }
        
        elif sport_lower in ['calcio', 'football', 'soccer']:
            return self.check_football_bet(match, bet_type, date)
        
        else:
            return {
                'found': False,
                'result': f'⏳ Sport {sport} non ancora supportato',
                'bet_won': None
            }
