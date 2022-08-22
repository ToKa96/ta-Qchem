"""
Author: Tobias Kaczun
"""
import os
import subprocess
import numpy as np

#TODO: finish docstrings/documentation


def read_qchem_temp(qchem_template):
    """_summary_

    Parameters
    ----------
    qchem_template : str
        path to (qchem) template

    Returns
    -------
    str
        read in template as a signle string
    """
    qin = ''
    with open(qchem_template) as tmp:
        for line in tmp:
            qin += line

    return qin


def extract_structur(xyzFile, timesteps=None):
    """extracts the xyz structurs at different timesteps from the given MD simulation 
    trajectory

    Parameters
    ----------
    xyzFile : str
        path to the file containing the xyz coordinates of the MD simulation
    timesteps : list or np.arrays, optional
        timesteps at which the yields can occur, by default None

    Yields
    ------
    dict
        'traj' the trajectorie name/number
        'time' : the current time step
        'structur' : the xyz structur at the timestep 
    """
    start_struct = False
    structur = ''
    traj = xyzFile.split('/')[-2]
    with open(xyzFile) as xyzFile:
        for line in xyzFile:
            if start_struct:

                if len(line.split()) == 4:
                    if line[-1] != '\n':
                        line = line + '\n'
                    structur += line
                else:
                    try:
                        if structur[-1] == '\n':
                            structur = structur[:-1]
                    except IndexError:
                        pass

                    start_struct = False

                    if timesteps is None:
                        yield {'structur': structur, 'time': time, 'traj': traj, }
                    else:
                        if float(time) in timesteps:
                            yield {'structur': structur, 'time': time, 'traj': traj}
                    structur = ''

            if 'Time' in line:
                time = float(line.split()[-1])
                start_struct = True

        if timesteps is None:
            yield {'structur': structur, 'time': time, 'traj': traj, }
        else:
            if float(time) in timesteps:
                yield {'structur': structur, 'time': time, 'traj': traj}


class QChemIn:
    """_summary_
    """

    def __init__(self,  qchem_template, extract_data=extract_structur, q_dir=None, 
                 qin_options=None, qsub_options=None) -> None:
        """_summary_

        Parameters
        ----------
        qchem_template : _type_
            _description_
        extract_data : _type_, optional
            _description_, by default extract_structur
        q_dir : _type_, optional
            _description_, by default None
        qin_options : _type_, optional
            _description_, by default None
        qsub_options : _type_, optional
            _description_, by default None
        """
        self.extract_structur = extract_data

        if os.path.isfile(qchem_template):
            self.qchem_input = read_qchem_temp(qchem_template)
        else:
            self.qchem_input = qchem_template

        if isinstance(q_dir, str):
            os.makedirs(q_dir, exist_ok=True)
            self.q_dir = q_dir
        else:
            self.q_dir = os.getcwd()

        if self.q_dir[-1] != '/':
            self.qdir += '/'

        if isinstance(qin_options, dict):
            self.qin_options = qin_options
        else:
            self.qin_options = {}

        if isinstance(qsub_options, str):
            self.qsub_options = qsub_options
        else:
            self.qsub_options = ''

    # there are now three ways to give options for the qchem input file all of them work
    # via str.format(**dcit)
    # 1. 'global'  those are given during class instance initilaization and are apllied
    #    to all qchem input files created with this instance
    # 2. 'mid range' those are given directly to wriet_qchem_file and are applied to all
    #    input files creatd by this specific function call
    # 3. 'local' those must be returned by the (user written) extract_structur() method
    #    and can give specific qchem options based on themselves
    #!   Warning: only 'options' wich have a field in the template file can be set (and
    #!   i think for every named field something has to be provided)

    def write_qchem_file(self, xyz_file, qin_options={}, qchem_send_job=True, echo=False):
        """writes the qchem input files using the xyz structurs supplied and the template and
        options given by the user here or at the class instance level.

        Parameters
        ----------
        xyz_file : str
            path to the MD simulation file containing the xyz coordinates
        qin_options : dict, optional
            general options to be written into the qchem input file requires an accordingly 
            written template file, by default {}
        qchem_send_job : bool, optional
            controls whether the qchem_send_job script will be called, but for actual sending
            '--send' must have been passed to the qsub_options of the class, by default True
        echo : bool, optional
            debugging option to echo rather than call the qchem_send_job scipt and its options,
            by default False
        """
        for qin_dict in self.extract_structur(xyz_file):
            # rework this stuff
            # time = qin_dict.pop('time')
            structur = qin_dict.pop('structur')

            # FIXME: how to deal with q_dir and user specified paths?
            try:
                infile_path = self.q_dir + qin_dict.pop('filepath')
            except KeyError:
                infile_path = self.q_dir + self._get_infile_path(qin_dict)

            try:
                qin_options_extract = qin_dict['qin_options']
            except KeyError:
                qin_options_extract = {}

            os.makedirs(os.path.dirname(infile_path), exist_ok=True)

            with open(infile_path, 'w') as infile:
                infile.write(self.qchem_input.format(structur=structur,
                                                     **qin_dict, **self.qin_options, **qin_options, **qin_options_extract))

            if qchem_send_job:
                self._send(infile_path)

            if echo:
                subprocess.run("echo qchem_send_job {options} {filepath}".format(
                    options=self.qsub_options, filepath=infile_path), shell=True)

    def _send(self, infile_path):
        """_summary_

        Parameters
        ----------
        infile_path : _type_
            _description_
        """
        subprocess.run("qchem_send_job {options} {filepath}".format(
            options=self.qsub_options, filepath=infile_path), shell=True)

    def _get_infile_path(self, qin_dict):
        """_summary_

        Parameters
        ----------
        qin_dict : _type_
            _description_

        Returns
        -------
        _type_
            _description_
        """
        return '/'.join([qin_dict['traj'], str(qin_dict['time']) + '.in'])


if __name__ == "__main__":
    # this will be required to set the timesteps to extract for
    # the extract_structur function
    from functools import partial
    import glob

    # finds the location of this file (i think) used to ensure this file runs with 
    # the supplied test data in the data/ directory idnependently of the (linux)
    # machine
    base_path = '/'.join(__file__.split('/')[:-2])
    
    # usage example and test
    # 1st define paths
    # to the qchem input template
    #! those paths will not work on other machines!
    qchem_temp = base_path + '/data/ta_send_test/input/qchem_test.template'
    # to the dir in whicht the input files are to be placed in general
    q_dir = base_path + '/data/ta_send_test/output/'
    # to the files/dirs from whch you want to extract the structur and
    # other stuff for the creation of the qchem input file
    data_dir = base_path + '/data/ta_send_test/input/'
    
    # set timesteps
    timesteps = np.arange( 0.0, 20.0, step=4)
    extract_func = partial(extract_structur, timesteps=timesteps)

    # define the additional general options you want to include into/home/tobias/heibox/ta-Qchem/data
    # the qchem_template via pythons str.format() function
    # those given here will be applied to all hereby created input
    # files!
    #! They must be given as a dictionary with keys as present in
    #! the template file
    qin_options = {'METHOD': 'hf'}

    # define options given to the qchem_send_job script via the command
    # line, if it is to be calculated at least send must be given!
    qsub_options = '--version qchem-5.2'

    # create the class instance
    #! if you have written your own extract_structur method give it here
    #! best implement any preselection of structurs/timesteps whatever
    #! that are supposed to be used in the extract_data function
    qwrite = QChemIn(qchem_temp, extract_data=extract_func, qin_options=qin_options,
                     q_dir=q_dir, qsub_options=qsub_options)

    # iterate over the files/dirs you for which you want to create (and send)
    # qchem calculations

    for filepath in glob.glob('**/*.xyz', root_dir=data_dir, recursive=True):
        #! for actual use set qchem_send_job to True and echo to False
        qwrite.write_qchem_file(data_dir + filepath,
                                qchem_send_job=False, echo=True)
