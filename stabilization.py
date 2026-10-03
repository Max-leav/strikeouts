from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time, random
from scrape_statcast import *
from pathlib import Path
from scrape_data import getMonthResults, getYearResults, getTotalResults
import statsmodels.api as sm
import shutil
from sklearn.metrics import log_loss

AVERAGES = pd.read_csv("data/averages.csv")
AVERAGES_DICT = AVERAGES.set_index(['bSide', 'pSide']).to_dict('index')

def getStabilizationParams(specificity):
    if specificity == 0:
        midpoints = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550]
        steepnesses = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]
    elif specificity == 1:
        midpoints = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 75, 100]
        steepnesses = [0.001, 0.0025, 0.005, 0.0075, 0.010, 0.0125, 0.015, 0.0175, 0.020, 0.0225, 0.025]

    params = []

    for midpoint in midpoints:
        for steepness in steepnesses:
            params.append({"midpoint": midpoint, "steepness": steepness})

    return params

def getStabilizationWeight(pa, midpoint, steepness):
    return 1 / (1 + np.exp(-steepness * (pa - midpoint)))

def getStabilizedValue(pa, variable, midpoint, steepness):
    prevVar = "p" + variable
    
    curPA = pa.get(f"{variable[0]}PA", 0)
    prevPA = pa.get(f"p{variable[0]}PA", 0)
    playerPA = curPA + prevPA

    curPA = 0 if pd.isna(curPA) else curPA
    prevPA = 0 if pd.isna(prevPA) else prevPA

    curValue = pa.get(variable, np.nan)
    prevValue = pa.get(prevVar, np.nan)

    curValid = curPA > 0 and pd.notna(curValue)
    prevValid = prevPA > 0 and pd.notna(prevValue)
    
    leagueValue = AVERAGES_DICT[(pa["bSide"], pa["pSide"])][variable[1:]]
    playerValue = leagueValue

    if curValid and prevValid:
        curWeight = getStabilizationWeight(curPA, midpoint, steepness)

        prevWeight = 1 - curWeight

        playerValue = (
            curValue * curWeight +
            prevValue * prevWeight
        )
    elif curValid:
        playerValue = curValue
        playerPA = curPA
    elif prevValid:
        playerValue = prevValue
        playerPA = prevPA

    playerWeight = getStabilizationWeight(
        playerPA,
        midpoint,
        steepness
    )

    leagueWeight = 1 - playerWeight

    return (
        playerValue * playerWeight +
        leagueValue * leagueWeight
    )

def calculateStabilizationMetrics(df, variable, midpoint, steepness):
    prevVar = "p" + variable

    testDf = df[
        df[variable].notna() |
        df[prevVar].notna()
    ].copy()

    # prev season only
    prevDf = testDf[testDf[prevVar].notna()].copy()

    # cur season only
    curDf = testDf[testDf[variable].notna()].copy()

    # Stabilized
    testDf["stabilized"] = testDf.apply(
        lambda row: getStabilizedValue(
            row,
            variable,
            midpoint,
            steepness
        ),
        axis=1
    )

    stabilizedDf = testDf[testDf["stabilized"].notna()].copy()

    results = {
        "prev_log_loss": np.nan,
        "cur_log_loss": np.nan,
        "stabilized_log_loss": np.nan
    }

    if len(prevDf) > 0:
        p = (prevDf[prevVar] / 100).clip(1e-6, 1 - 1e-6)
        y = prevDf["isStrikeout"]

        results["prev_log_loss"] = log_loss(y, p)

    if len(curDf) > 0:
        p = (curDf[variable] / 100).clip(1e-6, 1 - 1e-6)
        y = curDf["isStrikeout"]

        results["cur_log_loss"] = log_loss(y, p)

    if len(stabilizedDf) > 0:
        p = (stabilizedDf["stabilized"] / 100).clip(1e-6, 1 - 1e-6)
        y = stabilizedDf["isStrikeout"]

        results["stabilized_log_loss"] = log_loss(y, p)

    return results

def runStabilizationTests(df, variable, specificity):
    outFile = Path(f"data/testing/stabilization/{variable}.csv")
    
    params = getStabilizationParams(specificity)

    results = []

    for param in params:
        midpoint = param["midpoint"]
        steepness = param["steepness"]

        metrics = calculateStabilizationMetrics(
            df,
            variable,
            midpoint,
            steepness,
        )

        results.append({
            "variable": variable,
            "midpoint": midpoint,
            "steepness": steepness,
            **metrics
        })

    resultsDf = pd.DataFrame(results)

    resultsDf.to_csv(
        outFile,
        mode="a",
        header=not outFile.exists(),
        index=False
    )

    return resultsDf

if __name__ == '__main__':
    variables = [
        "bK%", "pK%", 
        "bPutaway%", "pPutaway%",
        "bCSW%", "pCSW%",
        "bWhiff%", "pWhiff%",
        "bChase%", "pChase%",
        "bSwStr%", "pSwStr%",
        "bcStr%", "pcStr%",
        "bBB%", "pBB%"
    ]
    
    specificity = 1

    df = pd.DataFrame()

    for year in range(2024, 2027):
        path = Path(f"data/pas/{year}")

        fNames = [
            file.name
            for file in path.iterdir()
            if file.is_file() and file.suffix == ".csv"
        ]

        for f in fNames:
            print(f"Loading {year}/{f}")

            fileDf = pd.read_csv(path / f)
            df = pd.concat([df, fileDf], ignore_index=True)

    print(f"\nLoaded {len(df)} PAs")

    Path("data/testing/stabilization").mkdir(
        parents=True,
        exist_ok=True
    )

    for variable in variables:
        print(f"\nTesting {variable}")
        runStabilizationTests(df, variable, specificity)