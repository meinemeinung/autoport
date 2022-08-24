# -*- coding: utf-8 -*-
"""
Created on Sat Jul  2 16:59:12 2022

@author: ricky
"""

import pandas as pd
import datetime

class Portfolio:
    def __init__(self, path):
        self.path = path
        self.readInput()
    
    def readInput(self):
        update_file = pd.ExcelFile(self.path)
        for sheet in update_file.sheet_names:
            setattr(self, sheet, update_file.parse(sheet_name=sheet))
        self.init_setup = self.init_setup.set_index('field')
        update_file.close()
    
    
    def setTradeDays(self):
        self.date_list = pd.date_range(self., end_date, freq='1D').date