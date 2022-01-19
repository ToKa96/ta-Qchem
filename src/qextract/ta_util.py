import h5py
import traceback
import numpy as np
import scipy as sp

# FIXME: no normalization condition implemented
# FIXME: only pump states with name X_(1)_A currently working!
# FIXME: what happens if time array is not ordered?
# TODO: add checks that warn if different amount of structures are used
#       at different times!

# `values` should be sorted
def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    
    return idx

def lorentzian(x, exc, osc, std_devi=0.4):
    if np.isnan(exc) or np.isnan(osc):
        return np.zeros_like(x)
    elif osc == 0:
        return np.zeros_like(x)
    else:
        return osc / (1 + np.power((x - exc) / (std_devi/2), 2))


def getMesh(filepath, wavelength_arr, time_arr, **kwargs):

    kwargs = kwargs

    return ConstructMesh(wavelength_arr, time_arr, **kwargs)._getMesh(filepath).z


def getTA(filepath, wavelength_arr, time_arr, **kwargs):

    kwargs = kwargs    

    return ConstructMesh(wavelength_arr, time_arr, **kwargs)._getMesh(filepath)

def getTAbyStruct(filepath, wavelength_arr, time_arr, structurname=None, **kwargs):

    kwargs = kwargs    

    return ConstructMesh(wavelength_arr, time_arr, **kwargs)._getMesh(filepath, structurname=structurname)


class TA():

    def __init__(self, x, y, z, x_unit=None, y_unit=None, z_unit=None) -> None:
        self.z = z
        self.x = x
        self.x_unit = x_unit
        self.y = y
        self.y_unit = y_unit

    def getIndexValue(self, arr, value):
        res = np.where(arr == value)[0]
        if res.size == 0:
            res = find_nearest(arr, value)
                
        return res 

    def loc(self, *args):
        if isinstance(args, list):
            if len(args) == 1:
                return self._loc1(*args)

            elif len(args) == 2:
                return self._loc2(*args)
            else:
                raise TypeError(
                    'wrong amount of arguments given! expected 1 or 2')
        else:
            return self._loc1(*args)

    def _loc1(self, arg):
        if isinstance(arg, list):
            if len(arg) == 1:
                return self.z[:, self.getIndexValue(self.x, arg[0])]

            elif len(arg) == 2:
                return self.z[:, slice(self.getIndexValue(self.x, arg[0]), self.getIndexValue(self.x, arg[1]))]

            elif len(arg) == 3:
                start = self.getIndexValue(self.x, arg[0])
                stop = self.getIndexValue(self.x, arg[1])
                diff = start - self.getIndexValue(self.x, arg[0]+arg[2])
                return self.z[:,start:stop:diff]

            else:
                raise TypeError('too long array given max: [start, end, step]')
        else:
            return self.z[:, self.getIndexValue(self.x, arg)]

    # def _loc2(self, wvl, time):


class ConstructMesh():

    def __init__(self, wavelength_arr, time_arr, diabatic=False, std_devi=0.4) -> None:
        self.std_devi = 0.4
        self.wavelength_arr = wavelength_arr
        self.time_arr = time_arr
        self.diabatic = diabatic

    def _calcStateSpectra(self, exc_arr, osc_arr):

        y = np.zeros_like(self.wavelength_arr)

        for exc, osc in zip(exc_arr, osc_arr):
            y += lorentzian(self.wavelength_arr, exc,
                            osc, std_devi=self.std_devi)

        return y

    def _getStructurSpectra(self, structurGroup):

        y = np.zeros_like(self.wavelength_arr)

        poptype = 'pop'
        k = 1

        if self.diabatic:
            poptype = 'diapop'
            k = 2

        for i, pop in enumerate(structurGroup[poptype]):
            if pop > 0:
                # S1 (i = 1) is mapped on 2_(1)_XX as ground state is 1_(1)_XX therefore i+1
                pumpName = '{}_(1)_A'.format(i+k)
                y += pop * self._calcStateSpectra(
                    structurGroup[pumpName + '/exc_energy'], structurGroup[pumpName + '/osc_strength'])

        return y

    def _getTimeSpectra(self, timeGroup, structurname=None, **kwargs):

        y = np.zeros_like(self.wavelength_arr)

        # FIXME: should attributes at the structurlevel be added this will make problems!
        for structur in timeGroup.keys():
            if structurname:
                if structur==structurname:
                    y += self._getStructurSpectra(timeGroup[structur])    
            else:
                y += self._getStructurSpectra(timeGroup[structur])

        return y

    def _buildMesh(self, hdf5File, **kwargs):

        mesh = np.zeros(
            (self.time_arr.shape[0], self.wavelength_arr.shape[0]), dtype=np.float64)

        time_str_list = np.asarray(list(hdf5File.keys()))
        time_fl_list = np.asarray([float(i) for i in time_str_list])

        for i, time in enumerate(self.time_arr):

            ind = np.where(time_fl_list == time)
            time_str = time_str_list[ind][0]
            try:
                mesh[i] = self._getTimeSpectra(hdf5File[time_str], **kwargs)
            except KeyError:
                # print(traceback.format_exc())
                print('{time} not found!'.format(time=time))

        return TA(self.wavelength_arr, self.time_arr, mesh)

    def _getMesh(self, filepath, **kwargs):

        kwargs = kwargs

        with h5py.File(filepath, 'r') as hdf5File:
            return self._buildMesh(hdf5File, **kwargs)


if __name__ == "__main__":
    hdf5_path = '/export/home/tkaczun/xray-ta/Pyrazine/ta_data.hdf5'
    time_arr = np.arange(59, 75.5, 0.5)
    wavelength_arr = np.linspace(280, 286, 50)

    getMesh(hdf5_path, wavelength_arr, time_arr)

    data = getTA(hdf5_path, wavelength_arr, time_arr)

    data.loc(281)
    data.loc([281])
    data.loc([281, 284])
    data.loc([281, 284, 1])
    # getMesh(os.getcwd() + '/' + hdf5_path, wavelength_arr, time_arr)
