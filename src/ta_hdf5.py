from qextract import ta_extract
import sys

# TODO: update this convenience script to the new methods
# TODO: implement with argparse!

if __name__ == "__main__":
    outpath = sys.argv[-2] 
    hdf5File = sys.argv[-1]

    ta_extract.writeHDF5(outpath, hdf5File, adiabatic=True)
