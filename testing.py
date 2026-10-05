from scraping_information import *
from datetime import datetime, date, timedelta
import json, pandas as pd, time, random
from scrape_statcast import *
from pathlib import Path
from scrape_data import getMonthResults, getYearResults, getTotalResults
import statsmodels.api as sm
import shutil
from stabilization import getStabilizedValue, getStabilizationWeight

LEAGUE_K_PCT = 22.28

STABILIZATION_PARAMS = {
    "bK%": {"midpoint": 40, "steepness": 0.0175},
    "pK%": {"midpoint": 35, "steepness": 0.0175},
    "bWhiff%": {"midpoint": 35, "steepness": 0.0250},
    "pWhiff%": {"midpoint": 35, "steepness": 0.0250},
    "bPutaway%": {"midpoint": 75, "steepness": 0.01},
    "pPutaway%": {"midpoint": 40, "steepness": 0.0225},
    "bChase%": {"midpoint": 200, "steepness": 0.005},
    "pChase%": {"midpoint": 100, "steepness": 0.0075},
    "bCSW%": {"midpoint": 50, "steepness": 0.005},
    "pCSW%": {"midpoint": 50, "steepness": 0.005},
}

WEIGHT_RANGES = {
    "K%": (0.7, 0.97),
    "bK%": (0.7, 0.98),
    "Whiff%": (0.00475, 0.3),
    "bWhiff%": (0.4, 0.6),
    "Putaway%": (0.02, 0.08),
    "bPutaway%": (0.5, 0.5),
    "Chase%": (0.0015, 0.06),
    "bChase%": (0.5, 0.5),
    "CSW%": (0.001, 0.06),
    "bCSW%": (0.5, 0.5),
    "SwStr%": (0.0, 1.0)
}

AVERAGES = pd.read_csv("data/averages.csv")

def getMethodVariables(method):
    if method == "001" or method == "004":
        return ["bK%"]
    elif method == "002" or method == "006":
        return ["bK%", "pK%"]
    elif method == "003":
        return ["bK%", "pbK%", "pK%", "ppK%"]
    elif method == "004":
        return ["bK%", "pbK%", "pK%", "ppK%"]
    elif method == "005":
        return ["pK%"]
    elif method == "007":
        return ["bWhiff%", "pWhiff%"]
    elif method == "008":
        return ["bK%", "pK%", "bWhiff%", "pWhiff%"]
    elif method == "009" or method == "015":
        return ["K%", "Whiff%"]
    elif method == "010" or method == "012":
        return ["K%", "Whiff%", "Putaway%"]
    elif method == "011" or method == "013":
        return ["K%", "Whiff%", "Putaway%", "Chase%"]
    elif method == "014":
        return ["K%", "Whiff%", "Putaway%", "Chase%", "CSW%"]
       
def getMethodWeights(method):
    variables = getMethodVariables(method)
    weights = dict()
    varWeights = dict()
    
    for var in variables:
        bRange = WEIGHT_RANGES["b" + var]
        weights["b" + var] = random.uniform(*bRange)
        weights["p" + var] = 1 - weights["b" + var]
        
        weightRange = WEIGHT_RANGES[var]
        varWeights[var] = random.uniform(*weightRange)

    total = sum(varWeights.values())

    varWeights = {variable: weight / total for variable, weight in varWeights.items()}
    
    weights = weights | varWeights

    return weights

def getTrueValues(pa, variables):
    trueValues = {}

    for variable in variables:
        for pre in ["p", "b"]:
            params = STABILIZATION_PARAMS[pre + variable]

            trueValues[pre + variable] = getStabilizedValue(pa, pre + variable, params["midpoint"], params["steepness"])

    return trueValues

def getCombinedVals(trueVals, variables, weights):
    combinedVals = {}

    for variable in variables:
        bValue = trueVals.get("b" + variable, np.nan)
        pValue = trueVals.get("p" + variable, np.nan)

        bWeight = weights["b" + variable]
        pWeight = weights["p" + variable]

        values = []
        usedWeights = []

        if pd.notna(bValue):
            values.append(bValue)
            usedWeights.append(bWeight)
        elif variable == "K%":
            values.append(LEAGUE_K_PCT)
            usedWeights.append(bWeight)

        if pd.notna(pValue):
            values.append(pValue)
            usedWeights.append(pWeight)
        elif variable == "K%":
            values.append(LEAGUE_K_PCT)
            usedWeights.append(pWeight)

        if len(values) == 0:
            continue

        weightTotal = sum(usedWeights)

        usedWeights = [
            weight / weightTotal
            for weight in usedWeights
        ]

        combinedVals[variable] = sum(
            value * weight
            for value, weight in zip(values, usedWeights)
        )

    return combinedVals

def getStrikeoutChance(pa, method, weights):
    variables = getMethodVariables(method)

    trueVals = getTrueValues(
        pa,
        variables
    )

    combinedVals = getCombinedVals(
        trueVals,
        variables,
        weights
    )

    vars = []
    usedWeights = []

    for variable in variables:
        value = combinedVals.get(variable, np.nan)

        if pd.notna(value):
            vars.append(value)
            usedWeights.append(weights[variable])

    if len(vars) == 0:
        return LEAGUE_K_PCT

    weightTotal = sum(usedWeights)

    usedWeights = [
        weight / weightTotal
        for weight in usedWeights
    ]

    exp_k_rate = sum(
        value * weight
        for value, weight in zip(vars, usedWeights)
    )

    return exp_k_rate

def getStrikeoutChanceVectorized(df, method, weights):
    variables = getMethodVariables(method)
    exp_k_rate_df = pd.DataFrame(index=df.index)
    
    for var in variables:
        # Map League Averages for this variable using a MultiIndex lookup
        lookup_series = AVERAGES.set_index(['bSide', 'pSide'])[var]
        lg_val = df.set_index(['bSide', 'pSide']).index.map(lookup_series).values
        
        # Convert to Series and fallback to LEAGUE_K_PCT if missing
        lg_series = pd.Series(lg_val, index=df.index)
        if var == "K%":
            lg_series = lg_series.fillna(LEAGUE_K_PCT)

        for pre in ["p", "b"]:
            col_name = pre + var
            prev_col_name = "p" + col_name
            pa_col = pre + "PA"
            prev_pa_col = "p" + pre + "PA"

            params = STABILIZATION_PARAMS[col_name]
            mid = params["midpoint"]
            steep = params["steepness"]

            # Fill missing PAs with 0
            cur_pa = df[pa_col].fillna(0)
            prev_pa = df[prev_pa_col].fillna(0)
            player_pa = cur_pa + prev_pa

            cur_val = df[col_name]
            prev_val = df[prev_col_name]

            # Establish valid masks
            cur_valid = (cur_pa > 0) & cur_val.notna()
            prev_valid = (prev_pa > 0) & prev_val.notna()

            # Vectorized exponential weights
            cur_weight = 1 / (1 + np.exp(-steep * (cur_pa - mid)))
            player_weight = 1 / (1 + np.exp(-steep * (player_pa - mid)))

            # Player value logic
            player_value = lg_series.copy()
            
            # Both Valid
            both_mask = cur_valid & prev_valid
            player_value = np.where(
                both_mask, 
                cur_val * cur_weight + prev_val * (1 - cur_weight), 
                player_value
            )

            # Only Current Valid
            cur_only_mask = cur_valid & ~prev_valid
            player_value = np.where(cur_only_mask, cur_val, player_value)

            # Only Previous Valid
            prev_only_mask = ~cur_valid & prev_valid
            player_value = np.where(prev_only_mask, prev_val, player_value)

            # Calculate true stabilized value
            true_val = player_value * player_weight + lg_series * (1 - player_weight)
            exp_k_rate_df[f"true_{col_name}"] = true_val

        # Combine Pitcher and Batter True Values
        b_weight = weights["b" + var]
        p_weight = weights["p" + var]
        exp_k_rate_df[f"comb_{var}"] = (
            exp_k_rate_df[f"true_b{var}"] * b_weight + 
            exp_k_rate_df[f"true_p{var}"] * p_weight
        )
        
    # Combine all core variables into the final expected K rate
    final_exp_k_rate = pd.Series(0.0, index=df.index)
    weight_total = sum(weights[var] for var in variables)
    
    for var in variables:
        normalized_weight = weights[var] / weight_total
        final_exp_k_rate += exp_k_rate_df[f"comb_{var}"] * normalized_weight
        
    return final_exp_k_rate
                
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

def loadPAData(yearFrom, yearTo):
    dfs = []

    for year in range(yearFrom, yearTo + 1):
        path = Path(f"data/pas/{year}")

        for file in path.iterdir():
            if not file.is_file():
                continue

            print(f"Loading {year}: {file.name}")

            df = pd.read_csv(file)
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True)

def getPATestingData(pas, cYearFrom, cYearTo, tYearFrom, tYearTo, method, numRuns, version, returnPAs):
    methodPath = Path(f"data/testing/method_{method}")

    calibrationDataPath = methodPath / "calibration" / "data"
    testingDataPath = methodPath / "testing" / "data"

    calibrationDataPath.mkdir(parents=True, exist_ok=True)
    testingDataPath.mkdir(parents=True, exist_ok=True)

    for i in range(numRuns):
        currentVersion = version + i

        weights = getMethodWeights(method)

        print(f"Running version v{currentVersion} with weights: {weights} at {datetime.now()}")

        df = pas.copy()

        df["exp_k_rate"] = getStrikeoutChanceVectorized(df, method, weights)

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

        if not returnPAs:
            calibrationOutPath = calibrationDataPath / f"v{currentVersion}"
            testingOutPath = testingDataPath / f"v{currentVersion}"

            calibrationOutPath.mkdir(parents=True, exist_ok=True)
            testingOutPath.mkdir(parents=True, exist_ok=True)

            calibrationOutFile = calibrationOutPath / "pas.csv"
            testingOutFile = testingOutPath / "pas.csv"
            
            if len(calibrationDf) > 0:
                calibrationDf.to_csv(
                    calibrationOutFile,
                    index=False
                )

            if len(testingDf) > 0:
                testingDf.to_csv(
                    testingOutFile,
                    index=False
                )

        print(
            f"Finished generating v{version}  at {datetime.now()}"
        )
        
        return calibrationDf, testingDf
            
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
            
def logisticRegression(method, version, df=None):
    methodPath = Path(
        f"data/testing/method_{method}"
    )

    outputPath = (
        methodPath /
        "calibration" /
        "logisticRegression.csv"
    )
    
    if df is None:
        pasPath = (
            methodPath /
            "calibration" /
            "data" /
            f"v{version}" /
            "pas.csv"
        )

        if not pasPath.exists():
            print(
                f"No calibration data found for "
                f"method {method}, version {version}"
            )
            return
        
        df = pd.read_csv(pasPath)

    print(
        f"Running logistic regression for "
        f"method {method}, v{version} at {datetime.now()}"
    )

    df["date"] = pd.to_datetime(
        df["date"]
    )

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

        # Default regression values
        intercept = np.nan
        slope = np.nan

        interceptSE = np.nan
        slopeSE = np.nan

        interceptZ = np.nan
        slopeZ = np.nan

        interceptP = np.nan
        slopeP = np.nan

        interceptCILow = np.nan
        interceptCIHigh = np.nan

        slopeCILow = np.nan
        slopeCIHigh = np.nan

        logLikelihood = np.nan
        pseudoR2 = np.nan

        # Logistic regression requires both
        # 0 and 1 outcomes.
        if y.nunique() >= 2 and len(groupDf) >= 15:
            X = sm.add_constant(
                expectedLogit
            )

            try:
                regression = sm.Logit(
                    y,
                    X
                ).fit(disp=False)

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

                interceptCILow = interceptCI.iloc[0]
                interceptCIHigh = interceptCI.iloc[1]

                slopeCILow = slopeCI.iloc[0]
                slopeCIHigh = slopeCI.iloc[1]

                logLikelihood = regression.llf
                pseudoR2 = regression.prsquared

            except Exception as e:
                print()
                print("=" * 60)
                print(
                    "!!! LOGISTIC REGRESSION FAILED !!!"
                )
                print("=" * 60)

                print(
                    f"Error type: {type(e).__name__}"
                )
                print(
                    f"Error: {e}"
                )

                print(
                    f"Method: {method}"
                )
                print(
                    f"Version: {version}"
                )
                print(
                    f"Group type: {groupType}"
                )
                print(
                    f"Group: {group}"
                )
                print(
                    f"n: {len(groupDf)}"
                )

                print(
                    f"isStrikeout unique: "
                    f"{y.nunique()}"
                )

                print(
                    f"isStrikeout counts: "
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

                print(
                    f"Weights: {weights}"
                )

                print("=" * 60)
                print()

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
                interceptCILow,
            "intercept_ci_high":
                interceptCIHigh,
            "slope_ci_low":
                slopeCILow,
            "slope_ci_high":
                slopeCIHigh,
            "log_likelihood":
                logLikelihood,
            "pseudo_r2":
                pseudoR2
        }

        result.update(weights)

        return result

    # Overall
    results.append(
        calculateResults(
            df,
            "overall",
            "all"
        )
    )

    # K-rate bins
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
                lowerBound=
                    groupDf["exp_k_rate"].min(),
                upperBound=
                    groupDf["exp_k_rate"].max()
            )
        )

    # Months
    df["month"] = df["date"].dt.month

    for month, monthDf in df.groupby(
        "month"
    ):
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
        f"results for v{version} at {datetime.now()}"
    )
    
    overallResult = results[0] 
    return overallResult["intercept"], overallResult["slope"]
    
def testCalibration(method, model, slope, intercept, df=None):
    version = model

    methodPath = Path(
        f"data/testing/method_{method}"
    )

    outputPath = (
        methodPath /
        "testing" /
        "results.csv"
    )
    
    if df is None:
        pasPath = (
            methodPath /
            "testing" /
            "data" /
            f"v{version}" /
            "pas.csv"
        )

        if not pasPath.exists():
            print(
                f"No testing data found for "
                f"method {method}, version {version}"
            )
            return
        
        df = pd.read_csv(pasPath)

    print(
        f"Running testing for "
        f"method {method}, v{version} at {datetime.now()}"
    )

    df["date"] = pd.to_datetime(df["date"])

    df["exp_k_rate"] = pd.to_numeric(
        df["exp_k_rate"]
    )

    df["isStrikeout"] = pd.to_numeric(
        df["isStrikeout"]
    )
    
    if pd.notna(intercept) and pd.notna(slope):
        p = (df["exp_k_rate"] / 100).clip(1e-6, 1 - 1e-6)
        expectedLogit = np.log(p / (1 - p))
        
        calibratedLogit = intercept + slope * expectedLogit
        
        calibrated_p = 1 / (1 + np.exp(-calibratedLogit))
        df["exp_k_rate"] = calibrated_p * 100
    # ---------------------------------------------------------

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
        f"Saved testing results for v{version} at {datetime.now()}"
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
    pas = loadPAData(cYearFrom, tYearTo)
    
    for i in range(numRuns):    
        regressionDf, testingDf = getPATestingData(pas, cYearFrom, cYearTo, tYearFrom, tYearTo, method, 1, startVersion + i, True)
        
        intercept, slope = logisticRegression(method, startVersion + i, regressionDf)
        
        testCalibration(method, startVersion + i, slope, intercept, testingDf)
        
        deletePAs(method, startVersion + i)
        
if __name__ == '__main__':
    method = "015"
    runs = 5000
    #testModelNumbers(2024, 2025, "001")
    #getPATestingData(2024, 2025, 2026, 2026, method, runs)
    #logisticRegression(method)
    #testCalibration(method, "all")
    runModel(method, 2024, 2025, 2026, 2026, runs)
