import pandas as pd
import numpy as np
from ff_espn_api import League
from keys import league_id, espn_s2, swid

REG_SEASON_END_WEEK = 13
# creates league
# takes arg current_week, ignores it for a complete season
def create_league(year, current_week=16, reg_season_end_week=REG_SEASON_END_WEEK, wild_card=6, league_id=league_id, espn_s2=espn_s2, sw  =swid):
    # using ff_espn_api
    league = League(league_id, year, espn_s2, swid)
    # get a list of columns for our dataframe
    df_columns = list(league.teams[0].__dict__.keys())
    # remove roster from list of columns
    df_columns.remove('roster')

    # instantiate empty dataframe
    league_year = pd.DataFrame()

    # append teams to dataframe
    for d in range(len(league.teams)):
        team_df = pd.DataFrame(league.teams[d].__dict__, columns=df_columns)
        league_year = league_year.append(team_df)


    # add columns
    league_year['delta_points'] = league_year['points_for'] - league_year['points_against']
    leauge_year = week_and_year(league_year, year)
    league_year = draft_order(league_year, league)
    league_year = playoffs(league_year, wild_card)
    league_year = cumsum_score(league_year, reg_season_end_week)
    league_year = overall_win_loss(league_year, current_week, reg_season_end_week, league) # must be last

    print(f'{year} Season complete!')
    return league_year

# creates year and week column
def week_and_year(league_year, year):
    league_year['year'] = year    # add a year column
    league_year.index.names = ['week']    # change index to 'week'

    league_year.reset_index(level='week', inplace=True)
    league_year['week'] = league_year['week'].apply(lambda x: x + 1)
    return league_year

# create draft order column
def draft_order(league_year, league):
    # instantiate empty dictionaries
    team_dict = {}
    league_dict = {}

    # create dictionary of {team name: draft order number}
    for draft_number in range(1, len(league.teams)+1):
        team_name = str(league.draft[draft_number-1].team) # convert to string
        team_name = team_name[5:-1] #eliminates strip 'team' problem
        team_dict = {team_name: draft_number}
        league_dict.update(team_dict)

    league_year['draft_order'] = league_year['team_name'].map(league_dict)

    return league_year

# adds *4* columns for overall win/loss for entire league
def overall_win_loss(league_year, current_week, reg_season_end_week, league):
    # set null values for columns
    league_year['weekly_wins'] = np.nan
    league_year['weekly_losses'] = np.nan
    league_year['weekly_OW'] = np.nan
    league_year['weekly_OL'] = np.nan
    league_year['season_OW'] = np.nan
    league_year['season_OL'] = np.nan



    # weekly_OW/OL columns
    for week in range(current_week + 1):
        # playoffs start at week 13
        if week <= reg_season_end_week:
            win = len(league.teams) - 1
            loss = 0
            # sets W/L for each team
            for i, row in league_year[league_year['week'] == week].sort_values('scores', ascending=False).iterrows():
                league_year['weekly_OW'].iloc[i] = win
                league_year['weekly_OL'].iloc[i] = loss
                win -= 1
                loss += 1
        # values remain the same during playoffs
        else:
            win = 0
            loss = 0
            # sets W/L for each team
            for i, row in league_year[league_year['week'] == week].sort_values('scores', ascending=False).iterrows():
                league_year['weekly_OW'].iloc[i] = win
                league_year['weekly_OL'].iloc[i] = loss
        # print(f'Week {week + 1} complete')

    # season_OW/OL columns AND weekly wins/losses
    for team in league_year['team_id'].unique():
        season_wins = 0
        season_loss = 0

        # change values for wins to manually calulate wins/losses
        weekly_wins = 0
        weekly_losses = 0

        # sets W/L for each team, week by week
        for i, row in league_year[league_year['team_id'] == team].sort_values('week').iterrows():
            season_wins = season_wins + row[-4]
            season_loss = season_loss + row[-3]
            league_year['season_OW'].iloc[i] = season_wins
            league_year['season_OL'].iloc[i] = season_loss

            # checks if regular season
            if league_year['week'].iloc[i] <= reg_season_end_week:
                # adds a win
                if league_year['mov'].iloc[i] > 0:
                    weekly_wins += 1
                    league_year['weekly_wins'].iloc[i] = weekly_wins
                    league_year['weekly_losses'].iloc[i] = weekly_losses
                # adds a loss
                elif league_year['mov'].iloc[i] < 0:
                    weekly_losses += 1
                    league_year['weekly_wins'].iloc[i] = weekly_wins
                    league_year['weekly_losses'].iloc[i] = weekly_losses
                # no need for an else statement
                # does nothing if the game hasn't been played yet
            else:
                league_year['weekly_wins'].iloc[i] = weekly_wins
                league_year['weekly_losses'].iloc[i] = weekly_losses

        # print(f'Team {team} complete')
    return league_year

def playoffs(league_year, wild_card):
    if wild_card == 6:
        league_year['playoffs'] = np.where(league_year['final_standing'] <= 6, 1, 0)
    else:
        # wildcard winner in playoffs
        league_year['playoffs'] = np.where(league_year['final_standing'] == wild_card, 1, league_year['final_standing'])
        # playoffs category for all other teams
        league_year['playoffs'] = np.where(league_year['final_standing'] <= 5, 1, 0)
    return league_year

def cumsum_score(league_year, reg_season_end_week):
    league_year['cumsum_score'] = np.nan
    for team in league_year['team_id'].unique():
        cumulative = 0
        for i, row in league_year[league_year['team_id'] == team].iterrows():
            if league_year['week'].iloc[i] <= reg_season_end_week:
                cumulative = cumulative + league_year['scores'].iloc[i]
            league_year['cumsum_score'].iloc[i] = cumulative

    return league_year
