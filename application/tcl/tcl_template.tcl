package require FullMonte

set fn "/sims/183test21.mesh_jYPfa5m.vtk"

VTKMeshReader R
     R filename $fn
     R read

set M [R mesh]

MaterialSet MS

Material adf
     adf     scatteringCoeff     1.0
     adf     absorptionCoeff     1.0
     adf     refractiveIndex     1.0
     adf     anisotropy     1.0

MS exterior adf

PencilBeam PB1
     PB1 position "None None None"
     PB1 direction "1.0 1.0 1.0"
     PB1 power 1

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
     W filename "/sims/183test21.mesh_jYPfa5m.out.vtk"
     W addData "Fluence" [EF result]
     W mesh $M
     W write

TextFileMatrixWriter TW
     TW filename "/sims/183test21.mesh_jYPfa5m.phi_v.txt"
     TW source [EF result]
     TW write
