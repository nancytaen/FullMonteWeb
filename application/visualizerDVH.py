import mpld3
import numpy as np
import sys, os, paramiko
import io
from multiprocessing import Process, Queue
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

    SMALL_SIZE = 16
    MEDIUM_SIZE = 18
    LARGE_SIZE = 20

    legendList = []

    xVals = (np.array(range(noBins)) / noBins * 100)

    for key in data:
        yVals = np.array(data[key]) * 100
        plt.plot(xVals[1:-1],yVals[1:-1])
        legendList.append(str(key))

    plt.title("Cumulative Dose-Volume Histogram")
    plt.ylabel("Relative Volume (% of region volume)")
    plt.xlabel("Relative Dose (% of max fluence)")
    plt.legend(legendList, loc='upper right', title='Region ID')

    plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
    plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
    plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
    plt.rc('figure', titlesize=LARGE_SIZE)  # fontsize of the figure title

    fig = plt.gcf()

    return mpld3.fig_to_html(fig)


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


def dose_volume_histogram(outputMeshFileName, dns, tcpPort, text_obj, dvhFig):

    remoteFilePath = "/home/ubuntu/docker_sims/" + outputMeshFileName
    localFilePath = os.path.dirname(__file__) + "/visualization/Meshes/" + outputMeshFileName

    print("remote file path: "+remoteFilePath)
    print("local file path: "+localFilePath)

    # tempororily get mesh from remote server to local
    private_key_file = io.StringIO(text_obj)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    print ('connecting to remote server in visualizerDVH')
    client.connect(dns, username='ubuntu', pkey=privkey)
    print ('connected to remote server in visualizerDVH')
    sftp = client.open_sftp()
    sftp.get(remoteFilePath, localFilePath)
    sftp.close()
    client.close()

    output = import_data(localFilePath)

    # delete temporory mesh
    os.remove(localFilePath)

    ## regionBoundaries = [100, 140, 55, 75, 80, 110] ## Good region for FullMonte_fluence_line mesh
    ## output = extract_mesh_subregion(output, regionBoundaries)

    # Arrays are of type numpy.ndarray
    numpyWrapper = npi.WrapDataObject( output )

    try:
        fluenceData = numpyWrapper.CellData["Fluence"] # Assuming you know the name of the array
        regionData = numpyWrapper.CellData["Region"]

        if (fluenceData.size != regionData.size):
            print("Fluence and region data do not match")
            return(-1)

    except AttributeError:
        print("Could not parse region or fluence data by name. Attempting to parse by index")

        try:
            regionData = numpyWrapper.CellData[0]
            fluenceData = numpyWrapper.CellData[1] # Assuming you know the number of the array

            if (fluenceData.size != regionData.size):
                print("Fluence and region data do not match")
                return(-1)

        except IndexError:
            print("Could not parse region or fluence data. Input mesh may not be a correctly formatted FullMonte output file.")
            return(-1)

        except:
            print("Unidentified error occurred. Could not parse input data")
            return(-2)


    noBins = 500
    noCells = fluenceData.size

    volumeData = calculate_volumes(output,regionData,noCells)
    doseData = populate_dictionary(fluenceData,regionData)
    DVHdata = calculate_DVH(doseData,volumeData,noBins)
    cumulativeDVH = calculate_cumulative_DVH(DVHdata, noBins)
    # pass dvh to Queue
    dvhFig.put(plot_DVH(cumulativeDVH,noBins))

