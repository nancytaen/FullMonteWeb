import shutil
import os
from datetime import datetime
from django.conf import settings
from application.storage_backends import *
from .models import *
from django.core.files.base import ContentFile

def tclGenerator(session, mesh):
    #initialize session inputs
    indent = '     '
    kernelType = session['kernelType']
    material = session['material']
    scatteringCoeff = session['scatteringCoeff']
    absorptionCoeff = session['absorptionCoeff']
    refractiveIndex = session['refractiveIndex']
    anisotropy = session['anisotropy']
    sourceType = session['sourceType']
    xPos = session['xPos']
    yPos = session['yPos']
    zPos = session['zPos']
    power = session['power']
    
    #initialize path for copying tcl template
    start = datetime.now().strftime('%H%M_%m%d%Y')
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
        mat = ma.lower()
        f.write('Material ' + mat + '\n')
        f.write(indent + mat + indent + 'scatteringCoeff' + indent + str(sc) + '\n')
        f.write(indent + mat + indent + 'absorptionCoeff' + indent + str(ab) + '\n')
        f.write(indent + mat + indent + 'refractiveIndex' + indent + str(re) + '\n')
        f.write(indent + mat + indent + 'anisotropy' + indent + str(ab) + '\n\n')
    
    for ma in material:
        mat = ma.lower()
        if mat == 'air':
            f.write('MS exterior air\n')
        else:
            f.write('MS append ' + mat + '\n')

    f.write('\n')

    #append sources to tcl script
    index = 1
    for st, x, y, z in zip(sourceType, xPos, yPos, zPos):
        f.write(st + ' P' + str(index) + '\n')
        line = 'P' + str(index) + ' position "' + str(x)+ ' ' + str(y) + ' ' + str(z) + '"\n\n'
        f.write(indent + line)
        index += 1

    #append kernel to tcl script
    f.write(kernelType + ' k\n')
    f.write(indent + 'k packetCount 100000\n')
    f.write(indent + 'k source P1\n')
    f.write(indent + 'k geometry $M\n')
    f.write(indent + 'k materials MS\n\n')

    #run and wait
    f.write(indent + 'k runSync\n\n')

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
    name = mesh.meshFile.name
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

    script_name = start + '.tcl'
    new_script = tclScript()
    new_script.script.save(script_name, ContentFile(_temp))
    new_script.save()

    f.close()
    
    return script_name
