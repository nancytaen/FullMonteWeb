package require FullMonte
proc progressTimer {} {
    while { ![k done] } {
        puts -nonewline [format "\rProgress %6.2f%%" [expr 100.0*[k progressFraction]]]
        flush stdout
        after 200
    }
    puts [format "\rProgress %6.2f%%" 100.0]
}

set fn "/sims/Bladder.mesh_CT4zdNX.vtk"

VTKMeshReader R
    R filename $fn
    R read

set M [R mesh]

MaterialSet MS

Material air
    air    scatteringCoeff    0.0
    air    absorptionCoeff    0.0
    air    refractiveIndex    1.0
    air    anisotropy    0.0

Material bladder
    bladder    scatteringCoeff    14.6
    bladder    absorptionCoeff    0.45
    bladder    refractiveIndex    1.33
    bladder    anisotropy    0.9

Material water
    water    scatteringCoeff    1.7e-06
    water    absorptionCoeff    4.09e-05
    water    refractiveIndex    1.37
    water    anisotropy    0.8

MS exterior air
MS append bladder
MS append water

Point P1
    P1 position "-2.5 20.0 1400.0"
    P1 power 1

TetraSVKernel k
    k packetCount 1000000
    k geometry $M
    k materials MS
    k source P1

    k startAsync
    progressTimer
    k finishAsync

set ODC [k results]

EnergyToFluence EF
    EF kernel k
    EF energy 10.0
    EF inputPhotonWeight
    EF source [$ODC getByName "VolumeEnergy"]
    EF outputFluence
    EF update

VTKMeshWriter W
    W filename "/sims/Bladder.mesh_tmROQ5e.out.vtk"
    W addData "Fluence" [EF result]
    W mesh $M
    W addHeaderComment "MeshUnit: cm EnergyUnit: J"
    W write

TextFileMatrixWriter TW
    TW filename "/sims/Bladder.mesh_tmROQ5e.phi_v.txt"
    TW source [EF result]
    TW write

DoseVolumeHistogramGenerator DVHG
    DVHG mesh $M
    DVHG dose [EF result]
    DVHG update

set DHC [DVHG result]

TextFileMatrixWriter TW
    TW filename "/sims/Bladder.mesh_tmROQ5e.dvh.txt"
    TW source [$DHC get 1]
    TW write

TextFileDoseHistogramWriter TDH
    TDH filename "/sims/Bladder.mesh_tmROQ5e.dvh.txt"
    TDH collection $DHC
    TDH write
