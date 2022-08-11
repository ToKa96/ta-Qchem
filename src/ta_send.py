"""
Author: Tobias Kaczun
"""
from genericpath import isdir, isfile
import os
import subprocess
import numpy as np


# TODO: add passing of qchem_send_job args


def read_qchem_temp(qchem_template):
    qin = ''
    with open(qchem_template) as tmp:
        for line in tmp:
            qin += line

    return qin


def extract_structur(xyzFile):

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

                    yield structur, time
                    structur = ''

            if 'Time' in line:
                time = float(line.split()[-1])
                start_struct = True

        yield {'structur': structur, 'time': time, 'traj': traj}


class QChemIn:

    def __init__(self,  qchem_template, extract_data=extract_structur, q_dir=None, qin_options=None, qsub_options=None) -> None:
        self.extract_structur = extract_data

        if os.isfile(qchem_template):
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
        # TODO add infile_path generation or passing
        for qin_dict in self.extract_structur(xyz_file):
            # rework this stuff
            # time = qin_dict.pop('time')
            structur = qin_dict.pop('structur')

            # FIXME: how to deal with q_dir and user specified paths?
            if qin_dict['filepath']:
                infile_path = self.q_dir + qin_dict.pop('filepath')
            else:
                infile_path = self.q_dir + self.get_infile_path(qin_dict)

            if qin_dict['qin_options']:
                qin_options_extract = qin_dict['qin_options']
            else:
                qin_options_extract = {}

            os.makedirs(os.path.dirname(infile_path), exist_ok=True)

            with open(infile_path) as infile:
                infile.write(self.qchem_input(structur=structur,
                                              **qin_dict, **self.qin_options, **qin_options, **qin_options_extract))

            if qchem_send_job:
                self.send(infile_path)

            if echo:
                subprocess.run("echo qchem_send_job {options} {filepath}".format(
                    options=self.qsub_options, filepath=infile_path), shell=True)

    def send(self, infile_path):
        subprocess.run("qchem_send_job {options} {filepath}".format(
            options=self.qsub_options, filepath=infile_path), shell=True)

    def get_infile_path(self, qin_dict):
        return '/'.join([qin_dict['traj'], str(qin_dict['time']) + '.in'])


if __name__ == "__main__":
    # usage example and test
    # 1st define paths
    # to the qchem input template
    qchem_temp = ''
    # to the dir in whicht the input files are to be placed in general
    q_dir = ''
    # to the files/dirs from whch you want to extract the structur and
    # other stuff for the creation of the qchem input file
    data_dir = ''

    # define the additional general options you want to include into
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
    # if you have written your own extract_structur method give it here
    qwrite = QChemIn(qchem_temp, qin_options=qin_options,
                     q_dir=q_dir, qsub_options=qsub_options)

    # iterate over the files/dirs you for which you want to create (and send)
    # qchem calculations

    for filepath in data_dir:
        #! for actual use set qchem_send_job to True and echo to False
        qwrite.write_qchem_file(filepath, qchem_send_job=False, echo=True)
