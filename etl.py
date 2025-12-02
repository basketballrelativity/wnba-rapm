"""
This script contains functions to process
play-by-play data with on-court player ID information
to split the game into possessions and allocate
points accordingly
"""

import pandas as pd

import data


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
        points (int): Number of points scored on the possession
            prior to the rebound
        remove_shot (int): Event number of the field goal to remove
            from the RAPM-style accounting for field goals
    """

    # We're looking for the shot immediately preceding the rebound
    rebound_event = play["eventnum"]

    # Isolate to missed field goals or the last missed free throw on
    # a trip to the line
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
                ) &
                (
                    (pbp_df["homedescription"].str.contains("1 of 1", na=False)) |
                    (pbp_df["visitordescription"].str.contains("1 of 1", na=False)) |
                    (pbp_df["homedescription"].str.contains("2 of 2", na=False)) |
                    (pbp_df["visitordescription"].str.contains("2 of 2", na=False)) |
                    (pbp_df["homedescription"].str.contains("3 of 3", na=False)) |
                    (pbp_df["visitordescription"].str.contains("3 of 3", na=False))
                )
            )
        )
    ].sort_values("eventnum")

    # If the shot is a qualified miss, we'll move on
    # If not, the rebound won't be processed
    if len(shot) > 0:
        shot = shot.iloc[-1]
    else:
        return False, 0, -1

    # We need to account for missed free throws either containing
    # a made field-goal (And 1) or prior made free throw(s) by
    # the same player at the same time
    remove_shot = -1
    if shot["eventmsgtype"] == 3:
        # Isolate to this possession
        poss_df = pbp_df[
            (
                pbp_df["eventnum"] > last_possession
            ) &
            (
                pbp_df["eventnum"] < rebound_event
            )
        ]

        # Identify any made shots by the player at the line
        made_shot_df = poss_df[
            (
                poss_df["eventmsgtype"]==1
            ) &
            (
                poss_df["player1_id"] == shot["player1_id"]
            )
        ]

        # Identify any missed shots by the player at the line. These
        # are filtered out of consideration for a RAPM-style possession
        # downstream
        missed_shot_df = poss_df[
            (
                poss_df["eventmsgtype"]==2
            ) &
            (
                poss_df["player1_id"] == shot["player1_id"]
            )
        ]
        if len(made_shot_df) > 0:
            # We'll take the last made shot on a possession (which should only be one anyway)
            made_shot = made_shot_df.iloc[-1]
            if ("3PT" in str(made_shot["homedescription"])) or ("3PT" in str(made_shot["visitordescription"])):
                points = 3
            else:
                points = 2
            
            made_free_throw_df = poss_df[
                (
                    poss_df["eventmsgtype"]==3
                ) &
                (
                    (
                        ~poss_df["homedescription"].str.contains("MISS", na=False)
                    ) &
                    (
                        ~poss_df["visitordescription"].str.contains("MISS", na=False)
                    )
                )
            ]
            points += len(made_free_throw_df)
            
            # Remove the made shot from being used as a separate possession
            # since we're accounting for it here
            remove_shot = made_shot["eventnum"]
        else:
            # Need to account for previous made free throws, so
            # this just tallies non-made free throws and adds the
            # total to points
            made_free_throw_df = poss_df[
            (
                poss_df["eventmsgtype"]==3
            ) &
            (
                (
                    ~poss_df["homedescription"].str.contains("MISS", na=False)
                ) &
                (
                    ~poss_df["visitordescription"].str.contains("MISS", na=False)
                )
            )
        ]
            points = len(made_free_throw_df)

            # Need to account for missed shots and remove those from
            # identifying the end of possessions that result in free throws
            if len(missed_shot_df) > 0:
                missed_shot = missed_shot_df.iloc[-1]
                remove_shot = missed_shot["eventnum"]
    else:
        points = 0

    # This is a defensive rebound if the rebounding team ID
    # does not equal the offensive team ID
    def_rebound = (shot["player1_team_id"] != play["player1_team_id"]) and (shot["player1_team_id"] != play["player1_id"])

    return def_rebound, points, remove_shot


def determine_scoring_type(play: pd.Series, pbp_df: pd.DataFrame, last_possession: int, home_id: int):
    """ This function finds the final made shot on a possesion
    and totals the number of points scored on that possession

    Args:
        play (pd.Series): Pandas series for an
            individual play
        pbp_df (pd.DataFrame): DataFrame of play-by-play
            data with home/away player IDs
        last_possession (int): Event number of the end of
            the last possession
        home_id (int): Integer identifier for the home
            team

    Returns:
        valid_shot (bool): Boolean indicating whether the shot
            constitutes the end of the possession
        points (int): Number of points scored on the possession
        remove_shot (int): Event number of the field goal to remove
            from the RAPM-style accounting for field goals
    """

    # We're looking for the shot immediately preceding the rebound
    shot_event = play["eventnum"]
    remove_shot = -1
    desc = "homedescription" if play["player1_team_id"] == home_id else "visitordescription"

    # We need to isolate to the possession of interest to identify potential
    # points scored before the possession concludes
    poss_df = pbp_df[
            (
                pbp_df["eventnum"] > last_possession
            ) &
            (
                pbp_df["eventnum"] <= shot_event
            )
        ]
    valid_shot = True
    if play["eventmsgtype"] == 1:
        if ("3PT" in str(play["homedescription"])) or ("3PT" in str(play["visitordescription"])):
            points = 3
        else:
            points = 2
        
        made_free_throw_df = poss_df[
                (
                    poss_df["eventmsgtype"]==3
                ) &
                (
                    (
                        ~poss_df[desc].str.contains("MISS", na=False)
                    ) 
                )
            ]
        points += len(made_free_throw_df)
    else:
        made_free_throw_df = poss_df[
                (
                    poss_df["eventmsgtype"]==3
                ) &
                (
                    poss_df["player1_id"] == play["player1_id"]
                ) &
                (
                    (
                        ~poss_df[desc].str.contains("MISS", na=False)
                    )
                )
            ]
        if len(made_free_throw_df) > 0:
            made_shot_df = poss_df[
                (
                    poss_df["eventmsgtype"]==1
                ) &
                (
                    poss_df["player1_id"] == play["player1_id"]
                )
            ]
            if len(made_shot_df) > 0:
                made_shot = made_shot_df.iloc[-1]
                if ("3PT" in str(made_shot[desc])):
                    points = 3
                else:
                    points = 2
                
                remove_shot = made_shot["eventnum"]
            else:
                points = 0
            made_free_throw_df = poss_df[
                (
                    poss_df["eventmsgtype"]==3
                ) &
                (
                    (
                        ~poss_df[desc].str.contains("MISS", na=False)
                    )
                )
            ]
            points += len(made_free_throw_df)
        else:
            valid_shot = False
            points = 0

    return valid_shot, points, remove_shot
    

def create_turnover_play(play: pd.Series, home_id: int, visitor_id: int):
    """ This helper function allocates the team
    turning the ball over to the offense, the
    other team to the defense, and points to zero

    Args:
        play (pd.Series): Pandas series for an
            individual play
        home_id (int): Integer identifier for the home
            team
        visitor_id (int): Integer identifier for the visiting
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
        off_id = home_id
        def_id = visitor_id
    else:
        off_prefix = "visitor_"
        def_prefix = "home_"
        off_id = visitor_id
        def_id = home_id
    
    # Initialize play DataFrame with 0 points
    play_df = pd.DataFrame(
        {
            "points": [0],
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


def create_rebound_play(play: pd.Series, home_id: int, visitor_id: int, points: int):
    """ This helper function allocates the team
    rebounding the ball over to the defense, the
    other team to the offense, and points to zero

    Args:
        play (pd.Series): Pandas series for an
            individual play
        home_id (int): Integer identifier for the home
            team
        visitor_id (int): Integer identifier for the visiting
            team
        points (int): Number of points scored on the
            possession

    Returns:
        play_df (pd.DataFrame): One-row DataFrame
            in RAPM format
    """

    # Player 1 corresponds to the player rebounding
    # the ball, so his team is on defense
    if play["player1_team_id"] == home_id:
        off_prefix = "visitor_"
        def_prefix = "home_"
        off_id = visitor_id
        def_id = home_id
    else:
        off_prefix = "home_"
        def_prefix = "visitor_"
        off_id = home_id
        def_id = visitor_id
    
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


def create_scoring_play(play: pd.Series, home_id: int, visitor_id: int, points: int):
    """ This helper function allocates the team
    scoring the ball over to the offense, the
    other team to the defense, and points to points

    Args:
        play (pd.Series): Pandas series for an
            individual play
        home_id (int): Integer identifier for the home
            team
        visitor_id (int): Integer identifier for the visiting
            team
        points (int): Number of points scored on the
            possession

    Returns:
        play_df (pd.DataFrame): One-row DataFrame
            in RAPM format
    """

    # Player 1 corresponds to the player scoring
    # the ball, so his team is on offense
    if play["player1_team_id"] == home_id:
        off_prefix = "home_"
        def_prefix = "visitor_"
        off_id = home_id
        def_id = visitor_id
    else:
        off_prefix = "visitor_"
        def_prefix = "home_"
        off_id = visitor_id
        def_id = home_id
    
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
    poss_df = pd.DataFrame(columns=["eventnum"])
    last_possession = 0

    # Pull game information
    game_df = data.ingest_game_data(game_id)
    home_id = game_df['home_team_id'].values[0]
    visitor_id = game_df['visitor_team_id'].values[0]

    # Loop through each play
    for index, row in pbp_df.iterrows():
        # This is a turnover, so it's fairly straightforward
        # to allocate offense, defense, and points
        if row["eventmsgtype"] == 5:
            play_df = create_turnover_play(row, home_id, visitor_id)
            last_possession = row["eventnum"]

            poss_df = pd.concat([poss_df, play_df])
        # This is a rebound, but only defensive rebounds end
        # possessions, so we need to identify those
        elif row["eventmsgtype"] == 4:
            def_rebound, points, remove_shot = determine_rebound_type(row, pbp_df, last_possession)
            if def_rebound:
                play_df = create_rebound_play(row, home_id, visitor_id, points)
                last_possession = row["eventnum"]
                poss_df = poss_df[poss_df["eventnum"] != remove_shot]
                poss_df = pd.concat([poss_df, play_df])

            # Reset rebound boolean
            def_rebound = False
        elif row["eventmsgtype"] in [1, 3]:
            valid_shot, points, remove_shot = determine_scoring_type(row, pbp_df, last_possession, home_id)
            if valid_shot:
                play_df = create_scoring_play(row, home_id, visitor_id, points)
                last_possession = row["eventnum"]
                poss_df = poss_df[poss_df["eventnum"] != remove_shot]
                poss_df = pd.concat([poss_df, play_df])

            # Reset shot boolean
            valid_shot = False

    return poss_df