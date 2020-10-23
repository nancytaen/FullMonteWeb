from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from .models import *
from .forms import *
from django.core.files.base import ContentFile
import sys

# Extremely hacky fix for VTK not importing correctly on Heroku
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
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import login, authenticate
from application.forms import SignUpForm
import paramiko
from django.db import models
from application.storage_backends import *
from django.core.files.storage import default_storage
from django.core import serializers
import time

from .tokens import account_activation_token
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string

from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.core.mail import EmailMessage

from decouple import config
from multiprocessing import Process

#send_mail('Subject here', 'Here is the message.', settings.EMAIL_HOST_USER,
 #        ['to@example.com'], fail_silently=False)

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

#Please login page - when trying to access simulator
def please_login(request):
    return render(request, "please_login.html")

# FullMonte Simulator start page
def fmSimulator(request):
    if not request.user.is_authenticated:
        return redirect('please_login')


    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        form = tclInputForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            # process cleaned data from formsets
            #print(form.cleaned_data)

            obj = form.save(commit = False)
            obj.user = request.user;
            obj.save()

            # proc = Process(target=obj.save())
            # proc.start()


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
    if not request.user.is_authenticated:
        return redirect('please_login')

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
                messages.success(request, 'Material added successfully, you can now see it in table below')

                return redirect("create_preset_material")

            else:
                messages.error(request, 'Failed to add material, material values must be within bounds')

                return redirect("create_preset_material")

    else:
        form = materialForm(request.GET)

    context = {
        'form': form,
        'presetMaterials': presetMaterial,
    }
    return render(request, "create_preset_material.html", context)

# FullMonte Simulator light source page
def fmSimulatorSource(request):
    if not request.user.is_authenticated:
        return redirect('please_login')
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

            mesh = tclInput.objects.filter(user = request.user).latest('id')

            script_path = tclGenerator(request.session, mesh, request.user)

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
            meshFileName = mesh.meshFile.name

            #send files to savi server
            tclName = "/home/Capstone/docker_sims/" + mesh.meshFile.name + ".tcl"
            ftp_client.put(source,tclName)
            ftp_client.putfo(f,"/home/Capstone/docker_sims/" + mesh.meshFile.name)
            f.close()
            ftp_client.close()

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
    if not request.user.is_authenticated:
        return redirect('please_login')

    #
    # context = {'dvhFig': dvhFig}

    # meshFileName = "183test21.mesh.vtk"
    try:
        mesh = tclInput.objects.filter(user = request.user).latest('id')
    except:
        messages.error(request, 'Error - please upload a mesh before trying to visualize')
        return render(request, "visualization.html")

    meshFileName = mesh.meshFile.name
    msg = "Using mesh " + meshFileName[:-4]

    filePath = "/visualization/Meshes/183test21.out.vtk"

    dvhFig = dvh(filePath)

    if (meshFileName):
        msg = "Using mesh " + meshFileName

    else:
        msg = "No output mesh was found. Root folder will be loaded for visualization."

    context = {'message': msg, 'dvhFig': dvhFig}

    proc = Process(target=visualizer, args=(meshFileName,))
    proc.start()

    return render(request, "visualization.html", context)

# page for viewing and downloading files
def downloadOutput(request):
    if not request.user.is_authenticated:
        return redirect('please_login')

    current_user = request.user

    meshes = tclInput.objects.filter(user = current_user)
    scripts = tclScript.objects.filter(user = current_user)
    outputs = fullmonteOutput.objects.filter(user = current_user)

    context = {
        'meshes': meshes,
        'scripts': scripts,
        'outputs': outputs,
    }

    if request.method == 'POST':
        if 'reset' in request.POST:
            tclInput.objects.filter(user = current_user).delete()
            tclScript.objects.filter(user = current_user).delete()
            fullmonteOutput.objects.filter(user = current_user).delete()

        if 'generate_output' in request.POST:
            # setup FTP client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect('142.1.145.194', port='9993', username='Capstone', password='pro929')
            ftp_client = client.open_sftp()

            # VTK and fluence file names and paths
            try:
                mesh = tclInput.objects.latest('id')
                meshName = mesh.meshFile.name[:-4]
                outVtk = "/home/Capstone/docker_sims/" + meshName + ".out.vtk"
                outFlu = "/home/Capstone/docker_sims/" + meshName + ".phi_v.txt"
            except:
                messages.error(request, 'Error - input mesh not found')
                return render(request, "download_output.html", context)

            # test
            #outVtk = "/home/Capstone/docker_sims/183test21.mesh_lcIjGkg.out.vtk"

            try:
                remote_vtk_file = ftp_client.open(outVtk)
                remote_flu_file = ftp_client.open(outFlu)
            except:
                messages.error(request, 'Error - output mesh not found')
                return render(request, "download_output.html", context)

            try:
                outVtk_name = meshName + ".out.vtk"
                outFlu_name = meshName + ".phi_v.txt"
                new_output = fullmonteOutput()
                new_output.user = current_user
                new_output.outputVtk.save(outVtk_name, remote_vtk_file)
                new_output.outputFluence.save(outFlu_name, remote_flu_file)
                new_output.save()
            except:
                messages.error(request, 'Error - failed to generate output mesh for downloading')
                return render(request, "download_output.html", context)

            finally:
                remote_vtk_file.close()
                remote_flu_file.close()

            ftp_client.close()
            messages.success(request, 'Successfully generated output mesh for downloading, click the files below to download')

    return render(request, "download_output.html", context)

# page for diplaying info about kernel type
def kernelInfo(request):
    return render(request, "kernel_info.html")

# page for downloading preset values
def downloadPreset(request):    
    if not request.user.is_authenticated:
        return redirect('please_login')
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
                messages.success(request, 'Mesh added successfully, you can now see it in table below')

                return redirect("download_preset")

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
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            #username = form.cleaned_data.get('username')
            #raw_password = form.cleaned_data.get('password1')
            #user = authenticate(username=username, password=raw_password)
            current_site = get_current_site(request)
            mail_subject = 'Activate your FullMonte account.'
            message = render_to_string('acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)),
                'token':account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(
                        mail_subject, message, to=[to_email]
            )
            email.send()
            return render(request, "account_registration.html")

    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # return redirect('home')
        return render(request, "activation_complete.html")
    else:
        return HttpResponse('Activation link is invalid!')

def account(request):
    if not request.user.is_authenticated:
        return redirect('please_login')
    return render(request, "account.html")

#for changing passwords
def change_password(request):
    if not request.user.is_authenticated:
        return redirect('please_login')
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully')
            return render(request, 'registration/change_password.html', {
                'form': form
    })
        else:
            messages.error(request, 'Please fix the shown error')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'registration/change_password.html', {
        'form': form
    })

# error page for 30 second timeout when uploading/generating mesh files
# Heroku h12 timeout error
def heroku_timeout(request):
    return render(request, 'heroku_timeout.html')

def aws(request):
    if request.method == 'POST':
        print(request)
        form = awsFiles(request.POST, request.FILES)
        print(request.POST.get("DNS"))
        if form.is_valid():
            handle_uploaded_file(request.FILES['pemfile'])
            sys.stdout.flush()
            return HttpResponseRedirect('/application/')
    else:
        form = awsFiles()

    context = {
        'form': form,
    }
    return render(request, "aws.html", context)

def handle_uploaded_file(f):
    for line in f:
        print (line)