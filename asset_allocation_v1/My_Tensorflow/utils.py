import numpy as np

def moving_average(a, n = 3):
    ret = np.cumsum(a, dtype = float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n-1:]/n

if __name__ == '__main__':
    a = range(10)
    print a
    print moving_average(a, 2)
