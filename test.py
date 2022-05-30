from MyoInterface import MyoInterface
interface = MyoInterface()
async def function(interface:MyoInterface):
    await interface.stream_raw_emg()
interface.connect_and_run_function(function)
