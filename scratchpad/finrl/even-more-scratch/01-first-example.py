"""First portfolio construction example from FinRL repo:


- https://finrl.readthedocs.io/en/latest/tutorial/Introduction/PortfolioAllocation.html
""" 


import datetime
import importlib.util

import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import os

from gym.utils import seeding
import gym
from gym import spaces
import matplotlib

import matplotlib.pyplot as plt

from finrl.marketdata.yahoodownloader import YahooDownloader
from finrl.preprocessing.preprocessors import FeatureEngineer
from finrl.preprocessing.data import data_split
from finrl.env.environment import EnvSetup
from finrl.env.EnvMultipleStock_train import StockEnvTrain
from finrl.env.EnvMultipleStock_trade import StockEnvTrade
from finrl.model.models import DRLAgent
from finrl.trade.backtest import BackTestStats, BaselineStats, BackTestPlot, backtest_strat, baseline_strat
from finrl.trade.backtest import backtest_strat, baseline_strat
from pyfolio import timeseries


matplotlib.use('Agg')


CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))

CACHE_PATH = os.path.expanduser("~/.cache/tradingstrategy/finrl")



class StockPortfolioEnv(gym.Env):
     """A single stock trading environment for OpenAI gym
     Attributes
     ----------
         df: DataFrame
             input data
         stock_dim : int
             number of unique stocks
         hmax : int
             maximum number of shares to trade
         initial_amount : int
             start money
         transaction_cost_pct: float
             transaction cost percentage per trade
         reward_scaling: float
             scaling factor for reward, good for training
         state_space: int
             the dimension of input features
         action_space: int
             equals stock dimension
         tech_indicator_list: list
             a list of technical indicator names
         turbulence_threshold: int
             a threshold to control risk aversion
         day: int
             an increment number to control date
     Methods
     -------
     _sell_stock()
         perform sell action based on the sign of the action
     _buy_stock()
         perform buy action based on the sign of the action
     step()
         at each step the agent will return actions, then
         we will calculate the reward, and return the next observation.
     reset()
         reset the environment
     render()
         use render to return other functions
     save_asset_memory()
         return account value at each time step
     save_action_memory()
         return actions/positions at each time step

     """
     metadata = {'render.modes': ['human']}

     def __init__(self,
                 df,
                 stock_dim,
                 hmax,
                 initial_amount,
                 transaction_cost_pct,
                 reward_scaling,
                 state_space,
                 action_space,
                 tech_indicator_list,
                 turbulence_threshold,
                 lookback=252,
                 day = 0):
         #super(StockEnv, self).__init__()
         #money = 10 , scope = 1
         self.day = day
         self.lookback=lookback
         self.df = df
         self.stock_dim = stock_dim
         self.hmax = hmax
         self.initial_amount = initial_amount
         self.transaction_cost_pct =transaction_cost_pct
         self.reward_scaling = reward_scaling
         self.state_space = state_space
         self.action_space = action_space
         self.tech_indicator_list = tech_indicator_list

         # action_space normalization and shape is self.stock_dim
         self.action_space = spaces.Box(low = 0, high = 1,shape = (self.action_space,))
         # Shape = (34, 30)
         # covariance matrix + technical indicators
         self.observation_space = spaces.Box(low=0,
                                             high=np.inf,
                                             shape = (self.state_space+len(self.tech_indicator_list),
                                                      self.state_space))

         # load data from a pandas dataframe
         self.data = self.df.loc[self.day,:]
         self.covs = self.data['cov_list'].values[0]
         self.state =  np.append(np.array(self.covs),
                       [self.data[tech].values.tolist() for tech in self.tech_indicator_list ], axis=0)
         self.terminal = False
         self.turbulence_threshold = turbulence_threshold
         # initalize state: inital portfolio return + individual stock return + individual weights
         self.portfolio_value = self.initial_amount

         # memorize portfolio value each step
         self.asset_memory = [self.initial_amount]
         # memorize portfolio return each step
         self.portfolio_return_memory = [0]
         self.actions_memory=[[1/self.stock_dim]*self.stock_dim]
         self.date_memory=[self.data.date.unique()[0]]


     def step(self, actions):
         # print(self.day)
         self.terminal = self.day >= len(self.df.index.unique())-1
         # print(actions)

         if self.terminal:
             df = pd.DataFrame(self.portfolio_return_memory)
             df.columns = ['daily_return']
             plt.plot(df.daily_return.cumsum(),'r')
             plt.savefig('results/cumulative_reward.png')
             plt.close()

             plt.plot(self.portfolio_return_memory,'r')
             plt.savefig('results/rewards.png')
             plt.close()

             print("=================================")
             print("begin_total_asset:{}".format(self.asset_memory[0]))
             print("end_total_asset:{}".format(self.portfolio_value))

             df_daily_return = pd.DataFrame(self.portfolio_return_memory)
             df_daily_return.columns = ['daily_return']
             if df_daily_return['daily_return'].std() !=0:
               sharpe = (252**0.5)*df_daily_return['daily_return'].mean()/ \
                        df_daily_return['daily_return'].std()
               print("Sharpe: ",sharpe)
             print("=================================")

             return self.state, self.reward, self.terminal,{}

         else:
             #print(actions)
             # actions are the portfolio weight
             # normalize to sum of 1
             norm_actions = (np.array(actions) - np.array(actions).min()) / (np.array(actions) - np.array(actions).min()).sum()
             weights = norm_actions
             #print(weights)
             self.actions_memory.append(weights)
             last_day_memory = self.data

             #load next state
             self.day += 1
             self.data = self.df.loc[self.day,:]
             self.covs = self.data['cov_list'].values[0]
             self.state =  np.append(np.array(self.covs), [self.data[tech].values.tolist() for tech in self.tech_indicator_list ], axis=0)
             # calcualte portfolio return
             # individual stocks' return * weight
             portfolio_return = sum(((self.data.close.values / last_day_memory.close.values)-1)*weights)
             # update portfolio value
             new_portfolio_value = self.portfolio_value*(1+portfolio_return)
             self.portfolio_value = new_portfolio_value

             # save into memory
             self.portfolio_return_memory.append(portfolio_return)
             self.date_memory.append(self.data.date.unique()[0])
             self.asset_memory.append(new_portfolio_value)

             # the reward is the new portfolio value or end portfolo value
             self.reward = new_portfolio_value
             #self.reward = self.reward*self.reward_scaling


         return self.state, self.reward, self.terminal, {}

     def reset(self):
         self.asset_memory = [self.initial_amount]
         self.day = 0
         self.data = self.df.loc[self.day,:]
         # load states
         self.covs = self.data['cov_list'].values[0]
         self.state =  np.append(np.array(self.covs), [self.data[tech].values.tolist() for tech in self.tech_indicator_list ], axis=0)
         self.portfolio_value = self.initial_amount
         #self.cost = 0
         #self.trades = 0
         self.terminal = False
         self.portfolio_return_memory = [0]
         self.actions_memory=[[1/self.stock_dim]*self.stock_dim]
         self.date_memory=[self.data.date.unique()[0]]
         return self.state

     def render(self, mode='human'):
         return self.state

     def save_asset_memory(self):
         date_list = self.date_memory
         portfolio_return = self.portfolio_return_memory
         #print(len(date_list))
         #print(len(asset_list))
         df_account_value = pd.DataFrame({'date':date_list,'daily_return':portfolio_return})
         return df_account_value

     def save_action_memory(self):
         # date and close price length must match actions length
         date_list = self.date_memory
         df_date = pd.DataFrame(date_list)
         df_date.columns = ['date']

         action_list = self.actions_memory
         df_actions = pd.DataFrame(action_list)
         df_actions.columns = self.data.tic.values
         df_actions.index = df_date.date
         #df_actions = pd.DataFrame({'date':date_list,'actions':action_list})
         return df_actions

     def _seed(self, seed=None):
         self.np_random, seed = seeding.np_random(seed)
         return [seed]


def dynamic_import(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

config = dynamic_import("config", CURRENT_PATH + "/config.py")
config_tickers = dynamic_import("config_tickers", CURRENT_PATH + "/config_tickers.py")

SAVE_BASE_PATH = os.path.dirname(os.path.realpath(__file__))

os.makedirs(SAVE_BASE_PATH.config.DATA_SAVE_DIR, exist_ok=True)
os.makedirs(SAVE_BASE_PATH.config.TRAINED_MODEL_DIR, exist_ok=True)
os.makedirs(SAVE_BASE_PATH.config.TENSORBOARD_LOG_DIR, exist_ok=True)
os.makedirs(SAVE_BASE_PATH.config.RESULTS_DIR, exist_ok=True)

fname = SAVE_BASE_PATH / "yahoo.csv"


def train(df: pd.DataFrame):
    trade = data_split(df,'2019-01-01', '2020-12-01')
    env_trade, obs_trade = env_setup.create_env_trading(data = trade, env_class = StockPortfolioEnv)
    df_daily_return, df_actions = DRLAgent.DRL_prediction(
        model=model_a2c,
        test_data = trade,
        test_env = env_trade,
        test_obs = obs_trade
    )
    return df_daily_return, df_actions


def setup_data() -> pd.DataFrame:
    # Download and save the data in a pandas DataFrame:
    if not fname.exists():
        data_df = YahooDownloader(start_date = '2008-01-01', end_date = '2020-12-01', ticker_list = config_tickers.DOW_30_TICKER).fetch_data()
        data_df.to_csv(fname)
    else:
        data_df = pd.read_csv(fname)

    #  Perform Feature Engineering:

    df = FeatureEngineer(
            data_df.copy(),
            use_technical_indicator=True,
            use_turbulence=False
        ).preprocess_data()

    # add covariance matrix as states
    df = df.sort_values(['date','tic'],ignore_index=True)
    df.index = df.date.factorize()[0]

    cov_list = []

    # look back is one year
    lookback=252

    for i in range(lookback,len(df.index.unique())):
    data_lookback = df.loc[i-lookback:i,:]
    price_lookback=data_lookback.pivot_table(index = 'date',columns = 'tic', values = 'close')
    return_lookback = price_lookback.pct_change().dropna()
    covs = return_lookback.cov().values
    cov_list.append(covs)

    df_cov = pd.DataFrame({'date':df.date.unique()[lookback:],'cov_list':cov_list})
    df = df.merge(df_cov, on='date')
    df = df.sort_values(['date','tic']).reset_index(drop=True)
    df.head()


def backtest(): 
 DRL_strat = backtest_strat(df_daily_return)
 perf_func = timeseries.perf_stats
 perf_stats_all = perf_func( returns=DRL_strat,
                               factor_returns=DRL_strat,
                                 positions=None, transactions=None, turnover_denom="AGB")
 print("==============DRL Strategy Stats===========")
 perf_stats_all
 print("==============Get Index Stats===========")
 baesline_perf_stats=BaselineStats('^DJI',
                                   baseline_start = '2019-01-01',
                                   baseline_end = '2020-12-01')


 # plot
 dji, dow_strat = baseline_strat('^DJI','2019-01-01','2020-12-01')
 with pyfolio.plotting.plotting_context(font_scale=1.1):
         pyfolio.create_full_tear_sheet(returns = DRL_strat,
                                        benchmark_rets=dow_strat, set_context=False)
    


def main():
    df = setup_data()
    df_daily_return, df_actions = train(df)





if __name__ == "__main__":
    main()