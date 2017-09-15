import pandas as pd
import numpy as np
import pywt

class TimingWt(object):

    def __init__(self, data):
        self.data = data
        self.wname = "sym4"
        self.maxlevel = 4
        self.filter_level = [0, 3, 4]

    def wavefilter(self, data):
        """
        This function requires that the NumPy and PyWavelet packages
        are installed. They are freely available at:

        NumPy - http://numpy.scipy.org/
        PyWavelets - http://www.pybytes.com/pywavelets/#download

        Filter a multi-channel signal using wavelet filtering.

        data     - n x m array, n=number of channels in the signal,
                    m=number of samples in the signal
        maxlevel - the level of decomposition to perform on the data. This integer
                    implicitly defines the cutoff frequency of the filter.
                    Specifically, cutoff frequency = samplingrate/(2^(maxlevel+1))
        """

        if len(data)%2 == 1:
            data = data[1:]
        # We will use the Daubechies(4) wavelet
        wname = self.wname

        data = np.atleast_2d(data)
        numwires, datalength = data.shape
        # Initialize the container for the filtered data
        fdata = np.empty((numwires, datalength))

        for i in range(numwires):
            # Decompose the signal
            c = pywt.wavedec(data[i,:], wname, level = self.maxlevel)
            #print c
            # Destroy the approximation coefficients
            for j in self.filter_level:
                c[j][:] = 0
            # Reconstruct the signal and save it
            fdata[i,:] = pywt.waverec(c, wname)

        if fdata.shape[0] == 1:
            return fdata.ravel() # If the signal is 1D, return a 1D array
        else:
            return fdata # Otherwise, give back the 2D array

    def handle(self):
        yoy = np.array(self.data.yoy)
        signal = []
        for i in np.arange(120, len(yoy)+1):
            fdata = self.wavefilter(yoy[:i])
            if fdata[-1] - fdata[-2] > 0:
                signal.append(1)
            else:
                signal.append(-1)
        signal = [np.nan]*(len(yoy) - len(signal)) + signal
        self.data['signal'] = signal
        self.data.to_csv('tmp/tw_sp500_result.csv', index_label = 'date')
        print self.data

if __name__ == '__main__':
    data = pd.read_csv('tmp/cycle_sp500_result.csv', index_col = 0, \
            parse_dates = True)
    tw = TimingWt(data)
    tw.handle()
