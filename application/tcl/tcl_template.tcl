package require FullMonte
proc progressTimer {} {
     while { ![k done] } {
          puts -nonewline [format "\rProgress %6.2f%%" [expr 100.0*[k progressFraction]]]
          flush stdout
          after 200
     }
     puts [format "\rProgress %6.2f%%" 100.0]
}

set fn "/sims/Bladder.mesh_PVWg2MD.vtk"

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

Material blader
     blader     scatteringCoeff     14.6
     blader     absorptionCoeff     0.45
     blader     refractiveIndex     1.33
     blader     anisotropy     0.9

Material water
     water     scatteringCoeff     1.7e-06
     water     absorptionCoeff     4.09e-05
     water     refractiveIndex     1.37
     water     anisotropy     0.8

MS exterior air
MS append blader
MS append water

Point P1
     P1 position "-2.9 23.0 1400.0"
     P1 power 1

TetraSVKernel k
     k packetCount 1000000
     k source P1
     k geometry $M
     k materials MS

     k startAsync
     progressTimer
     k finishAsync

set ODC [k results]

EnergyToFluence EF
     EF geometry $M
     EF materials MS
     EF source [$ODC getByName "VolumeEnergy"]
     EF inputEnergy
     EF outputFluence
     EF update

VTKMeshWriter W
     W filename "/sims/Bladder.mesh_PVWg2MD.out.vtk"
     W addData "Fluence" [EF result]
     W mesh $M
     W write

TextFileMatrixWriter TW
     TW filename "/sims/Bladder.mesh_PVWg2MD.phi_v.txt"
     TW source [EF result]
     TW write
