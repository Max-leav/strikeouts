import requests
import pandas as pd
from io import StringIO
import numpy as np
from scrape_statcast import *


# ============================================================
# SETTINGS
# ============================================================

BATTER_ID = 660271

START_DATE = "2026-03-25"
END_DATE   = "2026-08-30"


# ============================================================
# CONVERT INCLUSIVE DATES TO SAVANT'S > / < PARAMETERS
# ============================================================

from datetime import datetime, timedelta

start = datetime.strptime(START_DATE, "%Y-%m-%d")
end = datetime.strptime(END_DATE, "%Y-%m-%d")

game_date_gt = START_DATE
game_date_lt = END_DATE


# ============================================================
# STATCAST CSV URL
# ============================================================
url = "https://baseballsavant.mlb.com/statcast_search/csv"


params = {
    "all": "true",

    # Season type
    "hfGT": "R|",

    # Season
    "hfSea": "2026|2025|2024",

    "player_type": "pitcher",

    # Dates
    "game_date_gt": game_date_gt,
    "game_date_lt": game_date_lt,

    # IMPORTANT:
    # This is the actual Statcast player lookup parameter.
    "batters_lookup[]": str(BATTER_ID),

    # Search settings
    "min_pitches": "0",
    "min_results": "0",
    "min_pas": "0",

    "group_by": "name",

    "sort_col": "pitches",
    "player_event_sort": "api_p_release_speed",
    "sort_order": "desc",

    "min_abs": "0",

    # Raw pitch-level data
    "type": "details",
}


# ============================================================
# REQUEST
# ============================================================

# print("Requesting Baseball Savant...")

# response = requests.get(
#     url,
#     params=params,
#     timeout=10
# )

# print("Status:", response.status_code)
# print("Downloaded:", len(response.content), "bytes")

# print("\nREQUEST URL:")
# print(response.url)

# response.raise_for_status()


# ============================================================
# CHECK RESPONSE
# ============================================================

# print("\nFIRST 500 CHARACTERS OF RESPONSE:")
# print(response.text[:500])


# ============================================================
# READ CSV
# ============================================================

df = getRawPitches(670541, START_DATE, END_DATE, "batter")
LHB = df[df["stand"] == "L"]
RHB = df[df["stand"] == "R"]
LHP = df[df["p_throws"] == "L"]
RHP = df[df["p_throws"] == "R"]

# df = pd.read_csv(StringIO(response.text))
# df = df[
#     [
#         "pitch_type",
#         "pitch_name",
#         "game_date",
#         "release_speed",
#         "player_name",
#         "batter",
#         "pitcher",
#         "events",
#         "description",
#         "zone",
#         "stand",
#         "p_throws",
#         "balls",
#         "strikes",
#         "game_year",
#         "umpire",
#         "game_pk",
#         "n_thruorder_pitcher",
#         "n_priorpa_thisgame_player_at_bat",
#         "pitcher_days_since_prev_game",
#         "arm_angle",
#     ]
# ]

# df.to_csv(
#     "testsize.csv",
#     index=False
# )

# print("\nRows:", len(df))
# print("Columns:", len(df.columns))


# # ============================================================
# # VERIFY BATTER
# # ============================================================

# if len(df) == 0:
#     raise RuntimeError(
#         "Baseball Savant returned zero rows. "
#         "Print the REQUEST URL above and try opening it in your browser."
#     )


# df["batter"] = pd.to_numeric(
#     df["batter"],
#     errors="coerce"
# )

# df = df.dropna(subset=["pitch_type"])
# df = df[df["batter"] == BATTER_ID].copy()

# print("Batter rows:", len(df))


# ============================================================
# PITCH RESULT CLASSIFICATION
# ============================================================

SWING_DESCRIPTIONS = {
    "foul",
    "foul_bunt",
    "foul_tip",
    "swinging_pitchout",
    "swinging_strike",
    "swinging_strike_blocked",
    "hit_into_play",
    "hit_into_play_no_out",
    "hit_into_play_score",
}


WHIFF_DESCRIPTIONS = {
    "swinging_strike",
    "swinging_strike_blocked",
    "foul_tip_bunt",
    "missed_bunt",
    "foul_tip",
    "swinging_pitchout"
}

PITCH_GROUPINGS = {
    "FF": "FB",
    "SI": "FB",
    "FC": "FB",
    "CH": "OS",
    "FS": "OS",
    "FO": "OS",
    "CU": "BR",
    "KC": "BR",
    "CS": "BR",
    "SL": "BR",
    "ST": "BR",
    "SV": "BR",    
}

def pitchOutOfZone(zone):
    return zone < 1 or zone > 9

def isChase(row):
    return row["pitch_out_of_zone"] and row["swing"]

def isPutawayPitch(row):
    return row["strikes"] == 2 and row["events"] == "strikeout"

CALLED_STRIKE_DESCRIPTIONS = {
    "called_strike",
}

# df["pitch_group"] = df["pitch_type"].map(PITCH_GROUPINGS)

# df["swing"] = df["description"].isin(
#     SWING_DESCRIPTIONS
# )

# df["whiff"] = df["description"].isin(
#     WHIFF_DESCRIPTIONS
# )

# df["called_strike"] = df["description"].isin(
#     CALLED_STRIKE_DESCRIPTIONS
# )

# df["pitch_out_of_zone"] = df["zone"].map(pitchOutOfZone)

# df["chase"] = df.apply(isChase, axis=1)

# df["two_strike_pitch"] = df["strikes"] == 2

# df["putaway_pitch"] = df.apply(isPutawayPitch, axis=1)

# df["at_bat_vs_pitcher"] = np.minimum(
#     df["n_thruorder_pitcher"],
#     df["n_priorpa_thisgame_player_at_bat"] + 1
# )


# ============================================================
# GROUP BY PITCH TYPE
# ============================================================

stats = groupBatterByPitchType(df, False)
# stats2 = groupBatter(df, False)
LHB_stats = groupBatterByPitchType(LHB, False)
RHB_stats = groupBatterByPitchType(RHB, False)
LHP_stats = groupBatterByPitchType(LHP, False)
RHP_stats = groupBatterByPitchType(RHP, False)

# stats = (
#     df.groupby(
#         ["pitch_type", "pitch_name"],
#         dropna=False
#     )
#     .agg(
#         pitches=("pitch_type", "size"),

#         called_strikes=("called_strike", "sum"),

#         swings=("swing", "sum"),

#         whiffs=("whiff", "sum"),
        
#         pitches_out_of_zone=("pitch_out_of_zone", "sum"),
        
#         chases=("chase", "sum"),
        
#         two_strike_pitches=("two_strike_pitch", "sum"),
        
#         putaways=("putaway_pitch", "sum")
#     )
#     .reset_index()
# )

# stats["pitch_group"] = stats["pitch_type"].map(PITCH_GROUPINGS)
# stats["usage"] = (stats["pitches"] / stats["pitches"].sum() * 100).round(2)



# ============================================================
# CSW%
# ============================================================

# stats["csw_percent"] = (
#     (
#         stats["called_strikes"]
#         + stats["whiffs"]
#     )
#     / stats["pitches"]
#     * 100
# )


# # ============================================================
# # WHIFF%
# # ============================================================

# stats["whiff_percent"] = (
#     stats["whiffs"]
#     / stats["swings"]
#     * 100
# )

# stats["swstr_percent"] = (
#     stats["whiffs"]
#     / stats["pitches"]
#     * 100
# )

# stats["chase_percent"] = (
#     stats["chases"]
#     / stats["pitches_out_of_zone"]
#     * 100
# )

# stats["putaway_percent"] = (
#     stats["putaways"]
#     / stats["two_strike_pitches"]
#     * 100
# )

# # ============================================================
# # ROUND
# # ============================================================

# stats["csw_percent"] = stats["csw_percent"].round(2)
# stats["whiff_percent"] = stats["whiff_percent"].round(2)
# stats["swstr_percent"] = stats["swstr_percent"].round(2)
# stats["chase_percent"] = stats["chase_percent"].round(2)
# stats["putaway_percent"] = stats["putaway_percent"].round(2)

# ============================================================
# SORT
# ============================================================

# stats = stats.sort_values(
#     ["pitch_type", "pitches"],
#     ascending=[True, False]
# )


# ============================================================
# OUTPUT
# ============================================================

# stats = stats[
#     [
#         "pitch_type",
#         "pitch_name",
#         "pitch_group",
#         "pitches",
#         "usage",
#         "called_strikes",
#         "whiffs",
#         "csw_percent",
#         "swings",
#         "whiff_percent",
#         "swstr_percent",
#         "chase_percent",
#         "putaway_percent"
#     ]
# ]

condenseStats(stats)
condenseStats(LHB_stats)
condenseStats(RHB_stats)
condenseStats(LHP_stats)
condenseStats(RHP_stats)

print("\n")
print("=" * 100)
print("SHOHEI OHTANI — PITCH TYPE STATCAST")
print(f"{START_DATE} through {END_DATE}")
print("=" * 100)

print(
    RHP_stats.to_string(index=False)
)
print(
    LHP_stats.to_string(index=False)
)


# ============================================================
# SAVE
# ============================================================

stats.to_csv(
    "ohtani_pitch_type_stats.csv",
    index=False
)

print("\nSaved: ohtani_pitch_type_stats.csv")