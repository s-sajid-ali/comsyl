# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2017 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/
__authors__ = ["M Glass - ESRF ISDD Advanced Analysis and Modelling"]
__license__ = "MIT"
__date__ = "20/04/2017"



from comsyl.autocorrelation.SigmaMatrix import SigmaMatrix
from comsyl.autocorrelation.AutocorrelationInfo import AutocorrelationInfo
from comsyl.autocorrelation.DegreeOfCoherence import DegreeOfCoherence
from comsyl.autocorrelation.WignerFunction import Wignerfunction
from comsyl.math.Twoform import Twoform

__author__ = 'mglass'
import numpy as np
from comsyl.waveoptics.Wavefront import NumpyWavefront, SRWWavefront
from comsyl.autocorrelation.AutocorrelationFunctionIO import AutocorrelationFunctionIO
from comsyl.autocorrelation.PhaseSpaceDensity import PhaseSpaceDensity

from comsyl.comparisons.GSMComparer import GSMComparer
from comsyl.comparisons.SeparationComparer import SeparationComparer


try:
    from comsyl.math.utils import plotSurface, plot
except:
    pass

from BeamlineComponents.Source.Undulator import Undulator


class AutocorrelationFunction(object):
    def __init__(self, sigma_matrix, undulator, detuning_parameter, energy, electron_beam_energy, wavefront, exit_slit_wavefront,
                 srw_wavefront_rx, srw_wavefront_drx, srw_wavefront_ry, srw_wavefront_dry,
                 sampling_factor, minimal_size, beam_energies, weighted_fields, static_electron_density,  twoform, info):
        self._sigma_matrix = sigma_matrix
        self._undulator = undulator
        self._detuning_parameter = detuning_parameter
        self._energy = energy
        self._electron_beam_energy = electron_beam_energy
        self._wavefront = wavefront
        self._exit_slit_wavefront = exit_slit_wavefront
        self._srw_wavefront_rx = srw_wavefront_rx
        self._srw_wavefront_drx = srw_wavefront_drx
        self._srw_wavefront_ry = srw_wavefront_ry
        self._srw_wavefront_dry = srw_wavefront_dry
        self._sampling_factor = sampling_factor
        self._minimal_size = minimal_size
        self._beam_energies = beam_energies
        self._weighted_fields = weighted_fields
        self._static_electron_density = static_electron_density

        self.setInfo(info)
        self._setTwoform(twoform)

        self._io = AutocorrelationFunctionIO()

    def _setTwoform(self, twoform):
        self._twoform = twoform
        self._degree_of_coherence = DegreeOfCoherence(self._twoform)
        self._wigner_function = Wignerfunction(self._twoform, self._wavefront.wavenumbers()[0])

    def referenceWavefront(self):
        return self._wavefront

    def SRWWavefrontRx(self):
        return self._srw_wavefront_rx

    def SRWWavefrontRy(self):
        return self._srw_wavefront_ry

    def SRWWavefrontDRx(self):
        return self._srw_wavefront_drx

    def SRWWavefrontDRy(self):
        return self._srw_wavefront_dry

    def intensity(self):
        return self._twoform.intensity()

    def intensityFromModes(self):
        return self._twoform.intensityFromVectors()

    def xCoordinates(self):
        return self._twoform.xCoordinates()

    def yCoordinates(self):
        return self._twoform.yCoordinates()

    def gridSpacing(self):
        return self.Twoform().gridSpacing()

    def phaseOscillationPoints(self):
        return self.phaseSpaceDensity().expPhasePointsPerOscillation(self.gridSpacing() * (self.xCoordinates().size, self.yCoordinates().size)) * self.gridSpacing()

    def trace(self):
        return np.trapz(np.trapz(self.intensity(), self.yCoordinates()), self.xCoordinates())

    def wavefront(self):
        return self._wavefront

    def sigmaMatrix(self):
        return self._sigma_matrix

    def showIntensity(self):
        plotSurface(self.xCoordinates(), self.yCoordinates(), np.abs(self.intensity()[:, :]), "Intensity")
        plotSurface(self.xCoordinates(), self.yCoordinates(), np.abs(self.intensity()[:, :]), False)

    def showIntensityFromModes(self):
        intensity = self.intensityFromModes().real
        plotSurface(self.xCoordinates(), self.yCoordinates(), intensity, "Intensity")
        plotSurface(self.xCoordinates(), self.yCoordinates(), intensity, False)


    def saveIntensity(self, filename="intensity"):
        np.savez(filename,
                 x_coordinates=self.xCoordinates(),
                 y_coordinates=self.yCoordinates(),
                 intensity=np.abs(self.intensity()[:, :]))

    def showMode(self, i_mode):
        wfr = self.coherentModeAsWavefront(i_mode)
        wfr.showEField()

    def showModes(self, max_i_n=3):
        for i in range(max_i_n):
            self.showMode(i)

    def showStaticElectronDensity(self):
        plotSurface(self._wavefront.absolute_x_coordinates(),
                    self._wavefront.absolute_y_coordinates(), self._static_electron_density)
        plotSurface(self._wavefront.absolute_x_coordinates(),
                    self._wavefront.absolute_y_coordinates(), self._static_electron_density, contour_plot=False)

    def showModeDistribution(self):
        y = (self.modeDistribution()).real
        x = np.arange(y.shape[0])
        plot(x, y)

    def printModePeaks(self):
        for i_mode in range(self.numberModes()):
            mode = np.abs(self.coherentMode(i_mode))
            i, j = np.unravel_index(mode.argmax(), mode.shape)
            print("%i %e %e" % (i_mode, self.xCoordinates()[i], self.yCoordinates()[j]))

    def spatialElectronBeamDensity(self):
        return {"x" : self._wavefront.absolute_x_coordinates(),
                "y" : self._wavefront.absolute_y_coordinates(),
                "z" : self._static_electron_density}

    def angularElectronBeamDensity(self):
        #TODO: implement
        raise NotImplementedError
        return {"x" : self._wavefront.absolute_x_coordinates(),
                "y" : self._wavefront.absolute_y_coordinates(),
                "z" : None}


    def numberModes(self, total_fraction=None):

        if total_fraction is not None:
            fraction = 0.0
            for i, occupation in enumerate(self.modeDistribution()):
                fraction += occupation
                if fraction >= total_fraction:
                    break

            return i+1
        else:
            return self.Twoform().numberVectors()

    def coherentMode(self, i_mode):
        return self._twoform.vector(i_mode)

    def eigenvalue(self, i_mode):
        return self._twoform.eigenvalues()[i_mode]

    def modeDistribution(self):
        mode_distribution = self._twoform.eigenvalues()/self.trace()
        return mode_distribution

    def energy(self):
        return self._energy

    def electronBeamEnergy(self):
        return self._electron_beam_energy

    def setInfo(self, info):
        self._info = info

    def info(self):
        return self._info

    def coherentModeAsWavefront(self, i_mode):
        mode = self.coherentMode(i_mode)
        e_field = np.zeros((1, mode.shape[0], mode.shape[1], 2), dtype=mode.dtype)
        e_field[0, :, :, 0] = mode[:, :]

        e_field[abs(e_field) < 0.00001] = 0.0

        wavefront = NumpyWavefront(e_field,
                                   self.xCoordinates().min(),
                                   self.xCoordinates().max(),
                                   self.yCoordinates().min(),
                                   self.yCoordinates().max(),
                                   self._wavefront.z(),
                                   self._wavefront.energies(),
                                   )
        return wavefront

    def Twoform(self):
        return self._twoform

    def diagonalizeModes(self, number_modes):
        from comsyl.parallel.TwoformPETSc import TwoformPETSc
        twoform_petsc = TwoformPETSc(self.Twoform())
        self._setTwoform(twoform_petsc.diagonalize(number_modes))

    def wignerFunction(self):
        return self._wigner_function

    def degreeOfCoherence(self):
        return self._degree_of_coherence

    def evaluate(self, r_1, r_2):
        return self._twoform.evaluate(r_1, r_2)

    def evaluateAllForFixedR1(self, r_1):
        return self._twoform.evaluateAllForFixedR1(self.xCoordinates(), self.yCoordinates(), r_1)

    def plotDegreeOfCoherenceOneHoleFixed(self, x=0.0, y=0.0):
        x_coordinates = np.array(self._wavefront.absolute_x_coordinates())
        y_coordinates = np.array(self._wavefront.absolute_x_coordinates())
        values = self.degreeOfCoherence().planeForFixedR1(x_coordinates,
                                                          y_coordinates,
                                                          np.array([x, y]))
        plotSurface(x_coordinates, y_coordinates, values)
        plotSurface(x_coordinates, y_coordinates, values, False)

    def symmetricDisplacementDegreeOfCoherence(self):
        x_coordinates = self.xCoordinates()
        y_coordinates = self.yCoordinates()

        values = self.degreeOfCoherence().symmetricDisplacement(x_coordinates,
                                                                y_coordinates)
        return values

    def phaseSpaceDensity(self):
        return PhaseSpaceDensity(sigma_matrix=self._sigma_matrix, k=self._wavefront.wavenumbers()[0])

    def GSMComparer(self):
        return GSMComparer(self)

    def SeparationComparer(self, number_horizontal_modes=None):
        return SeparationComparer(self, number_horizontal_modes)

    def onCoordinates(self, new_x_coordinates, new_y_coordinates):
        new_two_form = self.Twoform().onNewCoordinates(new_x_coordinates, new_y_coordinates)
        self._setTwoform(new_two_form)

    def correctEnergySpreadNormalization(self):
        if float(self.info().version()) < 1.3:
            # correct for version below 1.3.
            # because integral is approximatievly sum over value times length of interval
            correction = np.diff(self._beam_energies)[0][0]
        else:
            correction = 1.0

        return correction

    def verify(self, compare_to):
        print("CM", np.abs(self._twoform.eigenvectors()-compare_to._twoform.eigenvectors()).max())
        print("EIG", np.abs(self._twoform.eigenvalues()-compare_to._twoform.eigenvalues()).max())
        print("SIG", np.abs(self._sigma_matrix._sigma_matrix-compare_to._sigma_matrix._sigma_matrix).max())
        print("INTENSITY", np.abs(self.intensity()-compare_to.intensity()).max())
        print("DETUNING", np.abs(self._detuning_parameter-compare_to._detuning_parameter).max())
        print("ENERGY",np.abs(self.energy()-compare_to.energy()).max())
        print("X_COORD", np.abs(self.xCoordinates()-compare_to.xCoordinates()).max())
        print("Y_COORD", np.abs(self.yCoordinates()-compare_to.yCoordinates()).max())
        print("STATIC ELECTRON DENS", np.abs(self._static_electron_density-compare_to._static_electron_density).max())
        print("EFIELD", np.abs(self._wavefront.E_field_as_numpy()-compare_to._wavefront.E_field_as_numpy()).max())
        print("EFIELD_COORD", np.abs(self._wavefront.asNumpyArray()[1]-compare_to._wavefront.asNumpyArray()[1]).max())
        print("UNDULATOR", np.abs(self._undulator.asNumpyArray()-compare_to._undulator.asNumpyArray()).max())

    def asDictionary(self):
        twoform_as_numpy = self.Twoform().asNumpyArray()
        data_dict={"sigma_matrix": self._sigma_matrix.asNumpyArray(),
                   "undulator": self._undulator.asNumpyArray(),
                   "detuning_parameter": np.array([self._detuning_parameter]),
                   "energy": np.array([self.energy()]),
                   "electron_beam_energy": np.array([self.electronBeamEnergy()]),
                   "wavefront_0": self._wavefront.asNumpyArray()[0],
                   "wavefront_1": self._wavefront.asNumpyArray()[1],
                   "wavefront_2": self._wavefront.asNumpyArray()[2],
                   "exit_slit_wavefront_0": self._exit_slit_wavefront.asNumpyArray()[0],
                   "exit_slit_wavefront_1": self._exit_slit_wavefront.asNumpyArray()[1],
                   "exit_slit_wavefront_2": self._exit_slit_wavefront.asNumpyArray()[2],
                   "srw_wavefront_rx": np.array([self.SRWWavefrontRx()]),
                   "srw_wavefront_drx": np.array([self.SRWWavefrontDRx()]),
                   "srw_wavefront_ry": np.array([self.SRWWavefrontRy()]),
                   "srw_wavefront_dry": np.array([self.SRWWavefrontDRy()]),
                   "sampling_factor": np.array([self._sampling_factor]),
                   "minimal_size" : np.array([self._minimal_size]),
                   "beam_energies": np.array([self._beam_energies]),
                   "weighted_fields": self._weighted_fields,
                   "static_electron_density": self._static_electron_density,
                   "twoform_0": twoform_as_numpy[0],
                   "twoform_1": twoform_as_numpy[1],
                   "twoform_2": twoform_as_numpy[2],
                   "twoform_3": twoform_as_numpy[3],
                   "twoform_4": twoform_as_numpy[4],
                   "twoform_5": twoform_as_numpy[5],
                   "info": self.info().toString(),
                   }

        return data_dict

    @staticmethod
    def fromDictionary(data_dict):
        sigma_matrix = SigmaMatrix.fromNumpyArray(data_dict["sigma_matrix"])
        undulator = Undulator.fromNumpyArray(data_dict["undulator"])
        detuning_parameter = data_dict["detuning_parameter"][0]
        energy = data_dict["energy"][0]

        electron_beam_energy = data_dict["electron_beam_energy"][0]


        np_wavefront_0=data_dict["wavefront_0"]
        np_wavefront_1=data_dict["wavefront_1"]
        np_wavefront_2=data_dict["wavefront_2"]
        wavefront = NumpyWavefront.fromNumpyArray(np_wavefront_0, np_wavefront_1, np_wavefront_2)

        try:
            np_exit_slit_wavefront_0=data_dict["exit_slit_wavefront_0"]
            np_exit_slit_wavefront_1=data_dict["exit_slit_wavefront_1"]
            np_exit_slit_wavefront_2=data_dict["exit_slit_wavefront_2"]
            exit_slit_wavefront = NumpyWavefront.fromNumpyArray(np_exit_slit_wavefront_0, np_exit_slit_wavefront_1, np_exit_slit_wavefront_2)
        except:
            exit_slit_wavefront = wavefront.clone()

        try:
            weighted_fields = data_dict["weighted_fields"]
        except:
            weighted_fields = None



        srw_wavefront_rx=data_dict["srw_wavefront_rx"][0]
        srw_wavefront_ry=data_dict["srw_wavefront_ry"][0]

        srw_wavefront_drx = data_dict["srw_wavefront_drx"][0]
        srw_wavefront_dry = data_dict["srw_wavefront_dry"][0]

        info_string = str(data_dict["info"])
        info = AutocorrelationInfo.fromString(info_string)


        sampling_factor=data_dict["sampling_factor"][0]
        minimal_size=data_dict["minimal_size"][0]

        beam_energies = data_dict["beam_energies"]

        static_electron_density = data_dict["static_electron_density"]
        coordinates_x = data_dict["twoform_0"]
        coordinates_y = data_dict["twoform_1"]
        diagonal_elements = data_dict["twoform_2"]
        eigenvalues = data_dict["twoform_3"]
        twoform_vectors = data_dict["twoform_4"]

        twoform = Twoform(coordinates_x, coordinates_y, diagonal_elements, eigenvalues, twoform_vectors)

        eigenvector_errors = data_dict["twoform_5"]
        twoform.setEigenvectorErrors(eigenvector_errors)

        af = AutocorrelationFunction(sigma_matrix, undulator, detuning_parameter,energy,electron_beam_energy,
                                     wavefront,exit_slit_wavefront,srw_wavefront_rx, srw_wavefront_drx, srw_wavefront_ry, srw_wavefront_dry,
                                     sampling_factor,minimal_size, beam_energies, weighted_fields,
                                     static_electron_density, twoform,
                                     info)

        return af

    def updateFile(self):
        self._io.updateFile(self)

    def save(self, filename):
        self._io.save(filename, self)

    @staticmethod
    def load(filename):
        data_dict = AutocorrelationFunctionIO.load(filename)

        af = AutocorrelationFunction.fromDictionary(data_dict)
        af._io._setWasFileLoaded(filename)

        return af