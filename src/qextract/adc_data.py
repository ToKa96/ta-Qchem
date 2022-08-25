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

    def set_data(self, keys, dfs):
        if isinstance(keys, list) or isinstance(dfs, list):
            for key, df in zip(keys, dfs):
                self.__dict__[key] = df
        else:
            self.__dict__[keys] = dfs

    def set_other_attr(self, *args):
        for obj in args:
            for key in obj.data:
                self.__dict__[key] = obj.data[key]

    def get_pump_probe_data(self, pump):
        return {'exc_energy': self.pump_probe.loc[pump, 'Excitation energy'].to_numpy(),
                'osc_strength': self.pump_probe.loc[pump, 'Osc. strength'].to_numpy(),
                }

    def get_pump_states(self):
        return self.pump_probe.index.unique(level=0)
