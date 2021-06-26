import adxl355
import spidev
import time
from pathlib import Path
import pandas as pd
import datetime
import signal
from multiprocessing import Process, Queue

def dump_data(q, outdir):
    data = q.get()
    df = pd.DataFrame(data)
    filename =outdir / (datetime.datetime.fromtimestamp(data[0][3]).isoformat() + '.csv')
    df.to_csv(str(filename), index=False, header=False, sep=',')
    print(f'saving... {filename}')

def init_spi():
    spi = spidev.SpiDev()
    bus = 0
    device = 0
    
    spi.open(bus, device)
    spi.max_speed_hz = 5000000
    # ADXL 355 has mode SPOL=0 SPHA=0, its bit code is 0b00
    # SPOL:
    # SPHA: 
    spi.mode = 0b00

    return adxl355.ADXL355(spi.xfer2)

def save_as_csv(data, filename):
    dataframe = pd.DataFrame(data)
    dataframe.to_csv(filename, index=False, header=False, sep=',')

def main():
    acc = init_spi()
    acc.dumpinfo()

    outdir = Path('./data/adxl355/').resolve()
    outdir.mkdir(exist_ok=True, parents=True)

    # sampling rate(100) * seconds(30)
    save_unit = 3000    

    mask = [signal.SIGALRM]
    signal.setitimer(signal.ITIMER_REAL, 0, 0.01)
    signal.pthread_sigmask(signal.SIG_BLOCK, mask)
    cnt = 0
    q = Queue()

    arrdata = []
    while True:
        received = signal.sigwait(mask)
        if received == signal.SIGALRM:
            data = acc.get3V()
            data.append(time.time())
            arrdata.append(data)
            cnt += 1
            if cnt == save_unit:
                q.put(arrdata)
                p = Process(name="dumper", target=dump_data, args=(q, outdir))
                p.start()
                arrdata = []
                cnt = 0
        
if __name__ == "__main__":
    main()