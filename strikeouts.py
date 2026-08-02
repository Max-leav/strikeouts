import requests, datetime
from datetime import timedelta
import scraping_information
from scraping_information import Pitcher, Batter, Game

def getDate():
    today = datetime.datetime.now()
    if today.hour >= 8:
        today = today + timedelta(days=1)
        
    return today.strftime("%Y-%m-%d")

def getGameInfo():
    date = getDate()
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&sportId=21&sportId=51&startDate={date}&endDate={date}&timeZone=America/New_York&gameType=E&&gameType=S&&gameType=R&&gameType=F&&gameType=D&&gameType=L&&gameType=W&&gameType=A&season=2026&language=en&leagueId=&&leagueId=&&leagueId=103&&leagueId=104&&leagueId=160&&leagueId=426&&leagueId=427&&leagueId=428&&leagueId=429&&leagueId=430&&leagueId=431&&leagueId=432&&leagueId=590&sortBy=gameDate,gameType&hydrate=team,linescore(matchup,runners),xrefId,flags,statusFlags,broadcasts(all),venue(location),decisions,person,probablePitcher,stats,game(content(media(epg),summary),tickets),seriesStatus(useOverride=true)"
    
    return []

def getLineups(gameId):
    url = f"https://statsapi.mlb.com/api/v1/schedule?gamePk={gameId}&language=en&hydrate=story,xrefId,lineups,broadcasts(all),probablePitcher(note),game(content(media(epg)),tickets)&useLatestGames=true&fields=dates,games,teams,probablePitcher,note,id,dates,games,broadcasts,type,name,homeAway,language,isNational,callSign,mediaState,mediaStateCode,availableForStreaming,freeGame,mediaId,dates,games,game,tickets,ticketType,ticketLinks,dates,games,content,media,epg,dates,games,lineups,homePlayers,awayPlayers,useName,lastName,primaryPosition,abbreviation,dates,games,xrefIds,xrefId,xrefType,story"
    info = requests.get(url, headers=scraping_information.headers).json()["date"][0]["games"][0]
    
    if len(info["lineups"] == 0):
        aLineup = None
        hLineup = None
    else:
        aLineup = info["lineups"]["awayPlayers"]
        hLineup = info["lineups"]["homePlayers"]
        
    if len(info["teams"]["away"] == 0):
        aPitcher = None
    else:
        aPitcher = info["teams"]["away"]["probablePitcher"]["id"]
        
    if len(info["teams"]["home"] == 0):
        hPitcher = None
    else:
        hPitcher = info["teams"]["home"]["probablePitcher"]["id"]
    
    return [hLineup, aLineup, hPitcher, aPitcher]

def getAllGames():
    gameInfo = getGameInfo()
    allGames = []
    
    for gameId in gameIds:
        lineups = getLineups(gameId)
        
        
        
        

def getGameInfo(game):
    return None

def getPitcherInfo(game):
    return None

def getHitterInfo(game):
    return None

if __name__ == '__main__':
    allGames = getAllGames()

    gameInfo = []

    for game in allGames:
        gameInfo.append(getGameInfo(game))

    pitcherInfo, hitterInfo = [], []

    for game in gameInfo:
        pitcherInfo.append(getPitcherInfo(game))
        hitterInfo.append(getHitterInfo(game))

    exit()