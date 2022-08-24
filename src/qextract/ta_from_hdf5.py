import enum
import numpy as np
import h5py
from qextract import ta_data


def lorentzian(x, exc, osc, std_devi=0.4):
    if np.isnan(exc) or np.isnan(osc):
        return np.zeros_like(x)
    elif osc == 0:
        return np.zeros_like(x)
    else:
        return osc / (1 + np.power((x - exc) / (std_devi/2), 2))

 
def get_ta(filepath, wavelengths, time=None, std_devi=0.4, trajectories=None, excited_state=None):
    ta_data = CalcTransientAbsorption().get_ta(filepath, wavelengths, time=None, std_devi=0.4, trajectories=None, excited_state=None)
    return ta_data.get_full_ta()


# FIXME: this currently only works with trajectorie major ordering rather
#        than the old time major ordering
class CalcTransientAbsorption():
    
    def get_ta(self, filepath, wavelengths, time=None, std_devi=0.4, trajectories=None, excited_state=None):
        self.std_devi = 0.4
        self.wavelengths = wavelengths
        
        if excited_state is not None:
            if isinstance(excited_state, int):
                self.excited_state = excited_state
            else:
                raise TypeError('excited_state should be of type int')
        else:
            self.excited_state = None
            
        with h5py.File(filepath, 'r') as hdf5_file:
            self.hdf5_file = hdf5_file
            
            if trajectories is None:
                self._get_trajectories()
            else:
                self.trajectories = trajectories
            
            if time is None:
                self.time = self._get_time()
            else:
                if isinstance(time, np.ndarray):
                        self.time = self._time_as_str(time)
                elif isinstance(time, list):
                        self.time = self._time_as_str(time)
                else:
                    raise TypeError('time should be either of type list or np.ndarray')
            
            return ta_data.TransientAbsorptionData(self._calc_full_ta(), self.wavelengths, self.time, self.trajectories)
        
    def _time_as_str(self, time):
            time = np.asarray(
                            ['{:.1f}'.format(x) for x in time])
            
            return time
            
    def _get_time(self):
        # FIXME: the keys wont work here!
        time = np.empty(1)
        
        for i, traj in enumerate(self.trajectories):
            time_tmp = np.fromiter(self.hdf5_file[traj].keys(), dtype=np.float16)
            time_tmp = np.sort(time_tmp)
            
            if time_tmp.size > time.size:
                time = time_tmp
                if i > 1:
                    print('* Warning * not all trajectories have the same amount of calculated timesteps!')
            
            if i > 1:
                if not np.allclose(time, time_tmp):
                    print('* Warning * not all trajectories have the same time steps')
                    
        return self._time_as_str(time)
    
    def _get_trajectories(self):
        self.trajectories = np.fromiter(self.hdf5_file.keys(), dtype='U32')
    
    def _calc_trajectory_ta(self, traj):
        
        mesh = np.zeros((self.time.size, self.wavelengths.size))
        
        for i, time in enumerate(self.time):
            try:
                mesh[i,:] = self._calc_geometry_spectra(self.hdf5_file[traj][time])
            except KeyError:
                print(f'{traj}, {time}')
        return mesh
    
    def _calc_full_ta(self):
        tensor = np.zeros((self.time.size, self.wavelengths.size, self.trajectories.size))
        
        for i, trajectory in enumerate(self.trajectories):
            tensor[...,i] = self._calc_trajectory_ta(trajectory)
            
        return tensor
    
    def _calc_geometry_spectra(self, hdf5_group):
        y = np.zeros_like(self.wavelengths)

        idx = np.where(hdf5_group['pop'][:] == 1.)
        
        for i in idx[0]:
            # FIXME: fin a way to give this as an argument?
            pump_name = f'{i+1}_(1)_A'
            try:
                y += self._calc_state_spectra(hdf5_group[pump_name + '/exc_energy'],
                                                 hdf5_group[pump_name + '/osc_strength'])
            except KeyError:
                print(f'* Warning * KeyError encountered in {hdf5_group.name} at {pump_name}')
        
        return y
        
    def _calc_state_spectra(self, excs, oscs):
        y = np.zeros_like(self.wavelengths)

        for exc, osc in zip(excs, oscs):
            y += lorentzian(self.wavelengths, exc,
                            osc, std_devi=self.std_devi)

        return y


if __name__ == '__main__':
    base_path = '/'.join(__file__.split('/')[:-3])
    
    hdf5_path = base_path + '/data/ta_extract_test/output/test.hdf5'
    
    wavelengths = np.linspace(280, 290, 100)
    
    ret = get_ta(hdf5_path, wavelengths)
    ret.plot()