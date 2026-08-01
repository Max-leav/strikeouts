import requests, json

headers = {
  'sec-ch-ua-platform': '"Windows"',
  'Referer': 'https://www.fangraphs.com/leaders/major-league?pos=all&stats=bat&lg=all&type=8&season=2026&month=0&season1=2026&ind=0&qual=0&pagenum=1&pageitems=2000000000',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 OPR/133.0.0.0 (Edition std-1)',
  'Accept': 'application/json, text/plain, */*',
  'sec-ch-ua': '"Opera GX";v="133", "Chromium";v="149", "Not)A;Brand";v="24"',
  'sec-ch-ua-mobile': '?0'
}

def getPlayerIds(player):
    ids = [player["xMLBAMID"], player["playerid"], player["PlayerName"]]
    return ids

def getFangraphPlayers():
    urls = ["https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=bat&lg=all&qual=0&season=2026&season1=2026&startdate=2026-03-01&enddate=2026-11-01&month=0&hand=&team=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&heatmapqual=y&sortdir=default&sortstat=WAR",
            "https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=pit&lg=all&qual=0&season=2026&season1=2026&startdate=2026-03-01&enddate=2026-11-01&month=0&hand=&team=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&heatmapqual=y&sortdir=default&sortstat=WAR"]
    
    mlbLookup = dict()
    fgLookup = dict()
    
    for url in urls[0:1]:
        data = requests.get(url=url, headers=headers).json()["data"]
        for player in data:
            ids = getPlayerIds(player)
            mlbLookup[ids[0]] = ids[1:]
            fgLookup[ids[1]] = [ids[0], ids[2]]
    
    return []

def loadFile(fName, data):
    file = open(fName, "w")
    file.write(json.dumps(data, indent=4))
    file.close()

if __name__ == '__main__':
    urls = ["https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=bat&lg=all&qual=0&season=2026&season1=2026&startdate=2026-03-01&enddate=2026-11-01&month=0&hand=&team=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&heatmapqual=y&sortdir=default&sortstat=WAR",
            "https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=pit&lg=all&qual=0&season=2026&season1=2026&startdate=2026-03-01&enddate=2026-11-01&month=0&hand=&team=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&heatmapqual=y&sortdir=default&sortstat=WAR"]
    
    mlbLookup = dict()
    fgLookup = dict()
    
    for url in urls[0:1]:
        data = requests.get(url=url, headers=headers).json()["data"]
        for player in data:
            ids = getPlayerIds(player)
            mlbLookup[ids[0]] = ids[1:]
            fgLookup[ids[1]] = [ids[0], ids[2]]
            
    loadFile("mlbLookup.json", mlbLookup)
    loadFile("fgLookup.json", fgLookup)
            
            
            
            
    # allPlayers = getFangraphPlayers()
    
    # loadFile(allPlayers)

