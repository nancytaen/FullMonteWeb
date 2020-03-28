package require FullMonte

set fn "/sims/Bladder.mesh_Bfuv4wu.vtk"

VTKMeshReader R
     R filename $fn
     R read

set M [R mesh]

MaterialSet MS

Material adsf1
     adsf1     scatteringCoeff     1.0
     adsf1     absorptionCoeff     1.0
     adsf1     refractiveIndex     11.0
     adsf1     anisotropy     1.0

MS exterior adsf1

Point P1
     P1 position "1.0 1.0 1.0"
     P1 power 1

TetraSVKernel k
     k packetCount 1000000
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
     W filename "/sims/Bladder.mesh_Bfuv4wu.out.vtk"
     W addData "Fluence" [EF result]
     W mesh $M
     W write

TextFileMatrixWriter TW
     TW filename "/sims/Bladder.mesh_Bfuv4wu.phi_v.txt"
     TW source [EF result]
     TW write
