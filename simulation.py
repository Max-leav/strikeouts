from scraping_information import *
import random

global apStats, hpStats, alStats, hlStats, eDate

def getPitcherStats(pid):
    pitcher = Pitcher(pid, eDate)
    
    data = get(pitcher.splitsUrl, headers=headers).json()

def getExpectedKPercentages(ap, hp, al, hl):
    global apStats, hpStats, alStats, hlStats
    
    apStats = getPitcherStats(ap)
    hpStats = getPitcherStats(hp)
    
    alStats = getLineupStats(al)
    hlStats = getLineupStats(hl)
    
    return {
        "away": [0.25 * 9],
        "home": [0.25 * 9]
    }
    
def simulate_one_game(abf, hbf, aek, hek):
    ak, hk = 0, 0
    
    for i in range(abf):
        outcome = random.uniform(0, 1)
        if outcome <= hek[i % 9]:
            ak += 1
            
    for i in range(hbf):
        outcome = random.uniform(0, 1)
        if outcome <= aek[i % 9]:
            hk += 1

def run_simulation(game):
    global eDate
    eDate = game.date[0:4]
    results = {
        "abf": [],
        "hbf": [],
        "aKs": [],
        "hKs": []
    }
    
    expectedKPercentages = getExpectedKPercentages(game.aPitcher, game.hPitcher, game.aLineup, game.hLineup)
    
    
    for i in range(10000):
        abf = getExpectedBf(game.aPitcher, game.hLineup)
        hbf = getExpectedBf(game.hPitcher, game.aLineup)
        
        simKs = simulate_one_game(abf, hbf, expectedKPercentages["home"], expectedKPercentages["away"])
        
        