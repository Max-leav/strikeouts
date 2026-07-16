def getAllGames():
    pass

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