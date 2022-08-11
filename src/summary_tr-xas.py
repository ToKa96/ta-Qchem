import h5py
import os
import numpy as np
import sys

# TODO: modifi for version 0.9
# TODO: add argparse
# TODO: better specification of Trajectorie names?

def of_write(of):
    of.write('\t'.join(['time', 'state',])+ '\n')
    for time in np.arange(0, 200.5, 0.5):
        try:
            time_traj = f['{:.1f}'.format(time)+'/'+traj]
            state_indx = int(np.where(time_traj['pop'][:]==1)[0])
            adibatic_state = 'S{}'.format(state_indx)
            adc_state = '{}_(1)_A'.format(state_indx+1)
            exc = ['{:.2f}'.format(x) for x in time_traj[adc_state+'/exc_energy'][:]]
            osc = ['{:.4f}'.format(x) for x in time_traj[adc_state+'/osc_strength'][:]]
            exc_osc = [value for sublist in zip(exc, osc) for value in sublist]
            of.write('{:.1f}'.format(time)+'\t'+adibatic_state+'\t'+'\t'.join(exc_osc)+'\n')
        except (KeyError, ):
            of.write('{:.1f}'.format(time)+'\n')

if __name__ == '__main__':

    hdf5File = sys.argv[-2]
    outputDir= sys.argv[-1]

    os.makedirs(outputDir , exist_ok=True)

    with h5py.File(hdf5File) as f:
        for traj in ['TRAJ{}'.format(i) for i in range(1, 101)]:
            with open(outputDir+ '/{}.dat'.format(traj), 'w') as of:
                of_write(of)

        for traj in ['TRAJ{}'.format(i) for i in [ 109, 115,
                                                    136, 151, 184, 198, 200, 232, 233, 236,
                                                    242, 250, 258, 264, 276, 284, 287, 288,
                                                    305, 311, 316, 338, 354, 358, 371, 385,
                                                    395, 403, 405, 413, 446, 455, 478, 483,
                                                    484, 498, 515, 533, 536, 537, 552, 558,
                                                    562, 585, 612, 630, 654, 662, 675, 696,
                                                    702, 711, 721, 733, 755, 768, 769, 772,
                                                    783, 792, 805, 806, 814, 843, 854, 857,
                                                    858, 873, 886, 887, 890, 892, 908, 938,
                                                    958, 959, 968, 983, 985, 994,]]: 
            with open(outputDir+ '/{}.dat'.format(traj), 'w') as of:
                of_write(of)
