import shutil
import os
from datetime import datetime
from django.conf import settings
from application.storage_backends import *
from django.core.files.storage import default_storage
from .models import *
from django.core.files.base import ContentFile

def tclGenerator(session, mesh, current_user):
    script_name = mesh.originalMeshFileName[:-4] + '.tcl'
    new_script = tclScript()
    _temp = ""
    new_script.user = current_user
    new_script.script.save(script_name, ContentFile(_temp))
    script_name = new_script.script.name

    #initialize session inputs
    indent = '     '
    kernelType = session['kernelType']
    scoredVolumeRegionID = session['scoredVolumeRegionID']
    packetCount = session['packetCount']
    material = session['material']
    scatteringCoeff = session['scatteringCoeff']
    absorptionCoeff = session['absorptionCoeff']
    refractiveIndex = session['refractiveIndex']
    anisotropy = session['anisotropy']
    sourceType = session['sourceType']
    xPos = session['xPos']
    yPos = session['yPos']
    zPos = session['zPos']
    xDir = session['xDir']
    yDir = session['yDir']
    zDir = session['zDir']
    vElement = session['vElement']
    rad = session['rad']
    power = session['power']
    
    #initialize path for copying tcl template
    dir_path = os.path.dirname(os.path.abspath(__file__))
    source = dir_path + '/tcl/tcl_template.tcl'

    #start by wiping script template
    with open(source, 'r') as f:
        lines = f.readlines()
    
    f = open(source, 'w')
    for line in lines[::-1]:
        del lines[-1]
    
    #start writing to tcl script
    f = open(source, 'a')
    f.write('package require FullMonte\n')

    f.write('proc progressTimer {} {\n')
    f.write(indent + 'while { ![k done] } {\n')
    f.write(indent + indent + 'puts -nonewline [format "\\rProgress %6.2f%%" [expr 100.0*[k progressFraction]]]\n')
    f.write(indent + indent + 'flush stdout\n')
    f.write(indent + indent + 'after 200\n')
    f.write(indent + '}\n')
    f.write(indent + 'puts [format "\\rProgress %6.2f%%" 100.0]\n')
    f.write('}\n')
    
    #append mesh to tcl script
    #meshpath = dir_path + '/' + mesh.meshFile.name
    meshpath = '/sims/' + mesh.meshFile.name
    f.write('\nset fn "' + meshpath + '"\n\n')
    f.write('VTKMeshReader R\n')
    f.write(indent + 'R filename $fn\n')
    f.write(indent + 'R read\n\n')
    f.write('set M [R mesh]\n\n')
    
    #append material set to tcl script
    f.write('MaterialSet MS\n\n')
    
    for ma, sc, ab, re, an in zip(material, scatteringCoeff, absorptionCoeff, refractiveIndex, anisotropy):
        matLower = ma.lower()
        mat = matLower.replace(' ','')
        f.write('Material ' + mat + '\n')
        f.write(indent + mat + indent + 'scatteringCoeff' + indent + str(sc) + '\n')
        f.write(indent + mat + indent + 'absorptionCoeff' + indent + str(ab) + '\n')
        f.write(indent + mat + indent + 'refractiveIndex' + indent + str(re) + '\n')
        f.write(indent + mat + indent + 'anisotropy' + indent + str(an) + '\n\n')
    
    i = 0
    for ma in material:
        matLower = ma.lower()
        mat = matLower.replace(' ','')
        if i == 0:
            f.write('MS exterior ' + mat + '\n')
        else:
            f.write('MS append ' + mat + '\n')
        i += 1

    f.write('\n')

    if kernelType == "TetraInternalKernel" or kernelType == "TetraCUDAInternalKernel":
        f.write('VolumeCellInRegionPredicate vol\n')
        f.write('vol setRegion '+ str(scoredVolumeRegionID) + '\n')

    #append sources to tcl script
    index = 1
    for st, x, y, z, xD, yD, zD, vE, ra, po in zip(sourceType, xPos, yPos, zPos, xDir, yDir, zDir, vElement, rad, power):
        if st == 'Point':
            f.write(st + ' P' + str(index) + '\n')
            line = 'P' + str(index) + ' position "' + str(x)+ ' ' + str(y) + ' ' + str(z) + '"\n'
            line2 = 'P' + str(index) + ' power ' + str(po) + '\n\n'
            f.write(indent + line)
            f.write(indent + line2)
        if st == 'PencilBeam':
            f.write(st + ' PB' + str(index) + '\n')
            line = 'PB' + str(index) + ' position "' + str(x)+ ' ' + str(y) + ' ' + str(z) + '"\n'
            line2 = 'PB' + str(index) + ' direction "' + str(xD)+ ' ' + str(yD) + ' ' + str(zD) + '"\n'
            line3 = 'PB' + str(index) + ' power ' + str(po) + '\n\n'
            f.write(indent + line)
            f.write(indent + line2)
            f.write(indent + line3)
        if st == 'Volume':
            f.write(st + ' V' + str(index) + '\n')
            line = 'V' + str(index) + ' elementID ' + str(vE) + '\n'
            line2 = 'V' + str(index) + ' power ' + str(po) + '\n\n'
            f.write(indent + line)
            f.write(indent + line2)
        if st == 'Ball':
            f.write(st + ' B' + str(index) + '\n')
            line = 'B' + str(index) + ' position "' + str(x)+ ' ' + str(y) + ' ' + str(z) + '"\n'
            line2 = 'B' + str(index) + ' radius ' + str(ra) + '\n'
            line3 = 'B' + str(index) + ' power ' + str(po) + '\n\n'
            f.write(indent + line)
            f.write(indent + line2)
        index += 1

    #append kernel to tcl script
    f.write(kernelType + ' k\n')
    f.write(indent + 'k packetCount ' + str(packetCount) + '\n')
    f.write(indent + 'k source P1\n')
    f.write(indent + 'k geometry $M\n')
    f.write(indent + 'k materials MS\n')
    if kernelType == "TetraInternalKernel":
        f.write(indent + '[k directedSurfaceScorer] addScoringRegionBoundary vol\n\n')
    elif kernelType == "TetraCUDAInternalKernel":
        f.write(indent + 'k addScoringRegionBoundary vol\n\n')

    #run and wait
    f.write(indent + 'k startAsync\n')
    f.write(indent + 'progressTimer\n')
    f.write(indent + 'k finishAsync\n\n')

    #get results
    f.write('set ODC [k results]\n\n')

    #convert energy absorbed per volume element to volume average fluence
    f.write('EnergyToFluence EF\n')
    f.write(indent + 'EF geometry $M\n')
    f.write(indent + 'EF materials MS\n')
    f.write(indent + 'EF source [$ODC getByName "VolumeEnergy"]\n')
    f.write(indent + 'EF inputEnergy\n')
    f.write(indent + 'EF outputFluence\n')
    f.write(indent + 'EF update\n\n')


    #initialize path for results
    #meshResult = dir_path + '/vtk/vtk_' + start + '.out.vtk'
    #fluenceResult = dir_path + '/vtk/vtk_' + start + '.phi_v.vtk'
    name = script_name[:-4]
    meshResult = '/sims/' + name + '.out.vtk'
    fluenceResult = '/sims/' + name + '.phi_v.txt'
    
    #write the mesh with fluence appended
    f.write('VTKMeshWriter W\n')
    f.write(indent + 'W filename "' + meshResult + '"\n')
    f.write(indent + 'W addData "Fluence" [EF result]\n')
    f.write(indent + 'W mesh $M\n')
    f.write(indent + 'W write\n\n')

    #write the fluence values only to a text file
    f.write('TextFileMatrixWriter TW\n')
    f.write(indent + 'TW filename "' + fluenceResult + '"\n')
    f.write(indent + 'TW source [EF result]\n')
    f.write(indent + 'TW write\n')

    #copy and save script to AWS
    f = open(source, 'r')
    lines = f.readlines()
    _temp = b''
    for line in lines:
        _temp += line.encode()

    new_script.user = current_user
    with default_storage.open(script_name, 'wb') as tcl_script:
        tcl_script.write(_temp)
    new_script.save()

    f.close()
    
    return new_script.script.name
