import h5py
import traceback
import numpy as np
import scipy as sp

# FIXME: no normalization condition implemented
# FIXME: only pump states with name X_(1)_A currently working!
# FIXME: what happens if time array is not ordered?
# TODO: add checks that warn if different amount of structures are used 
#       at different times!

def lorentzian(x, exc, osc, std_devi=0.4):
    if np.isnan(exc) or np.isnan(osc):
        return np.zeros_like(x)
    elif osc == 0:
        return np.zeros_like(x)
    else:
        return osc /(1 +  np.power( (x - exc) / (std_devi/2), 2))
    
def getMesh(filepath, wavelength_arr, time_arr, **kwargs):
    
    kwargs = kwargs
    
    return ConstructMesh(wavelength_arr, time_arr, **kwargs)._getMesh(filepath).z

class TAMesh():
    
    def __init__(self, x, y, meshgrid) -> None:
        self.z = meshgrid
        self.x = x
        self.y = y
        
    
        

class ConstructMesh():
    
    def __init__(self,wavelength_arr, time_arr, adiabatic=False, std_devi=0.4) -> None:
        self.std_devi=0.4
        self.wavelength_arr = wavelength_arr
        self.time_arr = time_arr
        self.adiabatic = adiabatic

    def _calcStateSpectra(self, exc_arr, osc_arr):
        
        y = np.zeros_like(self.wavelength_arr)
        
        for exc, osc in zip(exc_arr, osc_arr):
            y += lorentzian(self.wavelength_arr, exc, osc, std_devi=self.std_devi)
        
        return y
    
    def _getStructurSpectra(self, structurGroup):
        
        y = np.zeros_like(self.wavelength_arr)
        
        poptype = 'pop'
        k = 1
        
        if self.adiabatic:
            poptype = 'diapop'
            k = 2
        
        for i, pop in enumerate(structurGroup[poptype]):
            if pop > 0:
                # S1 (i = 1) is mapped on 2_(1)_XX as ground state is 1_(1)_XX therefore i+1
                pumpName = '{}_(1)_A'.format(i+k)
                y += pop * self._calcStateSpectra(structurGroup[pumpName + '/exc_energy'], structurGroup[pumpName + '/osc_strength'])
                
        return y
    
    def _getTimeSpectra(self, timeGroup):
        
        y = np.zeros_like(self.wavelength_arr)
        
        # FIXME: should attributes at the structurlevel be added this will make problems!
        for structur in timeGroup.keys():
            y += self._getStructurSpectra(timeGroup[structur])
            
        return y
    
    def _buildMesh(self, hdf5File):
        
        mesh = np.zeros((self.time_arr.shape[0], self.wavelength_arr.shape[0]), dtype=np.float64)
        
        time_str_list = np.asarray(list(hdf5File.keys()))
        time_fl_list = np.asarray([float(i) for i in time_str_list])
        
        for i, time in enumerate(self.time_arr):

                ind = np.where(time_fl_list == time)
                time_str = time_str_list[ind][0]
                try:
                    mesh[i] = self._getTimeSpectra(hdf5File[time_str])
                except KeyError:
                    # print(traceback.format_exc())
                    print('{time} not found!'.format(time=time))

        return TAMesh(wavelength_arr, time_arr, mesh)
    
    def _getMesh(self, filepath):
        
        with h5py.File(filepath, 'r') as hdf5File:
            return self._buildMesh(hdf5File)
        

if __name__ == "__main__":
    import os
    hdf5_path = '/export/home/tkaczun/xray-ta/Pyrazine/ta_data.hdf5'
    time_arr = np.arange(59, 75.5, 0.5)
    wavelength_arr = np.linspace(280, 286, 50)
    
    print(getMesh(hdf5_path, wavelength_arr, time_arr))
    # getMesh(os.getcwd() + '/' + hdf5_path, wavelength_arr, time_arr)