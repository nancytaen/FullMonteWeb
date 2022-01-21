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
from .mpld3CustomPlugin import CustomizedInteractiveLegendPlugin
import sys
import re


# Define CSS for custom labels
css = """
table, td
{
  border: 1px solid black;
  text-align: right;
  background-color: #cccccc;
}
"""
# read vtk file
def import_data(filePath):

    reader = vtkUnstructuredGridReader()
    reader.SetFileName(filePath)
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.Update()
    output = reader.GetOutput()

    return output

# load pdt-space dvh file
def load_dvh_data(num_material, filePath):
    mf = open(filePath, 'r')
    dvh_data = []
    for line in mf.read().splitlines():
        if len(line) != 0:
            if line[0:3] != "dvh":
                continue
            else:
                data_line = line.split(");")
                dvh_data.extend(data_line)
    
    dvh_data.pop(0)
    # print(dvh_data) 
    # temp = dvh_data[0].split('=')[1].split(';')

    dic = {}
    for x in range(1, num_material+1):
        dic[x]=[]
    
    # print(dic)
    # print(len(dvh_data))
    index = 1
    for d in dvh_data:
        temp = d.split('=')[1].split(';')
        for it in temp:
            if it != '':
                it = re.sub(r'\[','', it)
                it = re.sub(r'\]','', it)
                
                dic[index].append(float(it))
                index += 1
        index = 1
    # print(dic)
    return dic
    
# map each region to its volumes
def calculate_volumes(fullMonteOutputData, regionData):

    volumeData = {}
    global regionVolume
    regionVolume = {}
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

# map each region to its fluence
def get_doses(fluenceData, regionData):

    doseData = {}

    # get array of % threshold fluence for each region, also save the maximum % threshold fluence across all regions
    for region, dose in zip(regionData, fluenceData):
        if (region == 0): continue # region 0 is air, ignore this

        else:
            if region not in doseData:
                doseData[region] = []

            doseData[region].append(dose)

    return doseData

# compute relative dose to relative volume mapping
# with doseData and volumeData, each region can be associated with its volume
# and dose arrays. Now for each region, loop through all its data points, get
# its relative dose, which will be represented by the x-axis, get its volume,
# and add its volume to the volume that is associated with the relative dose.
# Finally, or each region, compute the total volume of region that received
# fluence greater than or equal to each fluence value. Returns an 2D array
# [dose array, volume array, umulative volume array]
def calculate_cumulative_DVH(doseData, volumeData):

    doseVolumeData = {}
    doseVolumeDataTemp = {}

    # map region volume to its corresponding dose for all regions
    for region, doses in doseData.items():
        doseVolumeDataTemp[region] = {}
        # for each point n on the region, cumulate volume to the total volume at dose
        for n in range(len(doses)):
            if doses[n] not in doseVolumeDataTemp[region]:
                doseVolumeDataTemp[region][doses[n]] = volumeData[region][n]
            else:
                doseVolumeDataTemp[region][doses[n]] += volumeData[region][n]

    # sort doses in order and split dictionary into key and value arrays
    for region, doseVol in doseVolumeDataTemp.items():
        doseVolumeData[region] = [[], []]
        for dose in sorted (doseVol):
            doseVolumeData[region][0].append(dose)
            doseVolumeData[region][1].append(doseVol[dose]) # volume

        # compute cumulative DVH
        n = len(doseVol)
        for i in range(n-2, -1, -1):
            doseVolumeData[region][1][i] += doseVolumeData[region][1][i+1]
        
    return doseVolumeData

def calculate_cdvh_for_v100(doseVolumeData, noBins, thresholdFluenceArray, cutoff):

    cumulativeDVH = {}

    # Find 100% threshold fluence at xx% volume for speciied tumor region
    n = len(doseVolumeData[5][0])
    hundred_percent_theshold_fluence = 0
    factor = 1
    for i in range(n - 1): #can be improved by binary searh instead
        if doseVolumeData[5][1][i+1] / regionVolume[5] < 0.98:
            hundred_percent_theshold_fluence = doseVolumeData[5][0][i]
            break
    if hundred_percent_theshold_fluence > 0:
        factor = thresholdFluenceArray[5] / hundred_percent_theshold_fluence

    for region, doseVolume in doseVolumeData.items():
        cumulativeDVH[region] = [-1] * noBins
        # adjust fluence by factor, compute %threshold fluence, and group them into bins
        lastID = n-1
        for i in range(n):
            dose = doseVolume[0][i] * factor
            if dose > cutoff[region]:
                lastID = i
                break
            bin_id = floor(dose / cutoff[region] * (noBins-1))
            if cumulativeDVH[region][bin_id] == -1:
                cumulativeDVH[region][bin_id] = doseVolume[1][i]

        # fill in gaps
        if cumulativeDVH[region][noBins-1] == -1:
            cumulativeDVH[region][noBins-1] = doseVolume[1][lastID]
        for i in range(noBins-2, -1, -1):
            if cumulativeDVH[region][i] == -1:
                cumulativeDVH[region][i] = cumulativeDVH[region][i+1]

    return cumulativeDVH, factor

# The cumulative DVH is plotted with bin doses (% threshold fluence) along the horizontal
# axis. The column height of each bin represents the volume of structure receiving a
# dose greater than or equal to that dose.
# plot using matplotlib and convert to html string
def plot_DVH(data, noBins, materials, outputMeshFileName, meshUnit, cutoffPercentage = 500):
    global export_data # for exporting to excel
    export_data = {}

    FIG_WIDTH = 11
    FIG_HEIGHT = 6
    LINE_WIDTH = 4

    # Plot style
    plt.style.use("bmh")

    # Set up figure and plot
    fig = plt.figure(linewidth=10, edgecolor="#04253a", frameon=True)
    fig.suptitle("Cumulative Dose-Volume Histogram", fontsize=30, y = 1)
    ax = fig.add_subplot(111)
    ax.set_xlabel("% Fluence Threshold",fontsize = 20) # xlabel
    ax.set_ylabel("% region volume coverage", fontsize = 20)# ylabel
    ax.grid(True)

    legendList = [] # legend items (region ID and material) for the interactive legend
    lines = []      # array of matplotlib objects; a line for each region for the interactive legend
    labelsList = [] # x,y labels for the interactive tooltip

    xVals = np.array(range(noBins)) / noBins * cutoffPercentage # % threshold dose

    # Plot for each region
    # color=next(ax._get_lines.prop_cycler)['color']
    for region, cumulativeDoseVolume in data.items():
        yVals = np.array(cumulativeDoseVolume) / regionVolume[region] * 100 # % region volume
        line = ax.plot(xVals[1:-1], yVals[1:-1], lw=LINE_WIDTH, ls='-', marker='o', ms=8, alpha=0.7)
        lines.append(line)
        if(len(materials) == len(data) + 1): # mesh file from simulation can use material info from simulation
            legendList.append(str(region) + " (" + materials[region] + ")")
        else: # uploaded mesh files cannot be associated with material info
            legendList.append(str(region) + " (No material info)")
        labels = []
        for i in range(1, len(xVals)):
            label = "<table><td>Dose: "+"{:.2f}".format(xVals[i])+"%, Volume: "+"{:.2f}".format(yVals[i])+"%</td></table>"
            labels.append(label)
        labelsList.append(labels)
        # save data to be exported (save % threshold fluence dose and cumulative region volume in order)
        export_data[region] = np.zeros((5, noBins))
        export_data[region][3] = xVals
        export_data[region][4] = yVals

    # Interactive legend
    interactive_legend = CustomizedInteractiveLegendPlugin(lines,
                                                     legendList,
                                                     alpha_unsel=0,
                                                     alpha_over=1.5, 
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

    # Save temporory DVH figure locally in png format
    localFilePath = os.path.dirname(__file__) + "/temp/" + outputMeshFileName[:-8] + '.dvh.png'
    plt.savefig(localFilePath, orientation='portrait', format="png")

    return mpld3.fig_to_html(fig)

# Function to plot DVH of PDT-SPACE
# This is function is copied from the plot_DVH() above with small changes.
# This function can be refactored later.
def plot_PDVH(data, noBins, materials, outputMeshFileName):
    FIG_WIDTH = 11
    FIG_HEIGHT = 6
    LINE_WIDTH = 4

    # Plot style
    plt.style.use("bmh")

    # Set up figure and plot
    fig = plt.figure(linewidth=10, edgecolor="#04253a", frameon=True)
    fig.suptitle("Cumulative Dose-Volume Histogram", fontsize=30, y = 1)
    ax = fig.add_subplot(111)
    ax.set_xlabel("Percentage of dose threshold",fontsize = 20) # xlabel
    ax.set_ylabel("Percentage of region volume", fontsize = 20)# ylabel
    ax.grid(True)

    legendList = [] # legend items (region ID and material) for the interactive legend
    lines = []      # array of matplotlib objects; a line for each region for the interactive legend
    labelsList = [] # x,y labels for the interactive tooltip

    xVals = (np.array(range(noBins)) ) # % max dose

    # Plot for each region
    # color=next(ax._get_lines.prop_cycler)['color']
    for region, cumulativeDoseVolume in data.items():
        yVals = np.array(cumulativeDoseVolume) 
        line = ax.plot(xVals[1:-1], yVals[1:-1], lw=LINE_WIDTH, ls='-', marker='o', ms=8, alpha=0.7)
        lines.append(line)
        if(len(materials) == len(data)):
            legendList.append(str(region) + " (" + materials[region-1] + ")")
        else: # uploaded mesh files cannot be associated with material info
            legendList.append(str(region) + " (No material info)")
        labels = []
        for i in range(1, len(xVals)):
            label = "<table><td>Dose: "+"{:.2f}".format(xVals[i])+"%, Volume: "+"{:.2f}".format(yVals[i])+"%</td></table>"
            labels.append(label)
        labelsList.append(labels)
        

    # Interactive legend
    interactive_legend = CustomizedInteractiveLegendPlugin(lines,
                                                     legendList,
                                                     alpha_unsel=0,
                                                     alpha_over=1.5, 
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

    # Save temporory DVH figure locally in png format
    localFilePath = os.path.dirname(__file__) + "/temp/" + outputMeshFileName[:-8] + '.dvh.png'
    plt.savefig(localFilePath, orientation='portrait', format="png")

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
def dose_volume_histogram(user, dns, tcpPort, text_obj, meshUnit, energyUnit, materials, thresholdFluence, power):
    conn = create_connection()
    conn.ensure_connection()
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
    print ('>>> connecting to remote server in visualizerDVH...')
    client.connect(dns, username='ubuntu', pkey=privkey)
    sftp = client.open_sftp()
    try:
        print ('>>> connected to remote server in visualizerDVH.')
        sys.stdout.flush()
        sftp.get(remoteFilePath, localFilePath)

        output = import_data(localFilePath)

        # delete temporory mesh
        os.remove(localFilePath)

        ## regionBoundaries = [100, 140, 55, 75, 80, 110] ## Good region for FullMonte_fluence_line mesh
        ## output = extract_mesh_subregion(output, regionBoundaries)

        # Arrays are of type numpy.ndarray
        numpyWrapper = npi.WrapDataObject( output )
        generation_success = True

        try:
            fluenceData = numpyWrapper.CellData["Fluence"] # Assuming you know the name of the array
            regionData = numpyWrapper.CellData["Region"]
            print()

            if (fluenceData.size != regionData.size):
                print("Fluence and region data do not match")
                generation_success = False

        except AttributeError:
            print("Could not parse region or fluence data by name. Attempting to parse by index")

            try:
                regionData = numpyWrapper.CellData[0]
                fluenceData = numpyWrapper.CellData[1] # Assuming you know the number of the array

                if (fluenceData.size != regionData.size):
                    print("Fluence and region data do not match")
                    generation_success = False

            except IndexError:
                print("Could not parse region or fluence data. Input mesh may not be a correctly formatted FullMonte output file.")
                generation_success = False

            except:
                print("Unidentified error occurred. Could not parse input data")
                generation_success = False

        noBins = 500    # max fluence is divided into

        volumeData = calculate_volumes(output,regionData)

        thresholdFluenceArray = [float(x) for x in thresholdFluence.split()]
        thresholdFluenceArray.insert(0, 0)
        print(">>>>>>>>>>>>>", thresholdFluenceArray)
        if len(volumeData) + 1 != len(thresholdFluenceArray):
            print("Number of tissue properties does not match number of regions in mesh")
            generation_success = False

        if generation_success == False:
            # info.maxFluence = 0
            # info.save()
            # update process status
            running_process = processRunning.objects.filter(user = user).latest('id')
            running_process.running = False
            running_process.save()
            sftp.close()
            client.close()
            conn.close()
            sys.stdout.flush()
            return(-1)
        cutoff = [i * 5 for i in thresholdFluenceArray] # 500%
        doseData = get_doses(fluenceData,regionData)
        DVHdata = calculate_cumulative_DVH(doseData,volumeData)
        cumulativeDVH_v100, scalingFactor = calculate_cdvh_for_v100(DVHdata, noBins, thresholdFluenceArray, cutoff)
        # save the figure's html string to session
        info.dvhFig = plot_DVH(cumulativeDVH_v100,noBins,materials,outputMeshFileName,meshUnit)
        info.powerAndScaling = "Simulation power used is " + "{:.2f}".format(power) + "\nScaled power to " + "{:.2f}".format(scalingFactor * power) + " to achieve V100 of 98%."
        # info.maxFluence = maxFluence
        info.save()
        # export the data to csv if mesh file comes from simulation
        localFilePath = os.path.dirname(__file__) + "/temp/" + outputMeshFileName[:-8] + '.dvh.png'
        if(len(materials) == len(volumeData) + 1): # only mesh files from simulation with manual input has material info
            print("Exporting DVH data to CSV")
            with sftp.open('/home/ubuntu/docker_sims/' + outputMeshFileName[:-8] + '.dvh.csv', "w") as f:
                for region in export_data:
                    title = ['', '', 'Region ' + str(region) + ' (' + materials[region] + ')']
                    df = pd.DataFrame(title).T
                    df.columns = ['', '', '']
                    f.write(df.to_csv(index=False))

                    df = pd.DataFrame(export_data[region]).T
                    df.columns = ['Fluence Dose'+' ('+energyUnit+')', 'Region Volume'+' ('+meshUnit+')', 'Region Volume Coverage', '% Max Fluence Dose', '% Region Volume Coverage']
                    f.write(df.to_csv(index=False, float_format='%.3f'))
            print("DVH data export complete")
            remoteFilePath = "/home/ubuntu/docker_sims/" + outputMeshFileName[:-8] + '.dvh.png'
            sftp.put(localFilePath, remoteFilePath) # transfer dvh figure from local to remote server

        # delete temporory dvh plot
        os.remove(localFilePath)
            
        # update process status
        running_process = processRunning.objects.filter(user = user).latest('id')
        running_process.running = False
        running_process.save()
        sftp.close()
    finally:
        sftp.close()
        client.close()
        conn.close()
        print ('>>> destroyed connection from remote server in dose_volume_histogram.')
    print("done generating DVH")
    sys.stdout.flush()

# Function to generate DVH for PDT-SPACE
def pdt_dose_volume_histogram(user, num_material, materials):
    conn = create_connection()
    conn.ensure_connection()
    try:
        info = meshFileInfo.objects.filter(user = user).latest('id')
        
        localFilePath = os.path.dirname(__file__) + "/temp/v100.m"
        dvh_data = load_dvh_data(int(num_material), localFilePath)
        noBins = 500
        print(materials)
        info.dvhFig = plot_PDVH(dvh_data,noBins,materials,"pdt_space_dvh")
        info.save()
        # update process status
        running_process = processRunning.objects.filter(user = user).latest('id')
        running_process.running = False
        running_process.save()
    finally:
        conn.close()
    print("done generating DVH")
    sys.stdout.flush()