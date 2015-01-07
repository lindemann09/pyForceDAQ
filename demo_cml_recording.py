"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from forceDAQ import DataRecorder, force_sensor, Clock

if __name__  == "__main__":
    clock = Clock()

    # create a sensor
    sensor1 = force_sensor.Settings(device_id=1, sync_clock=clock,
                                    calibration_file="FT_demo.cal")

    # create a data recorder
    recorder = DataRecorder(force_sensors = [sensor1],
                            poll_udp_connection=False, sync_clock=clock)
    recorder.open_data_file("outdata", directory="data", suffix=".csv",
                           time_stamp_filename=False,   comment_line="")

    print "setting bias, not touch the sensor!"
    #raw_input("Press Enter...")
    recorder.determine_biases(n_samples=100)

    clock.wait(1000)
    print "start recording"
    #raw_input("Press Enter...")

    recorder.start_recording()
    clock.wait(500)
    recorder.process_sensor_input()
    # record for two seconds and print ever 100th sample
    recorder.set_soft_trigger(100)
    clock.reset_stopwatch()
    while clock.stopwatch_time<1000:
        recorder.process_sensor_input()
    recorder.set_soft_trigger(200)

    clock.reset_stopwatch()
    counter = 0
    while clock.stopwatch_time <= 100:
        recorder.process_sensor_input()

        data = recorder.get_buffer()
        for d in data:
            counter += 1
            if isinstance(d, force_sensor.ForceData):
                if counter % 100 == 1:
                    print d
                    pass

    recorder.pause_recording()
    print "stop recording"

    print counter
    recorder.quit()


