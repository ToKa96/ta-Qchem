# ta_qchem

This is a simple package written to extract transient absorption data obtained by Qchem ADC, CVS-ADC and FANO (ADC) calculations during my Masterthesis.

## TO-DO-List

Things you will likely have to implement (read according section for detail)

- [ ] `extract_structur` function which parses over your MD data and gets the geometry
- [ ] `get_pop` function which parses your excited state population data
- [ ] `extractor` which parses the specific QM calculation output and returns the excitation energy and oscillator strength

## ta_send

This script is designed to create the necessary qchem input files for the calculation of the (excited state) absorption spectra at the different trajectories and times.

for most cases the already impelmented extract structur method will not work! Thus you willhave to implement your own version. It must take at least one argument, teh file name of the molecular dynamics file and must return as dict at least the geometry as a string.

~~~python
    def extract_structure(filename, *args, **kwargs):
        ...
        yield {'structur': xyz : str}
~~~

all further arguments to this function should be passed beforehand using the fucntools.partial() function

~~~python
    from functools import partial
    extract_func = partial(extract_structure, args, kwargs)
~~~

if you want to specify your own path for the qchem input files you can do so by returning the appropriate path with the keyword 'filepath' in the returned dict of the extract_structure function

~~~python
    def extract_structure(filename : str, *args, **kwargs):
        ...
        yield {'structur': xyz :str, 'filepath': path : str}
~~~

further 'options' for the qchem template can also be returned as additional keywords.

### ***Attention***

all fields which are to be completed by the script in the qchem input file must be specified by a keyword in braces for example:

    $molecule
    0 1
    {structur}
    $end

    $rem
        METHOD  ADC(2)
        E_SIGNLETS {singlets}
    $end

***all those keywords must at some point in the script be given as keys in a dict (empty string is ok) otehrwise an Error will be raised!***

this can be achieved either at the class instance level using the  `qin_options` keyword, at the function level using the  `qin_options` keyword when calling `write_qchem_file` or by suppling them during the `extract_structur` function. In all cases they have to be supplied as dictionary key value pairs.

the followup scripts are currently assuming the following directory/filestructur:

    outputdir/
    |----Trajectory1/
    |    |----0.0.out (qchem output file at 0 fs or whatever else start timestep you have)
    |    |----0.5.out
    |----Trajectory2/
    |    |----0.0.out
    ...

## qchem_to_hdf5

This script is designed to extract the relevant data for a Ta spectrum from the qchem .out files and the files containing the population data for the trajectories and write them into an HDF5 file for later reading and calculation of the TA spectrum. This is advised as the parsing time through hundreds if not thousands of output files takes much longer than reading in an HDF5 file.

you will likely have to implement a `get_pop` function (or generator) which will take as argument a general path (parent directory) to the files in which the population data is contained and returns the population data, time and trajectory as key values pairs of a dictionary in a list (or via generator). Example:

~~~python
def get_pop(path : str):
    # iterate over files in the parent directories and subdirs
    for files in path:
        ...
        # as generator
        yield {'traj': trajectory : str, 'time': time :str, 'pop': list or np.ndarray}
~~~

Additionally you will likely have to define your own parser (extractor) if you are not using the qchem fano method. This parser function should return an object with two methods: `get_pump_states` wich will return a list/array/tuple whatever of identifiers for your pump states. Over this Squence will be iterated and call the next function you will have to implement `get_pump_probe_data(pump_state)` which will have to return a dictionary containing your data and **Importantly return your excitation energy with the keyword __exc_energy__ and your oscillator strength with the keyword __osc_strength__**.

~~~python
class Data:

    def get_pump_states() -> Sequence:
        ...
        return list_of_pump_states

    def get_pump_probe_data(pump_state_name):
        ...
        return {
            'exc_energy': excitation_energy : Sequence,
            'osc_strength' : oscillator_strength : Sequence,
        }
~~~

If everything went fine you should now have a hdf5 file which can simply be plugged used with the functions from the ta_from_hdf5 module to calculate your TA spectrum

## ta_from_hdf5

# ***Use with care*** 

only limited testing has been performed! Only used on UNIX systems till now.
