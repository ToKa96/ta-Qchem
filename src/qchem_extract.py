import glob
import os
import numpy as np
import math
import pandas as pd

# TODO: Write Docstring!
#
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
            Extract.__init__(self)

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
        term_match = 'Term symbol:'

        def __init__(self):
                Extract.__init__(self)
                self.data = {
                        'Excitation energy': [],
                        'Osc. strength': [],
                        'converged': [],
                        'multiplicity': [],
                        'term': [],
                        'symmetry': [],
                        'state': [],
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

                if ExtractExcitation.term_match in line:
                    split = line.split()[2:5]
                    self.data['symmetry'].append(split[-1])
                    self.data['state'].append(split[0])
                    self.data['term'].append(' '.join(split))
                if ExtractExcitation.exc_energy_match in line:
                        self.data['Excitation energy'].append(float(line.split()[-2]))
                        self.data['Osc. strength'].append(np.nan)

                if ExtractExcitation.osc_strength_match in line:
                        self.data['Osc. strength'][-1] = float(line.split()[-1])

        def getDataFrame(self):
            df = pd.DataFrame.from_dict(self.data)
            df = df.set_index('term')
            return df

class ExtractPumpProbe(Extract):
    section_start = 'Pump-Probe Results'
    section_end = 'End of Pump-Probe Results'
    
    state_start = 'Transitions from pumped state'

    def __init__(self):
        Extract.__init__(self)
        self.data = {}
        self.cur_pump_key = None

    def readLine(self, line):
        if not self.section:
            self.checkStart(line)
        else:
            if not self.finished:
                self.getData(line)


    def getData(self, line):
            if ExtractPumpProbe.state_start in line:
                self.cur_pump_key = line.split(maxsplit=4)[-1].rstrip('\n')
                self.data[self.cur_pump_key]={}
            else:
                try:
                    probe_state = ' '.join(line.split()[:3])
                    probe_values = [float(x) for x in line.split()[3:]]
                    self.data[self.cur_pump_key][probe_state]=probe_values
                except (ValueError, KeyError):
                    self.checkEnd(line)

    def getDataFrame(self):
        df = pd.DataFrame.from_dict(self.data).stack().to_frame()
        df = pd.DataFrame(df[0].values.tolist(),columns=['E_pr - E_pu', 'osc. str.', 'overlap'], index=df.index)
        df = df.dropna()
        return df

class ExtractOther(Extract):
    """
    
    """
    cpu_time_match = 'Total job time:'

    def __init__(self):
        self.data = {
            'cpu':[]
        }
    
    def readLine(self, line):
        if ExtractOther.cpu_time_match in line:
            try:
                self.data['cpu'].append( float(line.split()[-1].split('(')[0][:-1]))
            except (TypeError, ValueError):
                self.data['cpu'].append(np.nan)

# TODO: Write docstrings
#
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
                            if not exRem.finished:
                                    exRem.readLine(line)
                            elif not exExc.finished:
                                    exExc.readLine(line)
                            else:
                                exOth.readLine(line)

#            
#            excDf = pd.DataFrame(exExc.data)
#            excDf['filename'] = [filename for x in excDf.index]
#            index = pd.MultiIndex.from_frame(excDf[['filename', 'term']])
#            testDf = excDf.set_index(['filename', 'term'])
#            print(testDf)
            # remDf = pd.DataFrame(exRem.data)
            # print(remDf)


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
            
            pd.DataFrame()

    def extractFileNew(self,filename):

        cur_data = adcData(filename)

        exRem = ExtractRem()
        exOth = ExtractOther()

        with open(filename, 'r') as outfile:
            for line in outfile:
                if not exRem.finished:
                    exRem.readLine(line)
                else:
                    break
            if 'FANO'.casefold() in exRem.data['METHOD'].casefold():
                cur_data.setData(['pump', 'probe', 'pump-probe'], self.extractFANO(outfile))
            elif 'adc' in exRem.data['METHOD'].casefold():
                cur_data.setData('adc', self.extractADC(outfile))
            else:
                raise KeyError('Unexpected METHOD encountered in .out file')

            for line in outfile:
                exOth.readLine(line)

        cur_data.setOtherAttr(exRem, exOth)

        return cur_data

    def extractFANO(self, outfile):
        
        exADC = ExtractExcitation()
        exCVS = ExtractExcitation()
        exPuP = ExtractPumpProbe()

        for line in outfile:
            if not exADC.finished:
                exADC.readLine(line)
            
            elif not exCVS.finished:
                exCVS.readLine(line)

            elif not exPuP.finished:
                exPuP.readLine(line)
            else:
                break

        return exADC.getDataFrame(), exCVS.getDataFrame(), exPuP.getDataFrame()


    def extractADC(self, outfile):
        
        exADC = ExtractExcitation()

        for line in outfile:
            if not exADC.finished:
                exADC.readLine(line)
            else:
                break

        return exADC.getDataFrame()


    def extractFilePP(self, filename):
        cur_data = adcData(filename)
        
        exRem = ExtractRem()
        exPuP = ExtractPumpProbe()
        exOth = ExtractOther()

        with open(filename, 'r') as outfile:
            for line in outfile:
                if not exRem.finished:
                    exRem.readLine(line)
                elif not exPuP.finished:
                    exPuP.readLine(line)
                else:
                    exOth.readLine(line)

        cur_data.setPumpProbeData(exPuP.getDataFrame())
        cur_data.setCalcAttr(exRem)
        cur_data.setOtherAttr(exOth)

        return cur_data


    def extractFolderNew(self, dirPath):
        """"""
        
        folder_data = {}

        os.chdir(dirPath)
        for filename in glob.glob("*.out"):
            print('extracting: {} ...'.format(filename))
            folder_data[filename] = self.extractFileNew(filename)
    
    def extractFolder(self, dirPath):
        """"""
        os.chdir(dirPath)
        for filename in glob.glob("*.out"):
            print('extracting: {} ...'.format(filename))
            self.extractFile(filename)

    def extractFolderPP(self, dirPath):
        """"""
        os.chdir(dirPath)
        data = {}
        for filename in glob.glob("*.out"):
            print('extracting: {} ...'.format(filename))
            data[filename] = self.extractFilePP(filename)

    def dictToDataFrame(self):
           return pd.DataFrame(self.data)


class adcData:

    def __init__(self, filename):
        self.filename = filename

    def setData(self, keys, dfs):
        if isinstance(keys, list) or  isinstance(dfs, list):
            for key, df in zip(keys, dfs):
                self.__dict__[key] = df
        else:
            self.__dict__[keys] = dfs

    def setOtherAttr(self, *args):
        for obj in args:
            for key in obj.data:
                self.__dict__[key] = obj.data[key]

    def __str__(self):
        objStr = '==== adcData =====\n'
        # print(self.__dict__)
        for key in self.__dict__:
            if not isinstance(self.__dict__[key], pd.DataFrame):
                objStr += '    {}: {}\n'.format(key, self.__dict__[key])
            else:
                objStr += '-- {} --\n'.format(key)
                objStr += self.__dict__[key].to_string()
                objStr += '\n'
                objStr += '-------\n'
        return objStr

if __name__ == "__main__":
    #filepath = '/export/home/ccprak10/scripts/qchem_extract/data'
    #exFile = ExtractFile()
    #exFile.extractFolder(filepath)
    filepath = '/export/home/ccprak10/scripts/qchem_extract/data/'
    exFile = ExtractFile()
    data = exFile.extractFolderNew(filepath)
