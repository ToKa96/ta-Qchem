import glob
import os
import numpy as np
import math
import pandas as pd

class Extract:
    section_start = ''
    section_end = ''
 
    def __init__(self):
        self.section = False
        self.finished = False
        self.data = {}

    def readLine(self, line):
        pass

    def checkStart(self,line):

        if self.section_start in line:
            self.section = True

    def checkEnd(self, line):

        if self.section_end in line:
            self.finished = True

    def getData(line):
        pass


# TODO: Update docstrings!
class ExtractRem(Extract):
        """
        class that deals with extracting information from the $rem section
        of qchem .out files.

        Parameters
        ----------
        rem_section : bool
                flag that is set to True once the $rem section has been reahced
        rem_finished : bool
                flag that is set to True once the $rem section is over
        data : dict
                Dictionary that contains the keywords and values of the qchem
                calculation as keys and values of the deictionary, all keys are
                UPPERCASE

        Attributes
        ----------
        rem_match : str
                pattern that indicates the start of the $rem section
        end_match : str
                pattern that indicates the end of the $rem section
        """

        section_start = "$rem"
        section_end = "$end"

        def __init__(self):
            Extract.__init__()

        def readLine(self, line):
                """
                wrapper function that sends the line to subroutines depending on
                flags.

                calls checkRemStart until 'rem_section' is set to True, the it
                constantly checks for the end of the $rem section and if that
                has not yet been reached calls the getData Method.

                Parameters
                ----------
                line : str
                        line from textfile to be read
                """
                if not self.section:
                        self.checkStart(line)

                else:
                        self.checkEnd(line)
                        if not self.finished:
                                self.getData(line)

        def getData(self, line):
                """
                Extracts the actual data from the rem line.

                Splits the line along its whitespaces. First split contains
                keywords, last split (should) contain value. If = present it
                will be contained in the middle split.

                Parameters
                ----------
                line : str
                        line from textfile to be read
                """
                line = line.lstrip().rstrip()
                self.data[line.split()[0].upper()] = line.split()[-1]


class ExtractExcitation(Extract):
        """
        Class that deals with extraction of excitation energys from the ADC
        section of the output file.

        Parameters
        ----------
        exc_section : bool
            Flag set to True once the start of the excitation section has been reached
        exc_finished : bool
            Flag thats set to True once the end of the excitation section has been reached
        data : dict
            Contains the excitation energy, oscillator strength, multiplicity
            and other excited state information as key and values with the
            values stored as lists

        Attributes
        ----------
        exc_match : str
            pattern that indicates the start of the excitation energy
            section
        end_match : str
            pattern that indicates the end of the excitation energy section
        mult_conv_match : str
            pattern that indicates the line containing multiplicity and
            convergence
        exc_energy_match : str
            pattern that indicates the line containing the excitation
            energy
        osc_strength_match : str
            pattern that indicates the line containing the oscillator
            strength
        """
        section_start = "Excited State Summary"
        section_end = "================================================================================"

        mult_conv_match = "Excited state"
        exc_energy_match = 'Excitation energy:'
        osc_strength_match = 'Osc. strength:'

        def __init__(self):
                Extract.__init__(self)
                self.data = {
                        'Excitation energy': [],
                        'Osc. strength': [],
                        'converged': [],
                        'multiplicity': [],
                }

        def readLine(self, line):
                """
                wrapper function that sends the line to subroutines depending on
                flags.

                calls checkExcStart until 'exc_section' is set to True, then it
                constantly checks for the end of the $rem section and if that
                has not yet been reached calls the getData Method.

                Parameters
                ----------
                line : str
                        line from textfile to be read
                """
                if not self.section:
                        self.checkStart(line)

                else:
                        self.checkEnd(line)
                        if not self.finished:
                                self.getData(line)

        def getData(self, line):
                """
                Extracts the actual data from the exc section lines.

                Depending upon the pattern found, the line is splitted and
                converted in different ways to extract the relevant data.

                Parameters
                ----------
                line : str
                        line from textfile to be read
                """
                if ExtractExcitation.mult_conv_match in line:
                        # removes special charackters such as , ( ... from line split for multiplicity
                        self.data['multiplicity'].append(''.join(filter(str.isalnum, line.split()[3])))
                        if '[converged]' in line.split()[-1]:
                                self.data['converged'].append(True)
                        else:
                                self.data['converged'].append(False)

                if ExtractExcitation.exc_energy_match in line:
                        self.data['Excitation energy'].append(float(line.split()[-2]))
                        self.data['Osc. strength'].append(np.nan)

                if ExtractExcitation.osc_strength_match in line:
                        self.data['Osc. strength'][-1] = float(line.split()[-1])


class ExtractOther(Extract):
    """
    
    """
    cpu_time_match = 'Total job time:'

    def __init__(self):
        self.data = {
            'cpu':[]
        }
    
    # FIXME:     will not append False if File does not contain the completed line!
    #            Ideas to Fix it? Put here! 
    def readLine(self, line):
        if ExtractOther.cpu_time_match in line:
            try:
                self.data['cpu'].append( float(line.split()[-1].split('(')[0][:-1]))
            except (TypeError, ValueError):
                self.data['cpu'].append(np.nan)


class ExtractFile:
    """
    
    """
    def __init__(self):
            self.data = {
                    'filename': [],
                    'BASIS': [],
                    'METHOD': [],
                    'cpu': []
            }

    def extractFile(self, filename):

            self.data['filename'].append(filename)

            exRem = ExtractRem()
            exExc = ExtractExcitation()
            exOth = ExtractOther()

            with open(filename, 'r') as outfile:
                    for line in outfile:
                            if not exRem.rem_finished:
                                    exRem.readLine(line)
                            elif not exExc.exc_finished:
                                    exExc.readLine(line)
                            else:
                                exOth.readLine(line)


            for key in ['BASIS', 'METHOD']:
                try:
                    self.data[key].append(exRem.data[key])
                except KeyError:
                    self.data[key].append(None)
            for key in exExc.data.keys():
                    try:
                            self.data[key].append(exExc.data[key])
                    except KeyError:
                            self.data[key] = []
                            self.data[key].append(exExc.data[key])
            
            if exOth.data['cpu']:
                self.data['cpu'].append(exOth.data['cpu'][0])
            else:
                self.data['cpu'].append(np.nan)

    def extractFolder(self, dirPath):
        """"""
        os.chdir(dirPath)
        for filename in glob.glob("*.out"):
            print('extracting: {} ...'.format(filename))
            self.extractFile(filename)

    def dictToDataFrame(self):
           return pd.DataFrame(self.data)


if __name__ == "__main__":
    filepath = '/export/home/ccprak10/scripts/qchem_extract/data'
    exFile = ExtractFile()
    exFile.extractFolder(filepath)
