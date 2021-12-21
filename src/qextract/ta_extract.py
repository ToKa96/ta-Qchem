"""

Author: Tobias Kaczun
"""

import os
import glob
import numpy as np
import pandas as pd
import h5py

from qextract import extract, adcData

# TODO: write docstrings


class TAtoHDF5:

    def __init__(self, pathname):
        self.pathname = pathname

    # TODO: option to choose where to save the HDF5, currently will be created
    # in the cwd
    def createHDF5(self, filename, **kwargs):
        """
        

        Parameters
        ----------
        filename : TYPE
            DESCRIPTION.
        **kwargs : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        outfiles = self.getOutputFiles()

        with h5py.File(filename, 'a', **kwargs) as hdf5File:
            self.iterateFiles(outfiles, hdf5File)

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
        exc = extract.ExtractFile()

        for filepath in outfiles:
            currentFileData = exc.extractFile(filepath)

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

    # FIXME: this will best be put separte with everything that directly acts on the
    # HDF5 file ?

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
        noStructureName = '_' + '_'.join(filename.split('_')[1:])
        # This might create bugs if a directory and a structure have the
        # same name
        groupstr = groupstr.replace(noStructureName, '')
        
        if groupstr[-1] != '/':
            groupstr = groupstr + '/'

        return groupstr


if __name__ == "__main__":
    tc = TAtoHDF5('/export/home/tkaczun/scripts/qextract/data/ta_data_test')
    tc.createHDF5('test.hdf5')
    os.remove('test.hdf5')
