"""
This script contains functions to process
play-by-play data with on-court player ID information
to split the game into possessions and allocate
points accordingly
"""

import pandas as pd

import data

def create_turnover_play(play: pd.Series, home_id: int):
    """ This helper function allocates the team
    turning the ball over to the offense, the
    other team to the defense, and points to zero

    Args:
        play (pd.Series): Pandas series for an
            individual play
        home_id (int): Integer identifier for the home
            team

    Returns:
        play_df (pd.DataFrame): One-row DataFrame
            in RAPM format
    """

    # Player 1 corresponds to the player committing
    # the turnover, so his team is on offense
    if play["player1_team_id"] == home_id:
        off_prefix = "home_"
        def_prefix = "visitor_"
    else:
        off_prefix = "visitor_"
        def_prefix = "home_"
    
    # Initialize play DataFrame with 0 points
    play_df = pd.DataFrame({"points": [0], "eventnum": [play["eventnum"]]})

    # Loop through to add 
    for player_number in range(1, 6):
        play_df["offensive_player_" + str(player_number)] = play[off_prefix + "player_" + str(player_number)]
        play_df["defensive_player_" + str(player_number)] = play[def_prefix + "player_" + str(player_number)]

    return play_df


def determine_rebound_type(play: pd.Series, pbp_df: pd.DataFrame, last_possession: int):
    """ This function determines whether a particular rebound
    is offensive (continuing a possession) or defensive
    (ending a possession)

    Args:
        play (pd.Series): Pandas series for an
            individual play
        pbp_df (pd.DataFrame): DataFrame of play-by-play
            data with home/away player IDs
        last_possession (int): Event number of the end of
            the last possession

    Returns:
        def_rebound (bool): Boolean indicating whether the
            rebound was defensive or not
    """

    # We're looking for the shot immediately preceding the rebound
    rebound_event = play["eventnum"]

    # Isolate to missed field goals or missed free throw
    shot = pbp_df[
        (pbp_df["eventnum"] > last_possession) &
        (pbp_df["eventnum"] < rebound_event) &
        (
            (pbp_df["eventmsgtype"]==2) | # Missed field goal
            (
                (pbp_df["eventmsgtype"]==3) &
                (
                    (pbp_df["homedescription"].str.contains("MISS", na=False)) |
                    (pbp_df["visitordescription"].str.contains("MISS", na=False)) 
                )
            )
        )
    ].sort_values("eventnum").iloc[-1]

    # This is a defensive rebound if the rebounding team ID
    # does not equal the offensive team ID
    def_rebound = shot["player1_team_id"] != play["player1_team_id"]

    return def_rebound


def create_rebound_play(play: pd.Series, home_id: int):
    """ This helper function allocates the team
    rebounding the ball over to the defense, the
    other team to the offense, and points to zero

    Args:
        play (pd.Series): Pandas series for an
            individual play
        home_id (int): Integer identifier for the home
            team

    Returns:
        play_df (pd.DataFrame): One-row DataFrame
            in RAPM format
    """

    # Player 1 corresponds to the player rebounding
    # the ball, so his team is on defense
    if play["player1_team_id"] == home_id:
        off_prefix = "visitor_"
        def_prefix = "home_"
    else:
        off_prefix = "home_"
        def_prefix = "visitor_"
    
    # Initialize play DataFrame with 0 points
    play_df = pd.DataFrame({"points": [0], "eventnum": [play["eventnum"]]})

    # Loop through to add 
    for player_number in range(1, 6):
        play_df["offensive_player_" + str(player_number)] = play[off_prefix + "player_" + str(player_number)]
        play_df["defensive_player_" + str(player_number)] = play[def_prefix + "player_" + str(player_number)]

    return play_df


def isolate_possessions(pbp_df: pd.DataFrame, game_id: int):
    """ This function isolates all possessions
    within a game and converts home/away player IDs
    into offensive and defensive IDs and allocates
    points accordingly

    Args:
        pbp_df (pd.DataFrame): DataFrame of play-by-play
            data with home/away player IDs
        game_id (int): The ID of the game to process.

    Returns:
        poss_df (pd.DataFrame): DataFrame of
            possessions with offensive/defensive IDs
            and points scored
    """

    # Initialize possession DataFrame
    poss_df = pd.DataFrame()
    last_possession = 0

    # Pull game information
    game_df = data.ingest_game_data(game_id)
    home_id = game_df['home_team_id'].values[0]

    # Loop through each play
    for index, row in pbp_df.iterrows():
        # This is a turnover, so it's fairly straightforward
        # to allocate offense, defense, and points
        if row["eventmsgtype"] == 5:
            play_df = create_turnover_play(row, home_id)
            last_possession = row["eventnum"]

            poss_df = pd.concat([poss_df, play_df])
        # This is a rebound, but only defensive rebounds end
        # possessions, so we need to identify those
        elif row["eventmsgtype"] == 4:
            def_rebound = determine_rebound_type(row, pbp_df, last_possession)
            if def_rebound:
                play_df = create_rebound_play(row, home_id)
                last_possession = row["eventnum"]
                poss_df = pd.concat([poss_df, play_df])

            # Reset rebound boolean
            def_rebound = False

    return poss_df