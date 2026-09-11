from requests import get
from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time
from scrape_statcast import *
from pathlib import Path

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

def convertLookupsToCsv():
    with open('lookups/mlbLookup.json', 'r') as file:
        data = json.load(file)

    cols = ["mlbid", "fgid", "name"]
    mlbIds = [int(key) for key in data.keys()]
    fgIds = [data[str(id)][0] for id in mlbIds]
    name = [data[str(id)][1] for id in mlbIds]

    df = pd.DataFrame(zip(mlbIds, fgIds, name), columns=cols)
    df.to_csv("data/lookup.csv", index=False)

def getAllGameIds(dateFrom, dateTo):
    allIds = pd.DataFrame(columns=["year", "date", "gid"])

    for year in range(int(dateFrom[0:4]), int(dateTo[0:4]) + 1):
        yearIds = pd.read_csv(f"data/gameIds/{year}.csv")
        yearIds = yearIds[yearIds["date"].between(dateFrom, dateTo)]
        allIds = pd.concat([allIds, yearIds], ignore_index=True)

    return allIds.sort_values(by="date")

def getGamePAs(gid):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{gid}/feed/live?language=en"

    js = get(url, headers=headers).json()
    
    return js["liveData"]["plays"]["allPlays"]

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

def getPA(play, gid, date):
    gameid = gid
    eventDate = date
    year = date[0:4]
    batter = play["matchup"]["batter"]["id"]
    batSide = play["matchup"]["batSide"]["code"]
    pitcher = play["matchup"]["pitcher"]["id"]
    pitchSide = play["matchup"]["pitchHand"]["code"]
    result = play["result"]["eventType"]
    isStrikeout = "strikeout" in result
    isWalk = "walk" in result

    return [gameid, eventDate, year, batter, batSide, pitcher, pitchSide, result, isStrikeout, isWalk]

def getAllPAs(dateFrom, dateTo):
    allGameIds = getAllGameIds(dateFrom, dateTo)
    #allGameIds = [747060]

    for year in allGameIds["year"].unique():
        allPlateAppearances = []
        month = "03"

        yearIds = allGameIds[allGameIds["year"] == year]

        for row in yearIds.itertuples(index=False):
            if row.date[5:7] != month:
                cols = ["gid","date", "year", "batter", "bSide", "pitcher", "pSide", "result", "isStrikeout", "isWalk"]
                df = pd.DataFrame(allPlateAppearances, columns=cols)
        
                df.to_csv(f"data/pas/{year}/{month}.csv", index=False)
                month = row.date[5:7]
                allPlateAppearances = []

            gid = row.gid
            print("gid: ", gid)
            allPAs = getGamePAs(gid)
            print("pas in game: ", len(allPAs))
            
            for play in allPAs:
                pa = getPA(play, gid, row.date)
                allPlateAppearances.append(pa)

        cols = ["gid","date", "year", "batter", "bSide", "pitcher", "pSide", "result", "isStrikeout", "isWalk"]
        df = pd.DataFrame(allPlateAppearances, columns=cols)

        df.to_csv(f"data/pas/{year}/{month}.csv", index=False)

def getYearlyData(yearFrom, yearTo, mlbid, position):
    df = getRawPitches(mlbid, mlbDates[yearFrom][0], mlbDates[yearTo][1], position)
    time.sleep(0.1)

    print(mlbid, position)
    if len(df) <= 0:
        return

    for year in range(yearFrom, yearTo + 1):
        ydf = df[df["game_year"] == year]
        if position == "batter":
            filt = "p_throws"
            fName1 = f"data/batters/{year}/vsLHP/{mlbid}.csv"
            fName2 = f"data/batters/{year}/vsRHP/{mlbid}.csv"
        else:
            filt = "stand"
            fName1 = f"data/pitchers/{year}/vsLHB/{mlbid}.csv"
            fName2 = f"data/pitchers/{year}/vsRHB/{mlbid}.csv"

        vsL = ydf[ydf[filt] == "L"]
        vsR = ydf[ydf[filt] == "R"]

        lStats = groupByPitches(vsL, "pitch_type", False)
        lStats = condenseStats(lStats, "pitch")
        rStats = groupByPitches(vsR, "pitch_type", False)
        rStats = condenseStats(rStats, "pitch")

        lStats.to_csv(fName1, index=False)
        rStats.to_csv(fName2, index=False)

def getAllPitchLevelData(yearFrom, yearTo):
    df = pd.read_csv("data/lookup.csv")

    for id in df['mlbid'].tolist()[2235:]:
        print("getting data for id: ", id)
        batterData = getYearlyData(yearFrom, yearTo, id, "batter")
        pitcherData = getYearlyData(yearFrom, yearTo, id, "pitcher")
        
def condenseYearlyPlayerData(yearFrom, yearTo):
    for year in range(yearFrom, yearTo + 1):
        paths = [f"data/batters/{year}/vsLHP", f"data/batters/{year}/vsRHP", f"data/pitchers/{year}/vsLHB", f"data/pitchers/{year}/vsRHB"]
        
        for p in paths:
            ydf = pd.read_csv("data/playerTemplate.csv")
            
            path = Path(p)
            fNames = [file.name for file in path.iterdir() if file.is_file()]
            
            for f in fNames:
                df = pd.read_csv(f"{path}/{f}")
                df["mlbid"] = int(f[0:6])
                ydf = pd.concat([ydf, df])
                
            ydf["mlbid"] = pd.to_numeric(ydf["mlbid"], errors="raise").astype("int64")
                
            ydf.to_csv(f"{path}.csv", index=False)
            
        

def getProbablePitchers(date):
    pass

if __name__ == '__main__':
    #getAllGameInfo()
    #getAllPAs(mlbDates[2024][0], mlbDates[2026][1])
    condenseYearlyPlayerData(2023, 2025)
    