package require FullMonte

set fn "/Users/charliechai/Documents/UT/4th_Year/ECE496/FullMonteWeb/application/183test21.mesh.vtk"

VTKMeshReader R
     R filname $fn
     R read

set M [R mesh]

MaterialSet MS

Material air
     air     scatteringCoeff     0.0
     air     absorptionCoeff     0.0
     air     refractiveIndex     1.0
     air     anisotropy     0.0

Material tumour
     tumour     scatteringCoeff     2.0
     tumour     absorptionCoeff     2.0
     tumour     refractiveIndex     2.0
     tumour     anisotropy     2.0

MS exterior air
MS append tumour

Point P1
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
     W filename "/Users/charliechai/Documents/UT/4th_Year/ECE496/FullMonteWeb/application/vtk/vtk_0208_01132020.out.vtk"
     W addData "Fluence" [EF result]
     W mesh $M
     W write

TextFileMatrixWriter TW
     TW filename "/Users/charliechai/Documents/UT/4th_Year/ECE496/FullMonteWeb/application/vtk/vtk_0208_01132020.phi_v.vtk"
     TW source [EF result]
     TW write
