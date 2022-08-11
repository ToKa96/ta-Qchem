# from dataclasses import dataclass
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


def norm_frob(array):
    return array / np.linalg.norm(array, ord='fro')


def meanError(ta, tmp):
    return abs(ta-tmp).mean()


def relError(ta, tmp):
    return (abs(ta-tmp) / ta).mean()


def frobeniusDist(ta, tmp):
    return np.sqrt(np.power(ta-tmp, 2).sum())


class TA():

    def __init__(self, energy, time, traj, tensor, x_unit=None, y_unit=None) -> None:
        self.tensor = tensor
        self.ta = np.sum(tensor, axis=2)
        self.z = traj
        self.e = energy
        self.t = time.astype(np.float16)
        self.x_unit = x_unit
        self.y_unit = y_unit

    def convergence(self, criterion, norm=norm_frob, errorfunc=frobeniusDist):
        ta = norm(self.tensor[..., 0])
        for i in range(2, self.tensor.shape[-1]):
            # TODO: Normalization of arrays still mising, convergence can not be achieved
            #       this way
            tmp = np.copy(ta)
            ta = norm(self.tensor[..., :i].sum(axis=-1))
            err = errorfunc(tmp, ta)
            if err < criterion:
                return ta, err, i
        # this should be deleted at some point:
        print('convergence criterion not met!')
        return ta, err, i


# FIXME: rewrite so that it can deal with time as major group and TRAJ as minor
class GetTA():

    def __init__(self, filepath, wavelength_arr, time_arr=None, std_devi=0.4, trajectories=None, trajectory_mode='strict', diabatic_state=None) -> None:
        self.std_devi = 0.4
        self.wavelength_arr = wavelength_arr
        if isinstance(diabatic_state, int):
            self.diabatic = True
            self.diabatic_state = diabatic_state
        else:
            self.diabatic = False

        with h5py.File(filepath, 'r') as hdf5File:
            self.hdf5File = hdf5File

            if time_arr is not None:
                if isinstance(time_arr, np.ndarray):
                    self.time_arr = np.asarray(
                        ['{:.1f}'.format(x) for x in time_arr])
                if isinstance(time_arr, list):
                    self.time_arr = np.asarray(
                        ['{:.1f}'.format(x) for x in time_arr])
            else:
                self.time_arr = self._getTime(hdf5File)

            if trajectories is not None:
                self.trajectories = trajectories
            else:
                self.trajectories = self._getTrajectories(
                    hdf5File, trajectory_mode=trajectory_mode)

            self.ta = self._getTA()

    def _getTrajectories(self, hdf5File, trajectory_mode='strict'):

        if trajectory_mode == 'strict':
            return self._getTrajectoriesStrict(hdf5File)

    def _getTrajectoriesStrict(self, hdf5File):

        # test = str(self.time_arr[0])
        tmp_arr = np.fromiter(
            hdf5File[str(self.time_arr[0])].keys(), dtype='U32')

        for time in self.time_arr[1:]:
            curr_arr = np.fromiter(hdf5File[time].keys(), dtype='U32')
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
            diapop = structurGroup['diapop'][:]
            truth_array = np.where(diapop == 1)
            if len(truth_array) > 0:
                if truth_array[0] != self.diabatic_state:
                    return np.zeros_like(self.wavelength_arr)
            else:
                return np.zeros_like(self.wavelength_arr)

        for i, pop in enumerate(structurGroup[poptype]):
            if pop == 1:
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
            mesh[t, :] = self._getStructurSpectra(
                self.hdf5File[time][trajectory])

        return mesh

    def _getAllTrajectories(self):
        tensor = np.zeros(
            (self.time_arr.shape[0], self.wavelength_arr.shape[0], self.trajectories.shape[0]))

        for i, trajectory in enumerate(self.trajectories):
            tensor[:, :, i] = self._getTrajectorySpectra(trajectory)

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
    hdf5_path = '/export/home/tkaczun/xray-ta/Pyrazine/ta_TRAJ100.hdf5'
    time_arr = np.arange(0, 200, 2)
    wavelength_arr = np.linspace(280, 290, 100)

#    ta_data = GetTA(hdf5_path, wavelength_arr, time_arr=time_arr).ta
    dia_data = GetTA(hdf5_path, wavelength_arr,
                     time_arr=time_arr, diabatic_state=0)
    # for error in [frobeniusDist]:
    # print('------- {} ------'.format(error.__name__))
    # for i in [0.1, 0.05, 0.01, 0.008, 0.005]:
    # ta , mse, num = ta_data.convergence(i, norm=norm_frob,errorfunc=error)
    # print(mse, num)

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
