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

# Define CSS for custom labels
css = """
table, td
{
  border: 1px solid black;
  text-align: right;
  background-color: #cccccc;
}
"""

# convert dose volume data into % max dose bins
def groupIntoBins(rawDVHData, maxFluence, noBins):
    cumulativeDVHData = {}
    for region in rawDVHData:
        cumulativeDVHData[region] = np.zeros((4, noBins)) # 4 rows: dose, %max dose, cumulative volume, %total volume
        cumulativeDVHData[region][1] = (np.array(range(noBins)) / noBins * 100) # % max dose for each bin
        cumulativeVolume = rawDVHData[region][0]
        percentVolume = rawDVHData[region][1]
        doses = rawDVHData[region][2]
        numEntries = len(doses)
        # compute the bin for each dose, and keep overwriting the dose and volume info in that bin with max value for that bin
        for n in range(numEntries):
            # 500 (noBins) bins, so the dose bin ID on the x-axis is dose/max_dose * noBins
            bin_id = floor(doses[n] / maxFluence * (noBins-1))
            cumulativeDVHData[region][0][bin_id] = doses[n] # max dose for this bin
            cumulativeDVHData[region][2][bin_id] = cumulativeVolume[n] # max cumulative volume for this bin
            cumulativeDVHData[region][3][bin_id] = percentVolume[n] # max %cumulative volume for this bin
        # fill in the gaps
        for n in range(1, noBins):
            if cumulativeDVHData[region][0][n] == 0:
                cumulativeDVHData[region][0][n] = cumulativeDVHData[region][0][n-1]
            if cumulativeDVHData[region][2][n] == 0:
                cumulativeDVHData[region][2][n] = cumulativeDVHData[region][2][n-1]
            if cumulativeDVHData[region][3][n] == 0:
                cumulativeDVHData[region][3][n] = cumulativeDVHData[region][3][n-1]
    return cumulativeDVHData

# The cumulative DVH is plotted with bin doses (% maximum dose) along the horizontal
# axis. The column height of each bin represents the %volume of structure receiving a
# dose greater than or equal to that dose.
# plot using matplotlib and convert to html string
def plot_DVH(cumulativeDVHData, materials, outputMeshFileName, noBins):
    FIG_WIDTH = 11
    FIG_HEIGHT = 6
    LINE_WIDTH = 4

    # Plot style
    plt.style.use("bmh")

    # Set up figure and plot
    fig = plt.figure(linewidth=10, edgecolor="#04253a", frameon=True)
    fig.suptitle("Cumulative Dose-Volume Histogram", fontsize=30, y = 1)
    ax = fig.add_subplot(111)
    ax.set_xlabel("% max fluence dose",fontsize = 20) # xlabel
    ax.set_ylabel("% region volume coverage", fontsize = 20)# ylabel
    ax.grid(True)

    legendList = [] # legend items (region ID and material) for the interactive legend
    lines = []      # array of matplotlib objects; a line for each region for the interactive legend
    labelsList = [] # x,y labels for the interactive tooltip

    xVals = (np.array(range(noBins)) / noBins * 100) # % max dose

    # Plot for each region
    # color=next(ax._get_lines.prop_cycler)['color']
    for region in cumulativeDVHData:
        yVals = cumulativeDVHData[region][3] # % cumulative volume
        line = ax.plot(xVals, yVals, lw=LINE_WIDTH, ls='-', marker='o', ms=8, alpha=0.7)
        lines.append(line)
        if(len(materials) > 0): # mesh file from simulation can use material info from simulation
            legendList.append(str(region) + " (" + materials[region] + ")")
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
def dose_volume_histogram(user, dns, tcpPort, text_obj, dvhTxtFileName, meshUnit, energyUnit, materials):
    print("Generating DVH")
    conn = create_connection()
    conn.ensure_connection()

    info = meshFileInfo.objects.filter(user = user).latest('id')
    outputMeshFileName = info.fileName
    remoteFilePath = "/home/ubuntu/docker_sims/" + dvhTxtFileName
    print("remote file path: "+remoteFilePath)

    # connect to EC2
    private_key_file = io.StringIO(text_obj)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    print ('connecting to remote server in visualizerDVH')
    client.connect(dns, username='ubuntu', pkey=privkey)
    print ('connected to remote server in visualizerDVH')
    sys.stdout.flush()
    sftp = client.open_sftp()

    # parce through DVH text file and extract data
    firstLine = True
    rawDVHData = {}
    RegionID = 0
    maxFluence = 0
    with sftp.open(filename=remoteFilePath, bufsize=1) as dvhFile:
        for line in dvhFile:
            if firstLine:
                numRegions = int(line) # first line is a single number that defines number of regions
                print("Number of regions in DVH:", numRegions)
                firstLine = False
            else:
                data = line.split()
                if len(data) == 1: # new region
                    RegionID = RegionID + 1 # start at 1 since region 0 (air) is ignored
                    print("Saving data for Region", RegionID)
                    rawDVHData[RegionID] = [[],[],[]]
                else:
                    rawDVHData[RegionID][0].append(float(data[0])) # CumulativeMeasure (cumulative volume)
                    rawDVHData[RegionID][1].append(float(data[1])) # CDF (% cumulative volume)
                    rawDVHData[RegionID][2].append(float(data[2])) # Dose (fluence)
                    maxFluence = max(maxFluence, float(data[2]))

    # check if number of regions is correct
    try:
        RegionID == numRegions
    except:
        print("Incorrect number of regions. Actual number of regions: " + numRegions + ", found number of regions: " + RegionID)
        return -1
    
    # Group fluence into bins
    noBins = 500    # max fluence is divided into this many bins
    cumulativeDVHData = groupIntoBins(rawDVHData, maxFluence, noBins)

    # plot DVH figure and save the figure's html string to session
    info.dvhFig = plot_DVH(cumulativeDVHData, materials, outputMeshFileName, noBins)
    info.maxFluence = maxFluence
    info.save()

    # export the data to csv if mesh file comes from simulation
    localFilePath = os.path.dirname(__file__) + "/temp/" + outputMeshFileName[:-8] + '.dvh.png'
    if(len(materials) > 0): # only mesh files from simulation has material info
        print("Exporting DVH data to CSV")
        with sftp.open('/home/ubuntu/docker_sims/' + outputMeshFileName[:-8] + '.dvh.csv', "w") as f:
            for region in cumulativeDVHData:
                title = ['', '', 'Region ' + str(region) + ' (' + materials[region] + ')']
                df = pd.DataFrame(title).T
                df.columns = ['', '', '']
                f.write(df.to_csv(index=False))

                df = pd.DataFrame(cumulativeDVHData[region]).T
                df.columns = ['Dose ('+energyUnit+')', '% Max Dose', 'Cumulative volume ('+meshUnit+')', '% Total coverage (% volume that received at most the respective dose)']
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
    client.close()
    conn.close()
    print("done generating DVH")
    sys.stdout.flush()