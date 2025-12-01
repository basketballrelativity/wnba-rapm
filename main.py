"""
This script contains the main functions to
produce and validate RAPM-style play-by-play
observations for a given game
"""
import argparse

import pandas as pd

import data
import etl

def main(game_id: int):
    """ This function pulls in the RAPM-style
    possession data and validates the total
    points scored for each team by comparing it
    to box score data

    Args:
        game_id (int): The ID of the game to process.

    Returns:
        poss_df (pd.DataFrame): DataFrame of
            possessions with offensive/defensive IDs
            and points scored
    """

    # Pull play-by-play and box score data
    pbp_df = data.ingest_pbp_data(game_id)
    box_df = data.ingest_boxscore_data(game_id)

    # Derive RAPM-style possession_data
    poss_df = etl.isolate_possessions(pbp_df, game_id)

    # Validate total points
    score_df = pd.DataFrame(poss_df.groupby("offensive_team_id")["points"].sum()).reset_index()
    comb_df = score_df.merge(box_df, left_on="offensive_team_id", right_on="team_id")
    
    # Confirm
    assert (comb_df["points_x"]==comb_df["points_y"]).all(), f"Points don't match! \n{comb_df}"

    return poss_df

def get_args():
    """ This function adds a command line interface
    to feed a game ID into this script

    Returns:
        args (argparse.Namespace): Command line argument
            containing the game ID to process
    """

    parser = argparse.ArgumentParser(description="CLI for producing RAPM-style possesion data")
    parser.add_argument("--game_id", help="The ID of the game to process.")

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = get_args()
    poss_df = main(int(args.game_id))