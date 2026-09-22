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

def getStrikeoutChance(pa, method):    
    # if method == "001":
    #     if pd.notna(pa["bK%"]):
    #         return pa["bK%"]
        
    #     if pd.notna(pa["pbK%"]):
    #         return pa["pbK%"]
    variables = getMethodVariables(method)

    vars = []
    weights = []

    for variable in variables:
        value = pa[variable]

        if pd.notna(value):
            vars.append(value)
            weights.append(weights[variable])
            continue

        value = pa[f"p{variable}"]
        
        if pd.notna(value):
            vars.append(value)
            weights.append(weights[variable])
            continue
            
        if "K%" in variable:
            vars.append(LEAGUE_K_PCT)
            weights.append(weights[variable])

    if len(vars) == 0:
        return LEAGUE_K_PCT

    weight_total = sum(weights)

    weights = [weight / weight_total for weight in weights]

    exp_k_rate = sum(value * weight for value, weight in zip(vars, weights))

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
    outPath = Path(f"data/testing/method_{method}")
    outPath.mkdir(parents=True, exist_ok=True)

    outFile = outPath / "pas.csv"

    # Generate the weights ONCE for this method.
    weights = getMethodWeights(method)

    print(f"\nMethod {method} weights:")
    for variable, weight in weights.items():
        print(f"  {variable}: {weight:.6f}")

    # Remove an existing file so repeated runs don't append
    # duplicate PA data.
    if outFile.exists():
        outFile.unlink()

    for year in range(yearFrom, yearTo + 1):

        p = f"data/pas/{year}"
        path = Path(p)

        fNames = [
            file.name
            for file in path.iterdir()
            if file.is_file()
        ]

        for f in fNames:
            print(f"{year}: {f}")

            df = pd.read_csv(f"{path}/{f}")

            df["exp_k_rate"] = df.apply(
                getStrikeoutChance,
                axis=1,
                args=(method, weights)
            )

            # Store the weights in the PA-level CSV.
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
                    "exp_k_rate",
                ]
                + [
                    f"{variable}_weight"
                    for variable in weights
                ]
            ].copy()

            df.to_csv(
                outFile,
                mode="a",
                header=not outFile.exists(),
                index=False
            )

def getPATestingData(yearFrom, yearTo, method, numRuns):
    for i in range(numRuns):
        outPath = Path(f"data/testing/method_{method}/v{i}")
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
                df = df[['gid','date','year','batter','pitcher','isStrikeout','exp_k_rate'] 
                        + [f"{variable}_weight"for variable in weights]].copy()
                
                df.to_csv(
                    outFile,
                    mode="a",
                    header=not outFile.exists(),
                    index=False
                )
            
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

    results = []

    # Find all version directories: v0, v1, v2, ...
    versions = [
        path for path in methodPath.iterdir()
        if path.is_dir() and path.name.startswith("v")
    ]

    # Sort numerically by version number
    versions.sort(key=lambda x: int(x.name[1:]))

    for versionPath in versions:

        version = versionPath.name
        pasFile = versionPath / "pas.csv"

        if not pasFile.exists():
            print(f"Skipping {version}: pas.csv does not exist")
            continue

        print(f"Running logistic regression: method {method}, {version}")

        df = pd.read_csv(pasFile)

        # Get weight columns
        weight_columns = [
            col for col in df.columns
            if col.endswith("_weight")
        ]

        # Get the weights from the first row.
        # They are the same for every PA in this version.
        weights = {}

        for col in weight_columns:
            weights[col] = df[col].iloc[0]

        df = df[
            ["date", "exp_k_rate", "isStrikeout"]
        ].copy()

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

        df["exp_k_rate"] = pd.to_numeric(
            df["exp_k_rate"],
            errors="coerce"
        )

        df["isStrikeout"] = pd.to_numeric(
            df["isStrikeout"],
            errors="coerce"
        )

        df = df.dropna()

        # Convert percentage to probability
        df["exp_k_rate"] /= 100

        df["exp_k_rate_pct"] = df["exp_k_rate"] * 100

        # Prevent log(0)
        df["exp_k_rate"] = df["exp_k_rate"].clip(
            1e-6,
            1 - 1e-6
        )

        df["month"] = df["date"].dt.month

        # --------------------------------------------------
        # Overall Brier score and log loss
        # --------------------------------------------------

        brier_score = np.mean(
            (df["exp_k_rate"] - df["isStrikeout"]) ** 2
        )

        log_loss = -np.mean(
            df["isStrikeout"] * np.log(df["exp_k_rate"])
            + (1 - df["isStrikeout"])
            * np.log(1 - df["exp_k_rate"])
        )

        # --------------------------------------------------
        # Calibration logistic regression
        # --------------------------------------------------

        df["expected_logit"] = np.log(
            df["exp_k_rate"]
            / (1 - df["exp_k_rate"])
        )

        X = sm.add_constant(df["expected_logit"])
        y = df["isStrikeout"]

        model = sm.Logit(y, X).fit(disp=False)

        conf_int = model.conf_int()

        # --------------------------------------------------
        # Add overall results
        # --------------------------------------------------

        overall_result = {
            "version": version,
            "group_type": "overall",
            "group": "overall",
            "month": np.nan,
            "lower_bound": np.nan,
            "upper_bound": np.nan,

            "n": len(df),

            "mean_exp_k_rate":
                df["exp_k_rate"].mean() * 100,

            "actual_k_rate":
                df["isStrikeout"].mean() * 100,

            "calibration_error":
                df["isStrikeout"].mean() * 100
                - df["exp_k_rate"].mean() * 100,

            "brier_score": brier_score,
            "log_loss": log_loss,

            "intercept": model.params["const"],
            "slope": model.params["expected_logit"],

            "intercept_std_error":
                model.bse["const"],

            "slope_std_error":
                model.bse["expected_logit"],

            "intercept_z":
                model.tvalues["const"],

            "slope_z":
                model.tvalues["expected_logit"],

            "intercept_p_value":
                model.pvalues["const"],

            "slope_p_value":
                model.pvalues["expected_logit"],

            "intercept_confidence_low":
                conf_int.loc["const", 0],

            "intercept_confidence_high":
                conf_int.loc["const", 1],

            "slope_confidence_low":
                conf_int.loc["expected_logit", 0],

            "slope_confidence_high":
                conf_int.loc["expected_logit", 1],

            "log_likelihood":
                model.llf,

            "pseudo_r2":
                model.prsquared
        }

        # Add weights to result
        for column, weight in weights.items():
            overall_result[column] = weight

        results.append(overall_result)

        # --------------------------------------------------
        # Function for grouped results
        # --------------------------------------------------

        def add_group(
            group_type,
            group_name,
            group_df,
            month=np.nan,
            lower_bound=np.nan,
            upper_bound=np.nan
        ):

            if len(group_df) == 0:
                return

            group_brier = np.mean(
                (group_df["exp_k_rate"]
                 - group_df["isStrikeout"]) ** 2
            )

            group_log_loss = -np.mean(
                group_df["isStrikeout"]
                * np.log(group_df["exp_k_rate"])
                +
                (1 - group_df["isStrikeout"])
                * np.log(1 - group_df["exp_k_rate"])
            )

            result = {
                "version": version,
                "group_type": group_type,
                "group": group_name,
                "month": month,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,

                "n": len(group_df),

                "mean_exp_k_rate":
                    group_df["exp_k_rate"].mean() * 100,

                "actual_k_rate":
                    group_df["isStrikeout"].mean() * 100,

                "calibration_error":
                    group_df["isStrikeout"].mean() * 100
                    - group_df["exp_k_rate"].mean() * 100,

                "brier_score": group_brier,
                "log_loss": group_log_loss,

                # Regression values don't apply to groups
                "intercept": np.nan,
                "slope": np.nan,
                "intercept_std_error": np.nan,
                "slope_std_error": np.nan,
                "intercept_z": np.nan,
                "slope_z": np.nan,
                "intercept_p_value": np.nan,
                "slope_p_value": np.nan,
                "intercept_confidence_low": np.nan,
                "intercept_confidence_high": np.nan,
                "slope_confidence_low": np.nan,
                "slope_confidence_high": np.nan,
                "log_likelihood": np.nan,
                "pseudo_r2": np.nan
            }

            # Add weights
            for column, weight in weights.items():
                result[column] = weight

            results.append(result)

        # --------------------------------------------------
        # K-rate bins
        # --------------------------------------------------

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

        df["k_rate_group"] = pd.cut(
            df["exp_k_rate_pct"],
            bins=bins,
            labels=labels,
            right=False,
            include_lowest=True
        )

        for i, group in enumerate(labels):

            group_df = df[
                df["k_rate_group"] == group
            ]

            add_group(
                "exp_k_rate",
                group,
                group_df,
                lower_bound=bins[i],
                upper_bound=bins[i + 1]
            )

        # --------------------------------------------------
        # Monthly results
        # --------------------------------------------------

        for month in sorted(df["month"].unique()):

            group_df = df[
                df["month"] == month
            ]

            add_group(
                "month",
                str(int(month)),
                group_df,
                month=int(month)
            )

        # --------------------------------------------------
        # K-rate x month results
        # --------------------------------------------------

        for i, group in enumerate(labels):

            for month in sorted(df["month"].unique()):

                group_df = df[
                    (df["k_rate_group"] == group)
                    &
                    (df["month"] == month)
                ]

                add_group(
                    "exp_k_rate_month",
                    f"{group}_{int(month)}",
                    group_df,
                    month=int(month),
                    lower_bound=bins[i],
                    upper_bound=bins[i + 1]
                )

    # ------------------------------------------------------
    # Save all versions
    # ------------------------------------------------------

    results = pd.DataFrame(results)

    results.to_csv(
        methodPath / "logisticRegression.csv",
        index=False
    )

    print(
        f"\nSaved results to "
        f"{methodPath / 'logisticRegression.csv'}"
    )

if __name__ == '__main__':
    #testModelNumbers(2024, 2025, "001")
    #getPATestingData(2024, 2026, "001")
    logisticRegression("001")
