"""pyATIDAQ: Python wrapper for atidaq c library

Notes
-----
see ftconfig.h & ftsharedrt.h for details

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from sys import platform
from ctypes import *

from .._lib.misc import find_calibration_file
# ### DATA TYPES ####
VOLTAGE_SAMPLE_TYPE = c_float * 7
FT_SAMPLE_TYPE = c_float * 6
DISPLACEMENT_VECTOR = c_float * 8
UNITS = c_char_p
MAX_AXES = 6
MAX_GAUGES = 8


# calibration information required for F/T conversions
class RTCoefs(Structure):
    _fields_ = [
        ('NumChannels', c_ushort),
        ('NumAxes', c_ushort),
        ('working_matrix', (c_float * MAX_AXES) * MAX_GAUGES),
        ('bias_slopes', c_float * MAX_GAUGES),
        ('gain_slopes', c_float * MAX_GAUGES),
        ('thermistor', c_float),
        ('bias_vector', c_float * (MAX_GAUGES + 1)),
        ('TCbias_vector', c_float * MAX_GAUGES)]


class Transform(Structure):
    _fields_ = [
        ('TT', c_float * 6),  # displacement/rotation vector dx, dy, dz, rx, ry, r
        ('DistUnits', UNITS),  # units of dx, dy, dz
        ('AngleUnits', UNITS)]  # units of rx, ry, rz


class Configuration(Structure):
    _fields_ = [
        ('ForceUnits', UNITS),  # force units of output
        ('TorqueUnits', UNITS),  # torque units of output
        ('UserTransform', Transform),  # coordinate system transform set by user
        ('TempCompEnabled', c_bool)]  # is temperature compensation enabled?


class Calibration(Structure):
    _fields_ = [
        ('BasicMatrix', (c_float * MAX_AXES) * MAX_GAUGES),  # non-usable matrix; use rt.working_matrix for calculations
        ('ForceUnits', UNITS),  # force units of basic matrix, as read from file; constant
        ('TorqueUnits', UNITS),  # torque units of basic matrix, as read from file; constant
        ('TempCompAvailable', c_bool),  # does this calibration have optional temperature compensation?
        ('BasicTransform', Transform),  # built-in coordinate transform; for internal use
        ('MaxLoads', c_float * MAX_AXES),  # maximum loads of each axis, in units above
        ('AxisNames', c_char_p * MAX_AXES),  # names of each axis
        ('Serial', c_char_p),  # serial number of transducer (such as "FT4566")
        ('BodyStyle', c_char_p),  # transducer's body style (such as "Delta")
        ('PartNumber', c_char_p),  # calibration part number (such as "US-600-3600")
        ('Family', c_char_p),  # family of transducer (typ. "DAQ")
        ('CalDate', c_char_p),  # date of calibration
        ('cfg', Configuration),  # struct containing configurable parameters
        ('rt', RTCoefs)]  # struct containing coefficients used in realtime calculations


calibration_p = POINTER(Calibration)


class ATI_CDLL(object):

    def __init__(self):

        if platform.startswith('linux'):
            lib_path = "/usr/lib/atidaq.so"
        elif platform == 'win32':
            lib_path = "C:\\Windows\\System\\atidaq.dll"
        else:
            raise RuntimeError("Your plattform is not supported")

        self.cdll = CDLL(lib_path)

        self.cdll.createCalibration.argtype = [c_char_p, c_ushort]
        self.cdll.createCalibration.restype = calibration_p

        self.cdll.destroyCalibration.argtype = [calibration_p]
        self.cdll.destroyCalibration.restype = None

        self.cdll.SetToolTransform.argtype = [calibration_p, DISPLACEMENT_VECTOR,
                                c_char_p, c_char_p]
        self.cdll.SetToolTransform.restype = c_short

        self.cdll.SetForceUnits.argtype = [calibration_p, c_char_p]
        self.cdll.SetForceUnits.restype = c_short

        self.cdll.SetTorqueUnits.argtype = [calibration_p, c_char_p]
        self.cdll.SetTorqueUnits.restype = c_short

        self.cdll.SetTempComp.argtype = [calibration_p, c_char_p]
        self.cdll.SetTempComp.restype = c_short

        self.cdll.Bias.argtype = [calibration_p, POINTER(c_float)]
        self.cdll.Bias.restype = None

        self.cdll.ConvertToFT.argtype = [calibration_p, POINTER(c_float),
                                POINTER(c_float)]
        self.cdll.ConvertToFT.restype = None

        self.cdll.printCalInfo.argtype = [calibration_p]
        self.cdll.printCalInfo.restype = None

        self._calibration = None

    def __del__(self):
        self.destroyCalibration()

    def calibration(self):
        """The current calibration
        Returns
           cal: POINTER(Calibration), calibration pointer
                initialized Calibration struct

        """
        return self._calibration

    def createCalibration(self, CalFilePath, index):
        """ Loads calibration info for a transducer into a new Calibration struct
        Parameters:
           CalFilePath: c_char_p
                the name and path of the calibration file
           index: c_ushort
                the number of the calibration within the file (usually 1)
           NULL: Could not load the desired calibration.
         Notes: For each Calibration object initialized by this function,
                destroyCalibration must be called for cleanup.
        """

        self._calibration = self.cdll.createCalibration(CalFilePath.encode(), index)
        if self._calibration == 0:
            raise RuntimeError("Specified calibration could not be loaded.")


    def destroyCalibration(self):
        """Frees memory allocated for Calibration struct by a successful
         call to createCalibration.  Must be called when Calibration
         struct is no longer needed.
        """

        return self.cdll.destroyCalibration(self._calibration)

    def setToolTransform(self, Vector, DistUnits, AngleUnits):
        """Performs a 6-axis translation/rotation on the transducer's coordinate system.
         Parameters:
           Vector: array of float
                displacements and rotations in the order Dx, Dy, Dz, Rx, Ry, Rz
           DistUnits: c_char_p
                units of Dx, Dy, Dz
           AngleUnits: c_char_p
                units of Rx, Ry, Rz
        """

        error = self.cdll.SetToolTransform(self._calibration, DISPLACEMENT_VECTOR(*Vector),
                                           DistUnits.encode(),
                                           AngleUnits.encode())
        if error:
            if error == 1:
                raise RuntimeError("Invalid Calibration struct.")
            elif error == 2:
                raise RuntimeError("Invalid distance units.")
            elif error == 3:
                raise RuntimeError("Invalid angle units.")
            else:
                raise RuntimeError("Unknown error.")



    def setForceUnits(self, NewUnits):
        """Sets the units of force output
         Parameters:
           NewUnits: c_char_p
                units for force output
        		("lb","klb","N","kN","g","kg")
        """

        error = self.cdll.SetForceUnits(self._calibration,
                                        NewUnits.encode())
        if error:
            if error == 1:
                raise RuntimeError("Invalid Calibration struct.")
            elif error == 2:
                raise RuntimeError("Invalid force units.")
            else:
                raise RuntimeError("Unknown error.")


    def setTorqueUnits(self, NewUnits):
        """Sets the units of torque output
         Parameters:
           NewUnits: c_char_p
                units for torque output
        		("in-lb","ft-lb","N-m","N-mm","kg-cm")
        """
        error = self.cdll.SetTorqueUnits(self._calibration,
                                         NewUnits.encode())
        if error:
            if error == 1:
                raise RuntimeError("Invalid Calibration struct.")
            elif error == 2:
                raise RuntimeError("Invalid torque units.")
            else:
                raise RuntimeError("Unknown error.")


    def setTempComp(self, TCEnabled):
        """Enables or disables temperature compensation, if available
         Parameters:
           TCEnabled: c_char_p
                      0 = temperature compensation off
                      1 = temperature compensation on
        """

        error = self.cdll.SetTempComp(self._calibration,
                                      TCEnabled.encode())
        if error:
            if error == 1:
                raise RuntimeError("Invalid Calibration struct.")
            elif error == 2:
                raise RuntimeError("Not available on this transducer system")
            else:
                raise RuntimeError("Unknown error.")

    def bias(self, voltages):
        """Stores a voltage reading to be subtracted from subsequent readings,
         effectively "zeroing" the transducer output to remove tooling weight, etc.
         Parameters:
           voltages: array of float
                array of voltages acquired by DAQ system
        """

        return self.cdll.Bias(self._calibration, VOLTAGE_SAMPLE_TYPE(*voltages))

    def convertToFT(self, voltages, reverse_parameters=[]):
        """Converts an array of voltages into forces and torques and
         returns them in result
         Parameters:
           voltages: array of float
                array of voltages acquired by DAQ system
            reverse_parameters: array of integer
                list of ids of parameter that should be reversed due to problems calibration with
                    the calibration
         Returns:
            array of force-torque values (typ. 6 elements)
        """
        ft_array = FT_SAMPLE_TYPE()
        self.cdll.ConvertToFT(self._calibration, VOLTAGE_SAMPLE_TYPE(*voltages),
                              byref(ft_array))
        rtn = list(map(lambda x: x, ft_array))  # convert ctype array to python
        # array
        for x in reverse_parameters:
            rtn[x] = -1*rtn[x]
        return rtn

    def printCalInfo(self):
        """print Calibration info on the console
        """

        return self.cdll.printCalInfo(self._calibration)

def print_calibration_info(calibration_file):
    """convinient function to print calibration file infos"""
    atidaq = ATI_CDLL()
    index = c_short(1)
    calibration = atidaq.createCalibration(calibration_file, index)
    atidaq.printCalInfo(calibration)
    atidaq.destroyCalibration(calibration)


if __name__ == "__main__":
    # test module

    # FT_sensor1.cal
    # Bias reading:
    #   0.265100 -0.017700 -0.038400 -0.042700 -0.189100  0.137300 -3.242300
    #   Measurement:
    #   -3.286300  0.387500 -3.487700  0.404300 -3.934100  0.547400 -3.210600
    #   Result:
    #   -0.065867  0.123803 111.156731  0.039974  0.040417  0.079049

    #filename = raw_input("Calibration file: ")
    filename = find_calibration_file("C:\\Users\\Force\\Desktop\\calibration",
                                     "FT30436")
    atidaq = ATI_CDLL()
    # get calibration
    index = c_short(1)
    atidaq.createCalibration(filename, index)
    atidaq.setForceUnits("N")
    atidaq.setTorqueUnits("N-m")

    atidaq.bias([0.2651, -0.0177, -0.0384, -0.0427, -0.1891, 0.1373, -3.2423])
    atidaq.printCalInfo()
    print("\nConverting")
    print(atidaq.convertToFT([-3.2863, 0.3875, -3.4877, 0.4043, -3.9341, 0.5474, -3.2106]))
