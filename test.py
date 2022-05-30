from MyoInterface import MyoInterface
import struct
interface = MyoInterface()

async def raw_emgg_callback(sender, data):
    emg = struct.unpack('<16b', data)
    await interface.emg_data_queue.put((emg))
    print(interface.emg_data_queue.qsize())
async def function(interface:MyoInterface):
    # await interface.subscribe_raw_eeg(raw_emgg_callback)
    await interface.stream_raw_emg(action = lambda x : ...)
interface.connect_and_run_function(function)
print()