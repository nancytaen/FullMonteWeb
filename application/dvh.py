import mpld3
import numpy as np
import sys
import os
from vtk import vtkUnstructuredGridReader, vtkUnstructuredGrid, vtkMeshQuality, vtkExtractUnstructuredGrid
from vtk.numpy_interface import dataset_adapter as npi
from math import floor
from matplotlib import pyplot as plt

def import_data(filePath):

    reader = vtkUnstructuredGridReader()
    reader.SetFileName(filePath)
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.Update()
    output = reader.GetOutput()

    return output


def populate_dictionary(fluenceData, regionData):

    maxFluence = fluenceData.max()
    loopEnd = fluenceData.size
    doseVolumeData = {}

    for n in range(loopEnd):
        val = fluenceData[n]
        key = regionData[n]
        if (key == 0): continue

        else:
            if key not in doseVolumeData:
                doseVolumeData[key] = []

            doseVolumeData[key].append(val)

    # for key in doseVolumeData:
    #     print(key)

    return doseVolumeData


def calculate_DVH(doseData, volumeData, noBins):

    maxFluence = 0

    for key in doseData:
        regionMax = max(doseData[key])
        if regionMax > maxFluence:
            maxFluence = regionMax

    # print("Max fluence: " + str(maxFluence))
    binSize = maxFluence / noBins
    doseVolumeData = {}

    for key in doseData:

        totalVolume = 0
        doseVolumeData[key] = [0] * noBins

        for n in range(len(doseData[key])):
            totalVolume += volumeData[key][n]
            idx = floor(doseData[key][n] / maxFluence * (noBins-1))
            doseVolumeData[key][idx] += volumeData[key][n]

        for n in range (len(doseVolumeData[key])):
            doseVolumeData[key][n] /= totalVolume

    # for key in doseVolumeData:
    #     print("Values for region " + str(key))
    #
    #     for val in doseVolumeData[key]:
    #         print(val)

    return doseVolumeData


def calculate_volumes(fullMonteOutputData, regionData, noCells):

    volumeData = {}

    for n in range(noCells):
        key = regionData[n]
        if (key == 0): continue

        else:
            if key not in volumeData:
                volumeData[key] = []

            curCell = fullMonteOutputData.GetCell(n)
            volume = vtkMeshQuality.TetVolume(curCell)
            volumeData[key].append(volume)

    return volumeData


def plot_DVH(data, noBins):

    xVals = np.array(range(noBins))
    for key in data:
        plt.plot(xVals,np.array(data[key]))

    # plt.yticks(np.arange(0,1,step=0.2))
    # plt.yticks(np.arange(6), ('0%','20%','40%','60%','80%','100%'))
    plt.ylabel("Relative Volume")
    plt.xlabel("Relative Dose Bin # (Number of Bins: " + str(noBins) + ")")
    # plt.savefig("DVH.png")
    # plt.show()

    # plt.legend(['Region 1', 'Region 1', 'Region 1', 'Region 1','Region 1','Region 1','Region 1'], loc='upper left')
    # mpld3.show()
    fig = plt.gcf()
    filePath = os.path.dirname(__file__) + "\\visualization\\scripts\\dvh_fig.html"
    mpld3.save_html(fig,filePath)


def calculate_cumulative_DVH(doseVolumeData, noBins):

    cumulativeDVH = {}

    for key in doseVolumeData:

        if key not in cumulativeDVH:
            cumulativeDVH[key] = [0] * noBins;

        cumulativeTotal = 0;

        for n in range(noBins-1, -1, -1):
            cumulativeTotal += doseVolumeData[key][n]
            cumulativeDVH[key][n] = cumulativeTotal

    return cumulativeDVH


# regionBoundaries is a 6-entry vector of floating point values
# This defines the boundaries of the subregion in the order xmin, xmax, ymin, ymax, zmin, zmax
def extract_mesh_subregion(mesh,regionBoundaries):
    subregionAlgorithm = vtkExtractUnstructuredGrid()
    subregionAlgorithm.SetInputData(mesh)
    subregionAlgorithm.SetExtent(regionBoundaries)
    subregionAlgorithm.Update()
    return subregionAlgorithm.GetOutput()


def main():

    filePath = os.path.dirname(__file__) + "\\visualization\\Meshes\\FullMonte_fluence_line.vtk"

    output = import_data(filePath)

    regionBoundaries = [100, 140, 55, 75, 80, 110] ## Good region for FullMonte_fluence_line mesh
    output = extract_mesh_subregion(output, regionBoundaries)

    # Arrays are of type numpy.ndarray
    numpyWrapper = npi.WrapDataObject( output )

    #fluenceData = numpyWrapper.CellData["Fluence"] # Assuming you know the name of the array
    fluenceData = numpyWrapper.CellData[1] # Assuming you know the number of the array

    #regionData = numpyWrapper.CellData["Region"]
    regionData = numpyWrapper.CellData[0]

    if (fluenceData.size != regionData.size):
        print("Fluence and region data do not match")
        exit(-1)

    noBins = 500
    noCells = fluenceData.size

    volumeData = calculate_volumes(output,regionData,noCells)
    doseData = populate_dictionary(fluenceData,regionData)
    DVHdata = calculate_DVH(doseData,volumeData,noBins)
    cumulativeDVH = calculate_cumulative_DVH(DVHdata, noBins)
    plot_DVH(cumulativeDVH,noBins)


if __name__ == '__main__':
    main()
