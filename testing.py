from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time, random
from scrape_statcast import *
from pathlib import Path
from scrape_data import getMonthResults, getYearResults, getTotalResults
import statsmodels.api as sm
import shutil

LEAGUE_K_PCT = 22.28

def getMethodVariables(method):
    if method == "001":
        return ["bK%"]
    elif method == "002":
        return ["bK%", "pK%"]
    elif method == "003":
        return ["bK%", "pbK%", "pK%", "ppK%"]
    
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
            if "K%" in variable:
                vars.append(LEAGUE_K_PCT)
                usedWeights.append(weights[variable])
            continue
        
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

def getPATestingData(cYearFrom, cYearTo, tYearFrom, tYearTo, method, numRuns, version):
    methodPath = Path(f"data/testing/method_{method}")

    calibrationDataPath = methodPath / "calibration" / "data"
    testingDataPath = methodPath / "testing" / "data"

    calibrationDataPath.mkdir(parents=True, exist_ok=True)
    testingDataPath.mkdir(parents=True, exist_ok=True)

    for i in range(numRuns):
        currentVersion = version + i

        calibrationOutPath = calibrationDataPath / f"v{currentVersion}"
        testingOutPath = testingDataPath / f"v{currentVersion}"

        calibrationOutPath.mkdir(parents=True, exist_ok=True)
        testingOutPath.mkdir(parents=True, exist_ok=True)

        calibrationOutFile = calibrationOutPath / "pas.csv"
        testingOutFile = testingOutPath / "pas.csv"

        weights = getMethodWeights(method)

        print(f"Running version v{currentVersion} with weights: {weights}")

        allYears = set(
            range(cYearFrom, cYearTo + 1)
        )

        allYears.update(
            range(tYearFrom, tYearTo + 1)
        )

        for year in sorted(allYears):
            path = Path(f"data/pas/{year}")

            fNames = [
                file.name
                for file in path.iterdir()
                if file.is_file()
            ]

            for f in fNames:
                print(f"v{currentVersion}: {f}")

                df = pd.read_csv(path / f)

                df["exp_k_rate"] = df.apply(
                    getStrikeoutChance,
                    axis=1,
                    args=(method, weights)
                )

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
                    + [
                        f"{variable}_weight"
                        for variable in weights
                    ]
                ].copy()

                calibrationDf = df[
                    (df["year"] >= cYearFrom) &
                    (df["year"] <= cYearTo)
                ]

                testingDf = df[
                    (df["year"] >= tYearFrom) &
                    (df["year"] <= tYearTo)
                ]

                if len(calibrationDf) > 0:
                    calibrationDf.to_csv(
                        calibrationOutFile,
                        mode="a",
                        header=not calibrationOutFile.exists(),
                        index=False
                    )

                if len(testingDf) > 0:
                    testingDf.to_csv(
                        testingOutFile,
                        mode="a",
                        header=not testingOutFile.exists(),
                        index=False
                    )

        print(f"Finished generating v{currentVersion}")
            
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
            
def logisticRegression(method, version):
    methodPath = Path(f"data/testing/method_{method}")

    pasPath = (
        methodPath /
        "calibration" /
        "data" /
        f"v{version}" /
        "pas.csv"
    )

    outputPath = (
        methodPath /
        "calibration" /
        "logisticRegression.csv"
    )

    if not pasPath.exists():
        print(
            f"No calibration data found for "
            f"method {method}, version {version}"
        )
        return

    print(
        f"Running logistic regression for "
        f"method {method}, v{version}"
    )

    df = pd.read_csv(pasPath)

    df["date"] = pd.to_datetime(df["date"])

    df["exp_k_rate"] = pd.to_numeric(
        df["exp_k_rate"]
    )

    df["isStrikeout"] = pd.to_numeric(
        df["isStrikeout"]
    )

    weightColumns = [
        column
        for column in df.columns
        if column.endswith("_weight")
    ]

    weights = {
        column: df[column].iloc[0]
        for column in weightColumns
    }

    results = []

    def calculateResults(
        groupDf,
        groupType,
        group,
        month=np.nan,
        lowerBound=np.nan,
        upperBound=np.nan
    ):
        p = (
            groupDf["exp_k_rate"] / 100
        ).clip(1e-6, 1 - 1e-6)

        y = groupDf["isStrikeout"]

        brierScore = np.mean(
            (p - y) ** 2
        )

        logLoss = -np.mean(
            y * np.log(p) +
            (1 - y) * np.log(1 - p)
        )

        expectedLogit = np.log(
            p / (1 - p)
        )

        # -----------------------------------------
        # Debug information
        # -----------------------------------------

        print()
        print("=" * 60)
        print(
            f"DEBUG: method={method}, "
            f"version={version}, "
            f"group_type={groupType}, "
            f"group={group}"
        )
        print("=" * 60)

        print(f"n: {len(groupDf)}")

        print(
            f"isStrikeout unique: "
            f"{y.nunique()}"
        )

        print(
            f"isStrikeout counts:\n"
            f"{y.value_counts().to_dict()}"
        )

        print(
            f"exp_k_rate unique: "
            f"{groupDf['exp_k_rate'].nunique()}"
        )

        print(
            f"exp_k_rate min: "
            f"{groupDf['exp_k_rate'].min()}"
        )

        print(
            f"exp_k_rate max: "
            f"{groupDf['exp_k_rate'].max()}"
        )

        print(
            f"exp_k_rate mean: "
            f"{groupDf['exp_k_rate'].mean()}"
        )

        print(
            f"exp_k_rate std: "
            f"{groupDf['exp_k_rate'].std()}"
        )

        print(
            f"expectedLogit unique: "
            f"{expectedLogit.nunique()}"
        )

        print(
            f"expectedLogit min: "
            f"{expectedLogit.min()}"
        )

        print(
            f"expectedLogit max: "
            f"{expectedLogit.max()}"
        )

        print(
            f"expectedLogit mean: "
            f"{expectedLogit.mean()}"
        )

        print(
            f"expectedLogit std: "
            f"{expectedLogit.std()}"
        )

        print(
            f"NaN exp_k_rate: "
            f"{groupDf['exp_k_rate'].isna().sum()}"
        )

        print(
            f"NaN expectedLogit: "
            f"{np.isnan(expectedLogit).sum()}"
        )

        print(
            f"Inf expectedLogit: "
            f"{np.isinf(expectedLogit).sum()}"
        )

        print(
            f"exp_k_rate <= 0: "
            f"{(groupDf['exp_k_rate'] <= 0).sum()}"
        )

        print(
            f"exp_k_rate >= 100: "
            f"{(groupDf['exp_k_rate'] >= 100).sum()}"
        )

        print(f"Weights: {weights}")

        # -----------------------------------------
        # Logistic regression
        # -----------------------------------------

        X = sm.add_constant(
            expectedLogit
        )

        try:
            regression = sm.Logit(
                y,
                X
            ).fit(disp=False)

        except Exception as e:
            print()
            print("!!! LOGISTIC REGRESSION FAILED !!!")
            print(
                f"Error type: {type(e).__name__}"
            )
            print(
                f"Error: {e}"
            )
            print(
                f"Group: {groupType} = {group}"
            )
            print(
                f"Version: {version}"
            )
            print(
                f"n: {len(groupDf)}"
            )
            print("=" * 60)
            print()

            raise

        intercept = regression.params.iloc[0]
        slope = regression.params.iloc[1]

        interceptSE = regression.bse.iloc[0]
        slopeSE = regression.bse.iloc[1]

        interceptZ = regression.tvalues.iloc[0]
        slopeZ = regression.tvalues.iloc[1]

        interceptP = regression.pvalues.iloc[0]
        slopeP = regression.pvalues.iloc[1]

        interceptCI = (
            regression.conf_int().iloc[0]
        )

        slopeCI = (
            regression.conf_int().iloc[1]
        )

        logLikelihood = regression.llf
        pseudoR2 = regression.prsquared

        result = {
            "method": method,
            "version": version,
            "group_type": groupType,
            "group": group,
            "month": month,
            "lower_bound": lowerBound,
            "upper_bound": upperBound,
            "n": len(groupDf),
            "mean_exp_k_rate":
                groupDf["exp_k_rate"].mean(),
            "actual_k_rate":
                y.mean() * 100,
            "calibration_error":
                y.mean() * 100 -
                groupDf["exp_k_rate"].mean(),
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
            "intercept_ci_low":
                interceptCI.iloc[0],
            "intercept_ci_high":
                interceptCI.iloc[1],
            "slope_ci_low":
                slopeCI.iloc[0],
            "slope_ci_high":
                slopeCI.iloc[1],
            "log_likelihood":
                logLikelihood,
            "pseudo_r2":
                pseudoR2
        }

        result.update(weights)

        return result

    results.append(
        calculateResults(
            df,
            "overall",
            "all"
        )
    )

    bins = [
        0, 5, 10, 15, 20, 25,
        30, 35, 40, 45, 50, 100
    ]

    labels = [
        "0-5%",
        "5-10%",
        "10-15%",
        "15-20%",
        "20-25%",
        "25-30%",
        "30-35%",
        "35-40%",
        "40-45%",
        "45-50%",
        "50%+"
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

        results.append(
            calculateResults(
                groupDf,
                "k_rate_bin",
                str(group),
                lowerBound=groupDf["exp_k_rate"].min(),
                upperBound=groupDf["exp_k_rate"].max()
            )
        )

    df["month"] = df["date"].dt.month

    for month, monthDf in df.groupby("month"):
        results.append(
            calculateResults(
                monthDf,
                "month",
                str(month),
                month=month
            )
        )

    resultsDf = pd.DataFrame(results)

    resultsDf.to_csv(
        outputPath,
        mode="a",
        header=not outputPath.exists(),
        index=False
    )

    print(
        f"Saved calibration regression "
        f"results for v{version}"
    )
    
def testCalibration(method, model):
    version = model

    methodPath = Path(
        f"data/testing/method_{method}"
    )

    pasPath = (
        methodPath /
        "testing" /
        "data" /
        f"v{version}" /
        "pas.csv"
    )

    outputPath = (
        methodPath /
        "testing" /
        "results.csv"
    )

    if not pasPath.exists():
        print(
            f"No testing data found for "
            f"method {method}, version {version}"
        )
        return

    print(
        f"Running testing for "
        f"method {method}, v{version}"
    )

    df = pd.read_csv(pasPath)

    df["date"] = pd.to_datetime(df["date"])

    df["exp_k_rate"] = pd.to_numeric(
        df["exp_k_rate"]
    )

    df["isStrikeout"] = pd.to_numeric(
        df["isStrikeout"]
    )

    weightColumns = [
        column
        for column in df.columns
        if column.endswith("_weight")
    ]

    weights = {
        column: df[column].iloc[0]
        for column in weightColumns
    }

    results = []

    def calculateResults(
        groupDf,
        groupType,
        group,
        month=np.nan,
        lowerBound=np.nan,
        upperBound=np.nan
    ):
        p = (
            groupDf["exp_k_rate"] / 100
        ).clip(1e-6, 1 - 1e-6)

        y = groupDf["isStrikeout"]

        brierScore = np.mean(
            (p - y) ** 2
        )

        logLoss = -np.mean(
            y * np.log(p) +
            (1 - y) * np.log(1 - p)
        )

        result = {
            "method": method,
            "version": version,
            "group_type": groupType,
            "group": group,
            "month": month,
            "lower_bound": lowerBound,
            "upper_bound": upperBound,
            "n": len(groupDf),
            "mean_exp_k_rate": groupDf["exp_k_rate"].mean(),
            "actual_k_rate": y.mean() * 100,
            "calibration_error":
                y.mean() * 100 -
                groupDf["exp_k_rate"].mean(),
            "brier_score": brierScore,
            "log_loss": logLoss
        }

        result.update(weights)

        return result

    results.append(
        calculateResults(
            df,
            "overall",
            "all"
        )
    )

    bins = [
        0, 5, 10, 15, 20, 25,
        30, 35, 40, 45, 50, 100
    ]

    labels = [
        "0-5%",
        "5-10%",
        "10-15%",
        "15-20%",
        "20-25%",
        "25-30%",
        "30-35%",
        "35-40%",
        "40-45%",
        "45-50%",
        "50%+"
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

        results.append(
            calculateResults(
                groupDf,
                "k_rate_bin",
                str(group),
                lowerBound=groupDf["exp_k_rate"].min(),
                upperBound=groupDf["exp_k_rate"].max()
            )
        )

    df["month"] = df["date"].dt.month

    for month, monthDf in df.groupby("month"):
        results.append(
            calculateResults(
                monthDf,
                "month",
                str(month),
                month=month
            )
        )

    resultsDf = pd.DataFrame(results)

    resultsDf.to_csv(
        outputPath,
        mode="a",
        header=not outputPath.exists(),
        index=False
    )

    print(
        f"Saved testing results for v{version}"
    )

def getVersion(method):
    path = Path(
        f"data/testing/method_{method}/testing/results.csv"
    )

    if not path.exists():
        return 0

    df = pd.read_csv(
        path,
        usecols=["version"]
    )

    if len(df) == 0:
        return 0

    return int(df["version"].iloc[-1]) + 1

def deletePAs(method, version):
    methodPath = Path(f"data/testing/method_{method}")

    calibrationPath = (
        methodPath /
        "calibration" /
        "data" /
        f"v{version}"
    )

    testingPath = (
        methodPath /
        "testing" /
        "data" /
        f"v{version}"
    )

    if calibrationPath.exists():
        shutil.rmtree(calibrationPath)

    if testingPath.exists():
        shutil.rmtree(testingPath)

def runModel(method, cYearFrom, cYearTo, tYearFrom, tYearTo, numRuns):
    startVersion = getVersion(method)
    
    for i in range(numRuns):    
        getPATestingData(cYearFrom, cYearTo, tYearFrom, tYearTo, method, 1, startVersion + i)
        logisticRegression(method, startVersion + i)
        testCalibration(method, startVersion + i)
        deletePAs(method, startVersion + i)
        
if __name__ == '__main__':
    method = "003"
    runs = 2991
    #testModelNumbers(2024, 2025, "001")
    #getPATestingData(2024, 2025, 2026, 2026, method, runs)
    #logisticRegression(method)
    #testCalibration(method, "all")
    runModel(method, 2024, 2025, 2026, 2026, runs)
