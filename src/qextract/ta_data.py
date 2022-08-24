import dataclasses
import numpy as np
import matplotlib.pyplot as plt

@dataclasses.dataclass
class TransientAbsorptionSpectrum():

    ta : np.ndarray
    energy : np.ndarray
    time: np.ndarray 
    e_unit : str = 'eV'
    t_unit : str = 'fs'
    
    def plot(self, save=None, show=True):
    
        plt.figure()
        
        p = plt.pcolormesh(self.energy, self.time, self.ta)
        
        plt.xlabel(f'energy [{self.e_unit}]')
        plt.ylabel(f'time [{self.t_unit}]')
        
        plt.gca().invert_yaxis()
        
        plt.colorbar(p)
        
        if show:
            plt.show()
    
        if save is not None:
            plt.savefig(save)
    
    
class TransientAbsorptionData():
    
    def __init__(self, tensor, energy, time, traj, ) -> None:
        self.tensor = tensor
        self.z = traj
        self.e = energy
        self.t = time.astype(np.float16)
        
    def get_full_ta(self):
        return TransientAbsorptionSpectrum(self.tensor.sum(axis=2), self.e, self.t)
        
