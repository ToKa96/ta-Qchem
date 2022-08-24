# ta_qchem

This is a simple package written to extract transient absorption data obtained by Qchem ADC, CVS-ADC and FANO (ADC) calculations during my Masterthesis.

## ta_send

for most cases the already impelmented extract structur method will not work! Thus you willhave to implement your own version. It must take at least one argument, teh file name of the molecular dynamics file and must return as dict at least the geometry as a string.

~~~python
    def extract_structure(filename, *args, **kwargs):
        whatever ...

        yield {'structur': xyz (type:str)}
~~~

all further arguments to this function should be passed beforehand using the fucntools.partial() function

~~~python
    from functools import partial
    extract_func = partial(extract_structure, args, kwargs)
~~~

if you want to specify your own path for the qchem input files you can do so by returning the appropriate path with the keyword 'filepath' in the returned dict of the extract_structure function

~~~python
    def extract_structure(filename, *args, **kwargs):
        whatever ...

        yield {'structur': xyz (type:str), 'filepath': path (type:str)}
~~~

further 'options' for the qchem template can also be returned as additional keywords.

### ==Attention==

all fields which are to be completed by the script in the qchem input file must be specified by a keyword in braces for example:

    $molecule
    0 1
    {structur}
    $end

    $rem
        METHOD  ADC(2)
        E_SIGNLETS {singlets}
    $end

==all those keywords must at some point in the script be given as keys in a dict (empty string is ok) otehrwise an Error will be raised!==

this can be achieved either at the class instance level using the  `qin_options` keyword, at the function level using the  `qin_options` keyword when calling `write_qchem_file` or by suppling them during the `extract_structur` function. In all cases they have to be supplied as dictionary key value pairs.

the followup scripts are currently assuming the following directory/filestructur:

    outputdit/
    |----Trajectory1/
    |    |----0.0.out (qchem output file at 0 fs or whatever else start timestep you have)
    |    |----0.5.out
    |----Trajectory2/
    |    |----0.0.out
    ...

## Use with care 

only limited testing has been performed! Only used on UNIX systems till now.
