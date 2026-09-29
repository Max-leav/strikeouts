from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time, random
from scrape_statcast import *
from pathlib import Path
from scrape_data import getMonthResults, getYearResults, getTotalResults
import statsmodels.api as sm
import shutil
from sklearn.metrics import log_loss

def getStabilizationParams():
    midpoints = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550]

    steepnesses = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]

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

    curPA = 0 if pd.isna(curPA) else curPA
    prevPA = 0 if pd.isna(prevPA) else prevPA

    curValue = pa.get(variable, np.nan)
    prevValue = pa.get(prevVar, np.nan)

    curValid = curPA > 0 and pd.notna(curValue)
    prevValid = prevPA > 0 and pd.notna(prevValue)

    if curValid and prevValid:
        curWeight = getStabilizationWeight(curPA, midpoint, steepness)

        prevWeight = 1 - curWeight

        return (
            curValue * curWeight +
            prevValue * prevWeight
        )

    if curValid:
        return curValue

    if prevValid:
        return prevValue

    return np.nan

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

def runStabilizationTests(df, variable):
    params = getStabilizationParams()

    results = []

    for param in params:
        midpoint = param["midpoint"]
        steepness = param["steepness"]

        metrics = calculateStabilizationMetrics(df, variable, midpoint, steepness)

        results.append({
            "variable": variable,
            "midpoint": midpoint,
            "steepness": steepness,
            **metrics
        })

    resultsDf = pd.DataFrame(results)

    resultsDf.to_csv(
        f"data/testing/stabilization/{variable}.csv",
        index=False
    )

    return resultsDf

from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time, random
from scrape_statcast import *
from pathlib import Path
from scrape_data import getMonthResults, getYearResults, getTotalResults
import statsmodels.api as sm
import shutil
from sklearn.metrics import log_loss

def getStabilizationParams():
    midpoints = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550]

    steepnesses = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]

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

    curPA = 0 if pd.isna(curPA) else curPA
    prevPA = 0 if pd.isna(prevPA) else prevPA

    curValue = pa.get(variable, np.nan)
    prevValue = pa.get(prevVar, np.nan)

    curValid = curPA > 0 and pd.notna(curValue)
    prevValid = prevPA > 0 and pd.notna(prevValue)

    if curValid and prevValid:
        curWeight = getStabilizationWeight(curPA, midpoint, steepness)

        prevWeight = 1 - curWeight

        return (
            curValue * curWeight +
            prevValue * prevWeight
        )

    if curValid:
        return curValue

    if prevValid:
        return prevValue

    return np.nan

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

def runStabilizationTests(df, variable):
    params = getStabilizationParams()

    results = []

    for param in params:
        midpoint = param["midpoint"]
        steepness = param["steepness"]

        metrics = calculateStabilizationMetrics(df, variable, midpoint, steepness)

        results.append({
            "variable": variable,
            "midpoint": midpoint,
            "steepness": steepness,
            **metrics
        })

    resultsDf = pd.DataFrame(results)

    resultsDf.to_csv(
        f"data/testing/stabilization/{variable}.csv",
        index=False
    )

    return resultsDf

from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time, random
from scrape_statcast import *
from pathlib import Path
from scrape_data import getMonthResults, getYearResults, getTotalResults
import statsmodels.api as sm
import shutil
from sklearn.metrics import log_loss

def getStabilizationParams():
    midpoints = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550]

    steepnesses = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]

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

    curPA = 0 if pd.isna(curPA) else curPA
    prevPA = 0 if pd.isna(prevPA) else prevPA

    curValue = pa.get(variable, np.nan)
    prevValue = pa.get(prevVar, np.nan)

    curValid = curPA > 0 and pd.notna(curValue)
    prevValid = prevPA > 0 and pd.notna(prevValue)

    if curValid and prevValid:
        curWeight = getStabilizationWeight(curPA, midpoint, steepness)

        prevWeight = 1 - curWeight

        return (
            curValue * curWeight +
            prevValue * prevWeight
        )

    if curValid:
        return curValue

    if prevValid:
        return prevValue

    return np.nan

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

def runStabilizationTests(df, variable):
    params = getStabilizationParams()

    results = []

    for param in params:
        midpoint = param["midpoint"]
        steepness = param["steepness"]

        metrics = calculateStabilizationMetrics(
            df,
            variable,
            midpoint,
            steepness
        )

        results.append({
            "variable": variable,
            "midpoint": midpoint,
            "steepness": steepness,
            **metrics
        })

    resultsDf = pd.DataFrame(results)

    resultsDf.to_csv(
        f"data/testing/stabilization/{variable}.csv",
        index=False
    )

    return resultsDf

if __name__ == '__main__':
    variables = [
        "bK%",
        "bBB%",
        "bWhiff%",
        "bSwStr%",
        "bcStr%",
        "bCSW%",
        "bChase%",
        "bPutaway%",

        "pK%",
        "pBB%",
        "pWhiff%",
        "pSwStr%",
        "pcStr%",
        "pCSW%",
        "pChase%",
        "pPutaway%"
    ]

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

    for variable in variables[0:1]:
        print(f"\nTesting {variable}")
        runStabilizationTests(df, variable)