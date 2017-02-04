#   Copyright 2012-2013 Eric Ptak - trouch.com
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

from webiopi.utils.types import toint
from webiopi.devices.i2c import I2C
from webiopi.devices.digital import GPIOPort

class PCA9535(I2C, GPIOPort):
    
    INPUT_PORT0 = 0
    INPUT_PORT1 = 1
    OUTPUT_PORT0 = 2
    OUTPUT_PORT1 = 3
    POLARITY_INVERSION_PORT0 = 4
    POLARITY_INVERSION_PORT1 = 5
    CONFIGURATION_PORT0 = 6
    CONFIGURATION_PORT1 = 7
    
    def __init__(self, slave=0x27):
        slave = toint(slave)
        if slave in range(0x20, 0x28):
            self.name = "PCA9535"
        else:
            raise ValueError("Bad slave address for PCA9535 : 0x%02X not in range [0x20..0x27]" % slave)
        print("PCA9535: 0x{:02X}".format(slave))

        I2C.__init__(self, slave)
        GPIOPort.__init__(self, 16)
        self.banks = int(16 / 8)
        
    def __str__(self):
        return "%s(slave=0x%02X)" % (self.name, self.slave)
        
    def getAddress(self, register, channel=0):
        return register + int(channel / 8)

    def getChannel(self, register, channel):
        #print("getChannel ", register, channel)
        self.checkDigitalChannel(channel)
        addr = self.getAddress(register, channel) 
        mask = 1 << (channel % 8)
        #print(addr, mask)
        return (addr, mask)
    
    def __digitalRead__(self, channel):
        #print("digitalRead ", channel)
        (addr, mask) = self.getChannel(self.INPUT_PORT0, channel) 
        d = self.readRegister(addr)
        #print("d = 0x{:02X}".format(d))
        return (d & mask) == mask

    def __digitalWrite__(self, channel, value):
        (addr, mask) = self.getChannel(self.OUTPUT_PORT0, channel) 
        d = self.readRegister(addr)
        if value:
            d |= mask
        else:
            d &= ~mask
        self.writeRegister(addr, d)
        
    def __getFunction__(self, channel):
        (addr, mask) = self.getChannel(self.CONFIGURATION_PORT0, channel) 
        d = self.readRegister(addr)
        return self.IN if (d & mask) == mask else self.OUT
        
    def __setFunction__(self, channel, value):
        if not value in [self.IN, self.OUT]:
            raise ValueError("Requested function not supported")

        (addr, mask) = self.getChannel(self.CONFIGURATION_PORT0, channel) 
        d = self.readRegister(addr)
        if value == self.IN:
            d |= mask
        else:
            d &= ~mask
        self.writeRegister(addr, d)

    def __portRead__(self):
        #print("portRead ", self.banks)
        value = 0
        for i in range(self.banks):
            #print("readRegister ", i)
            value |= self.readRegister(self.INPUT_PORT0+i) << 8*i
        #print("value = 0x{:02X}".format(value))
        return value
    
    def __portWrite__(self, value):
        for i in range(self.banks):
            self.writeRegister(self.banks*self.OUTPUT_PORT0+i,  (value >> 8*i) & 0xFF)
