"""

Author: Tobias Kaczun
"""

import pandas as pd


class adcData:

    def __init__(self, filename):
        self.filename = filename

    def setData(self, keys, dfs):
        if isinstance(keys, list) or  isinstance(dfs, list):
            for key, df in zip(keys, dfs):
                self.__dict__[key] = df
        else:
            self.__dict__[keys] = dfs

    def setOtherAttr(self, *args):
        for obj in args:
            for key in obj.data:
                self.__dict__[key] = obj.data[key]

    def __str__(self):
        objStr = '==== adcData =====\n'
        # print(self.__dict__)
        for key in self.__dict__:
            if not isinstance(self.__dict__[key], pd.DataFrame):
                objStr += '    {}: {}\n'.format(key, self.__dict__[key])
            else:
                objStr += '-- {} --\n'.format(key)
                objStr += self.__dict__[key].to_string()
                objStr += '\n'
                objStr += '-------\n'
        return objStr
