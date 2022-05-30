from MyoInterface import MyoInterface
interface = MyoInterface()
async def function(interface:MyoInterface):
    await interface.record_raw_emg(r'C:\Users\madwill\Desktop\test.csv')
interface.connect_and_run_function(function)
