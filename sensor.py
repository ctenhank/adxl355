import spidev
import time

class ADXL355Driver():

    # SPI config
    SPI_MAX_CLOCK_HZ = 5000000
    SPI_MODE = 0b00
    SPI_BUS = 0
    SPI_DEVICE = 0

    # ADXL355 Address
    XDATA3 = 0x08
    XDATA2 = 0x09
    XDATA1 = 0x0A
    YDATA3 = 0x0B
    YDATA2 = 0x0C
    YDATA1 = 0x0D
    ZDATA3 = 0x0E
    ZDATA2 = 0x0F
    ZDATA1 = 0x10
    FIFO_ENTRIES = 0x05
    FIFO_DATA = 0x11
    RANGE = 0x2C
    POWER_CTL = 0x2D
    RESET = 0x2F
    FILTER = 0x28
    STATUS = 0x04

    # Configuration bit
    RANGE_2G = 0x01
    RANGE_4G = 0x02
    RANGE_8G = 0x03
    
    # Sps configure
    ODR_LPF = 0x03
    # ODR_LPF = 0x0A

    # Bit configuration
    READ_BIT = 0x01
    WRITE_BIT = 0x00
    DUMMY_BYTE = 0xAA
    RESET_BYTE = 0x52
    
    # Acceleration divider
    # ACC_DIV = (1 << 19) / 2.048
    
    # Axis scale factor
    # SCALE_FACTOR = 3.9 * (10 ** -6)
    SCALE_FACTOR = 2.048 / 2 ** 19
    
    def __init__(self, measure_range=0x01):
        # SPI init
        self.spi = spidev.SpiDev()
        self.spi.open(self.SPI_BUS, self.SPI_DEVICE)
        self.spi.max_speed_hz = self.SPI_MAX_CLOCK_HZ
        self.spi.mode = self.SPI_MODE

        # device reset
        time.sleep(0.1)
        self.write_data(self.RESET, self.RESET_BYTE)
        time.sleep(0.1)
        
        dev_ad_expected = 0xAD
        dev_mst_expected = 0x1D
        reg_id_expected = 0xED

        dad = self.read_data(0x00)
        mst = self.read_data(0x01)
        reg = self.read_data(0x02)

        print(dad == dev_ad_expected, mst == dev_mst_expected, reg == reg_id_expected)
        # Device init
        
        self._set_measure_range(measure_range)
        self.write_data(self.FILTER, self.ODR_LPF)
        self._enable_measure_mode()

    def write_data(self, address, value):
        device_address = address << 1 | self.WRITE_BIT
        self.spi.xfer2([device_address, value])

    def read_data(self, address):
        device_address = address << 1 | self.READ_BIT
        return self.spi.xfer2([device_address, self.DUMMY_BYTE])[1]
    
    def get_fifo_entries(self):
        return self.read_data(self.FIFO_ENTRIES)
    
    def read_from_fifo(self):
        x_data = []
        y_data = []
        z_data = []
        
        for x in range(3):
            x_data.append(self.read_data(self.FIFO_DATA))
        for y in range(3):
            y_data.append(self.read_data(self.FIFO_DATA))
        for z in range(3):
            z_data.append(self.read_data(self.FIFO_DATA))
            
        return [x_data, y_data, z_data]

    def _set_measure_range(self, measure_range):
        self.write_data(self.RANGE, measure_range)

    def read_multiple_data(self, address_list):
        spi_ops = []
        for address in address_list:
            spi_ops.append(address << 1 | self.READ_BIT)
        spi_ops.append(self.DUMMY_BYTE)

        return self.spi.xfer2(spi_ops)[1:]

    def read_three_bytes(self, address):
        spi_ops = [
            address << 1 | self.READ_BIT,
            self.DUMMY_BYTE,
            self.DUMMY_BYTE,
            self.DUMMY_BYTE
        ]
        rx = self.spi.xfer2(spi_ops)[1:]
        result = rx[2] << 16 + rx[1] << 8 + rx[0]
        print(result)
        return result
        
    
    def _enable_measure_mode(self, drdy_off: bool = True, temp_off: bool = True):
        drdy_on = 0x04
        temp_on = 0x02

        conf_byte = 0x00

        if drdy_off:
            conf_byte = conf_byte | drdy_on
        
        if temp_off:
            conf_byte = conf_byte | temp_on
        
        print('Measurement setting', conf_byte)
        self.write_data(self.POWER_CTL, conf_byte)
        

    def get_axes(self):
        """
        Gets the current data from the axes.
        Returns:
            dict: Current value for x, y and z axis
        """

        # Reading data
        #raw_data = self.read_multiple_data(
        #    [self.XDATA1, self.XDATA2, self.XDATA3, self.YDATA1, self.YDATA2, self.YDATA3, self.ZDATA1, self.ZDATA2, self.ZDATA3]
        #)
        
        #x_data = raw_data[0:3]
        #y_data = raw_data[3:6]
        #z_data = raw_data[6:9]
        
        x_data_list = []
        y_data_list = []
        z_data_list = []
        print(self.get_fifo_entries())
        entries = int(self.get_fifo_entries() / 3)
    
        for i in range(entries):
            # Read data from fifo
            
            raw_data = self.read_from_fifo()
            x_raw_data = raw_data[0]
            y_raw_data = raw_data[1]
            z_raw_data = raw_data[2]
            #print(x_raw_data[2] & 1)

            # Join data
            x_data = (x_raw_data[0] >> 4) + (x_raw_data[1] << 4) + (x_raw_data[2] << 12)
            y_data = (y_raw_data[0] >> 4) + (y_raw_data[1] << 4) + (y_raw_data[2] << 12)
            z_data = (z_raw_data[0] >> 4) + (z_raw_data[1] << 4) + (z_raw_data[2] << 12)
            
            
            #x_data = (x_raw_data[0] << 12) | (x_raw_data[1] << 4) | (x_raw_data[2] >> 4)
            #y_data = (y_raw_data[0] << 12) | (y_raw_data[1] << 4) | (y_raw_data[2] >> 4)
            #z_data = (z_raw_data[0] << 12) | (z_raw_data[1] << 4) | (z_raw_data[2] >> 4)

            # Apply two complement
            if x_data & 0x80000 == 0x80000:
                x_data = ~x_data + 1

            if y_data & 0x80000 == 0x80000:
                y_data = ~y_data + 1

            if z_data & 0x80000 == 0x80000:
                z_data = ~z_data + 1

            x_data = x_data / self.SCALE_FACTOR
            y_data = y_data / self.SCALE_FACTOR
            z_data = z_data / self.SCALE_FACTOR
            x_data_list.append(x_data)
            y_data_list.append(y_data)
            z_data_list.append(z_data)
        
        # Return values
        return {'x': x_data_list, 'y': y_data_list, 'z': z_data_list,
                'len': entries}

    def get_axes_2(self):
        x_data = self.read_three_bytes(self.XDATA3)
        y_data = self.read_three_bytes(self.YDATA3)
        z_data = self.read_three_bytes(self.ZDATA3)

        x_data = x_data >> 4
        y_data = y_data >> 4
        z_data = z_data >> 4

        # Apply two complement
        if x_data & 0x80000 == 0x80000:
            x_data = ~x_data + 1

        if y_data & 0x80000 == 0x80000:
            y_data = ~y_data + 1

        if z_data & 0x80000 == 0x80000:
            z_data = ~z_data + 1

        # Return values
        return {'x': x_data, 'y': y_data, 'z': z_data}
    
    def get_axes_from_reg(self):
        """
        Gets the current data from the axes.
        Returns:
            dict: Current value for x, y and z axis
        """
        
        targets = [
            [self.XDATA1, self.XDATA2, self.XDATA3],
            [self.YDATA1, self.YDATA2, self.YDATA3],
            [self.ZDATA1, self.ZDATA2, self.ZDATA3]
        ]
        
        results = []
        
        for axis in targets:
            raw_data = self.read_multiple_data(axis)
            while (raw_data[0] == 0 and raw_data[1] == 0 and raw_data[2] == 0):
                time.sleep(0.1)
                print(raw_data)
                raw_data = self.read_multiple_data(axis)
            results.append(raw_data)
        '''
        for axis in targets:
            raw_data = [
                self.read_data(axis[0]),
                self.read_data(axis[1]),
                self.read_data(axis[2])
            ]
            print(raw_data)
        '''
        print(results)
        x_data = results[0]
        y_data = results[1]
        z_data = results[2]
        
        x_data = (x_data[0] >> 4) + (x_data[1] << 4) + (x_data[2] << 12)
        y_data = (y_data[0] >> 4) + (y_data[1] << 4) + (y_data[2] << 12)
        z_data = (z_data[0] >> 4) + (z_data[1] << 4) + (z_data[2] << 12)
            
        #x_data = (x_raw_data[0] << 12) | (x_raw_data[1] << 4) | (x_raw_data[2] >> 4)
        #y_data = (y_raw_data[0] << 12) | (y_raw_data[1] << 4) | (y_raw_data[2] >> 4)
        #z_data = (z_raw_data[0] << 12) | (z_raw_data[1] << 4) | (z_raw_data[2] >> 4)

        
        def two_comp(val):
            if val >= 1 << 19:
                val -= 1 << 20
            return val
        
        '''
        def two_comp(val):
            if 0x80000 & val:
                ret = -(0x0100000 - val)
            else:
                ret = val
            return ret
        
        def two_comp(val):
            if (0x80000 & val):
                ret = - (0x0100000 - val)
            else:
                ret = val
            return ret
        '''
        x_data = two_comp(x_data)
        y_data = two_comp(y_data)
        z_data = two_comp(z_data)

        x_data = x_data * self.SCALE_FACTOR
        y_data = y_data * self.SCALE_FACTOR
        z_data = z_data * self.SCALE_FACTOR
        
        # Return values
        return {'x': x_data, 'y': y_data, 'z': z_data}


if __name__ == '__main__':
    import time

    sensor = ADXL355Driver()

    while True:        
        axes = sensor.get_axes_from_reg()
        print('x:', axes['x'],'y:', axes['y'], 'z:', axes['z'])
        #print(axes)
        # time.sleep(0.5)


    
