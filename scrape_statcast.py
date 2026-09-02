from requests import get
import pandas as pd, numpy as np
from io import StringIO
from datetime import datetime, timedelta

url = "https://baseballsavant.mlb.com/statcast_search/csv"

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
    # "foul_tip_bunt",
    "missed_bunt",
    "foul_tip",
    "swinging_pitchout"
}

CALLED_STRIKE_DESCRIPTIONS = {
    "called_strike",
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

AB_EVENTS = {
    "single",
    "double",
    "triple",
    "home_run",
    "field_out",
    "force_out",
    "field_error",
    "fielders_choice",
    "fielders_choice_out",
    "grounded_into_double_play",
    "double_play",
    "triple_play",
    "strikeout",
    "strikeout_double_play",
    "other_out",
    "catcher_interf"
}

HIT_EVENTS = {
    "single",
    "double",
    "triple",
    "home_run"
}

def pitchOutOfZone(zone):
    return zone >= 11 or zone <= 14

def isChase(row):
    return row["pitch_out_of_zone"] and row["swing"]

def isPutawayPitch(row):
    return row["strikes"] == 2 and row["events"] == "strikeout"

def getParams(mlbid, startDate, endDate, position):
    if position == "batter":
        return {
            "all": "true",

            # Season type
            "hfGT": "R|",

            # Season
            "hfSea": "2026|2025|2024",

            "player_type": "batter",

            # Dates
            "game_date_gt": startDate,
            "game_date_lt": endDate,

            "batters_lookup[]": str(mlbid),

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
    elif position == "pitcher":
        return {
            "all": "true",

            # Season type
            "hfGT": "R|",

            # Season
            "hfSea": "2026|2025|2024",

            "player_type": "pitcher",

            # Dates
            "game_date_gt": startDate,
            "game_date_lt": endDate,

            "pitchers_lookup[]": str(mlbid),

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

def getRawPitches(mlbid, startDate, endDate, position):
    params = getParams(mlbid, startDate, endDate, position)
    
    response = get(url, params=params, timeout=10)
    response.raise_for_status()
    print(response.url)

    df = pd.read_csv(StringIO(response.text))
    df = df[
        [
            "pitch_type",
            "pitch_name",
            "game_date",
            "release_speed",
            "player_name",
            "batter",
            "pitcher",
            "events",
            "description",
            "zone",
            "stand",
            "p_throws",
            "balls",
            "strikes",
            "game_year",
            "umpire",
            "game_pk",
            "n_thruorder_pitcher",
            "n_priorpa_thisgame_player_at_bat",
            "pitcher_days_since_prev_game",
            "arm_angle",
        ]
    ]
    
    df["pitch_group"] = df["pitch_type"].map(PITCH_GROUPINGS)

    df["swing"] = df["description"].isin(
        SWING_DESCRIPTIONS
    )

    df["whiff"] = df["description"].isin(
        WHIFF_DESCRIPTIONS
    )

    df["called_strike"] = df["description"].isin(
        CALLED_STRIKE_DESCRIPTIONS
    )
    
    df["pitch_out_of_zone"] = df["zone"].map(pitchOutOfZone)

    df["chase"] = df.apply(isChase, axis=1)
    
    df["two_strike_pitch"] = df["strikes"] == 2

    df["putaway_pitch"] = df.apply(isPutawayPitch, axis=1)

    df["at_bat_vs_pitcher"] = np.minimum(
        df["n_thruorder_pitcher"],
        df["n_priorpa_thisgame_player_at_bat"] + 1
    )
    
    df["isAB"] = df["events"].isin(AB_EVENTS)
    df["isHit"] = df["events"].isin(HIT_EVENTS)

    if len(df) == 0:
        raise RuntimeError(
            "Baseball Savant returned zero rows.\n"
        )

    df["batter"] = pd.to_numeric(
        df["batter"],
        errors="coerce"
    )
    
    df = df.dropna(subset=["pitch_type"])
    if position == "batter":
        df = df[df["batter"] == mlbid].copy()
    elif position == "pitcher":
        df = df[df["pitcher"] == mlbid].copy()
    
    return df

def addStatPercentages(stats):
    stats["cstr_pct"] = (
        stats["called_strikes"]
        / stats["pitches"]
        * 100
    )
    
    stats["csw_pct"] = (
        (
            stats["called_strikes"]
            + stats["whiffs"]
        )
        / stats["pitches"]
        * 100
    )

    stats["whiff_pct"] = (
        stats["whiffs"]
        / stats["swings"]
        * 100
    )

    stats["swstr_pct"] = (
        stats["whiffs"]
        / stats["pitches"]
        * 100
    )
    
    stats["chase_pct"] = (
        stats["chases"]
        / stats["pitches_ooz"]
        * 100
    )
    
    stats["putaway_pct"] = (
        stats["putaways"]
        / stats["putaway_pitches"]
        * 100
    )
    
    stats["batting_avg"] = (
        stats["hits"]
        / stats["at_bats"]
    )
    
    stats["pitch_group"] = stats["pitch_type"].map(PITCH_GROUPINGS)
    stats["usage"] = (stats["pitches"] / stats["pitches"].sum() * 100).round(2)
    stats["putaway_usg"] = (stats["putaway_pitches"] / stats["putaway_pitches"].sum() * 100).round(2)
    
    stats["cstr_pct"] = stats["cstr_pct"].round(2)
    stats["csw_pct"] = stats["csw_pct"].round(2)
    stats["whiff_pct"] = stats["whiff_pct"].round(2)
    stats["swstr_pct"] = stats["swstr_pct"].round(2)
    stats["chase_pct"] = stats["chase_pct"].round(2)
    stats["putaway_pct"] = stats["putaway_pct"].round(2)
    stats["batting_avg"] = stats["batting_avg"].round(3)

def condenseStats(stats):
    stats = stats[
       [
            "pitch_type",
            "pitch_name",
            "pitch_group",
            "pitches",
            "usage",
            "called_strikes",
            "whiffs",
            "csw_pct",
            "swings",
            "whiff_pct",
            "swstr_pct",
            "cstr_pct",
            "chase_pct",
            "putaway_pct",
            "putaway_usg",
            "batting_avg"
        ]
    ]

def groupBatterByPitchType(df, byZone):
    if byZone:
        grouping = ["pitch_type", "pitch_name", "zone"]
    else:
        grouping = ["pitch_type", "pitch_name"]
        
    stats = (
        df.groupby(
            grouping,
            dropna=False
        )
        .agg(
            pitches=("pitch_type", "size"),

            called_strikes=("called_strike", "sum"),

            swings=("swing", "sum"),

            whiffs=("whiff", "sum"),
        
            pitches_ooz=("pitch_out_of_zone", "sum"),
            
            chases=("chase", "sum"),
            
            putaway_pitches=("two_strike_pitch", "sum"),
            
            putaways=("putaway_pitch", "sum"),
            
            at_bats=("isAB", "sum"),
            
            hits=("isHit", "sum")
        )
        .reset_index()
    )
    
    stats = stats.sort_values(
        "pitches",
        ascending=False
    )
    
    addStatPercentages(stats)
    
    return stats

def groupBatterByPitchGroup(df, byZone):
    if byZone:
        grouping = ["pitch_group", "zone"]
    else:
        grouping = ["pitch_group"]
        
    stats = (
        df.groupby(
            grouping,
            dropna=False
        )
        .agg(
            pitches=("pitch_group", "size"),

            called_strikes=("called_strike", "sum"),

            swings=("swing", "sum"),

            whiffs=("whiff", "sum"),
        
            pitches_ooz=("pitch_out_of_zone", "sum"),
            
            chases=("chase", "sum"),
            
            putaway_pitches=("two_strike_pitch", "sum"),
            
            putaways=("putaway_pitch", "sum"),
            
            at_bats=("isAB", "sum"),
            
            hits=("isHit", "sum")
        )
        .reset_index()
    )
    
    stats = stats.sort_values(
        "pitches",
        ascending=False
    )
    
    addStatPercentages(stats)
    
    return stats

def groupBatter(df, byZone):
    if byZone:
        grouping = ["batter", "zone"]
    else:
        grouping = ["batter"]
        
    stats = (
        df.groupby(
            grouping,
            dropna=False
        )
        .agg(
            pitches=("pitch_group", "size"),

            called_strikes=("called_strike", "sum"),

            swings=("swing", "sum"),

            whiffs=("whiff", "sum"),
        
            pitches_ooz=("pitch_out_of_zone", "sum"),
            
            chases=("chase", "sum"),
            
            putaway_pitches=("two_strike_pitch", "sum"),
            
            putaways=("putaway_pitch", "sum"),
            
            at_bats=("isAB", "sum"),
            
            hits=("isHit", "sum")
        )
        .reset_index()
    )
    
    stats = stats.sort_values(
        "pitches",
        ascending=False
    )
    
    addStatPercentages(stats)
    
    return stats