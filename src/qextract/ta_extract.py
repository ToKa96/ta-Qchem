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
        self.pathname

    # FIXME: this might be dangerous ...
    # better use with open(...)
    def createHDF5(self, filename, **kwargs):
        self.hdf5 = h5py.File(filename, 'a', **kwargs)

    def getOutputFiles(self):
        """


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

    def iterateFiles(self, outfiles):
        
        exc = extract.ExtractFile()
        
        for filepath in outfiles:
            currentFileData = exc.extractFile(filepath)    
            
            for pump in currentFileData.pump_probe.index.unique(level=0):
                
            # best directly create subgroups when initiating datasets
            self.hdf5.create_group()
            
            

    # this will best be put separte with everything that directly acts on the 
    # HDF5 file ?
    def getGroupfromPath(self, filepath):
        
            groupstr = filepath.replace(self.pathname)
            filename = groupstr.split('/')[-1]
            noStructureName = filename.split('_')[1:]
            # This might create bugs if a directory and a structure have the 
            # same name
            groupstr = groupstr.replace(noStructureName)
            
            return groupstr
        
    
            
            
