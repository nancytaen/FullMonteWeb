package require FullMonte

set fn "C:\Users\galen\git\fullMonteWeb\application/Colin27.mesh_0SWsDiW.vtk"

VTKMeshReader R
     R filename $fn
     R read

set M [R mesh]

MaterialSet MS

Material muscle
     muscle     scatteringCoeff     89.2
     muscle     absorptionCoeff     1.17
     muscle     refractiveIndex     1.37
     muscle     anisotropy     1.17

Material tumour
     tumour     scatteringCoeff     9.35
     tumour     absorptionCoeff     0.13
     tumour     refractiveIndex     1.39
     tumour     anisotropy     0.13

MS append muscle
MS append tumour

Volume P1
     P1 position "2.0 4.0 -2.0"

TetraSVKernal k
     k packetCount 100000
     k source P1
     k geometry $M
     k materials MS

     k runSync

set ODC [k results]

EnergyToFluence EF
     EF geometry $M
     EF materials MS
     EF source [$ODC getByName "VolumeEnergy"]
     EF inputEnergy
     EF outputFluence
     EF update

VTKMeshWriter W
     W filename "C:\Users\galen\git\fullMonteWeb\application/vtk/vtk_1043_02262020.out.vtk"
     W addData "Fluence" [EF result]
     W mesh $M
     W write

TextFileMatrixWriter TW
     TW filename "C:\Users\galen\git\fullMonteWeb\application/vtk/vtk_1043_02262020.phi_v.vtk"
     TW source [EF result]
     TW write
