"""
reading and storing as .hdf of TA data calculated with Qchem using ADC pump-probe.

!Attention! This stuff down here is outdated:

This module is intended for a certain data structure:

root_dir/timestep_dir/structureA_bla.out

eg.:

pyrazine_TA/
|---0fs/
|   |---StructureA_bla.out
|   |---StructureB_bla.out
|---20fs/
|   |---StructureC_bla.out
|   |---StructureD_bla.out

This will result in the following structure in the hdf:

/ (root)
|---0fs/
|   |---StructureA/
|   |   |---pump1/
|   |   |   |---'exc_energy'    (Dataset)   
|   |   |   |---'osc_strength'  (Dataset)
|   |   |---pump2/
|   |   |   ...
...
With only the first part of the .out Filename up to the first '_' will be used as group name in the hdf File

Author: Tobias Kaczun
"""

import os
import glob
import h5py

from qextract import fano_extract
# TODO: command line call
# TODO: modifiy get_pop?


def write_hdf5(qchem_calc, hdf5_filename, h5_mode='a', pop_path=None, extractor=None, get_pop=None, **kwargs):
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
    TAtoHDF5().create_hdf5(qchem_calc, hdf5_filename, h5_mode=h5_mode,
                          extractor=extractor, pop_path=pop_path, get_pop=get_pop, **kwargs)


class TAtoHDF5:
    """
    class to read in excitation energies and oscillator strengths of a directory and store them in an hdf5 File.
    """

    def create_hdf5(self, pathname, filename, h5_mode='a', pop_path=None, extractor=None, get_pop=None, **kwargs):
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
        # self.pop_path = pop_path
        
        # if get_pop is None:
        #     self.pop = self._set_pop
        # else:
        #     self.pop = get_pop

        if extractor is None:
            from qextract import fano_extract
            self.extractor = fano_extract.ExtractFile().extractFile
        else:
            self.extractor = extractor

        if self.pathname[-1] != '/':
            self.pathname = self.pathname + '/'

        outfiles = self.get_output_files()

        with h5py.File(filename, h5_mode, **kwargs) as hdf5_file:
            self.iterate_files(outfiles, hdf5_file)

            if get_pop is None:
                self._set_pop(hdf5_file, pop_path=pop_path)
            else:
                #! add a possibility to give args to get_pop?!
                get_pop(hdf5_file, pop_path=pop_path)

    def get_output_files(self):
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

    def iterate_files(self, outfiles, hdf5_file):
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

            groupstr = self.get_group_from_path(filepath)
            # iterates over all unique pump state (indeces)            
            for pump in current_file_data.get_pump_states():
                # creates the base names for the datasets belonging to this pump state
                # it seems white spaces in the group/ dataset names create problems ...
                pump_name = pump.replace(' ', '_')
                dataset_name = groupstr + pump_name + '/'
                
                data = current_file_data.get_pump_probe_data(pump)
                
                for key in data.keys():
                    hdf5_file.create_dataset(dataset_name + key, data=data[key])
                    
            # self.pop()
                
    # ? might this already work for directories with time and outputfiles with TRAJ name?
    def get_group_from_path(self, filepath):
        """
        generates the hdf5 groups for the data of the file based on its path
        and its filename.

        first part of the filename separated by "_" is expected to be the
        identifier (structure) used.

        Parameters
        ----------
        filepath : str
            path to the qchem .out file

        Returns
        -------
        groupstr : str
            hdf5 path with Groups based on directory and the filename

        """
        groupstr = filepath.replace(self.pathname, '')
        filename = groupstr.split('/')[-1]
        # should a filename start with '_' it will not append any structure name to the
        # the groupstr
        if not filename.split('_')[1:]:
            # Not sure whether this might create problems in some special cases
            noStructureName = ''
        else:
            noStructureName = '_' + '_'.join(filename.split('_')[1:])
        # This might create bugs if a directory and a structure have the
        # same name
        groupstr = groupstr.replace(noStructureName, '')

        groupstr = groupstr.replace('.out', '')

        if groupstr[-1] != '/':
            groupstr = groupstr + '/'

        if groupstr[0] != '/':
            groupstr = '/' + groupstr

        return groupstr
    
    # def _set_pop2(self, filename):
    #     pass

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
                    try:
                        time = float(line.split()[0])
                        pop = [float(i) for i in line.split()[1:]]

                        if hdf5_file['{time}/{structur}'.format(time=time, structur=structur)]:
                            hdf5_file.create_dataset('/{time}/{structur}/{pattern}'.format(
                                time=time, structur=structur, pattern=pattern), data=pop)                            

                        if hdf5_file['{structur}/{time}'.format(time=time, structur=structur)]:
                            hdf5_file.create_dataset('/{structur}/{time}/pop'.format(
                                time=time, structur=structur), data=pop)

                    except (IndexError, KeyError):
                        print('Index or Key Error encountered in {time}/{structur}'.format(
                            time=time, structur=structur))
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

    # prints out its conten
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
