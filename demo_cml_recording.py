"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from forceDAQ.recorder import DataRecorder, Clock, SoftTrigger, ForceData, SensorSettings

if __name__  == "__main__":
    clock = Clock()

    # create a sensor
    sensor1 = SensorSettings(device_id=1, sync_clock=clock,
                                    calibration_file="FT_demo.cal") 

    # create a data recorder
    recorder = DataRecorder(force_sensors = [sensor1],
                            poll_udp_connection=False, sync_clock=clock)
    recorder.open_data_file("outdata", directory="data", suffix=".csv",
                           time_stamp_filename=False,   comment_line="")

    print "setting bias, not touch the sensor!"
    #raw_input("Press Enter...")
    recorder.determine_biases(n_samples=100)
    data = []
    clock.wait(1000)
    print "start recording"
    #raw_input("Press Enter...")

    recorder.start_recording()
    clock.wait(500)
    recorder.set_soft_trigger(100)
    clock.wait(1000)
    recorder.set_soft_trigger(200)

    data = recorder.process_sensor_input()
    recorder.quit()
    print "stop recording"

    counter = 0
    for d in data:
        counter += 1
        if isinstance(d, ForceData):
            if counter % 100 == 1:
                print d
                pass
        if isinstance(d, SoftTrigger):
            print d.time

    print counter


