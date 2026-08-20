headers = {
  'sec-ch-ua-platform': '"Windows"',
  'Referer': 'https://www.fangraphs.com/players/eury-perez/27768/stats/pitching',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 OPR/133.0.0.0 (Edition std-1)',
  'sec-ch-ua': '"Opera GX";v="133", "Chromium";v="149", "Not)A;Brand";v="24"',
  'sec-ch-ua-mobile': '?0'
}


def getMlbScheduleUrl(dateFrom, dateTo):
    return f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&sportId=21&sportId=51&startDate={dateFrom}&endDate={dateTo}&timeZone=America/New_York&gameType=E&&gameType=S&&gameType=R&&gameType=F&&gameType=D&&gameType=L&&gameType=W&&gameType=A&season=2026&language=en&leagueId=&&leagueId=&&leagueId=103&&leagueId=104&&leagueId=160&&leagueId=426&&leagueId=427&&leagueId=428&&leagueId=429&&leagueId=430&&leagueId=431&&leagueId=432&&leagueId=590&sortBy=gameDate,gameType&hydrate=team,linescore(matchup,runners),xrefId,flags,statusFlags,broadcasts(all),venue(location),decisions,person,probablePitcher,stats,game(content(media(epg),summary),tickets),seriesStatus(useOverride=true)"

fg_PitchersBaseUrl = "https://www.fangraphs.com/_next/data/Srtn7z-JINs_4qWLRn9y2/players/eury-perez/27768/stats/pitching.json?playerNameRoute=eury-perez&playerId=27768"

class Pitcher:
    def __init__(self, firstName, lastName):
        self.fName = firstName
        self.lName = lastName
        self.playerId = getPlayerId(firstName, lastName)
        self.url = f"https://www.fangraphs.com/_next/data/Srtn7z-JINs_4qWLRn9y2/players/{firstName}-{lastName}/{self.playerId}/stats/pitching.json?playerNameRoute={firstName}-{lastName}&playerId={self.playerId}"
  
class Batter:
    def __init__(self, firstName, lastName):
        self.fName = firstName
        self.lName = lastName
        self.playerId = getPlayerId(firstName, lastName)
        self.url = f"https://www.fangraphs.com/_next/data/qzBSEHXDTj0Ut4UbaRB2T/players/{firstName}-{lastName}/{self.playerId}/splits.json?position=NP&playerNameRoute={firstName}-{lastName}&playerId={self.playerId}"
  
class Game:
    def __init__(self, home, away, hPitcher, aPitcher, hLineup, aLineup, gameId, date):
        self.home = home
        self.away = away
        self.hPitcher = hPitcher
        self.aPitcher = aPitcher
        self.hLineup = hLineup
        self.aLineup = aLineup
        self.gameId = gameId
        self.date = date
        
class Market:
    def __init__(self, sport, propName):
        self.sport = sport
        self.propName = propName
        
class Prop:
    def __init__(self, market, line, overOdds, underOdds):
        self.market = market
        self.line = line
        self.overOdds = overOdds
        self.underOdds = underOdds
        
class Bet:
    def __init__(self, prop, ou, betAmount, result):
        self.prop = prop
        self.ou = ou
        self.betAmount = betAmount
        self.result = result
        
class Event:
    def __init__(self, game, bet):
        self.game = game
        self.bet = bet