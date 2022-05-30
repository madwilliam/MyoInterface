from MyoInterface import MyoInterface
import struct
interface = MyoInterface()

async def function(interface:MyoInterface):
    # await interface.subscribe_raw_eeg(raw_emgg_callback)
    await interface.stream_raw_emg()
interface.connect_and_run_function(function)
print()