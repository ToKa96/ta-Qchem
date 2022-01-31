from dataclasses import dataclass
import enum
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


# def getMesh(filepath, wavelength_arr, time_arr, **kwargs):

#     kwargs = kwargs

#     return ConstructMesh(wavelength_arr, time_arr, **kwargs)._getMesh(filepath).z


# def getTA(filepath, wavelength_arr, time_arr, **kwargs):

#     kwargs = kwargs    

#     return ConstructMesh(wavelength_arr, time_arr, **kwargs)._getMesh(filepath)

# def getTAbyStruct(filepath, wavelength_arr, time_arr, structurname=None, **kwargs):

#     kwargs = kwargs    

#     return ConstructMesh(wavelength_arr, time_arr, **kwargs)._getMesh(filepath, structurname=structurname)

def norm_max(array):
    return array / array.max()

def norm_sum(array):
    return array /array.sum()
class TA():

    def __init__(self, x, y, z, tensor, x_unit=None, y_unit=None, z_unit=None) -> None:
        self.tensor = tensor
        self.ta = np.sum(tensor, axis=2)
        self.z = z
        self.x = x
        self.y = y
        self.x_unit = x_unit
        self.y_unit = y_unit
        self.z_unit = z_unit
        
    def convergence(self, criterion, norm=norm_max):
        if norm == 'max':
            norm=norm_max
        if norm == 'sum':
            norm=norm_sum
        ta = norm(self.tensor[...,0])
        for i in range(2, self.tensor.shape[-1]):
            # TODO: Normalization of arrays still mising, convergence can not be achieved 
            #       this way
            tmp = np.copy(ta)
            ta = norm(self.tensor[...,:i].sum(axis=-1))
            mse = (np.square(ta-tmp)).mean()
            if mse < criterion:
                return ta, mse, i
        # this should be deleted at some point:
        print('convergence criterion not met!')
        return ta, mse, i
    
    def convergence_maxSE(self, criterion, norm="max"):
        if norm == 'max':
            norm=norm_max
        if norm == 'sum':
            norm=norm_sum
        
        ta = norm(self.tensor[...,0])
        for i in range(2, self.tensor.shape[-1]):
            # TODO: Normalization of arrays still mising, convergence can not be achieved 
            #       this way
            tmp = np.copy(ta)
            ta = norm(self.tensor[...,:i].sum(axis=-1))
            mse = (np.square(ta-tmp)).max()
            if mse < criterion:
                return ta, mse, i
        # this should be deleted at some point:
        print('convergence criterion not met!')
        return ta, mse, i

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


class GetTA():

    def __init__(self, filepath, wavelength_arr, time_arr=None, diabatic=False, std_devi=0.4, trajectories=None, trajectory_mode='strict') -> None:
        self.std_devi = 0.4
        self.wavelength_arr = wavelength_arr
        self.diabatic = diabatic

        with h5py.File(filepath, 'r') as hdf5File:
            self.hdf5File = hdf5File
            
            if time_arr is not None:
                if isinstance(time_arr, np.ndarray):
                    self.time_arr = np.asarray(['{:.1f}'.format(x) for x in time_arr])
                if isinstance(time_arr, list):
                    self.time_arr = np.asarray(['{:.1f}'.format(x) for x in time_arr])
            else:
                self.time_arr = self._getTime(hdf5File)

            if trajectories is not None:
                self.trajectories=trajectories
            else:
                self.trajectories = self._getTrajectories(hdf5File, trajectory_mode=trajectory_mode)
            
            self.ta = self._getTA()
            
    def _getTrajectories(self, hdf5File, trajectory_mode='strict'):
        
        if trajectory_mode == 'strict':
            return self._getTrajectoriesStrict(hdf5File)
    
    def _getTrajectoriesStrict(self, hdf5File):
        
        # test = str(self.time_arr[0])
        tmp_arr = np.fromiter(hdf5File[str(self.time_arr[0])].keys(), dtype='U32')
        
        for time in self.time_arr[1:]:
            curr_arr = np.fromiter(hdf5File[time].keys(),dtype='U32')
            tmp_arr = np.intersect1d(tmp_arr, curr_arr)
            
        return tmp_arr
        
    def _getTime(self, hdf5File):
        sorted_arr = np.fromiter(hdf5File.keys(), dtype=np.float16)
        sorted_arr = np.sort(sorted_arr)
        return sorted_arr.astype(str)
    
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
                try:
                    y += pop * self._calcStateSpectra(
                        structurGroup[pumpName + '/exc_energy'], structurGroup[pumpName + '/osc_strength'])
                except KeyError:
                    print('{} @ {}'.format(structurGroup.name, pumpName))
        return y
    
    def _getTrajectorySpectra(self, trajectory):
        mesh = np.zeros((self.time_arr.shape[0], self.wavelength_arr.shape[0]))
        
        for t, time in enumerate(self.time_arr):
            mesh[t,:] = self._getStructurSpectra(self.hdf5File[time][trajectory])
            
        return mesh
    
    def _getAllTrajectories(self):
        tensor = np.zeros((self.time_arr.shape[0], self.wavelength_arr.shape[0], self.trajectories.shape[0]))
        
        for i, trajectory in enumerate(self.trajectories):
            tensor[:,:,i] = self._getTrajectorySpectra(trajectory)
            
        return tensor
    
    def _getTA(self):
        tensor = self._getAllTrajectories()
        
        return TA(self.time_arr, self.wavelength_arr, self.trajectories, tensor)

    # def _getTimeSpectra(self, timeGroup, structurname=None, **kwargs):

    #     y = np.zeros_like(self.wavelength_arr)

    #     # FIXME: should attributes at the structurlevel be added this will make problems!
    #     for structur in timeGroup.keys():
    #         if structurname:
    #             if structur==structurname:
    #                 y += self._getStructurSpectra(timeGroup[structur])    
    #         else:
    #             y += self._getStructurSpectra(timeGroup[structur])

    #     return y

    # def _buildMesh(self, hdf5File, **kwargs):

    #     mesh = np.zeros(
    #         (self.time_arr.shape[0], self.wavelength_arr.shape[0]), dtype=np.float64)

    #     time_str_list = np.asarray(list(hdf5File.keys()))
    #     time_fl_list = np.asarray([float(i) for i in time_str_list])

    #     for i, time in enumerate(self.time_arr):

    #         ind = np.where(time_fl_list == time)
    #         time_str = time_str_list[ind][0]
    #         try:
    #             mesh[i] = self._getTimeSpectra(hdf5File[time_str], **kwargs)
    #         except KeyError:
    #             # print(traceback.format_exc())
    #             print('{time} not found!'.format(time=time))

    #     return TA(self.wavelength_arr, self.time_arr, mesh)

    # def _getMesh(self, filepath, **kwargs):

    #     kwargs = kwargs

    #     with h5py.File(filepath, 'r') as hdf5File:
    #         return self._buildMesh(hdf5File, **kwargs)


if __name__ == "__main__":
    hdf5_path = '/export/home/tkaczun/xray-ta/Pyrazine/ta_TRAJ10.hdf5'
    time_arr = np.arange(0, 200, 2)
    wavelength_arr = np.linspace(280, 290, 100)

    ta_data = GetTA(hdf5_path, wavelength_arr, time_arr=time_arr).ta
    
    for i in [1e-10, 1e-11, 1e-12]:
        ta , mse, num = ta_data.convergence(i)
        print(mse, num)
    
    # print(ta_data.tensor.shape)
    # print(ta_data.z)
    # print(ta_data.z)
    # print(ta_data.x)
    # print(ta_data.y)

    # import matplotlib.pyplot as plt
    
    # plt.figure()
    
    # plt.pcolormesh(ta_data.ta)
    
    # plt.savefig('/export/home/tkaczun/scripts/qextract/data/ta_util.plot.png', )
    

    # getMesh(os.getcwd() + '/' + hdf5_path, wavelength_arr, time_arr)
