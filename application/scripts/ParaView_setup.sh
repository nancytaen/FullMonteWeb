#!/bin/bash
echo "Starting ParaView Visualizer Setup..." >> ~/setup_paraview.log
if [[ ! -e ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit ]]; then
    echo "No ParaView binary package detected. Starting download..." >> ~/setup_paraview.log
    wget -O ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit.tar.gz "https://www.paraview.org/paraview-downloads/download.php?submit=Download&version=v5.8&type=binary&os=Linux&downloadFile=ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit.tar.gz"
    echo 8 > ~/setup.log
    echo "Successfully downloaded binary files from ParaView.org" >> ~/setup_paraview.log
    tar xzvf ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit.tar.gz
    echo "Successfully unzipped binary files" >> ~/setup_paraview.log
    echo 9 > ~/setup.log
else
    echo "ParaView binary package is detected. Skipping download." >> ~/setup_paraview.log
    echo 9 > ~/setup.log
fi

package='pvw-visualizer'
if [ `npm list -g | grep -c $package` -eq 0 ]; then
    echo "No ParaView Visualizer commandline package detected. Starting installation..." >> ~/setup_paraview.log
    sudo apt update && sudo apt upgrade -y
    echo 10 > ~/setup.log
    echo "Successfully updated and upgraded packages" >> ~/setup_paraview.log
    sudo apt-get -y install libglu1
    echo 11 > ~/setup.log
    echo "Successfully installed libglu1" >> ~/setup_paraview.log
    sudo apt -y install npm
    echo 12 > ~/setup.log
    echo "Successfully installed npm" >> ~/setup_paraview.log
    sudo npm install -g $package --no-shrinkwrap
    echo 13 > ~/setup.log
    echo "Successfully installed pvw-visualizer" >> ~/setup_paraview.log
else
    echo "ParaView commandline package is detected. Skipping installation." >> ~/setup_paraview.log
    echo 13 > ~/setup.log
fi
echo "Paraview Visualizer setup is done." >> ~/setup_paraview.log