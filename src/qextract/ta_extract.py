"""
reading and storing as .hdf of TA data calculated with Qchem using ADC pump-probe.

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

from qextract import extract

# TODO: write docstrings
# TODO: parallelization and
# TODO: 'append mode'
# TODO: command line call


def writeHDF5(outFilepath, hdf5_filename):
    TAtoHDF5().createHDF5(outFilepath, hdf5_filename)


class TAtoHDF5:
    """
    class to read in excitation energies and oscillator strengths of a directory and store them in an hdf5 File.
    """

    def createHDF5(self, pathname, filename, h5_mode = 'a', extractor=None, get_pop=None, **kwargs):
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
        
        if extractor is None:
            self.extractor = extract.ExtractFile().extractFile
        else:
            self.extractor = extractor

        if self.pathname[-1] != '/':
            self.pathname = self.pathname + '/'

        outfiles = self.getOutputFiles()

        with h5py.File(filename, h5_mode, **kwargs) as hdf5File:
            self.iterateFiles(outfiles, hdf5File)

            if get_pop is None:
                self.setAdibaticPop(hdf5File)
            else:
                #! add a possibility to give args to get_pop?!
                get_pop(hdf5File)

    def getOutputFiles(self):
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

    def iterateFiles(self, outfiles, hdf5File):
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
            currentFileData = self.extractor(filepath)

            groupstr = self.getGroupfromPath(filepath)
            # iterates over all unique pump state (indeces)
            for pump in currentFileData.pump_probe.index.unique(level=0):
                # creates the base names for the datasets belonging to this pump state
                # it seems white spaces in the group/ dataset names create problems ...
                pump_name = pump.replace(' ', '_')
                dataset_name = groupstr + pump_name + '/'
                # create Excitation energy dataset
                # gets all excitation energies by the 'pump' index
                # creates new pandas DataFrame with all excitation enegry
                # associated with the current 'pump' index and converts it to a
                # numpy array
                hdf5File.create_dataset(dataset_name + 'exc_energy',
                                        data=currentFileData.pump_probe.loc[pump, 'Excitation energy'].to_numpy())
                # create OScillator strength dataset
                # same procedure as for excitation energy (new DataFrame ->
                # numpy array)
                # FIXME: what happens if no oscillator strength is given due to
                # faield convergence? Is this even possible at this stage?
                hdf5File.create_dataset(dataset_name + 'osc_strength',
                                        data=currentFileData.pump_probe.loc[pump, 'Osc. strength'].to_numpy())
    #? might this already work for directories with time and outputfiles with TRAJ name?
    def getGroupfromPath(self, filepath):
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

    def setAdibaticPop(self, hdf5File):
        """[summary]

        Parameters
        ----------
        hdf5File : [type]
            [description]
        """
        self._setPop(hdf5File, 'pop')

    def _setPop(self, hdf5File, pattern):
        """[summary]

        Parameters
        ----------
        hdf5File : [type]
            [description]
        pattern : [type]
            [description]
        """
        popFiles = glob.glob(self.pathname + '*_' + pattern + '.dat')

        for popFile in popFiles:
            # This might again lead to bugs in case of unusual file/structur names!
            structur = os.path.basename(popFile).split('_')[0]
            with open(popFile) as pFile:
                for line in pFile:
                    try:
                        time = float(line.split()[0])
                        pop = [float(i) for i in line.split()[1:]]

                        if hdf5File['{time}/{structur}'.format(time=time, structur=structur)]:
                            hdf5File.create_dataset('/{time}/{structur}/{pattern}'.format(
                                time=time, structur=structur, pattern=pattern), data=pop)

                    except (IndexError, KeyError):
                        print('Index or Key Error encountered in {time}/{structur}, {pattern}'.format(
                            time=time, structur=structur, pattern=pattern))
                        pass


if __name__ == "__main__":
    TAtoHDF5().createHDF5(
        '/export/home/tkaczun/scripts/qextract/data/ta_data_test', 'test.hdf5')
    os.remove('test.hdf5')
