from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time, random
from scrape_statcast import *
from pathlib import Path
from scrape_data import getMonthResults, getYearResults, getTotalResults
import statsmodels.api as sm

LEAGUE_K_PCT = 22.28

def getMethodVariables(method):
    if method == "001":
        return ["bK%"]
    elif method == "002":
        return ["bK%", "pK%"]
    
def getMethodWeights(method):
    variables = getMethodVariables(method)

    weights = {variable: random.random() for variable in variables}

    total = sum(weights.values())

    weights = {variable: weight / total for variable, weight in weights.items()}

    return weights

def getStrikeoutChance(pa, method, weights):    
    # if method == "001":
    #     if pd.notna(pa["bK%"]):
    #         return pa["bK%"]
        
    #     if pd.notna(pa["pbK%"]):
    #         return pa["pbK%"]
    variables = getMethodVariables(method)

    vars = []
    usedWeights = []

    for variable in variables:
        value = pa[variable]

        if pd.notna(value):
            vars.append(value)
            usedWeights.append(weights[variable])
            continue

        try:
            value = pa[f"p{variable}"]
        except:
            pass
        
        if pd.notna(value):
            vars.append(value)
            usedWeights.append(weights[variable])
            continue
            
        if "K%" in variable:
            vars.append(LEAGUE_K_PCT)
            usedWeights.append(weights[variable])

    if len(vars) == 0:
        return LEAGUE_K_PCT

    weight_total = sum(usedWeights)

    usedWeights = [weight / weight_total for weight in usedWeights]

    exp_k_rate = sum(value * weight for value, weight in zip(vars, usedWeights))

    return exp_k_rate
                
def getPAPrediction(pa, method):
    xk_pct = getStrikeoutChance(pa, method)
    res = random.random()
    
    return res * 100 < xk_pct

def testModelNumbers(yearFrom, yearTo, method):
    stats = pd.DataFrame({
        "Year": pd.Series(dtype="int"),
        "Month": pd.Series(dtype="int"),
        "PA": pd.Series(dtype="int"),
        "K": pd.Series(dtype="int"),
        "BB": pd.Series(dtype="int"),
        "K%": pd.Series(dtype="float"),
        "BB%": pd.Series(dtype="float")
    })
    
    for year in range(yearFrom, yearTo + 1):
        p = f"data/pas/{year}"
        path = Path(p)
            
        fNames = [file.name for file in path.iterdir() if file.is_file()]
        
        for f in fNames:
            print(f)
            
            df = pd.read_csv(f"{path}/{f}")
            df["isStrikeout"] = df.apply(getPAPrediction, axis=1, args=(method,))
            
            stats.loc[len(stats)] = getMonthResults(df, year, int(f[0:2]))
            
        stats.loc[len(stats)] = getYearResults(stats, year)
    
    stats.loc[len(stats)] = getTotalResults(stats)
    
    stats.to_csv(f"data/testing/method_{method}_Results.csv", index=False)

def getPATestingData2(yearFrom, yearTo, method):
    methodPath = Path(f"data/testing/method_{method}")
    dataPath = methodPath / "data"

    methodPath.mkdir(parents=True, exist_ok=True)
    dataPath.mkdir(parents=True, exist_ok=True)

    print(dataPath.iterdir()[-1])
    exit(1)
    # Find existing version directories inside data/
    versions = [p for p in dataPath.iterdir()]
    
    if len(versions) > 0:
        highestVersion = versions[-1]
        startVersion = highestVersion + 1
    else:
        startVersion = 0

    print(f"Starting at version v{startVersion}")

    for i in range(numRuns):
        version = startVersion + i

        outPath = dataPath / f"v{version}"
        outPath.mkdir(parents=True, exist_ok=True)

        outFile = outPath / "pas.csv"

        weights = getMethodWeights(method)

        print(f"Running version v{version} with weights: {weights}")

        for year in range(yearFrom, yearTo + 1):
            p = f"data/pas/{year}"
            path = Path(p)

            fNames = [
                file.name
                for file in path.iterdir()
                if file.is_file()
            ]

            for f in fNames:
                print(f"v{version}: {f}")

                df = pd.read_csv(path / f)

                df["exp_k_rate"] = df.apply(
                    getStrikeoutChance,
                    axis=1,
                    args=(method, weights)
                )

                # Store the weights used for this version
                for variable, weight in weights.items():
                    df[f"{variable}_weight"] = weight

                df = df[
                    [
                        "gid",
                        "date",
                        "year",
                        "batter",
                        "pitcher",
                        "isStrikeout",
                        "exp_k_rate"
                    ]
                    + [f"{variable}_weight" for variable in weights]
                ].copy()

                df.to_csv(
                    outFile,
                    mode="a",
                    header=not outFile.exists(),
                    index=False
                )

        print(f"Finished version v{version}")

def getPATestingData(yearFrom, yearTo, method, numRuns):
    methodPath = Path(f"data/testing/method_{method}")
    dataPath = methodPath / "data"

    methodPath.mkdir(parents=True, exist_ok=True)
    dataPath.mkdir(parents=True, exist_ok=True)

    versions = [p for p in dataPath.iterdir()]
    
    if len(versions) > 0:
        highestVersion = int(versions[-1].name[1:])
        startVersion = highestVersion + 1
    else:
        startVersion = 0

    for i in range(numRuns):
        version = startVersion + i
        
        outPath = dataPath / f"v{version}"
        outPath.mkdir(parents=True, exist_ok=True)
        outFile = outPath / "pas.csv"
        
        weights = getMethodWeights(method)
        
        for year in range(yearFrom, yearTo + 1):
            p = f"data/pas/{year}"
            path = Path(p)
                
            fNames = [file.name for file in path.iterdir() if file.is_file()]
            
            for f in fNames:
                print(f)
                
                df = pd.read_csv(f"{path}/{f}")
                
                df["exp_k_rate"] = df.apply(getStrikeoutChance, axis=1, args=(method, weights))
                
                for variable, weight in weights.items():
                    df[f"{variable}_weight"] = weight
                
                df = df[['gid','date','year','batter','pitcher','isStrikeout','exp_k_rate'] 
                        + [f"{variable}_weight" for variable in weights]].copy()
                
                df.to_csv(
                    outFile,
                    mode="a",
                    header=not outFile.exists(),
                    index=False
                )
        print(f"Finished version v{version}")
            
def combinePAs(yearFrom, yearTo, method):
    outPath = Path(f"data/testing/method_{method}")
    outFile = outPath / "pas.csv"
    
    for year in range(yearFrom, yearTo + 1):
        p = f"data/testing/method_{method}/{year}"
        path = Path(p)
            
        fNames = [file.name for file in path.iterdir() if file.is_file()]
        
        for f in fNames:
            print(f)
            
            df = pd.read_csv(f"{path}/{f}")
            
            df.to_csv(
                outFile,
                mode="a",
                header=not outFile.exists(),
                index=False
            )
            
def logisticRegression(method):
    methodPath = Path(f"data/testing/method_{method}")
    dataPath = methodPath / "data"
    outputPath = methodPath / "logisticRegression.csv"

    results = []

    if not dataPath.exists():
        print(f"No data directory found: {dataPath}")
        return

    versionPaths = sorted(
        [
            p for p in dataPath.iterdir()
            if p.is_dir()
            and p.name.startswith("v")
            and p.name[1:].isdigit()
        ],
        key=lambda p: int(p.name[1:])
    )

    for versionPath in versionPaths:
        pasPath = versionPath / "pas.csv"

        if not pasPath.exists():
            continue

        # Store version as an integer rather than "v0", "v1", etc.
        version = int(versionPath.name[1:])

        print(
            f"Running logistic regression for "
            f"method {method}, v{version}"
        )

        df = pd.read_csv(pasPath)

        df["date"] = pd.to_datetime(df["date"])
        df["exp_k_rate"] = pd.to_numeric(df["exp_k_rate"])
        df["isStrikeout"] = pd.to_numeric(df["isStrikeout"])

        p = (
            df["exp_k_rate"] / 100
        ).clip(1e-6, 1 - 1e-6)

        y = df["isStrikeout"]

        brierScore = np.mean((p - y) ** 2)

        logLoss = -np.mean(
            y * np.log(p) +
            (1 - y) * np.log(1 - p)
        )

        # Calibration regression:
        # logit(actual) ~ intercept + slope * logit(expected)
        expectedLogit = np.log(p / (1 - p))

        X = sm.add_constant(expectedLogit)

        model = sm.Logit(y, X).fit(disp=False)

        intercept = model.params.iloc[0]
        slope = model.params.iloc[1]

        interceptSE = model.bse.iloc[0]
        slopeSE = model.bse.iloc[1]

        interceptZ = model.tvalues.iloc[0]
        slopeZ = model.tvalues.iloc[1]

        interceptP = model.pvalues.iloc[0]
        slopeP = model.pvalues.iloc[1]

        interceptCI = model.conf_int().iloc[0]
        slopeCI = model.conf_int().iloc[1]

        logLikelihood = model.llf
        pseudoR2 = model.prsquared

        # Get the weights stored in pas.csv
        weightColumns = [
            column
            for column in df.columns
            if column.endswith("_weight")
        ]

        weights = {
            column: df[column].iloc[0]
            for column in weightColumns
        }

        # Overall
        result = {
            "method": method,
            "version": version,
            "group_type": "overall",
            "group": "all",
            "month": np.nan,
            "lower_bound": np.nan,
            "upper_bound": np.nan,
            "n": len(df),
            "mean_exp_k_rate": df["exp_k_rate"].mean(),
            "actual_k_rate": y.mean() * 100,
            "calibration_error":
                y.mean() * 100 -
                df["exp_k_rate"].mean(),
            "brier_score": brierScore,
            "log_loss": logLoss,
            "intercept": intercept,
            "slope": slope,
            "intercept_se": interceptSE,
            "slope_se": slopeSE,
            "intercept_z": interceptZ,
            "slope_z": slopeZ,
            "intercept_p": interceptP,
            "slope_p": slopeP,
            "intercept_ci_low": interceptCI.iloc[0],
            "intercept_ci_high": interceptCI.iloc[1],
            "slope_ci_low": slopeCI.iloc[0],
            "slope_ci_high": slopeCI.iloc[1],
            "log_likelihood": logLikelihood,
            "pseudo_r2": pseudoR2
        }

        result.update(weights)
        results.append(result)

        # K-rate bins
        bins = [
            0, 5, 10, 15, 20, 25,
            30, 35, 40, 45, 50, 100
        ]

        labels = [
            "0-5%", "5-10%", "10-15%",
            "15-20%", "20-25%", "25-30%",
            "30-35%", "35-40%", "40-45%",
            "45-50%", "50%+"
        ]

        df["k_rate_bin"] = pd.cut(
            df["exp_k_rate"],
            bins=bins,
            labels=labels,
            right=False,
            include_lowest=True
        )

        for group, groupDf in df.groupby(
            "k_rate_bin",
            observed=False
        ):
            if len(groupDf) == 0:
                continue

            groupP = (
                groupDf["exp_k_rate"] / 100
            ).clip(1e-6, 1 - 1e-6)

            groupY = groupDf["isStrikeout"]

            result = {
                "method": method,
                "version": version,
                "group_type": "k_rate_bin",
                "group": str(group),
                "month": np.nan,
                "lower_bound": groupDf["exp_k_rate"].min(),
                "upper_bound": groupDf["exp_k_rate"].max(),
                "n": len(groupDf),
                "mean_exp_k_rate": groupDf["exp_k_rate"].mean(),
                "actual_k_rate": groupY.mean() * 100,
                "calibration_error":
                    groupY.mean() * 100 -
                    groupDf["exp_k_rate"].mean(),
                "brier_score":
                    np.mean((groupP - groupY) ** 2),
                "log_loss":
                    -np.mean(
                        groupY * np.log(groupP) +
                        (1 - groupY) * np.log(1 - groupP)
                    )
            }

            result.update(weights)
            results.append(result)

        # Month
        df["month"] = df["date"].dt.month

        for month, monthDf in df.groupby("month"):
            monthP = (
                monthDf["exp_k_rate"] / 100
            ).clip(1e-6, 1 - 1e-6)

            monthY = monthDf["isStrikeout"]

            result = {
                "method": method,
                "version": version,
                "group_type": "month",
                "group": str(month),
                "month": month,
                "lower_bound": np.nan,
                "upper_bound": np.nan,
                "n": len(monthDf),
                "mean_exp_k_rate": monthDf["exp_k_rate"].mean(),
                "actual_k_rate": monthY.mean() * 100,
                "calibration_error":
                    monthY.mean() * 100 -
                    monthDf["exp_k_rate"].mean(),
                "brier_score":
                    np.mean((monthP - monthY) ** 2),
                "log_loss":
                    -np.mean(
                        monthY * np.log(monthP) +
                        (1 - monthY) * np.log(1 - monthP)
                    )
            }

            result.update(weights)
            results.append(result)

    resultsDf = pd.DataFrame(results)

    resultsDf.to_csv(
        outputPath,
        index=False
    )

if __name__ == '__main__':
    method = "002"
    runs = 1000
    #testModelNumbers(2024, 2025, "001")
    getPATestingData(2024, 2026, method, runs)
    logisticRegression(method)
