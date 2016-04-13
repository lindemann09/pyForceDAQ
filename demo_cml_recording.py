"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from forceDAQ.recorder_classes import ForceData, DAQEvents, Timer, DataRecorder, SensorSettings

if __name__  == "__main__":
    timer = Timer()

    # create a sensor
    sensor1 = SensorSettings(device_id="Dev1", sync_timer=timer,
                             calibration_file="FT_sensor1.cal") #FIXME

    # create a data recorder
    recorder = DataRecorder(force_sensor_settings= [sensor1],
                            timer=timer,
                            poll_udp_connection=False)
    recorder.open_data_file("outdata", directory="data", suffix=".csv",
                           time_stamp_filename=False,   comment_line="")

    print "setting bias, not touch the sensor!"
    #raw_input("Press Enter...")
    recorder.determine_biases(n_samples=100)
    data = []
    timer.wait(1000)
    print "start recording"
    #raw_input("Press Enter...")

    recorder.start_recording()
    timer.wait(500)
    recorder.save_soft_trigger(100)
    timer.wait(1000)
    recorder.save_soft_trigger(200)

    print "pause recording"
    data = recorder.pause_recording()
    counter = 0
    for d in data:
        counter += 1
        if isinstance(d, ForceData):
            if counter % 100 == 1:
                print d
                pass
        if isinstance(d, DAQEvents):
            print d.time

    print "counter", counter

    recorder.quit()
    print "quitted"





