"""
This script contains functions to process
play-by-play data with on-court player ID information
to split the game into possessions and allocate
points accordingly
"""

import pandas as pd

def create_turnover_play(play: pd.Series):
    """ This helper function allocates the team
    turning the ball over to the offense, the
    other team to the defense, and points to zero

    Args:
        play (pd.Series): Pandas series for an
            individual play

    Returns:
        play_df (pd.DataFrame): One-row DataFrame
            in RAPM format
    """

    

def isolate_possessions(pbp_df: pd.DataFrame):
    """ This function isolates all possessions
    within a game and converts home/away player IDs
    into offensive and defensive IDs and allocates
    points accordingly

    Args:
        pbp_df (pd.DataFrame): DataFrame of play-by-play
            data with home/away player IDs

    Returns:
        poss_df (pd.DataFrame): DataFrame of
            possessions with offensive/defensive IDs
            and points scored
    """

    # Initialize possession DataFrame
    poss_df = pd.DataFrame()

    # Loop through each play
    for index, row in pbp_df.iterrows():
        # This is a turnover, so it's fairly straightforward
        # to allocate offense, defense, and points
        if row["eventmsgtype"] == 5:
            play_df = create_turnover_play(row)