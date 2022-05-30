import matplotlib.pyplot as plt
import numpy as np
import asyncio
from bleak import BleakClient
from enum import Enum
import struct
from command_codes import *
from matplotlib.animation import FuncAnimation
class MyoInterface:
    def __init__(self,address = "F3:F8:2E:FB:8C:3C"):
        self.address = address
        self.code = CommandCode()
        self.loop = asyncio.get_event_loop()
        self.emg_data_queue = asyncio.Queue()

    def construct_uuid(self,command_code):
        return f'd506{command_code}-a904-deb9-4748-2c7f4a124842'
    
    async def set_mode(self,emg_mode = EmgMode.record_raw_emg, imu_mode = ImuMode.off, classifier_mode = ClassifierMode.disabled):
        print('Setting Myo Recording Mode')
        command = struct.pack('<5B', Commands.set_mode, 3, emg_mode, imu_mode, classifier_mode)
        await self.run_command(command)
    
    async def unlock_device(self,unlock_mode = UnlockModes.remain_unlocked_until_lock_command):
        print('Setting Myo Unlock Mode')
        command = struct.pack('<3B', Commands.unlock, 1, unlock_mode)
        await self.run_command(command)
    
    async def set_sleep_mode(self,sleep_mode = SleepModes.never_sleep):
        print('Setting Myo Sleep Mode')
        command = struct.pack('<3B', Commands.unlock, 1, sleep_mode)
        await self.run_command(command)
    
    async def run_command(self,command):
        uuid = self.construct_uuid(self.code.command)
        await self.client.write_gatt_char(uuid,command)
    
    async def read_data(self,uuid):
        return await self.client.read_gatt_char(uuid)
    
    async def subscribe(self,codes,callback=None,time = 120,stream_funtion = None):
        if callback is None:
            def callback(sender: int, data: bytearray):
                print(f"{sender}: {data}")
        for code in codes:
            uuid = self.construct_uuid(code)
            await self.client.start_notify(uuid, callback)
        if stream_funtion is not None:
            await stream_funtion()
        else:
            await asyncio.sleep(time)
        for code in codes:
            await self.client.stop_notify(uuid)
    
    async def subscribe_raw_eeg(self,raw_emgg_callback=None,stream_funtion = None,set_up_function = None):
        if set_up_function is not None:
            set_up_function()
        await self.unlock_device()
        await self.set_sleep_mode()
        await self.set_mode()
        await self.subscribe(self.code.emg_data,callback=raw_emgg_callback,stream_funtion=stream_funtion)
    
    async def stream_raw_emg(self,set_up_function = None,action=None):
        print('Starting Emg Stream')
        self.emg_data_stream = [[] for _ in range(8)]
        async def raw_emgg_callback(sender, data):
            id = self.code.emg_handles.index(sender)
            print(data)
            emg = struct.unpack('<16b', data)
            print(emg)
            await self.emg_data_queue.put((id,emg))
        if action is None:
            action = lambda self:print(self.emg_data_stream)
        stream_function = lambda : self.process_emg_data(action)
        await self.subscribe_raw_eeg(raw_emgg_callback,stream_funtion = stream_function,set_up_function=set_up_function)
    
    async def plot_live_raw_emg(self):
        self.lines = []
        self.nsamples_displayed = 1000
        plt.ion()
        def set_up_function():
            self.figure = plt.figure(figsize=[15,15])
            for i in range(8):
                ax = plt.subplot(8,1,i+1)
                line, = ax.plot(np.zeros(self.nsamples_displayed))
                ax.set_ylim(-50,50)
                self.lines.append(line)
        def update(self):
            for i in range(8):
                # print('updateing',len(self.emg_data_stream[i]))
                # xdata = self.emg_data_stream[i]
                ydata = self.emg_data_stream[i]
                if len(ydata) < self.nsamples_displayed:
                    ydata = np.pad(ydata,[0,self.nsamples_displayed-len(ydata)])
                # self.lines[i].set_xdata()
                self.lines[i].set_ydata(ydata)
            self.figure.canvas.draw()
            self.figure.canvas.flush_events()
        await self.stream_raw_emg(set_up_function=set_up_function,action = update)

    async def async_connect_and_run_function(self,function):
        print("Connecting to device...")
        async with BleakClient(self.address) as self.client:
            print('Connected')
            result = await function(self)
        return result
    
    def connect_and_run_function(self,function):
        result = asyncio.run(self.async_connect_and_run_function(function))
        return result
    
    async def read_basic_info(self):
        uuid = self.construct_uuid(self.code.basic_info)
        r = await self.read_data(uuid)
        serial_number = r[:6]
        unlock_pose = r[6:8]
        classifier_type = r[8:9]
        classifier_index = r[9:10]
        has_custom_classifier = r[10:11]
        stream_indicating = r[11:12]
        sku = r[12:13]
        reserved = r[13:]
    
    async def read_firmware_version(self):
        uuid = self.construct_uuid(self.code.firmware_version)
        r = await self.read_data(uuid)
        major = int.from_bytes(r[:2],'big')
        minor = int.from_bytes(r[2:4],'big') 
        patch = int.from_bytes(r[4:6],'big') 
        hardware_rev = int.from_bytes(r[6:],'big') 
    
    async def process_emg_data(self,action):
        while True:
            await self.process_queued_emg_data()
            action(self)
    
    async def process_queued_emg_data(self):
        print(self.emg_data_queue.qsize())
        while self.emg_data_queue.qsize() > 0:
            recv_characteristic,emg = await self.emg_data_queue.get()
            emg1 = emg[:8]
            emg2 = emg[8:16]
            # progression = (recv_characteristic - last_recv_characteristic) % 4
            # if progression > 1:
            #     for i in range(1,progression):
            #         for _ in range(0,8):
            #             self.emg_data_stream[i].append(0)
            # last_recv_characteristic = recv_characteristic
            for i in range(0,8):
                self.emg_data_stream[i].append(emg1[i])
                self.emg_data_stream[i].append(emg2[i])
            else:
                await asyncio.sleep(0.0001)

    async def plot_live_raw_emg_animate(self):
        self.lines = []
        self.nsamples_displayed = 1000
        def set_up_function():
            self.figure = plt.figure(figsize=[15,15])
            for i in range(8):
                ax = plt.subplot(8,1,i+1)
                line, = ax.plot(np.zeros(self.nsamples_displayed))
                ax.set_ylim(-50,50)
                self.lines.append(line)
        async def update(t):
            for i in range(8):
                ydata = self.emg_data_stream[i]
                if len(ydata) < self.nsamples_displayed:
                    ydata = np.pad(ydata,[0,self.nsamples_displayed-len(ydata)])
                self.lines[i].set_ydata(ydata)
                await self.process_queued_emg_data()
        async def raw_emgg_callback(sender, data):
            id = self.code.emg_handles.index(sender)
            emg = struct.unpack('<16b', data)
            await self.emg_data_queue.put((id,emg))
        async def stream_function():
            await self.process_queued_emg_data()
            ani = FuncAnimation(self.figure, update, interval=1)
            plt.show()
        self.emg_data_stream = [[] for _ in range(8)]
        await self.subscribe_raw_eeg(raw_emgg_callback,stream_funtion = stream_function,set_up_function=set_up_function)

class CommandCode:
    def __init__(self):
        self.basic_info='0101'
        self.firmware_version='0201'
        self.imu_data='0402'
        self.emg_data=['0105','0205','0305','0405']
        self.emg_handles = [42,45,48,51]
        self.battery_level='2a19'
        self.device_name='2a00'
        self.command = '0401'
