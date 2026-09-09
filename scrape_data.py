from requests import get
from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd

def getLineups(gid):
    url = f"https://statsapi.mlb.com/api/v1/schedule?gamePk={gid}&language=en&hydrate=story,xrefId,lineups,broadcasts(all),probablePitcher(note),game(content(media(epg)),tickets)&useLatestGames=true&fields=dates,games,teams,probablePitcher,note,id,dates,games,broadcasts,type,name,homeAway,language,isNational,callSign,mediaState,mediaStateCode,availableForStreaming,freeGame,mediaId,dates,games,game,tickets,ticketType,ticketLinks,dates,games,content,media,epg,dates,games,lineups,homePlayers,awayPlayers,useName,lastName,primaryPosition,abbreviation,dates,games,xrefIds,xrefId,xrefType,story"
    lineups = dict()
    
    try:
        data = get(url, headers=headers).json()["dates"][0]["games"][0]["lineups"]
        lineups["home"] = [p["id"] for p in data["homePlayers"]]
        lineups["away"] = [p["id"] for p in data["awayPlayers"]]
    except:
        return None
    
    return lineups

def getAllGameInfo():
    gameInfo = {
        2023: dict(),
        2024: dict(),
        2025: dict(),
        2026: dict()
    }
    
    
    for year in mlbDates.keys():
        dateFrom = date.fromisoformat(mlbDates[year][0])
        dateTo = date.fromisoformat(mlbDates[year][1])
        
        while dateFrom < dateTo:
            df = date.isoformat(dateFrom)
            data = get(getMlbScheduleUrl(df,df), headers=headers).json()["dates"]
            print(df)
            
            if len(data) <= 0:
                dateFrom = dateFrom + timedelta(days=1)
                continue
            
            data = data[0]["games"]
            
            for game in data:
                gid = game["gamePk"]
                away = game["teams"]["away"]["team"]["abbreviation"]
                home = game["teams"]["home"]["team"]["abbreviation"]
                print(f"{home} vs {away}")
                try:
                    aPitcher = game["teams"]["away"]["probablePitcher"]["id"]
                except:
                    aPitcher = None
                try:
                    hPitcher = game["teams"]["home"]["probablePitcher"]["id"]
                except:
                    hPitcher = None
                lineups = getLineups(gid)
                
                if lineups == None:
                    dateFrom = dateFrom + timedelta(days=1)
                    continue
                
                event = Game(home, away, hPitcher, aPitcher, lineups["home"], lineups["away"], gid, df)
            
                gameInfo[dateFrom.year][gid] = event.getDict()
                #gameInfo[dateFrom.year].extend([d["gamePk"] for d in data])
            
            dateFrom = dateFrom + timedelta(days=1)
            
    file = open("mlbGameInfo.json", "w")
    file.write(json.dumps(gameInfo, indent=4))
    file.close()

def getEventDate(gid):
    url = f"https://ws.statsapi.mlb.com/api/v1.1/game/{gid}/feed/live?language=en"
        
    js = get(url, headers).json()
    dateData = js["gameData"]

    return dateData["datetime"]["dateTime"][0:10]

def convertGameInfoToCsv():
    file = open("data/mlbGameInfo.json", "r")
    allGameInfo = json.load(file)
    print("file loaded")
    file.close()

    allRows = []

    for year in allGameInfo.keys():
        if year == "2024":
            continue
        games = allGameInfo[year]

        curDate = mlbDates[int(year)][0]

        for gid in games.keys():
            info = games[gid]
            eventDate = getEventDate(gid)

            if eventDate != curDate:
                print(eventDate)
                curDate = eventDate
            #     # df = pd.DataFrame(allRows, columns=["year", "date", "gid", "home", "away", "hPitcher", "aPitcher", "hLineup", "aLineup"])
            #     # df.to_csv(f"data/gameInfo/{curDate}.csv")
            #     # df = df[["year", "date", "gid"]]
            #     # df.to_csv(f"data/gameIds/{curDate}.csv")

            #     allRows = []
            #     curDate = eventDate

            allRows.append([year, eventDate, gid, info["home"], info["away"], info["hPitcher"], info["aPitcher"], info["hLineup"], info["aLineup"]])

        df = pd.DataFrame(allRows, columns=["year", "date", "gid", "home", "away", "hPitcher", "aPitcher", "hLineup", "aLineup"])
        df.to_csv(f"data/gameInfo/{year}.csv")
        df = df[["year", "date", "gid"]]
        df.to_csv(f"data/gameIds/{year}.csv")


def getAllGameIds(yearFrom, yearTo):
    file = open("mlbGameIds.json", "r")
    allIds = json.load(file)
    file.close()

    ids = []
    for year in range(int(yearFrom), int(yearTo) + 1):
        yearIds = allIds[str(year)]
        ids.extend(yearIds)

    return ids

def getGamePAs(gid):
    url = f"https://ws.statsapi.mlb.com/api/v1.1/game/{gid}/feed/live?language=en"
    
    return get(url, headers).json()["liveData"]["plays"]["allPlays"]

def getPAInfo(pa):
    eventDate = pa["playEndTime"][0:10]
    year = pa["playEndTime"][0:4]
    batter = Batter(pa["matchup"]["batter"]["id"], year)
    batSide = pa["matchup"]["batSide"]["code"]
    pitcher = Pitcher(pa["matchup"]["pitcher"]["id"], year)
    pitchSide = pa["matchup"]["pitchHand"]["code"]
    isStrikeout = ("strikeout" in pa["result"]["event"])

def getPAData(pa):
    paInfo = getPAInfo(pa)

def getPA(play, gid):
    gameid = gid
    eventDate = play["playEndTime"][0:10]
    year = play["playEndTime"][0:4]
    batter = play["matchup"]["batter"]["id"]
    batSide = play["matchup"]["batSide"]["code"]
    pitcher = play["matchup"]["pitcher"]["id"]
    pitchSide = play["matchup"]["pitchHand"]["code"]
    result = play["result"]["eventType"]
    isStrikeout = "strikeout" in result
    isWalk = "walk" in result

    return [gameid, eventDate, year, batter, batSide, pitcher, pitchSide, result, isStrikeout, isWalk]

def getAllPAs(yearFrom, yearTo):
    allGameIds = getAllGameIds(yearFrom, yearTo)
    #allGameIds = [747060]
    allPlateAppearances = []
    
    for gid in allGameIds[0:100]:
        allPAs = getGamePAs(gid)
        
        for play in allPAs:
            pa = getPA(play, gid)
            # for key, value in paData.getDict():
            #     print(key, value)
            allPlateAppearances.append(pa)

    cols = ["gid","date", "year", "batter", "bSide", "pitcher", "pSide", "result", "isStrikeout", "isWalk"]
    df = pd.DataFrame(allPlateAppearances, columns=cols)

    df.to_csv("data/pas.csv", index=False)

    

def getProbablePitchers(date):
    pass

if __name__ == '__main__':
    #getAllGameInfo()
    #getAllPAs('2024', '2026')
    #convertGameInfoToCsv()
    for year in ["2024", "2025", "2026"]:
        s = f"data/gameIds/{year}.csv"
        s2 = f"data/gameInfo/{year}.csv"
        df = pd.read_csv(s)
        df2 = pd.read_csv(s2)
        df2['hPitcher'] = df2['hPitcher'].astype('Int64')
        df2['aPitcher'] = df2['aPitcher'].astype('Int64')
        df.to_csv(s, index=False)
        df2.to_csv(s2, index=False)