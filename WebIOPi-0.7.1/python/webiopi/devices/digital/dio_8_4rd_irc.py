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

from webiopi.decorators.rest import request, response
from webiopi.devices.digital.pca9555 import PCA9535
from webiopi.utils.types import M_JSON
from webiopi.utils.types import toint

class DIO_8_4RD_IRC():
    def __init__(self, slave=0x23):
        self.digitalChannelCount = 16
        
        self.slave = toint(slave)
        self.expander = PCA9535(self.slave)
        self.IN = self.expander.IN
        self.OUT = self.expander.OUT
        for channel in range(8):
            self.expander.__setFunctionString__(channel, 'out')

    def __str__(self):
        return "DIO-8/4RD-IRC(slave=0x{:02X})".format(self.slave)

    def __family__(self):
        return "GPIOPort"

    def close(self):
        self.portWrite(0)

    def checkDigitalChannel(self, channel):
        if not 0 <= channel < self.digitalChannelCount:
            raise ValueError("Channel %d out of range [%d..%d]" % (channel, 0, self.digitalChannelCount - 1))

    def checkDigitalValue(self, value):
        if not (value == 0 or value == 1):
            raise ValueError("Value %d not in {0, 1}")

    @request("GET", "count")
    @response("%d")
    def digitalCount(self):
        return self.digitalChannelCount

    def getFunction(self, channel):
        self.checkDigitalChannel(channel)
        return self.expander.getFunction(channel)

    @request("GET", "%(channel)d/function")
    def getFunctionString(self, channel):
        func = self.getFunction(channel)
        if func == self.IN:
            return "IN"
        elif func == self.OUT:
            return "OUT"
        else:
            return "UNKNOWN"

    def setFunction(self, channel, value):
        return self.getFunction(channel)

    def setFunctionString(self, channel, value):
        return self.getFunctionString(channel)

    @request("GET", "%(channel)d/value")
    @response("%d")
    def digitalRead(self, channel):
        self.checkDigitalChannel(channel)
        return not self.expander.digitalRead(channel)

    @request("GET", "*/integer")
    @response("%d")
    def portRead(self):
        return ~self.expander.portRead() & 0xffff
    
    @request("POST", "%(channel)d/value/%(value)d")
    @response("%d")
    def digitalWrite(self, channel, value):
        self.checkDigitalChannel(channel)
        self.checkDigitalValue(value)
        self.expander.digitalWrite(channel, not value)
        return self.digitalRead(channel)  

    @request("POST", "*/integer/%(value)d")
    @response("%d")
    def portWrite(self, value):
        self.expander.portWrite(~value & 0xffff)
        return self.portRead()

    @request("GET", "*")
    @response(contentType=M_JSON)
    def wildcard(self, compact=False):
        if compact:
            f = "f"
            v = "v"
        else:
            f = "function"
            v = "value"
            
        values = {}
        for i in range(self.digitalChannelCount):
            if compact:
                func = self.getFunction(i)
            else:
                func = self.getFunctionString(i)
            values[i] = {f: func, v: int(self.digitalRead(i))}
        return values

