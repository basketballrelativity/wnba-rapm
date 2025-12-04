"""
This contains several helper
functions to process RAPM-style
play-by-play data
"""

import pandas as pd

def construct_rapm_observation(play: pd.Series, points: int, off_id: int, off_prefix: str, def_id: int, def_prefix: str):
    """ This function creates a one-row DataFrame of offsenive and
    defensive player IDs and points scored

    Args:
        play (pd.Series): Pandas series for an
            individual play
        points (int): Number of points scored on the possession
        off_id (int): Integer identifier for the offensive
            team
        off_prefix (str): Whether the offensive team is "home_"
            or "_visitor"
        def_id (int): Integer identifier for the defensive
            team
        def_prefix (str): Whether the defensive team is "home_"
            or "_visitor"

    Returns:
        play_df (pd.DataFrame): One-row DataFrame
            in RAPM format
    """

    # Initialize play DataFrame with points
    play_df = pd.DataFrame(
        {
            "points": [points],
            "eventnum": [play["eventnum"]],
            "offensive_team_id": [off_id],
            "defensive_team_id": [def_id]
        }
    )

    # Loop through to add 
    for player_number in range(1, 6):
        play_df["offensive_player_" + str(player_number)] = play[off_prefix + "player_" + str(player_number)]
        play_df["defensive_player_" + str(player_number)] = play[def_prefix + "player_" + str(player_number)]

    return play_df