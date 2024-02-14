import numpy as np
import pandas as pd
import yfinance as yf
import copy
import datetime as dt
import configparser
from typing import Dict, List

class Portfolio:
    def __init__(self, file_path: str, config_path: str, start_date: dt.datetime, end_date: dt.datetime) -> None:
        self.file_path = file_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.__date_list = pd.date_range(start_date, end_date, freq='1D')
        self.__set_trading_days(start_date, end_date)
        self.__initialize_portfolio_data()
    
    def __set_trading_days(self, start_date: dt.datetime, end_date: dt.datetime) -> None:
        benchmark_price = yf.download(
            self.config['Tickers']['benchmark'],
            start_date,
            end_date+dt.timedelta(days=1),
            progress=False
            )
        self.__trading_days = pd.to_datetime(benchmark_price.index).tz_localize(None)
    
    def __initialize_portfolio_data(self) -> None:
        file = pd.read_excel(self.file_path, sheet_name=None)

        self.transaction_list = file['trx_list']
        self.corp_act = file['corp_act']
        
        self.port_cash = pd.Series(
            index=self.__date_list,
            dtype=float
            )
        self.port_cash[self.__date_list[0]] = float(file['init_cash'].columns[1])

        self.port_shares = {}
        self.port_shares[self.__date_list[0]] = file['init_port'].set_index('ticker')

        self.port_shares_adj = {}

        self.port_equity = {}
        self.port_total = pd.Series(
            index=self.__date_list,
            dtype=float
            )
        
        self.port_cash_flow = []
        
    def __get_corp_act_on_date(self, date: dt.datetime) -> Dict[str, pd.DataFrame]:
        ca_list = {}
        ca_list['dividend'] = self.corp_act[
            (self.corp_act['ca_type']=='Dividend') & 
            (self.corp_act['payment_date']==date)
            ]
        
        ca_list['stock_split'] = self.corp_act[
            (self.corp_act['ca_type']=='Stock Split') & 
            (self.corp_act['ex_date']==date)
            ]
        
        ca_list['stock_dividend'] = self.corp_act[
            (self.corp_act['ca_type']=='Stock Dividend') & 
            (self.corp_act['ex_date']==date)
        ]

        return ca_list

    def __fill_forward_portfolio_data(self, date: dt.datetime):
        prev_date = self.__date_list[self.__date_list < date].max()
        self.port_cash[date] = self.port_cash[prev_date]
        self.port_shares[date] = copy.deepcopy(self.port_shares[prev_date])

    def __update_portfolio_on_corp_act(self, date: dt.datetime):
        ca_list = self.__get_corp_act_on_date(date)
        self.__update_portfolio_on_dividend(ca_list['dividend'])
        self.__update_portfolio_on_stock_split(ca_list['stock_split'])
        self.__update_portfolio_on_stock_dividend(ca_list['stock_dividend'])

    def __update_portfolio_on_dividend(self, dividends: pd.DataFrame):
        for i, div in dividends.iterrows():
            if div['ticker'] in self.port_shares[div['cum_date']].index:
                share_eligible = self.port_shares[div['cum_date']].loc[
                    div['ticker'], 'amount_of_shares'
                    ]
            else:
                share_eligible = 0
            
            cash_flow = div['price'] * share_eligible * (1 - div['tax'])
            self.port_cash[div['payment_date']] += cash_flow
            self.port_cash_flow.append({'date':div['payment_date'], 'cash_flow':cash_flow, 'type':'dividend'})

    def __update_portfolio_on_stock_split(self, splits: pd.DataFrame):
        for i, split in splits.iterrows():
            current_shares = self.port_shares[split['cum_date']].loc[
                split['ticker'], 'amount_of_shares'
                ]
            avg_price = self.port_shares[split['cum_date']].loc[
                split['ticker'], 'average_price'
                ]

            self.port_shares[split['ex_date']].loc[
                split['ticker'], 'amount_of_shares'
            ] = current_shares * split['ratio_old_new']

            self.port_shares[split['ex_date']].loc[
                split['ticker'], 'average_price'
            ] = avg_price / split['ratio_old_new']

    def __update_portfolio_on_stock_dividend(self, stock_dividends: pd.DataFrame):
        for i, stock_div in stock_dividends.iterrows():
            current_shares = self.port_shares[stock_div['cum_date']].loc[
                stock_div['ticker'], 'amount_of_shares'
            ]

            self.port_shares[stock_div['ex_date']].loc[
                stock_div['ticker'], 'amount_of_shares'
            ] = np.floor(current_shares * (1 + 1/stock_div['ratio_old_new']))

    def __update_portfolio_on_transaction(self, transaction: pd.Series):
        ticker, date = transaction['ticker'], transaction['date']

        if transaction['transaction_type']=='Transfer':

            ## Update Port Cash
            self.port_cash[date] += transaction['price']
            self.port_cash_flow.append({'date':date, 'cash_flow':transaction['price'], 'type':'transfer'})

        elif transaction['transaction_type']=='Buy':

            ## Update Port Cash
            cash_flow = transaction['price'] * transaction['amount'] * (1 + transaction['tax'])
            self.port_cash[date] -= cash_flow
            self.port_cash_flow.append({'date':date, 'cash_flow':-cash_flow, 'type':'purchase'})

            ## Update Port Shares
            if ticker in self.port_shares[date].index:
                avg_price = self.port_shares[date].loc[ticker, 'average_price']
                init_share_amnt = self.port_shares[date].loc[ticker, 'amount_of_shares']
                self.port_shares[date].loc[ticker, 'amount_of_shares'] += transaction['amount']
                self.port_shares[date].loc[ticker, 'average_price'] = \
                (avg_price * init_share_amnt + transaction['price'] * transaction['amount']) / (init_share_amnt + transaction['amount'])
            else:
                self.port_shares[date].loc[ticker, 'amount_of_shares'] = transaction['amount']
                self.port_shares[date].loc[ticker, 'average_price'] = transaction['price']
        
        elif transaction['transaction_type']=='Sell':

            ## Update Port Cash
            cash_flow = transaction['price'] * transaction['amount'] * (1 - transaction['tax'])
            self.port_cash[date] += cash_flow
            self.port_cash_flow.append({'date':date, 'cash_flow':cash_flow, 'type':'purchase'})

            ## Update Port Shares
            self.port_shares[date].loc[ticker, 'amount_of_shares'] -= transaction['amount']

        if transaction['transaction_type'] in ['Buy', 'Sell']:
            self.port_shares[date] = \
            self.port_shares[date][self.port_shares[date]['amount_of_shares'] != 0].sort_index().copy()

    def __compute_port_shares_adj(self):
        self.port_shares_adj = copy.deepcopy(self.port_shares)
        splits = self.corp_act[self.corp_act['ca_type']=='Stock Split']

        for i, split in splits.iterrows():
            update_date = self.__date_list[self.__date_list < split['ex_date']]
            for date in update_date:
                self.port_shares_adj[date].loc[split['ticker'], 'amount_of_shares'] *= split['ratio_old_new']
                self.port_shares_adj[date].loc[split['ticker'], 'average_price'] /= split['ratio_old_new']

    def __compute_market_value(self):
        self.__compute_port_shares_adj()
        ticker_list = pd.concat(self.port_shares_adj).index.get_level_values(1).unique().to_list()
        yf_ticker_list = [ticker + self.config['Tickers']['country'] for ticker in ticker_list]
        price = yf.download(
            yf_ticker_list,
            self.__date_list[0],
            self.__date_list[-1] + dt.timedelta(days=1),
            progress=False
            )
        price.index = pd.to_datetime(price.index).tz_localize(None)
        price = price['Close']
        price.columns = price.columns.str.split('.').str[0]
        for date, holding in self.port_shares_adj.items():
            if date in self.__date_list_trading:
                self.port_equity[date] = copy.deepcopy(holding)
                curr_holding = holding.index
                self.port_equity[date]['market_price'] = price.loc[date, curr_holding]
                self.port_equity[date]['market_value'] = self.port_equity[date]['market_price'] * self.port_equity[date]['amount_of_shares']
            else:
                prev_date = self.__date_list[self.__date_list < date].max()
                self.port_equity[date] = copy.deepcopy(self.port_equity[prev_date])
            self.port_total[date] = self.port_equity[date]['market_value'].sum() + self.port_cash[date]

    def __compute_nav(self):
        cash_flow = pd.DataFrame.from_records(self.port_cash_flow)
        self.subs_redeem = cash_flow[cash_flow['type']=='transfer']
        self.subs_redeem = self.subs_redeem.groupby("date").sum()['cash_flow']
        self.subs_redeem = self.subs_redeem.reindex(self.__date_list, fill_value=0)

        self.port_unit = pd.Series(index=self.__date_list)
        self.port_nav = pd.Series(index=self.__date_list)
        self.port_nav.iloc[0] = 1000

        for i, date in enumerate(self.__date_list):
            if i == 0:
                self.port_unit.loc[date] = self.port_total.loc[date]/self.port_nav.loc[date]
            else:
                prev_date = self.__date_list[i-1]
                unit_created = self.subs_redeem.loc[date]/self.port_nav.loc[prev_date]
                self.port_unit.loc[date] = self.port_unit.loc[prev_date] + unit_created
            self.port_nav.loc[date] = self.port_total.loc[date]/self.port_unit.loc[date]

    def update(self):
        for date in self.__date_list:
            if date != self.__date_list[0]:
                self.__fill_forward_portfolio_data(date)
            self.__update_portfolio_on_corp_act(date)
            transactions = self.transaction_list[self.transaction_list['date']==date]
            for _, row in transactions.iterrows():
                self.__update_portfolio_on_transaction(row)
        
        self.__compute_market_value()
        self.__compute_nav()

    def to_excel(self, file_path):
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            self.transaction_list.to_excel(writer, sheet_name='Transaction')

            cash_flow = pd.DataFrame.from_records(self.port_cash_flow)
            cash_flow.to_excel(writer, sheet_name='Cash Flow')

            self.port_total.to_excel(writer, sheet_name='Total Portfolio')
            
            nav_report = pd.DataFrame({
                'nav':self.port_nav,
                'unit':self.port_unit
            })
            nav_report.to_excel(writer, sheet_name='NAV')

            eqy = pd.concat(self.port_equity)
            eqy['weight'] = eqy['market_value'].div(self.port_total, axis=0, level=0)
            last_eqy = eqy.loc[eqy.index.get_level_values(0).max()]
            last_eqy.to_excel(writer, sheet_name='Current Portfolio')

            self.port_cash.to_excel(writer, sheet_name='Cash Historical')
            eqy.to_excel(writer, sheet_name='Equity Historical')