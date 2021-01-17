import mpld3
import numpy as np
import sys, os, paramiko
import io
from .models import *
from multiprocessing import Process
from vtk import vtkUnstructuredGridReader, vtkUnstructuredGrid, vtkMeshQuality, vtkExtractUnstructuredGrid
from vtk.numpy_interface import dataset_adapter as npi
from math import floor
from matplotlib import pyplot as plt
from django.db import models, connections
from django.db.utils import DEFAULT_DB_ALIAS, load_backend

# read vtk file
def import_data(filePath):

    reader = vtkUnstructuredGridReader()
    reader.SetFileName(filePath)
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.Update()
    output = reader.GetOutput()

    return output

# map each region to its volumes
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

# map each region to its doses (fluence)
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

# compute relative dose to relative volume mapping
# with doseData and volumeData, each region can be associated with its volume
# and dose arrays. Now for each region, loop through all its data points, get
# its relative dose, which will be represented by the x-axis, get its volume,
# and add its volume to the volume that is associated with the relative dose.
# Finally, compute the relative volume (fraction of volume against total volume).
def calculate_DVH(doseData, volumeData, noBins):

    maxFluence = 0

    for key in doseData:
        regionMax = max(doseData[key])
        if regionMax > maxFluence:
            maxFluence = regionMax

    # print("Max fluence: " + str(maxFluence))
    binSize = maxFluence / noBins
    doseVolumeData = {}

    # for each region
    for key in doseData:
        totalVolume = 0
        doseVolumeData[key] = [0] * noBins
        # for each point n on the region, cumulate volume_n to the volume at dose_n
        for n in range(len(doseData[key])):
            # 500 (noBins) data points, so the dose on the x-axis is dose_n/max_dose * nBins
            idx = floor(doseData[key][n] / maxFluence * (noBins-1))
            doseVolumeData[key][idx] += volumeData[key][n]
            totalVolume += volumeData[key][n]

        # compute relative
        for n in range (len(doseVolumeData[key])):
            doseVolumeData[key][n] /= totalVolume

    # for key in doseVolumeData:
    #     print("Values for region " + str(key))
    #
    #     for val in doseVolumeData[key]:
    #         print(val)

    return doseVolumeData

# compute relative dose to cumulative relative volume mapping
def calculate_cumulative_DVH(doseVolumeData, noBins):

    cumulativeDVH = {}

    # for each dose interval
    for key in doseVolumeData:

        if key not in cumulativeDVH:
            cumulativeDVH[key] = [0] * noBins;

        cumulativeTotal = 0;

        for n in range(noBins-1, -1, -1):
            cumulativeTotal += doseVolumeData[key][n]
            cumulativeDVH[key][n] = cumulativeTotal

    return cumulativeDVH

# plot using matplotlib and convert to html string
def plot_DVH(data, noBins):
    FIG_WIDTH = 10
    FIG_HEIGHT = 7
    LINE_WIDTH = 3

    fig = plt.figure(linewidth=10, edgecolor="#04253a", frameon=True)
    fig.suptitle('Figure 1', fontsize=50)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(top=0.80)
    ax.set_title('Cumulative Dose-Volume Histogram',fontsize= 30) # title of plot
    ax.set_xlabel("Relative Dose (% of max fluence)",fontsize = 20) #xlabel
    ax.set_ylabel("Relative Volume (% of region volume)", fontsize = 20)#ylabel
    ax.grid(True)

    legendList = []

    xVals = (np.array(range(noBins)) / noBins * 100)

    for key in data:
        yVals = np.array(data[key]) * 100
        ax.plot(xVals[1:-1],yVals[1:-1],'-o',linewidth=LINE_WIDTH)
        legendList.append(str(key))

    ax.legend(legendList, loc='upper right', title='Region ID')
    fig.set_size_inches(FIG_WIDTH, FIG_HEIGHT)

    return mpld3.fig_to_html(fig)


# regionBoundaries is a 6-entry vector of floating point values
# This defines the boundaries of the subregion in the order xmin, xmax, ymin, ymax, zmin, zmax
# def extract_mesh_subregion(mesh,regionBoundaries):
#     subregionAlgorithm = vtkExtractUnstructuredGrid()
#     subregionAlgorithm.SetInputData(mesh)
#     subregionAlgorithm.SetExtent(regionBoundaries)
#     subregionAlgorithm.Update()
#     return subregionAlgorithm.GetOutput()

# https://stackoverflow.com/questions/56733112/how-to-create-new-database-connection-in-django
def create_connection(alias=DEFAULT_DB_ALIAS):
    connections.ensure_defaults(alias)
    connections.prepare_test_settings(alias)
    db = connections.databases[alias]
    backend = load_backend(db['ENGINE'])
    return backend.DatabaseWrapper(db, alias)


def dose_volume_histogram(user, dns, tcpPort, text_obj):
    info = meshFileInfo.objects.filter(user = user).latest('id')
    outputMeshFileName = info.fileName
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
        print()

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
    # save the figure's html string to session
    conn = create_connection()
    conn.ensure_connection()
    info.dvhFig = plot_DVH(cumulativeDVH,noBins)
    info.save()
    running_process = processRunning.objects.filter(user = user).latest('id')
    running_process.running = False
    running_process.save()
    conn.close()
    print("done generating DVH")

