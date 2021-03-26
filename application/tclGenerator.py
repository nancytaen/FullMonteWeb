import shutil
import os
from datetime import datetime
from django.conf import settings
from application.storage_backends import *
from django.core.files.storage import default_storage
from .models import *
from django.core.files.base import ContentFile

def tclGenerator(session, mesh, mesh_unit, energy, energy_unit, current_user):
    script_name = mesh.originalMeshFileName[:-4] + '.tcl'
    new_script = tclScript()
    _temp = ""
    new_script.user = current_user
    new_script.script.save(script_name, ContentFile(_temp))
    script_name = new_script.script.name

    #initialize session inputs
    indent = '    '
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
    volumeRegion = session['volumeRegion']
    emitHemiSphere = session['emitHemiSphere']
    hemiSphereEmitDistribution = session['hemiSphereEmitDistribution']
    numericalAperture = session['numericalAperture']
    checkDirection = session['checkDirection']
    xDir1 = session['xDir1']
    yDir1 = session['yDir1']
    zDir1 = session['zDir1']
    xPos0 = session['xPos0']
    yPos0 = session['yPos0']
    zPos0 = session['zPos0']
    xPos1 = session['xPos1']
    yPos1 = session['yPos1']
    zPos1 = session['zPos1']
    emitVolume = session['emitVolume']
    
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
    for st, x, y, z, xD, yD, zD, vE, ra, po, vr, ehs, hsed, na, cd, xD1, yD1, zD1, x0, y0, z0, x1, y1, z1, ev in \
            zip(sourceType, xPos, yPos, zPos, xDir, yDir, zDir, vElement, rad, power, \
            volumeRegion, emitHemiSphere, hemiSphereEmitDistribution, numericalAperture, checkDirection, xDir, yDir, zDir, xPos0, yPos0, zPos0, xPos1, yPos1, zPos1, emitVolume):
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
        if st == 'Cylinder':
            f.write(st + ' CY' + str(index) + '\n')
            line = 'CY' + str(index) + ' endpoint 0 \"' + str(x0)+ ' ' + str(y0) + ' ' + str(z0) + '\"\n'
            line2 = 'CY' + str(index) + ' endpoint 1 \"' + str(x1)+ ' ' + str(y1) + ' ' + str(z1) + '\"\n'
            line3 = 'CY' + str(index) + ' radius ' + str(ra) + '\n'
            line4 = 'CY' + str(index) + ' power ' + str(po) + '\n\n'
            f.write(indent + line)
            f.write(indent + line2)
            f.write(indent + line3)
            f.write(indent + line4)
            line5 = 'CY' + str(index) + ' emitVolume ' + str(ev) + '\n'
            f.write(indent + line5)
            if ev == "false":
                line6 = 'CY' + str(index) + ' emitHemiSphere ' + str(ehs) + '\n'
                f.write(indent + line6)
                if ehs == "true":
                    line7 = 'CY' + str(index) + ' hemiSphereEmitDistribution \"' + str(hsed) + '\"\n'
                    f.write(indent + line7)
                    if hsed == "CUSTOM":
                        line8 = 'CY' + str(index) + ' numericalAperture ' + str(na) + '\n'
                        f.write(indent + line8)
        if st == 'SurfaceSourceBuilder':
            f.write('VolumeCellInRegionPredicate SSBvol' + str(index) + '\n')
            f.write('SSBvol' + str(index) +' setRegion ' + str(vr) +'\n\n')

            f.write(st + ' SSB' + str(index) + '\n')
            line = 'SSB' + str(index) + ' mesh $M\n'
            line2 = 'SSB' + str(index) + ' setRegion SSBvol' + str(index) + '\n'
            line3 = 'SSB' + str(index) + ' power ' + str(po) + '\n\n'
            f.write(indent + line)
            f.write(indent + line2)
            f.write(indent + line3)

            line4 = 'SSB' + str(index) + ' emitHemiSphere ' + str(ehs) + '\n'
            f.write(indent + line4)
            if ehs == "true":
                line5 = 'SSB' + str(index) + ' hemiSphereEmitDistribution \"' + str(hsed) + '\"\n'
                f.write(indent + line5)
                if hsed == "CUSTOM":
                    line6 = 'SSB' + str(index) + ' numericalAperture ' + str(na) + '\n'
                    f.write(indent + line6)
            if cd == "true":
                line7 = 'SSB' + str(index) + ' checkDirection 1\n'
                line8 = 'SSB' + str(index) + ' emitDirection \"' + str(xD1)+ ' ' + str(yD1) + ' ' + str(zD1) + '\"\n'
                f.write(indent + line7)
                f.write(indent + line8)
            else:
                line7 = 'SSB' + str(index) + ' checkDirection 0\n'
                f.write(indent + line7)
            f.write(indent + 'SSB' + str(index) + ' update\n')
            f.write(indent + 'set C' + str(index) + ' [SSB' + str(index) + ' output]\n\n')
        index += 1

    #append kernel to tcl script
    f.write(kernelType + ' k\n')
    f.write(indent + 'k packetCount ' + str(packetCount) + '\n')
    # f.write(indent + 'k source P1\n')
    f.write(indent + 'k geometry $M\n')
    f.write(indent + 'k materials MS\n')
    if kernelType == "TetraInternalKernel":
        f.write(indent + '[k directedSurfaceScorer] addScoringRegionBoundary vol\n')
    elif kernelType == "TetraCUDAInternalKernel":
        f.write(indent + 'k addScoringRegionBoundary vol\n')

    index = 1
    for st, x, y, z, xD, yD, zD, vE, ra, po, vr, ehs, hsed, na, cd in zip(sourceType, xPos, yPos, zPos, xDir, yDir, zDir, vElement, rad, power, volumeRegion, emitHemiSphere, hemiSphereEmitDistribution, numericalAperture, checkDirection):
        if st == 'Point':
            f.write(indent + 'k source P' + str(index) + '\n\n')
        if st == 'PencilBeam':
            f.write(indent + 'k source PB' + str(index) + '\n\n')
        if st == 'Volume':
            f.write(indent + 'k source V' + str(index) + '\n\n')
        if st == 'Ball':
            f.write(indent + 'k source B' + str(index) + '\n\n')
        if st == 'Cylinder':
            f.write(indent + 'k source CY' + str(index) + '\n\n')
        if st == 'SurfaceSourceBuilder':
            f.write(indent + 'k source $C' + str(index) + '\n\n')
        index += 1

    #run and wait
    f.write(indent + 'k startAsync\n')
    f.write(indent + 'progressTimer\n')
    f.write(indent + 'k finishAsync\n\n')

    #get results
    f.write('set ODC [k results]\n\n')

    #convert photon weight from simulation raw results to energy absorbed per volume element
    f.write('EnergyToFluence EF\n')
    f.write(indent + 'EF kernel k\n')
    f.write(indent + 'EF energy ' + str(energy) + '\n')
    f.write(indent + 'EF inputPhotonWeight\n')
    f.write(indent + 'EF source [$ODC getByName "VolumeEnergy"]\n')
    f.write(indent + 'EF outputFluence\n')
    f.write(indent + 'EF update\n\n')


    #initialize path for results
    #meshResult = dir_path + '/vtk/vtk_' + start + '.out.vtk'
    #fluenceResult = dir_path + '/vtk/vtk_' + start + '.phi_v.vtk'
    name = script_name[:-4]
    meshResult = '/sims/' + name + '.out.vtk'
    fluenceResult = '/sims/' + name + '.phi_v.txt'
    dvhResult = '/sims/' + name + '.dvh.txt'
    comment = 'MeshUnit: ' + mesh_unit + ' EnergyUnit: ' + energy_unit
    
    #write the mesh with fluence appended
    f.write('VTKMeshWriter W\n')
    f.write(indent + 'W filename "' + meshResult + '"\n')
    f.write(indent + 'W addData "Fluence" [EF result]\n')
    f.write(indent + 'W mesh $M\n')
    f.write(indent + 'W addHeaderComment "' + comment + '"\n')
    f.write(indent + 'W write\n\n')

    #write the fluence values only to a text file
    f.write('TextFileMatrixWriter TW\n')
    f.write(indent + 'TW filename "' + fluenceResult + '"\n')
    f.write(indent + 'TW source [EF result]\n')
    f.write(indent + 'TW write\n\n')

    #generate dose volume histogram
    f.write('DoseVolumeHistogramGenerator DVHG\n')
    f.write(indent + 'DVHG mesh $M\n')
    f.write(indent + 'DVHG dose [EF result]\n')
    f.write(indent + 'DVHG update\n\n')

    f.write('set DHC [DVHG result]\n\n')

    #write dvh matrix to a text file
    f.write('TextFileMatrixWriter TW\n')
    f.write(indent + 'TW filename "' + dvhResult + '"\n')
    f.write(indent + 'TW source [$DHC get 1]\n')
    f.write(indent + 'TW write\n\n')

    #overwrite the dvh textfile to dvh format
    f.write('TextFileDoseHistogramWriter TDH\n')
    f.write(indent + 'TDH filename "' + dvhResult + '"\n')
    f.write(indent + 'TDH collection $DHC\n')
    f.write(indent + 'TDH write\n')

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
