"""
Modulo per integrare API sportive e ottenere risultati automatici.
Questo file mostra come integrare API gratuite per NBA, Calcio e Tennis.
"""

import requests
from datetime import datetime
import re
import os 

class SportsAPIIntegration:
    """
    Integrazione con API sportive gratuite per ottenere risultati.
    """
    
    def __init__(self):
        # API Keys (tutte gratuite)
        self.api_football_key = "TUA_API_KEY_QUI"  # https://www.api-football.com (gratuita)
        self.rapid_api_key = "TUA_RAPID_API_KEY"   # https://rapidapi.com (gratuita)
        
    def parse_nba_teams(self, match_string):
        """Estrae i nomi delle squadre NBA"""
        # Es: "New York Knicks vs Denver Nuggets"
        parts = match_string.split(' vs ')
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return None, None
    
    def get_nba_player_stats(self, player_name, team1, team2, date):
        """
        Ottiene statistiche giocatore NBA.
        Usa API-Basketball (gratuita): https://www.api-football.com/documentation-v3
        """
        try:
            # Formato data per API
            game_date = self.parse_date(date)
            
            # Endpoint API-Basketball (esempio)
            url = "https://v1.basketball.api-sports.io/games"
            headers = {
                'x-rapidapi-host': "v1.basketball.api-sports.io",
                'x-rapidapi-key': self.rapid_api_key
            }
            
            params = {
                'league': '12',  # NBA league ID
                'season': game_date.split('-')[0],  # Anno
                'date': game_date,
                'team': team1  # o team2
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Cerca il giocatore nelle statistiche
                # Questo dipende dalla struttura della risposta API
                for game in data.get('response', []):
                    # Cerca statistiche del giocatore
                    # Es: game['players'][player_name]['threePointsMade']
                    pass
                
                return {
                    'found': True,
                    'player_stats': {},
                    'game_finished': True
                }
            else:
                return {'found': False, 'error': 'API non disponibile'}
                
        except Exception as e:
            return {'found': False, 'error': str(e)}
    
    def check_nba_player_bet(self, player_name, bet_type, match, date):
        """
        Verifica scommessa su giocatore NBA.
        Es: "Landry Shamet OVER 1.5 tiri da 3"
        """
        team1, team2 = self.parse_nba_teams(match)
        
        if not team1 or not team2:
            return {
                'found': False,
                'result': 'Impossibile identificare le squadre',
                'bet_won': None
            }
        
        # Estrai il tipo di statistica e il valore
        over_under = None
        stat_type = None
        threshold = None
        
        # Parse del bet_type
        # Es: "OVER 1.5 tiri da 3" → over, 1.5, three_pointers
        if 'OVER' in bet_type.upper():
            over_under = 'over'
        elif 'UNDER' in bet_type.upper():
            over_under = 'under'
        
        # Estrai il numero
        numbers = re.findall(r'\d+\.?\d*', bet_type)
        if numbers:
            threshold = float(numbers[0])
        
        # Identifica il tipo di statistica
        bet_lower = bet_type.lower()
        if 'tiri da 3' in bet_lower or 'tiri da tre' in bet_lower:
            stat_type = 'three_pointers'
        elif 'punti' in bet_lower or 'points' in bet_lower:
            stat_type = 'points'
        elif 'assist' in bet_lower:
            stat_type = 'assists'
        elif 'rimbalzi' in bet_lower or 'rebounds' in bet_lower:
            stat_type = 'rebounds'
        
        # Ottieni le statistiche
        stats = self.get_nba_player_stats(player_name, team1, team2, date)
        
        if not stats['found']:
            return {
                'found': False,
                'result': '⏳ Partita non ancora conclusa',
                'bet_won': None,
                'details': ''
            }
        
        # Verifica la scommessa
        player_value = stats['player_stats'].get(stat_type, 0)
        
        if over_under == 'over':
            bet_won = player_value > threshold
        else:  # under
            bet_won = player_value < threshold
        
        result_text = f"{player_name}: {player_value} {stat_type}"
        
        return {
            'found': True,
            'result': result_text,
            'bet_won': bet_won,
            'details': f'Soglia: {threshold}, Risultato: {player_value}'
        }
    
    def get_football_match_result(self, match, date):
        """
        Ottiene risultato partita di calcio.
        Usa API-Football: https://www.api-football.com
        """
        try:
            url = "https://v3.football.api-sports.io/fixtures"
            headers = {
                'x-rapidapi-host': "v3.football.api-sports.io",
                'x-rapidapi-key': self.api_football_key
            }
            
            game_date = self.parse_date(date)
            
            params = {
                'date': game_date
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Cerca la partita nei risultati
                for fixture in data.get('response', []):
                    home_team = fixture['teams']['home']['name']
                    away_team = fixture['teams']['away']['name']
                    
                    # Match trovato
                    if home_team in match or away_team in match:
                        goals_home = fixture['goals']['home']
                        goals_away = fixture['goals']['away']
                        
                        return {
                            'found': True,
                            'home_team': home_team,
                            'away_team': away_team,
                            'score_home': goals_home,
                            'score_away': goals_away,
                            'finished': fixture['fixture']['status']['short'] == 'FT'
                        }
                
                return {'found': False}
            
            return {'found': False}
            
        except Exception as e:
            return {'found': False, 'error': str(e)}
    
    def check_football_bet(self, match, bet_type, date):
        """Verifica scommessa sul calcio"""
        result = self.get_football_match_result(match, date)
        
        if not result['found']:
            return {
                'found': False,
                'result': '⏳ Partita non ancora conclusa',
                'bet_won': None
            }
        
        if not result.get('finished'):
            return {
                'found': True,
                'result': '⏳ Partita in corso',
                'bet_won': None
            }
        
        # Analizza il tipo di scommessa
        bet_lower = bet_type.lower()
        score_home = result['score_home']
        score_away = result['score_away']
        total_goals = score_home + score_away
        
        # 1X2
        if '1' in bet_type and 'x' not in bet_lower:
            bet_won = score_home > score_away
        elif '2' in bet_type:
            bet_won = score_away > score_home
        elif 'x' in bet_lower or 'pareggio' in bet_lower:
            bet_won = score_home == score_away
        
        # Over/Under gol
        elif 'over' in bet_lower or 'under' in bet_lower:
            numbers = re.findall(r'\d+\.?\d*', bet_type)
            if numbers:
                threshold = float(numbers[0])
                if 'over' in bet_lower:
                    bet_won = total_goals > threshold
                else:
                    bet_won = total_goals < threshold
        else:
            # Tipo di scommessa non riconosciuto
            return {
                'found': True,
                'result': f'{result["home_team"]} {score_home}-{score_away} {result["away_team"]}',
                'bet_won': None,
                'details': 'Tipo di scommessa non riconosciuto automaticamente'
            }
        
        return {
            'found': True,
            'result': f'{result["home_team"]} {score_home}-{score_away} {result["away_team"]}',
            'bet_won': bet_won,
            'details': f'Gol totali: {total_goals}'
        }
    
    def get_tennis_match_result(self, match, date):
        """Ottiene risultato partita tennis"""
        # Implementazione simile con API Tennis
        # Es: https://rapidapi.com/api-sports/api/api-tennis
        return {
            'found': False,
            'result': '⏳ API Tennis non ancora integrata'
        }
    
    def parse_date(self, date_string):
        """Converte data in formato API (YYYY-MM-DD)"""
        try:
            # Da "05/02/2026 02:10" a "2026-02-05"
            if '/' in date_string:
                parts = date_string.split()[0].split('/')
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return date_string
        except:
            return datetime.now().strftime('%Y-%m-%d')


# ============================================
# ISTRUZIONI PER INTEGRARE NEL BOT PRINCIPALE
# ============================================

"""
1. Ottieni le API keys gratuite:
   - API-Football: https://www.api-football.com (registrazione gratuita)
   - RapidAPI: https://rapidapi.com (account gratuito)

2. Nel file betting_bot_complete.py, importa questo modulo:
   
   from sports_api import SportsAPIIntegration
   
3. Inizializza nel BettingAnalyzer:
   
   self.api = SportsAPIIntegration()
   
4. Modifica i metodi search_match_result_xxx per usare le API:

   def search_match_result_nba(self, match, player=None, bet_type="", date=""):
       if player:
           return self.api.check_nba_player_bet(player, bet_type, match, date)
       else:
           # Scommessa sul risultato
           return self.api.get_nba_match_result(match, date)
   
   def search_match_result_football(self, match, bet_type, date):
       return self.api.check_football_bet(match, bet_type, date)

5. Le API gratuite hanno limiti:
   - API-Football: 100 richieste/giorno (gratuita)
   - RapidAPI Sports: varia per API (solitamente 100-500/giorno)
   
   Perfetto per uso personale!
"""
