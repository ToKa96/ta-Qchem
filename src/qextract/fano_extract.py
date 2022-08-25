"""

Author: Tobias Kaczun
"""
import glob
import os
import numpy as np
import pandas as pd

from qextract import adc_data


class NotEndOfCalcError(Exception):
    pass

# TODO: Write Docstring!
#


class Extract:
    section_start = ''
    section_end = ''

    def __init__(self):
        self.section = False
        self.finished = False
        self.data = {}

    def read_line(self, line):
        pass

    def check_start(self, line):

        if self.section_start in line:
            self.section = True

    def check_end(self, line):

        if self.section_end in line:
            self.finished = True

    def get_data(line):
        pass


# TODO: Update docstrings!
class extract_rem(Extract):
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

    def read_line(self, line):
        """
        wrapper function that sends the line to subroutines depending on
        flags.

        calls checkRemStart until 'rem_section' is set to True, the it
        constantly checks for the end of the $rem section and if that
        has not yet been reached calls the get_data Method.

        Parameters
        ----------
        line : str
                line from textfile to be read
        """
        if not self.section:
            self.check_start(line)

        else:
            self.check_end(line)
            if not self.finished:
                self.get_data(line)

    def get_data(self, line):
        """
        Extracts the actual data from the rem line.

        Splits the line along its whitespaces. First split contains
        keywords, last split (should) contain value. If = present it
        will be contained in the middle split. Inline comments will 
        screw up this function.

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

    def read_line(self, line):
        """
        wrapper function that sends the line to subroutines depending on
        flags.

        calls checkExcStart until 'exc_section' is set to True, then it
        constantly checks for the end of the $rem section and if that
        has not yet been reached calls the get_data Method.

        Parameters
        ----------
        line : str
                line from textfile to be read
        """
        if not self.section:
            self.check_start(line)

        else:
            self.check_end(line)
            if not self.finished:
                self.get_data(line)

    def get_data(self, line):
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
            self.data['multiplicity'].append(
                ''.join(filter(str.isalnum, line.split()[3])))
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

    def get_dataframe(self):
        """[summary]

        Returns
        -------
        [type]
            [description]
        """
        df = pd.DataFrame.from_dict(self.data)
        df = df.set_index('term')
        return df


class ExtractPumpProbe(Extract):
    """[summary]

    Parameters
    ----------
    Extract : [type]
        [description]

    Returns
    -------
    [type]
        [description]
    """
    section_start = 'Pump-Probe Results'
    section_end = 'End of Pump-Probe Results'

    state_start = 'Transitions from pumped state'

    def __init__(self):
        Extract.__init__(self)
        self.data = {}
        self.cur_pump_key = None

    def read_line(self, line):
        """[summary]

        Parameters
        ----------
        line : [type]
            [description]
        """
        if not self.section:
            self.check_start(line)
        else:
            if not self.finished:
                self.get_data(line)

    def get_data(self, line):
        """[summary]

        Parameters
        ----------
        line : [type]
            [description]
        """
        if ExtractPumpProbe.state_start in line:
            self.cur_pump_key = line.split(maxsplit=4)[-1].rstrip('\n')
            self.data[self.cur_pump_key] = {}
        else:
            try:
                probe_state = ' '.join(line.split()[:3])
                probe_values = [float(x) for x in line.split()[3:]]
                self.data[self.cur_pump_key][probe_state] = probe_values
            except (ValueError, KeyError):
                self.check_end(line)

    def get_dataframe(self):
        """[summary]

        Returns
        -------
        [type]
            [description]
        """
        df = pd.DataFrame.from_dict(self.data).stack().to_frame()
        df = pd.DataFrame(df[0].values.tolist(), columns=[
                          'Excitation energy', 'Osc. strength', 'overlap'], index=df.index)
        df = df.dropna()
        df = df.swaplevel()
        return df


class ExtractOther(Extract):
    """

    """
    cpu_time_match = 'Total job time:'
    end_match = 'Thank you very much for using Q-Chem.  Have a nice day.'
    continuos_job_match = 'User input:'

    def __init__(self):
        self.data = {
            'cpu': [],
            'success': False,
        }

    def read_line(self, line):
        """[summary]

        Parameters
        ----------
        line : [type]
            [description]

        Raises
        ------
        NotEndOfCalcError
            [description]
        """
        if ExtractOther.cpu_time_match in line:
            try:
                self.data['cpu'].append(
                    float(line.split()[-1].split('(')[0][:-1]))
            except (TypeError, ValueError):
                self.data['cpu'].append(np.nan)

        if ExtractOther.end_match in line:
            self.data['success'] = True

        if self.data['success']:
            if ExtractOther.continuos_job_match in line:
                # add something to 'restart' reading of the second part of the file
                raise NotEndOfCalcError(
                    'File continues with additional calculation')

# TODO: Write docstrings
# TODO: rewrite to staticmethods? or other direct call?


class ExtractFile:
    """

    """

    def extract_file(self, filename):
        """[summary]

        Parameters
        ----------
        filename : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """

        with open(filename, 'r') as outfile:

            cur_data = self.extract_job(outfile, filename)

            return cur_data

    def extract_job(self, outfile, filename):
        """[summary]

        Parameters
        ----------
        outfile : [type]
            [description]
        filename : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """

        cur_data = adc_data.ADCData(filename)

        exRem = self.extract_rem(outfile)
        exOth = ExtractOther()

        if 'FANO'.casefold() in exRem.data['METHOD'].casefold():
            cur_data.set_data(['pump', 'probe', 'pump_probe'],
                             self.extract_fano(outfile))
        elif 'adc' in exRem.data['METHOD'].casefold():
            cur_data.set_data('adc', self.extract_adc(outfile))
        else:
            # This has to be rewritten
            pass

        try:
            for line in outfile:
                exOth.read_line(line)
        except NotEndOfCalcError:
            cur_data = self.extract_job(outfile, filename)

        cur_data.set_other_attr(exRem, exOth)

        return cur_data

    def extract_rem(self, outfile):
        """[summary]

        Parameters
        ----------
        outfile : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """

        exRem = extract_rem()

        for line in outfile:
            if not exRem.finished:
                exRem.read_line(line)
            else:
                break

        return exRem

    def extract_fano(self, outfile):
        """[summary]

        Parameters
        ----------
        outfile : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """

        exADC = ExtractExcitation()
        exCVS = ExtractExcitation()
        exPuP = ExtractPumpProbe()

        for line in outfile:
            if not exADC.finished:
                exADC.read_line(line)

            elif not exCVS.finished:
                exCVS.read_line(line)

            elif not exPuP.finished:
                exPuP.read_line(line)
            else:
                break

        return exCVS.get_dataframe(), exADC.get_dataframe(), exPuP.get_dataframe()

    def extract_adc(self, outfile):
        """[summary]

        Parameters
        ----------
        outfile : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """

        exADC = ExtractExcitation()

        for line in outfile:
            if not exADC.finished:
                exADC.read_line(line)
            else:
                break

        return exADC.get_dataframe()

    def extract_dir(self, dirPath, pattern='*.out'):
        """[summary]

        Parameters
        ----------
        dirPath : [type]
            [description]
        pattern : str, optional
            [description], by default '*.out'

        Returns
        -------
        [type]
            [description]
        """

        folder_data = {}

        os.chdir(dirPath)
        for filename in glob.glob(pattern):
            try:
                print('extracting: {} ...'.format(filename))
                folder_data[filename] = self.extract_file(filename)
            except (KeyError):
                print('Extraction of {} failed'.format(filename))

        return folder_data


if __name__ == "__main__":
    filepath = '/export/home/ccprak10/scripts/qextract/data/'
    exFile = ExtractFile()
    data = exFile.extract_dir(filepath)
