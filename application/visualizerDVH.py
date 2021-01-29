import mpld3
from mpld3 import plugins
import numpy as np
import sys, os, paramiko
import io
import pandas as pd
from .models import *
from multiprocessing import Process
from vtk import vtkUnstructuredGridReader, vtkUnstructuredGrid, vtkMeshQuality, vtkExtractUnstructuredGrid
from vtk.numpy_interface import dataset_adapter as npi
from math import floor
from matplotlib import pyplot as plt
from django.db import models, connections
from django.db.utils import DEFAULT_DB_ALIAS, load_backend

# Define CSS for custom labels
css = """
table, td
{
  border: 1px solid black;
  text-align: right;
  background-color: #cccccc;
}
"""

# Max Fluence
maxFluence = 0
regionVolume = {}

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
def calculate_volumes(fullMonteOutputData, regionData):

    volumeData = {}
    regionVolume.clear()
    numCells = regionData.size

    # get array of volumes for each region
    for n in range(numCells):
        region = regionData[n]
        if (region == 0): continue # region 0 is air, ignore this

        else:
            if region not in volumeData:
                volumeData[region] = []

            curCell = fullMonteOutputData.GetCell(n)
            volume = vtkMeshQuality.TetVolume(curCell)
            volumeData[region].append(volume)

    # compute and save total volume in each region
    for region, volumes in volumeData.items():
        regionVolume[region] = sum(volumes)

    return volumeData

# map each region to its doses (fluence)
def populate_dictionary(fluenceData, regionData):

    doseData = {}
    maxFluence = 0

    # get array of doses for each region, also save the maximum fluence across all regions
    for region, dose in zip(regionData, fluenceData):
        if (region == 0): continue # region 0 is air, ignore this

        else:
            if region not in doseData:
                doseData[region] = []

            doseData[region].append(dose)
            if(dose > maxFluence):
                maxFluence = dose

    return doseData

# compute relative dose to relative volume mapping
# with doseData and volumeData, each region can be associated with its volume
# and dose arrays. Now for each region, loop through all its data points, get
# its relative dose, which will be represented by the x-axis, get its volume,
# and add its volume to the volume that is associated with the relative dose.
# Finally, compute the relative volume (fraction of volume against total volume).
def calculate_DVH(doseData, volumeData, noBins):

    doseVolumeData = {}

    # map region volume to its corresponding dose bin for all regions
    for region, doses in doseData.items():
        doseVolumeData[region] = [0] * noBins
        # for each point n on the region, cumulate volume to the total volume at dose_n
        for n in range(len(doses)):
            # 500 (noBins) bins, so the dose bin ID on the x-axis is dose/max_dose * noBins
            bin_id = floor(doses[n] / maxFluence * (noBins-1))
            doseVolumeData[region][bin_id] += volumeData[region][n]

    return doseVolumeData

# For each region, compute the total volume of region that is greater than or qual to each bin
def calculate_cumulative_DVH(doseVolumeData, noBins):

    cumulativeDVH = {}

    # for each dose interval
    for region, doseVolume in doseVolumeData.items():

        if region not in cumulativeDVH:
            cumulativeDVH[region] = [0] * noBins

        cumulativeTotal = 0

        for n in range(noBins-1, -1, -1):
            cumulativeTotal += doseVolume[n]
            cumulativeDVH[region][n] = cumulativeTotal

    return cumulativeDVH

# The cumulative DVH is plotted with bin doses (% maximum dose) along the horizontal
# axis. The column height of each bin represents the %volume of structure receiving a
# dose greater than or equal to that dose.
# plot using matplotlib and convert to html string
def plot_DVH(data, noBins, materials):
    FIG_WIDTH = 11
    FIG_HEIGHT = 6
    LINE_WIDTH = 4

    # Plot graph
    fig = plt.figure(linewidth=10, edgecolor="#04253a", frameon=True)
    fig.suptitle('Figure 1', fontsize=50)
    ax = fig.add_subplot(111)
    ax.set_xlabel("Relative Dose (% of max fluence)",fontsize = 20) #xlabel
    ax.set_ylabel("Relative Volume (% of region volume)", fontsize = 20)#ylabel
    ax.grid(True)

    legendList = [] # legend items (region ID and material) for the interactive legend
    lines = []      # matplotlib object; a line for each region for the interactive legend
    labelsList = [] # x,y labels for the interactive tooltip

    xVals = (np.array(range(noBins)) / noBins * 100)

    for key in data:
        yVals = np.array(data[key]) * 100
        line = ax.plot(xVals[1:-1], yVals[1:-1], lw=LINE_WIDTH, ls='-', marker='o', ms=8, alpha=0.7)
        lines.append(line)
        if(len(materials) > 0):
            legendList.append(str(key) + " (" + materials[key] + ")")
        else:
            legendList.append(str(key) + " (No material info)")
        labels = []
        for i in range(1, len(xVals)):
            label = "<table><td>Dose: "+"{:.2f}".format(xVals[i])+"%, Volume: "+"{:.2f}".format(yVals[i])+"%</td></table>"
            labels.append(label)
        labelsList.append(labels)

    # Interactive legend
    interactive_legend = plugins.InteractiveLegendPlugin(lines,
                                                     legendList,
                                                     alpha_unsel=0,
                                                     alpha_over=2, 
                                                     start_visible=True)
    plugins.connect(fig, interactive_legend)

    # Interactive tooltip
    for line, labels in zip(lines, labelsList):
        tooltip = plugins.PointHTMLTooltip(line[0], labels=labels,
                                    voffset=10, hoffset=10, css=css)
        plugins.connect(fig, tooltip)

    # Adjust chart margins
    fig.set_size_inches(FIG_WIDTH, FIG_HEIGHT)
    plt.subplots_adjust(left=0.07, bottom=0.1, right=0.77, top=0.99) # avoid legend going off screen

    return mpld3.fig_to_html(fig)


# https://stackoverflow.com/questions/56733112/how-to-create-new-database-connection-in-django
def create_connection(alias=DEFAULT_DB_ALIAS):
    connections.ensure_defaults(alias)
    connections.prepare_test_settings(alias)
    db = connections.databases[alias]
    backend = load_backend(db['ENGINE'])
    return backend.DatabaseWrapper(db, alias)

# regionBoundaries is a 6-entry vector of floating point values
# This defines the boundaries of the subregion in the order xmin, xmax, ymin, ymax, zmin, zmax
# def extract_mesh_subregion(mesh,regionBoundaries):
#     subregionAlgorithm = vtkExtractUnstructuredGrid()
#     subregionAlgorithm.SetInputData(mesh)
#     subregionAlgorithm.SetExtent(regionBoundaries)
#     subregionAlgorithm.Update()
#     return subregionAlgorithm.GetOutput()
def dose_volume_histogram(user, dns, tcpPort, text_obj, materials):
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


    noBins = 500    # max fluence is divided into

    volumeData = calculate_volumes(output,regionData)
    doseData = populate_dictionary(fluenceData,regionData)
    DVHdata = calculate_DVH(doseData,volumeData,noBins)
    cumulativeDVH = calculate_cumulative_DVH(DVHdata, noBins)
    # save the figure's html string to session
    conn = create_connection()
    conn.ensure_connection()
    info.dvhFig = plot_DVH(cumulativeDVH,noBins,materials)
    info.maxFluence = maxFluence
    info.save()
    running_process = processRunning.objects.filter(user = user).latest('id')
    running_process.running = False
    running_process.save()
    conn.close()
    print("done generating DVH")

