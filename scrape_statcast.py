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
}

HIT_EVENTS = {
    "single",
    "double",
    "triple",
    "home_run"
}

STRIKEOUT_EVENTS = {
    "strikeout",
    "strikeout_double_play"
}

WALK_EVENTS = {
    "intent_walk",
    "walk"
}

ON_BASE_EVENTS = {
    "intent_walk",
    "walk",
    "single",
    "double",
    "triple",
    "home_run",
    "hit_by_pitch"
}

ON_BASE_OPPORTUNITIES = {
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
    "intent_walk",
    "walk",
    "hit_by_pitch",
    "sac_fly"
}

def pitchOutOfZone(zone):
    return zone >= 11 and zone <= 14

def isChase(row):
    return row["pitch_out_of_zone"] and row["swing"]

def isPutawayPitch(row):
    return row["strikes"] == 2 and row["events"] == "strikeout"

def sluggingValue(event):
    if event == "single":
        return 1.0
    elif event == "double":
        return 2.0
    elif event == "triple":
        return 3.0
    elif event == "home_run":
        return 4.0
    else:
        return 0

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

    df["isPA"] = df["events"].notna()
    df["isAB"] = df["events"].isin(AB_EVENTS)
    df["isHit"] = df["events"].isin(HIT_EVENTS)
    df["isStrikeout"] = df["events"].isin(STRIKEOUT_EVENTS)
    df["isWalk"] = df["events"].isin(WALK_EVENTS)
    df["isOnBase"] = df["events"].isin(ON_BASE_EVENTS)
    df["onBaseOpp"] = df["events"].isin(ON_BASE_OPPORTUNITIES)
    df["slug"] = df["events"].map(sluggingValue)

    if len(df) == 0:
        raise RuntimeError(
            "Baseball Savant returned zero rows.\n"
        )
    
    return df

def addStatPercentages(stats, pitchGroup):
    stats["cstr_pct"] = (
        stats["called_strikes"]
        / stats["pitches"]
        * 100
    ).round(2)
    
    stats["csw_pct"] = (
        (
            stats["called_strikes"]
            + stats["whiffs"]
        )
        / stats["pitches"]
        * 100
    ).round(2)

    stats["whiff_pct"] = (
        stats["whiffs"]
        / stats["swings"]
        * 100
    ).round(2)

    stats["swstr_pct"] = (
        stats["whiffs"]
        / stats["pitches"]
        * 100
    ).round(2)
    
    stats["chase_pct"] = (
        stats["chases"]
        / stats["pitches_ooz"]
        * 100
    ).round(2)
    
    stats["putaway_pct"] = (
        stats["putaways"]
        / stats["putaway_pitches"]
        * 100
    ).round(2)
    
    stats["batting_avg"] = (
        stats["hits"]
        / stats["at_bats"]
    ).round(3)

    stats["bb_pct"] = (
        stats["walks"]
        / stats["plate_appearances"] * 100
    ).round(2)

    stats["k_pct"] = (
        stats["strikeouts"]
        / stats["plate_appearances"] * 100
    ).round(2)
    
    stats["obp"] = (
        stats["timesOnBase"]
        / stats["onBaseOpps"]
    ).round(3)
    
    stats["slug_pct"] = (
        stats["slugging"]
        / stats["at_bats"]
    ).round(3) 
    
    stats["ops"] = stats["obp"] + stats["slug_pct"]
    stats["iso"] = stats["slug_pct"] - stats["batting_avg"]
    
    if pitchGroup:
        stats["pitch_group"] = stats["pitch_type"].map(PITCH_GROUPINGS)
    stats["usage"] = (stats["pitches"] / stats["pitches"].sum() * 100).round(2)
    stats["putaway_usg"] = (stats["putaway_pitches"] / stats["putaway_pitches"].sum() * 100).round(2)

def condenseStats(stats, type):
    if type == "overall":
        return stats[
            [
                "plate_appearances",
                "at_bats",
                "pitches",
                "batting_avg",
                "strikeouts",
                "k_pct",
                "walks",
                "bb_pct",
                "obp",
                "slug_pct",
                "ops",
                "iso"
            ]
        ]
    else:
        return stats[
            [
                "pitch_type",
                "pitch_name",
                "pitch_group",
                "pitches",
                "usage",
                "plate_appearances",
                "at_bats",
                "strikeouts",
                "k_pct",
                "walks",
                "bb_pct",
                "swings",
                "whiffs",
                "whiff_pct",
                "swstr_pct",
                "called_strikes",
                "cstr_pct",
                "csw_pct",
                "chase_pct",
                "putaway_usg",
                "putaway_pct",
                "batting_avg",
                "obp",
                "slug_pct",
                "ops",
                "iso"
            ]
        ]

def getGrouping(datatype, byZone):
    grouping = []

    if datatype == "pitch_type":
        grouping  = ["pitch_type", "pitch_name"]
    elif datatype == "pitch_group":
        grouping = ["pitch_group"]
    else:
        grouping = datatype

    if byZone:
        grouping.append("zone")

    return grouping
        
def groupByPitches(df, groupType, byZone):
    grouping = getGrouping(groupType, byZone)
        
    stats = (
        df.groupby(
            grouping,
            dropna=False
        )
        .agg(
            pitches=("batter", "size"),

            called_strikes=("called_strike", "sum"),

            swings=("swing", "sum"),

            whiffs=("whiff", "sum"),
        
            pitches_ooz=("pitch_out_of_zone", "sum"),
            
            chases=("chase", "sum"),
            
            putaway_pitches=("two_strike_pitch", "sum"),
            
            putaways=("putaway_pitch", "sum"),

            plate_appearances=("isPA", "sum"),
            
            at_bats=("isAB", "sum"),
            
            hits=("isHit", "sum"),

            strikeouts=("isStrikeout", "sum"),

            walks=("isWalk", "sum"),
            
            timesOnBase=("isOnBase", "sum"),
            
            onBaseOpps=("onBaseOpp", "sum"),
            
            slugging=("slug", "sum")
        )
        .reset_index()
    )
    
    stats = stats.sort_values(
        "pitches",
        ascending=False
    )
    
    addStatPercentages(stats, True)
    
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
            pitches=("batter", "size"),

            called_strikes=("called_strike", "sum"),

            swings=("swing", "sum"),

            whiffs=("whiff", "sum"),
        
            pitches_ooz=("pitch_out_of_zone", "sum"),
            
            chases=("chase", "sum"),
            
            putaway_pitches=("two_strike_pitch", "sum"),
            
            putaways=("putaway_pitch", "sum"),

            plate_appearances=("isPA", "sum"),
            
            at_bats=("isAB", "sum"),
            
            hits=("isHit", "sum"),

            strikeouts=("isStrikeout", "sum"),

            walks=("isWalk", "sum"),
            
            timesOnBase=("isOnBase", "sum"),
            
            onBaseOpps=("onBaseOpp", "sum"),
            
            slugging=("slug", "sum")
        )
        .reset_index()
    )
    
    stats = stats.sort_values(
        "pitches",
        ascending=False
    )
    
    addStatPercentages(stats, True)
    
    return stats

def groupOverall(df, position, byZone):
    grouping = getGrouping(position, byZone)
        
    stats = (
        df.groupby(
            grouping,
            dropna=False
        )
        .agg(
            pitches=("batter", "size"),

            called_strikes=("called_strike", "sum"),

            swings=("swing", "sum"),

            whiffs=("whiff", "sum"),
        
            pitches_ooz=("pitch_out_of_zone", "sum"),
            
            chases=("chase", "sum"),
            
            putaway_pitches=("two_strike_pitch", "sum"),
            
            putaways=("putaway_pitch", "sum"),

            plate_appearances=("isPA", "sum"),
            
            at_bats=("isAB", "sum"),
            
            hits=("isHit", "sum"),

            strikeouts=("isStrikeout", "sum"),

            walks=("isWalk", "sum"),
            
            timesOnBase=("isOnBase", "sum"),
            
            onBaseOpps=("onBaseOpp", "sum"),
            
            slugging=("slug", "sum")
        )
        .reset_index()
    )
    
    stats = stats.sort_values(
        "pitches",
        ascending=False
    )
    
    addStatPercentages(stats, False)
    
    return stats

if __name__ == '__main__':
    START_DATE = "2026-03-25"
    END_DATE   = "2026-09-02"

    ID = 660271

    df = getRawPitches(ID, START_DATE, END_DATE, "batter")
    LHB = df[df["stand"] == "L"]
    RHB = df[df["stand"] == "R"]
    LHP = df[df["p_throws"] == "L"]
    RHP = df[df["p_throws"] == "R"]

    stats = groupByPitches(df, "pitch_type", False)
    stats2 = groupOverall(df, "batter", False)
    LHB_stats = groupByPitches(LHB, "pitch_type", False)
    RHB_stats = groupByPitches(RHB, "pitch_type", False)
    LHP_stats = groupByPitches(LHP, "pitch_type", False)
    RHP_stats = groupByPitches(RHP, "pitch_type", False)

    stats = condenseStats(stats, "pitch")
    stats2 = condenseStats(stats2, "overall")
    LHB_stats = condenseStats(LHB_stats, "pitch")
    RHB_stats = condenseStats(RHB_stats, "pitch")
    LHP_stats = condenseStats(LHP_stats, "pitch")
    RHP_stats = condenseStats(RHP_stats, "pitch")

    print("\n")
    print("=" * 100)
    print("STATCAST")
    print(f"{START_DATE} through {END_DATE}")
    print("=" * 100)

    print(
        stats2.to_string(index=False)
    )
    # print(
    #     LHP_stats.to_string(index=False)
    # )