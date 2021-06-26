from lib import adxl355
import spidev
import time
from pathlib import Path
import pandas as pd
import datetime
import signal
from multiprocessing import Process, Queue

def dump_data(q, outdir):
    """
    To save the data as .csv file
    For blocking issues, I used the mechanism of the multiprocessing Queue.
    """
    data = q.get()
    df = pd.DataFrame(data)
    filename =outdir / (datetime.datetime.fromtimestamp(data[0][3]).isoformat() + '.csv')
    df.to_csv(str(filename), index=False, header=False, sep=',')
    print(f'saving... {filename}')

def init_spi():
    """
    Initialize the spi serial connection
    """
    spi = spidev.SpiDev()
    bus = 0
    device = 0
    
    spi.open(bus, device)
    spi.max_speed_hz = 5000000
    spi.mode = 0b00

    return adxl355.ADXL355(spi.xfer2)

def main():
    acc = init_spi()

    # print information of this accelerometer
    acc.dumpinfo()

    # output directory
    outdir = Path('./data/adxl355/').resolve()
    outdir.mkdir(exist_ok=True, parents=True)

    # sampling rate
    # rate(100) * seconds(30)
    save_unit = 3000    

    # The best method to capture in the exact time interval
    # actually, THIS IS NOT EXCAT, but the most exact method rather than 'sleep(1)'
    mask = [signal.SIGALRM]
    signal.setitimer(signal.ITIMER_REAL, 0.1, 0.01)
    signal.pthread_sigmask(signal.SIG_BLOCK, mask)

    # initialize loop to collect sensor data
    q = Queue()
    # cnt: the number of raw
    cnt = 0
    # the collection of the data
    arrdata = []
    while True:
        # if get a signal from OS, it check the type of signal
        received = signal.sigwait(mask)
        # if the signal is SIGALRM
        # collect data
        if received == signal.SIGALRM:
            data = acc.get3V()
            data.append(time.time())
            arrdata.append(data)
            cnt += 1
            # if the number of data is 3000, save the data
            if cnt == save_unit:
                q.put(arrdata)
                p = Process(name="dumper", target=dump_data, args=(q, outdir))
                p.start()
                arrdata = []
                cnt = 0
        
if __name__ == "__main__":
    main()