import requests, json

def getFangraphHitters():
    urls = ["https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=bat&lg=all&qual=0&season=2026&season1=2026&startdate=2026-03-01&enddate=2026-11-01&month=0&hand=&team=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&heatmapqual=y&sortdir=default&sortstat=WAR",
            "https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=pit&lg=all&qual=0&season=2026&season1=2026&startdate=2026-03-01&enddate=2026-11-01&month=0&hand=&team=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&heatmapqual=y&sortdir=default&sortstat=WAR"]
    return []

def loadFile(players):
    pass

if __name__ == '__main__':
    allPlayers = getFangraphPlayers()
    
    loadFile(allPlayers)

