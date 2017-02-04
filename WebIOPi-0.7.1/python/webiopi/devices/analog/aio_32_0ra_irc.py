#   Copyright 2017 Y2 Corporation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from time import sleep
from webiopi.decorators.rest import request, response
from webiopi.devices.analog import ADC
from webiopi.devices.i2c import I2C
from webiopi.utils.types import M_JSON
from webiopi.utils.types import toint, signInteger

class AIO_32_0RA_IRC():
    def __init__(self, slaveAdc=0x49, slaveMux=0x3e):
        self._analogCount = 32
        self._analogResolution = 16
        self._analogMax = 2 ** (self._analogResolution - 1) - 1
        self._analogRef = 2.048 / 10 * 49
        
        slaveAdc = toint(slaveAdc)
        self.slaveAdc = slaveAdc
        self.adc = ADS1115(self.slaveAdc)

        slaveMux = toint(slaveMux)
        self.slaveMux = slaveMux
        self.mux = PCA9554C(self.slaveMux)
        self.mux.writeRegister(self.mux.CONFIGURATION_PORT, 0x00)

    def __str__(self):
        return "AIO-32/0RA-IRC(slaveAdc=0x{:02X}, slaveMux=0x{:02X})".format(self.slaveAdc, self.slaveMux)

    def __family__(self):
        return "ADC"

    def checkAnalogChannel(self, channel):
        if not 0 <= channel < self._analogCount:
            raise ValueError("Channel {} out of range [{}..{}]".format(channel, 0, self._analogCount - 1))

    @request("GET", "analog/count")
    @response("%d")
    def analogCount(self):
        return self._analogCount

    @request("GET", "analog/resolution")
    @response("%d")
    def analogResolution(self):
        return self._analogResolution
    
    @request("GET", "analog/max")
    @response("%d")
    def analogMaximum(self):
        return int(self._analogMax)
    
    @request("GET", "analog/vref")
    @response("%.2f")
    def analogReference(self):
        return self._analogRef
    
    def __analogRead__(self, channel, diff):
        d = self.mux.readRegister(self.mux.OUTPUT_PORT)
        if 16 <= channel:
            self.mux.__portWrite__(d & 0xf | ((channel & 0x0f) << 4))
        else:
            self.mux.__portWrite__(d & 0xf0 | channel)
        sleep(0.001)
        return self.adc.analogRead(channel / 16, diff)
    
    @request("GET", "analog/%(channel)d/integer")
    @response("%d")
    def analogRead(self, channel, diff=False):
        self.checkAnalogChannel(channel)
        return self.__analogRead__(channel, diff)
    
    @request("GET", "analog/%(channel)d/float")
    @response("%.2f")
    def analogReadFloat(self, channel, diff=False):
        return self.analogRead(channel, diff) / float(self._analogMax)
    
    @request("GET", "analog/%(channel)d/volt")
    @response("%.2f")
    def analogReadVolt(self, channel, diff=False):
        if self._analogRef == 0:
            raise NotImplementedError
        return self.analogReadFloat(channel, diff) * self._analogRef
    
    @request("GET", "analog/*/integer")
    @response(contentType=M_JSON)
    def analogReadAll(self, diff=False):
        values = {}
        for i in range(self._analogCount):
            values[i] = self.analogRead(i, diff)
        return values
            
    @request("GET", "analog/*/float")
    @response(contentType=M_JSON)
    def analogReadAllFloat(self, diff=False):
        values = {}
        for i in range(self._analogCount):
            values[i] = float("%.3f" % self.analogReadFloat(i, diff))
        return values
    
    @request("GET", "analog/*/volt")
    @response(contentType=M_JSON)
    def analogReadAllVolt(self, diff=False):
        values = {}
        for i in range(self._analogCount):
            values[i] = float("%.3f" % self.analogReadVolt(i, diff))
        return values
    
class PCA9554C(I2C):

    INPUT_PORT = 0
    OUTPUT_PORT = 1
    POLARITY_INVERSION_PORT = 2
    CONFIGURATION_PORT = 3

    def __init__(self, slave=0x3e):
        I2C.__init__(self, toint(slave))

    def __str__(self):
        return "PCA9554C(slave=0x{:02X})".format(self.slave)

    def __portWrite__(self, value):
        self.writeRegister(self.OUTPUT_PORT,  value)

class ADS1X1X(ADC, I2C):
    VALUE     = 0x00
    CONFIG    = 0x01
    LO_THRESH = 0x02
    HI_THRESH = 0x03
    
    CONFIG_STATUS_MASK  = 0x80
    CONFIG_CHANNEL_MASK = 0x70
    CONFIG_GAIN_MASK    = 0x0E
    CONFIG_MODE_MASK    = 0x01
    
    def __init__(self, slave, channelCount, resolution, name):
        I2C.__init__(self, toint(slave))
        ADC.__init__(self, channelCount, resolution, 2.048)
        self._analogMax = 2**(resolution-1)
        
        config = self.readRegisters(self.CONFIG, 2)
        
        mode = 1 # single shot conversion
        config[0] &= ~self.CONFIG_MODE_MASK
        config[0] |= mode
        
        gain = 0x2 # FS = +/- 2.048V
        config[0] &= ~self.CONFIG_GAIN_MASK
        config[0] |= gain << 1
        
        config[0] |= 0x80
        self.writeRegisters(self.CONFIG, config)
    
    def __str__(self):
        return "ADS1115(slave=0x{:02X})".format(self.slave)
        
    def __analogRead__(self, channel, diff=False):
        config = self.readRegisters(self.CONFIG, 2)
        config[0] &= ~self.CONFIG_CHANNEL_MASK
        if diff:
            config[0] |= channel << 4
        else:
            config[0] |= int(channel + 4) << 4
        self.writeRegisters(self.CONFIG, config)
        sleep(0.008)
        d = self.readRegisters(self.VALUE, 2)
        value = (d[0] << 8 | d[1]) >> (16-self._analogResolution)
        return signInteger(value, self._analogResolution)

class ADS1115(ADS1X1X):
    def __init__(self, slave=0x49):
        ADS1X1X.__init__(self, slave, 4, 16, "ADS1115")
