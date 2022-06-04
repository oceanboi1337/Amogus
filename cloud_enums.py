from enum import Enum

class CloudRegion(str, Enum):
    NewYork1 = 'nyc1'
    SanFrancisco1 = 'sfo1'
    NewYork2 = 'nyc2'
    Amsterdam2 = 'ams2'
    Singapore1 = 'sgp1'
    London1 = 'lon1'
    NewYork3 = 'nyc3'
    Amsterdam3 = 'ams3'
    Frankfurt1 = 'fra1'
    Toronto1 = 'tor1'
    SanFrancisco2 = 'sfo2'
    Bangalore1 = 'blr1'
    SanFrancisco3 = 'sfo3'

class CloudSize(str, Enum):
    Cpu1Gb1 = 's-1vcpu-1gb'
    Cpu1Gb2 = 's-1vcpu-2gb'
    Cpu2Gb2 = 's-2vcpu-2gb'
    Cpu2Gb4 = 's-2vcpu-4gb'

class CloudImage(str, Enum):
    Ubuntu_22_04_LTS_x64 = 'ubuntu-22-04-x64'