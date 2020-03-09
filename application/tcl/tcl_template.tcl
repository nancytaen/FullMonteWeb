package require FullMonte

set fn "/sims/183test21.mesh_bPZXlpU.vtk"

VTKMeshReader R
     R filename $fn
     R read

set M [R mesh]

MaterialSet MS

Material air
     air     scatteringCoeff     0.0
     air     absorptionCoeff     0.0
     air     refractiveIndex     1.0
     air     anisotropy     0.0

Material tongue
     tongue     scatteringCoeff     83.3
     tongue     absorptionCoeff     0.95
     tongue     refractiveIndex     1.37
     tongue     anisotropy     0.95

Material larynx
     larynx     scatteringCoeff     15.0
     larynx     absorptionCoeff     0.55
     larynx     refractiveIndex     1.36
     larynx     anisotropy     0.55

Material tumour
     tumour     scatteringCoeff     9.35
     tumour     absorptionCoeff     0.13
     tumour     refractiveIndex     1.39
     tumour     anisotropy     0.13

Material teeth
     teeth     scatteringCoeff     60.0
     teeth     absorptionCoeff     0.99
     teeth     refractiveIndex     1.48
     teeth     anisotropy     0.99

Material bone
     bone     scatteringCoeff     100.0
     bone     absorptionCoeff     0.3
     bone     refractiveIndex     1.56
     bone     anisotropy     0.3

Material surroundingtissues
     surroundingtissues     scatteringCoeff     10.0
     surroundingtissues     absorptionCoeff     1.49
     surroundingtissues     refractiveIndex     1.35
     surroundingtissues     anisotropy     1.49

Material subcutaneousfat
     subcutaneousfat     scatteringCoeff     30.0
     subcutaneousfat     absorptionCoeff     0.2
     subcutaneousfat     refractiveIndex     1.32
     subcutaneousfat     anisotropy     0.2

Material skin
     skin     scatteringCoeff     187.0
     skin     absorptionCoeff     2.0
     skin     refractiveIndex     1.38
     skin     anisotropy     2.0

MS exterior air
MS append tongue
MS append larynx
MS append tumour
MS append teeth
MS append bone
MS append surroundingtissues
MS append subcutaneousfat
MS append skin

Point P1
     P1 position "7.9683 108.2337 -45.4809"

TetraSVKernel k
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
     W filename "/sims/183test21.mesh_bPZXlpU.out.vtk"
     W addData "Fluence" [EF result]
     W mesh $M
     W write

TextFileMatrixWriter TW
     TW filename "/sims/183test21.mesh_bPZXlpU.phi_v.txt"
     TW source [EF result]
     TW write
