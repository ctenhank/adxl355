from lib import adxl355
import spidev
import time
from pathlib import Path
import pandas as pd
import datetime
import signal
from multiprocessing import Process, Queue
import logging

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
    bus = 1
    device = 1
    
    spi.open(bus, device)
    spi.max_speed_hz = 5000000
    spi.mode = 0b00

    return adxl355.ADXL355(spi.xfer2)

def main():
    global logger

    acc = init_spi()
    acc.stop()
    # sensor reset
    acc.write(adxl355.REG_RESET, 0x52)
    #time.sleep(0.5)
    # change mode to measurement mode
    acc.start()
    time.sleep(1)
    # print information of this accelerometer
    logger.info(acc.dumpinfo())

    # output directory
    outdir = Path('./data/adxl355/').resolve()
    outdir.mkdir(exist_ok=True, parents=True)

    # sampling rate
    rate = 100
    interval = 1 / rate
    # time
    seconds = 7200
    
    save_unit = rate * seconds    

    # The best method to capture in the exact time interval
    # actually, THIS IS NOT EXCAT, but the most exact method rather than 'sleep(1)'
    mask = [signal.SIGALRM]
    signal.setitimer(signal.ITIMER_REAL, 0.1, interval)
    signal.pthread_sigmask(signal.SIG_BLOCK, mask)

    # initialize loop to collect sensor data
    q = Queue()
    # cnt: the number of raw
    cnt = 0
    # the collection of the data
    arrdata = []
    start_time_file = 0
    while True:
        # if get a signal from OS, it check the type of signal
        received = signal.sigwait(mask)
        # if the signal is SIGALRM
        # collect data
        if received == signal.SIGALRM:
            data = acc.get3V()
            #logger.info(data)
            _time = time.time()
            data.append(_time)
            arrdata.append(data)
            if cnt == 0:
                start_time_file = _time
            cnt += 1
            # if the number of data is same as the save_unit, save the data
            if cnt == save_unit:
                logger.info(f"Create a {seconds}s data file since {datetime.datetime.utcfromtimestamp(start_time_file).strftime('%Y-%m-%d %H:%M:%S.%f')}")
                #break
                q.put(arrdata)
                p = Process(name="dumper", target=dump_data, args=(q, outdir))
                p.start()
                arrdata = []
                cnt = 0
        
if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler('adxl355.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    main()
