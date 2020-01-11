package require FullMonte

## Read VTK mesh

#set mesh file name 
set fn

VTKMeshReader R
    R filename $fn
    R read

set M [R mesh]


## create material set

MaterialSet MS

# Create source
   
# Set up kernel

# Run and wait until completes
    k runSync

# Get results OutputDataCollection
set ODC [k results]


# List results (for demonstration purposes only)
puts "Results available: "
for { set i 0 } { $i < [$ODC size] } { incr i } {
    set res [$ODC getByIndex $i]
    puts "  type=[[$res type] name] name=[$res name]"
}

# Convert energy absorbed per volume element to volume average fluence
EnergyToFluence EF
    EF geometry $M
    EF materials MS
    EF source [$ODC getByName "VolumeEnergy"]
    EF inputEnergy
    EF outputFluence
    EF update

# Write the mesh with fluence appended
VTKMeshWriter W
    W filename
    W addData "Fluence" [EF result]
    W mesh $M
    W write

# Write the fluence values only to a text file
TextFileMatrixWriter TW
    TW filename
    TW source [EF result]
    TW write
