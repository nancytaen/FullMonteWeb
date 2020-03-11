from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from .models import *
from .forms import *

try:
    from shutil import copyfile
    initSrc = "./application/scripts/__init__.py"
    initDst = ".heroku/python/lib/python3.7/site-packages/vtk/__init__.py"
    copyfile(initSrc, initDst)

except OSError:
    pass

from .dvh import dose_volume_histogram as dvh
from .setup_visualizer import visualizer
from application.tclGenerator import *
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.contrib.auth import login, authenticate
from application.forms import SignUpForm
from multiprocessing import Process
import paramiko
from django.db import models
from application.storage_backends import *
from django.core.files.storage import default_storage
from django.core import serializers
import time

from django.conf import settings
from django.core.mail import send_mail

send_mail('Subject here', 'Here is the message.', settings.EMAIL_HOST_USER,
         ['to@example.com'], fail_silently=False)

# Create your views here.

# homepage
def home(request):

    return render(request, "home.html")

# FullMonte Tutorial page
def fmTutorial(request):
    return render(request, "tutorial.html")

# FullMonte About page
def about(request):
    return render(request, "about.html")

# FullMonte Simulator start page
def fmSimulator(request):

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        form = tclInputForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            # process cleaned data from formsets
            #print(form.cleaned_data)

            form.save()
            
            request.session['kernelType'] = form.cleaned_data['kernelType']
            request.session['packetCount'] = form.cleaned_data['packetCount']

            return HttpResponseRedirect('/application/simulator_material')

    # If this is a GET (or any other method) create the default form.
    else:
        form = tclInputForm(request.GET or None)

    context = {
        'form': form,
    }

    return render(request, "simulator.html", context)

# FullMonte Simulator material page
def fmSimulatorMaterial(request):

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        formset1 = materialSetSet(request.POST)

        # check whether it's valid:
        if formset1.is_valid():
            # process cleaned data from formsets

            request.session['material'] = []
            request.session['scatteringCoeff'] = []
            request.session['absorptionCoeff'] = []
            request.session['refractiveIndex'] = []
            request.session['anisotropy'] = []

            for form in formset1:
                #print(form.cleaned_data)
                request.session['material'].append(form.cleaned_data['material'])
                request.session['scatteringCoeff'].append(form.cleaned_data['scatteringCoeff'])
                request.session['absorptionCoeff'].append(form.cleaned_data['absorptionCoeff'])
                request.session['refractiveIndex'].append(form.cleaned_data['refractiveIndex'])
                request.session['anisotropy'].append(form.cleaned_data['anisotropy'])

            return HttpResponseRedirect('/application/simulator_source')

    # If this is a GET (or any other method) create the default form.
    else:
        formset1 = materialSetSet(request.GET or None)

    context = {
        'formset1': formset1,
    }

    return render(request, "simulator_material.html", context)

# ajax requests
def ajaxrequests_view(request):
    ind = request.POST.get('ind', None)
    if(ind):
        ind = int(ind)
        get_data = Material.objects.filter(id=ind)
        ser_data = serializers.serialize("json", get_data)
        return HttpResponse(ser_data, content_type="application/json")
    else:
        return HttpResponse(None, content_type="application/json")

# developer page for creating new preset materials
def createPresetMaterial(request):
    presetMaterial = Material.objects.all()
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        if 'reset' in request.POST:
            Material.objects.all().delete()
            form = materialForm(request.POST)
        else:
            form = materialForm(request.POST, request.FILES)
            
            # check whether it's valid:
            if form.is_valid():
                # process cleaned data from formsets
                #print(form.cleaned_data)
                
                form.save()

    else:
        form = materialForm(request.GET)
        
    context = {
        'form': form,
        'presetMaterials': presetMaterial,
    }
    return render(request, "create_preset_material.html", context)

# FullMonte Simulator light source page
def fmSimulatorSource(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        formset2 = lightSourceSet(request.POST)
        
        # check whether it's valid:
        if formset2.is_valid():
            # process cleaned data from formsets
            
            request.session['sourceType'] = []
            request.session['xPos'] = []
            request.session['yPos'] = []
            request.session['zPos'] = []
            request.session['xDir'] = []
            request.session['yDir'] = []
            request.session['zDir'] = []
            request.session['vElement'] = []
            request.session['rad'] = []
            request.session['power'] = []
            
            for form in formset2:
                print(form.cleaned_data)
                request.session['sourceType'].append(form.cleaned_data['sourceType'])
                request.session['xPos'].append(form.cleaned_data['xPos'])
                request.session['yPos'].append(form.cleaned_data['yPos'])
                request.session['zPos'].append(form.cleaned_data['zPos'])
                request.session['xDir'].append(form.cleaned_data['xDir'])
                request.session['yDir'].append(form.cleaned_data['yDir'])
                request.session['zDir'].append(form.cleaned_data['zDir'])
                request.session['vElement'].append(form.cleaned_data['vElement'])
                request.session['rad'].append(form.cleaned_data['rad'])
                request.session['power'].append(form.cleaned_data['power'])
            
            mesh = tclInput.objects.latest('id')
            
            script_path = tclGenerator(request.session, mesh)
            
            request.session['script_path'] = script_path
            
            #print(tclInput.objects.all())
            #tclInput.objects.all().delete()
            #tclScript.objects.all().delete()
            #print(mesh.meshFile)
            #print(tclInput.objects.all())

            #key = paramiko.RSAKey(data=base64.b64decode(b'AAA...'))
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            #client.get_host_keys().add('ssh.example.com', 'ssh-rsa', key)
            client.connect('142.1.145.194', port='9993', username='Capstone', password='pro929')


            #send file to savi
            ftp_client=client.open_sftp()

            dir_path = os.path.dirname(os.path.abspath(__file__))

            #tc file
            source = dir_path + '/tcl/tcl_template.tcl'
            source = str(source)

            #mesh file
            f = default_storage.open(mesh.meshFile.name)


            #send files to savi server
            tclName = "/home/Capstone/docker_sims/" + mesh.meshFile.name + ".tcl"
            ftp_client.put(source,tclName)
            ftp_client.putfo(f,"/home/Capstone/docker_sims/" + mesh.meshFile.name)
            f.close()
            ftp_client.close()


            '''
            print("______________________________________________________________")
            ##cd to folder
            print("cd")
            stdin, stdout, stderr = client.exec_command('cd docker_sims', get_pty=True)
            ##ls
            print("ls")
            stdin, stdout, stderr = client.exec_command('ls', get_pty=True)
            
            ## run script
            print("run script")
            
            
            stdin, stdout, stderr = client.exec_command('sudo /opt/util/FullMonteSW_setup.sh', get_pty=True)

            stdin.write('pro929\n')  # Password for sudo
            stdin.flush()
            stdin.write('pro929\n')  #gitlab user
            stdin.flush()
            stdin.write('1\n')  #run as user
            stdin.flush()
            stdin.write('capstone929!\n')  #gitlab pw
            stdin.flush()
            stdin.write('cd sims\n')  #when docer opens cd to sims
            stdin.flush()
            stdin.write('ls\n')  #ls
            stdin.flush()

            print("\n")
            stdin.write('stty size\n')  #ls
            stdin.flush()
            stdin.write('reset -w\n')  #ls
            stdin.flush()
            stdin.write('stty size\n')  #ls
            stdin.flush()

            stdin.write('tclmonte.sh ./Run_HeadNeck.tcl\n')  #run tcl
            stdin.flush()

            time.sleep(15)

            stdin.write('exit\n')  #exit
            stdin.flush()

            
            '''
            
            channel = client.invoke_shell()

            out = channel.recv(9999)

            channel.send('cd docker_sims\n')
            time.sleep(0.2)
            channel.send('sudo /opt/util/FullMonteSW_setup.sh\n')
            time.sleep(0.2)
            channel.send('pro929\n')
            time.sleep(0.2)
            channel.send('pro929\n')
            time.sleep(0.2)
            channel.send('1\n')
            time.sleep(0.2)
            channel.send('capstone929!\n')
            time.sleep(1)
            channel.send('cd sims\n')
            time.sleep(0.2)
            channel.send('stty size\n')
            time.sleep(0.5)
            channel.send('reset -w\n')
            time.sleep(0.5)
            channel.send('stty size -w\n')
            time.sleep(0.3)
            time.sleep(0.2)
            channel.send('tclmonte.sh ./' + mesh.meshFile.name + '.tcl' + '\n')
            #time.sleep(15)
            
            test = channel.recv(9999)
            #print(test)
            channel.close


            
            
            ##exit
            #print("exit")
            #stdin, stdout, stderr = client.exec_command('exit', get_pty=True)
            #print("stdout")
            #for line in stdout:
            #    print('... ' + line.strip('\n'))
            #print("stderr")
            #for line in stderr:
            #    print('... ' + line.strip('\n'))

            print("______________________________________________________________")
            #stdin, stdout, stderr = client.exec_command('cd docker_sims')
            stdin, stdout, stderr = client.exec_command('cd docker_sims;ls')
            for line in stdout:
                print('... ' + line.strip('\n'))

            #while()
            
            
            client.close()

            return HttpResponseRedirect('/application/visualization')

    # If this is a GET (or any other method) create the default form.
    else:
        formset2 = lightSourceSet(request.GET or None)
        
    context = {
        'formset2': formset2,
    }

    return render(request, "simulator_source.html", context)

# FullMonte Output page
def fmVisualization(request):

    # filePath = "/visualization/Meshes/FullMonte_fluence_line.vtk"
    # dvhFig = dvh(filePath) # Figure in HTML string format
    #
    # context = {'dvhFig': dvhFig}

    proc = Process(target=visualizer)
    proc.start()

    return render(request, "visualization.html")
    # return render(request, "visualization.html", context)

# page for viewing generated TCL scripts
def tclViewer(request):
    meshes = tclInput.objects.all()
    scripts = tclScript.objects.all()

    context = {
        'meshes': meshes,
        'scripts': scripts,
    }

    if request.method == 'POST':
        if 'reset' in request.POST:
            tclScript.objects.all().delete()
            tclInput.objects.all().delete()
        if 'download_output' in request.POST:
            #print(":)")
            
            # setup FTP client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect('142.1.145.194', port='9993', username='Capstone', password='pro929')
            ftp_client = client.open_sftp()
                    
            # VTK and fluence file names and paths
            mesh = tclInput.objects.latest('id')
            meshName = mesh.meshFile.name[:-4]
            outVtk = "/home/Capstone/docker_sims/" + meshName + ".out.vtk"
            outFlu = "/home/Capstone/docker_sims/" + meshName + ".phi_v.txt"
            destPath = os.path.expanduser("~/Downloads")
            destVtk = destPath + "/" + meshName + ".out.vtk"
            destFlu = destPath + "/" + meshName + ".phi_v.txt"
            
            # test
            #outVtk = "/home/Capstone/docker_sims/183test21.mesh_lcIjGkg.out.vtk"
            
            # retrieve from SAVI
            ftp_client.get(outVtk, destVtk)
            ftp_client.get(outVtk, destFlu)
            
            ftp_client.close()

    return render(request, "tcl_viewer.html", context)

# page for diplaying info about kernel type
def kernelInfo(request):
    return render(request, "kernel_info.html")

# page for downloading preset values
def downloadPreset(request):
    presetObjects = preset.objects.all()

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        if 'reset' in request.POST:
            preset.objects.all().delete()
            form = presetForm(request.POST)
        else:
            form = presetForm(request.POST, request.FILES)

            # check whether it's valid:
            if form.is_valid():
                # process cleaned data from formsets
                #print(form.cleaned_data)

                form.save()

    # If this is a GET (or any other method) create the default form.
    else:
        form = presetForm(request.GET)

    context = {
        'form': form,
        'presetObjects': presetObjects,
    }

    return render(request, "download_preset.html", context)

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})
