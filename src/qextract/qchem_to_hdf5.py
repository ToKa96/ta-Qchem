"""_summary_
"""
    
import os
import glob
from typing import Protocol, Any
import h5py

from qextract import fano_extract


def write_hdf5(qchem_calc, hdf5_filename, file_structur='TRAJ/TIME', h5_mode='a', pop_path=None, extractor=None, get_pop=None, **kwargs):
    """wrapper function for the creation of an hdf5 file containing the excitation energy and oscillator strength
    of all time steps calculated for the transient absorption spectrum.

    Parameters
    ----------
    qchem_calc : str
        path to the qchem .out files containing the data
    hdf5_filename : str
        path and filename of the hdf5 file
    h5_mode : str, optional
        opening mode of the hdf5 file, by default 'a'
    pop_path : str, optional
        path to the files containing the population data, if None assumed to be in the same dir as the
        qchem .out files, by default None
    extractor : callable, optional
        parser for the (qchem) files, by default None
    get_pop : callable, optional
        parser or other function which specifies how to set the excited state population, by default None
    """
    QChemHDF5().create_hdf5(qchem_calc, hdf5_filename, file_structur=file_structur, h5_mode=h5_mode,
                          extractor=extractor, pop_path=pop_path, get_pop=get_pop, **kwargs)


class PumpProbeData(Protocol):
    
    def get_pump_states() ->  Any:
        ...
        
    def get_pump_probe_data(pump: str) -> dict:
        ...

class QChemHDF5():
    
    def create_hdf5(self, pathname, filename, file_structur='traj/time', h5_mode='a', pop_path=None, extractor=None, get_pop=None, **kwargs):
        """
        creates an hdf5 File containing excitation energies and oscillator strengths of the pump_probe calculation in the given directory.

        Parameters
        ----------
        pathname : str
            path to directory that is to be read
        filename : str
            filename (and path) for the hdf5 that is to be created
        Returns
        -------
        None.

        """
        self.pathname = pathname
        
        if pop_path is None:
            pop_path = pathname
        
        self._get_file_structur(file_structur)

        if extractor is None:
            from qextract import fano_extract
            self.extractor = fano_extract.ExtractFile().extract_file
        else:
            self.extractor = extractor

        if self.pathname[-1] != '/':
            self.pathname = self.pathname + '/'

        outfiles = self._get_output_files()

        with h5py.File(filename, h5_mode, **kwargs) as hdf5_file:
            self._iterate_files(outfiles, hdf5_file)

            if get_pop is None:
                self._set_pop(hdf5_file, pop_path=pop_path)
            else:
                #! add a possibility to give args to get_pop?!
                self._set_pop_external(hdf5_file, get_pop, pop_path)
    
    def _set_pop_external(self, hdf5_file, get_pop, pop_path):
        
        for dictionary in get_pop(pop_path):
            traj = dictionary['traj']
            time = dictionary['time']
            pop = dictionary['pop']
            dataset_name = '/' + traj + '/' + time + '/'
            try:
                hdf5_file.create_dataset(dataset_name + 'pop', data=pop)
            except (KeyError, IndexError):
                print(f'Index or Key Error encountered in {traj}/{time}')
            
    def _get_output_files(self):
        """
        iterates over all files and subdirectories in the path and collects path to all .out files.

        Returns
        -------
        outfiles : list(str)
            list of paths as strings to .outfiles in project directory

        """
        outfiles = []

        # root is always the current directory of os.walk not the actual
        # project directory!
        for root, dirs, files in os.walk(self.pathname):
            for file in files:
                if file.endswith('.out'):
                    outfiles.append(root + '/' + file)

        return outfiles
    
    def _iterate_files(self, outfiles, hdf5_file):
        """
        iterates over .out files and appends their Pump-Probe excitation energy and oscillator strength to the HDF5.

        Parameters
        ----------
        outfiles : list (str)
            list of paths for files to iterate
        hdf5File : h5py File object
            file object to which the data is to be appended

        Returns
        -------
        None.

        """
        for filepath in outfiles:
            current_file_data = self.extractor(filepath)

            groupstr = self._get_group_from_path(filepath)
            # iterates over all unique pump state (indeces)
            # FIXME: this might genereate problems
            # add pump_states as data? maybe not necessary here
            # TODO: rewrite ADCData and extractor in a way which is more flexible!
            self._set_data(hdf5_file, groupstr, current_file_data)      
                    
    def _set_data(self, hdf5_file, groupstr, pump_probe_data: PumpProbeData) -> None:
            for pump in pump_probe_data.get_pump_states():
                # creates the base names for the datasets belonging to this pump state
                # it seems white spaces in the group/ dataset names create problems ...
                pump_name = pump.replace(' ', '_')
                dataset_name = groupstr + pump_name + '/'
                
                data = pump_probe_data.get_pump_probe_data(pump)
                
                for key in data.keys():
                    hdf5_file.create_dataset(dataset_name + key, data=data[key])
        
    
    def _get_file_structur(self, file_structur):
        file_structur.upper()
        split = file_structur.split('/')
        self.traj_pos = split.index('TRAJ')
        self.time_pos = split.index('TIME')
        
    #* NOTE: this might be even better handeld at the extractor level...
    def _get_group_from_path(self, filepath):
        path = filepath.replace(self.pathname, '')
        groupstr = '/' + path.split('/')[self.traj_pos] + '/' + path.split('/')[self.time_pos] + '/'
        return groupstr.replace('.out', '')
    
    def _set_pop(self, hdf5_file, pop_path=None):
        """[summary]

        Parameters
        ----------
        hdf5File : [type]
            [description]
        pattern : [type]
            [description]
        """
        pattern = 'pop'
        
        if pop_path is None:
            path = self.pathname
        else:
            path = pop_path

        pop_files = glob.glob(path + '*_' + pattern + '.dat')

        for pop_file in pop_files:
            # This might again lead to bugs in case of unusual file/structur names!
            structur = os.path.basename(pop_file).split('_')[0]
            with open(pop_file) as pf:
                for line in pf:
                    time = float(line.split()[0])
                    pop = [float(i) for i in line.split()[1:]]
                    
                    try:
                        if hdf5_file['{structur}/{time}'.format(time=time, structur=structur)]:
                            hdf5_file.create_dataset('/{structur}/{time}/pop'.format(
                                time=time, structur=structur), data=pop)

                    except (IndexError, KeyError):
                        try:
                            if hdf5_file['{time}/{structur}'.format(time=time, structur=structur)]:
                                hdf5_file.create_dataset('/{time}/{structur}/{pattern}'.format(
                                    time=time, structur=structur, pattern=pattern), data=pop)                            
                        except (IndexError, KeyError):
                            # print('Index or Key Error encountered in {time}/{structur}'.format(
                            #     time=time, structur=structur))
                            pass


if __name__ == "__main__":
    # finds the location of this file (i think) used to ensure this file runs with
    # the supplied test data in the data/ directory idnependently of the (linux)
    # machine
    base_path = '/'.join(__file__.split('/')[:-3])

    # set the path for input directory where the calculations from which to extract are located
    input_dir = '/data/ta_extract_test/input'
    # set the destination where the h5py file should be written
    hdf5_file = '/data/ta_extract_test/output/test.hdf5'

    # removes any previously written h5p file to prevent an Exception because the file
    # already exists
    if os.path.isfile(base_path + hdf5_file):
        os.remove(base_path + hdf5_file)

    # writes the actuals HDF5 file
    write_hdf5(base_path + input_dir,
              base_path + hdf5_file)

    # prints out its contentmostly 
    with h5py.File(base_path + hdf5_file, 'r') as h5f:

        def visitor(name, node):
            if isinstance(node, h5py.Group):
                # print(node.name, 'is a Group')
                pass
            elif isinstance(node, h5py.Dataset):
                if (node.dtype == 'object'):
                    # print (node.name, 'is an object Dataset')
                    pass
                else:
                    print(node.name, 'is a Dataset')
                    print(node[:])
            else:
                print(node.name, 'is an unknown type')

        h5f.visititems(visitor)
