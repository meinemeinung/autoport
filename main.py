# -*- coding: utf-8 -*-
"""
Created on Sat Jul  2 17:06:20 2022

@author: ricky
"""

import pandas as pd
from Portfolio.portfolio import Portfolio

# init_setup = pd.read_excel('Data/RTR2255_init.xlsx',
#                            sheet_name='init_setup',
#                            index_col='field')
# init_port = pd.read_excel('Data/RTR2255_init.xlsx', sheet_name='init_port')
# transaction = pd.read_excel('Data/RTR2255_init.xlsx', sheet_name='transaction')
# cash = pd.read_excel('Data/RTR2255_init.xlsx', sheet_name='cash')
# corp_act = pd.read_excel('Data/RTR2255_init.xlsx', sheet_name='corp_act')


port = Portfolio('Data/RTR2255_init.xlsx')