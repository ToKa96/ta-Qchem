"""

Author: Tobias Kaczun
"""

import dataclasses
import pandas as pd

# TODO: test if this has to be updated


class ADCData:

    def __init__(self, filename):
        self.filename = filename
        self.pump_probe = None

    def setData(self, keys, dfs):
        if isinstance(keys, list) or isinstance(dfs, list):
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

    def get_pump_probe_data(self, pump):
        return {'exc_energy': self.pump_probe.loc[pump, 'Excitation energy'].to_numpy(),
                'osc_strength': self.pump_probe.loc[pump, 'Osc. strength'].to_numpy(),
                }

    def get_pump_states(self):
        return self.pump_probe.index.unique(level=0)
