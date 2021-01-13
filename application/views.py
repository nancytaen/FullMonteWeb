from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from .models import *
from .forms import *
from django.core.files.base import ContentFile
import sys
import socket
import io
import codecs
import psutil
from datetime import datetime, timezone
# Extremely hacky fix for VTK not importing correctly on Heroku
try:
    from shutil import copyfile
    initSrc = "./application/scripts/__init__.py"
    initDst = ".heroku/python/lib/python3.7/site-packages/vtk/__init__.py"
    copyfile(initSrc, initDst)

except OSError:
    pass

from .visualizerDVH import dose_volume_histogram as dvh
from .visualizer3D import visualizer
from application.tclGenerator import *
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import login, authenticate
from application.forms import SignUpForm
import paramiko
from django.db import models, connections
from django.db.utils import DEFAULT_DB_ALIAS, load_backend
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
from django.views.generic.detail import DetailView   
from django.http import FileResponse

from decouple import config
from multiprocessing import Process, Event, Queue
import threading
import select
#send_mail('Subject here', 'Here is the message.', settings.EMAIL_HOST_USER,
 #        ['to@example.com'], fail_silently=False)

# Create your views here.
class BaseFileDownloadView(DetailView):
    def get(self, request, *args, **kwargs):
        filename=self.kwargs.get('filename', None)
        if filename is None:
            raise ValueError("Found empty filename")
        some_file = default_storage.open(filename)
        response = FileResponse(some_file)
        # https://docs.djangoproject.com/en/1.11/howto/outputting-csv/#streaming-large-csv-files
        response['Content-Disposition'] = 'attachment; filename="%s"'%filename
        return response

class fileDownloadView(BaseFileDownloadView):
    pass

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

    try:
        dns = request.session['DNS']
        text_obj = request.session['text_obj']
        tcpPort = request.session['tcpPort']
    except:
        messages.error(request, 'Error - please connect to an AWS remote server before trying to simulate')
        return HttpResponseRedirect('/application/aws')

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
            generated_tcl = tclScript.objects.filter(user = request.user).latest('id')

            request.session['script_path'] = script_path

            #mesh file
            mesh_file = default_storage.open(mesh.meshFile.name)
            tcl_file = default_storage.open(generated_tcl.script.name)
            meshFilePath = mesh.meshFile.name

            print("DNS is", request.session['DNS'])
            uploadedAWSPemFile = awsFile.objects.filter(user = request.user).latest('id')
            pemfile = uploadedAWSPemFile.pemfile

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print('SSH into the instance: {}'.format(request.session['DNS']))
            
            private_key_file = io.BytesIO()
            for line in pemfile:
                private_key_file.write(line)
            private_key_file.seek(0)

            byte_str = private_key_file.read()
            text_obj = byte_str.decode('UTF-8')
            private_key_file = io.StringIO(text_obj)
            
            privkey = paramiko.RSAKey.from_private_key(private_key_file)
            request.session['text_obj'] = text_obj
            client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)
            ftp = client.open_sftp()

            ftp.chdir('docker_sims/')
            file=ftp.file('docker.sh', "w")
            file.write('#!/bin/bash\ncd sims/\ntclmonte.sh ./'+generated_tcl.script.name)
            file.flush()
            ftp.chmod('docker.sh', 700)

            ftp.putfo(mesh_file, './'+mesh.meshFile.name)
            ftp.putfo(tcl_file, './'+generated_tcl.script.name)
            ftp.close()

            command = "sudo ~/docker_sims/FullMonteSW_setup.sh | tee ~/sim_run.log"
            channel = client.get_transport().open_session()
            channel.exec_command(command)
            request.session['start_time'] = str(datetime.now(timezone.utc))
            request.session['started'] = "false"
            # time.sleep(3)   # wait tclsh start  # todo: improve this for performance
            #                 # the method in comment below is faster but hard coded for output, may lead to unexpected behaviour
            return HttpResponseRedirect('/application/running')

    # If this is a GET (or any other method) create the default form.
    else:
        formset2 = lightSourceSet(request.GET or None)

    context = {
        'formset2': formset2,
    }

    return render(request, "simulator_source.html", context)

# https://stackoverflow.com/questions/56733112/how-to-create-new-database-connection-in-django
def create_connection(alias=DEFAULT_DB_ALIAS):
    connections.ensure_defaults(alias)
    connections.prepare_test_settings(alias)
    db = connections.databases[alias]
    backend = load_backend(db['ENGINE'])
    return backend.DatabaseWrapper(db, alias)

# run fullMonte on EC2 instance specified by the user
def run_fullmonte_remotely(request, finished_event):
    time.sleep(3)
    conn = create_connection()
    conn.ensure_connection()
    #print(conn)
    print("inside:",request)
    mesh = tclInput.objects.filter(user = request.user).latest('id')

    script_path = tclGenerator(request.session, mesh, request.user)
    generated_tcl = tclScript.objects.filter(user = request.user).latest('id')

    #mesh file
    mesh_file = default_storage.open(mesh.meshFile.name)
    tcl_file = default_storage.open(generated_tcl.script.name)
    meshFileName = mesh.meshFile.name

    print("DNS is", request.session['DNS'])
    uploadedAWSPemFile = awsFile.objects.filter(user = request.user).latest('id')
    pemfile = uploadedAWSPemFile.pemfile

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print('SSH into the instance: {}'.format(request.session['DNS']))
    
    private_key_file = io.BytesIO()
    for line in pemfile:
        private_key_file.write(line)
    private_key_file.seek(0)

    byte_str = private_key_file.read()
    text_obj = byte_str.decode('UTF-8')
    private_key_file = io.StringIO(text_obj)
    
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    #request.session['text_obj'] = text_obj
    client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)
    ftp = client.open_sftp()

    ftp.chdir('docker_sims/')
    file=ftp.file('docker.sh', "w")
    file.write('#!/bin/bash\ncd sims/\ntclmonte.sh ./'+generated_tcl.script.name)
    file.flush()
    ftp.chmod('docker.sh', 700)

    ftp.putfo(mesh_file, './'+mesh.meshFile.name)
    ftp.putfo(tcl_file, './'+generated_tcl.script.name)
    ftp.close()

    #command = "sudo ~/docker_sims/FullMonteSW_setup.sh > sim_run.log"
    command = "sudo ~/docker_sims/FullMonteSW_setup.sh"
    stdin, stdout, stderr = client.exec_command(command)
    #print(stdout.readlines())
    #print(stderr.readlines())
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    for line in stdout_line:
        print (line)
    for line in stderr_line:
        print (line)
    sys.stdout.flush()
    client.close()
    finished_event.set()
    print("finished executing")
    sys.stdout.flush()
    conn.close()

# Output mesh upload page
def visualization_mesh_upload(request):
    if request.method == 'POST':
        print(request)
        form = visualizeMeshForm(request.POST, request.FILES)
        if form.is_valid():
            print(form.cleaned_data)
            # get mesh file from form
            obj = form.save(commit = False)
            obj.user = request.user;
            obj.save()
            uploadedOutputMeshFile = visualizeMesh.objects.filter(user = request.user).latest('id')
            outputMeshFileName = uploadedOutputMeshFile.outputMeshFile.name
            request.session['outputMesh'] = outputMeshFileName
            outputMeshFile = default_storage.open(outputMeshFileName)
            print(outputMeshFileName)

            # copy mesh into remote server
            text_obj = request.session['text_obj']
            private_key_file = io.StringIO(text_obj)
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            privkey = paramiko.RSAKey.from_private_key(private_key_file)
            client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)

            sftp = client.open_sftp()
            sftp.chdir('docker_sims/')
            sftp.putfo(outputMeshFile, './'+outputMeshFileName)
            sftp.close()
            client.close()
            return HttpResponseRedirect('/application/visualization')
    else:
        form = visualizeMeshForm(request.GET or None)
    context = {
        'form': form,
    }
    return render(request, "mesh_upload.html", context)

# FullMonte output Visualization page
def fmVisualization(request):
    if not request.user.is_authenticated:
        return redirect('please_login')

    try:
        dns = request.session['DNS']
        text_obj = request.session['text_obj']
        tcpPort = request.session['tcpPort']
    except:
        messages.error(request, 'Error - please connect to an AWS remote server before trying to visualize')
        return HttpResponseRedirect('/application/aws')

    try:
        outputMeshFileName = request.session['outputMesh']
    except:
        messages.error(request, 'Error - please run simulation or upload a mesh before trying to visualize')
        return HttpResponseRedirect('/application/mesh_upload')

    # generate ParaView Visualization URL
    dns = request.session['DNS']
    tcpPort = request.session['tcpPort']
    visURL = dns + ":" + tcpPort

    # check if file exists in the remote server
    private_key_file = io.StringIO(text_obj)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    client.connect(dns, username='ubuntu', pkey=privkey)

    sftp = client.open_sftp()
    try:
        sftp.stat('docker_sims/'+outputMeshFileName)
        msg = "Using output mesh \"" + outputMeshFileName + "\" from the last simulation or upload."
        fileExists = True
    except:
        msg = "Mesh \"" + outputMeshFileName + "\" from the last simulation or upload was not found. Perhaps it was deleted. Root folder will be loaded for visualization."
        fileExists = False
    sftp.close()
    client.close()

    # render 3D visualizer
    text_obj = request.session['text_obj']
    proc1 = Process(target=visualizer, args=(outputMeshFileName, fileExists, dns, tcpPort, text_obj, ))
    proc1.start()

    # generate DVH
    dvhFig = Queue()
    proc2 = Process(target=dvh, args=(outputMeshFileName, fileExists, dns, tcpPort, text_obj, dvhFig, ))
    proc2.start()
    
    # pass message, DVH figure, and 3D visualizer link to the HTML
    context = {'message': msg, 'dvhFig': dvhFig.get(), 'visURL': visURL}
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

# user account signup page
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

# user account activation page
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

# user acount info page
def account(request):
    if not request.user.is_authenticated:
        return redirect('please_login')
    return render(request, "account.html")

# user account changing passwords page
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

# AWS EC2 instance setup page
def aws(request):
    if not request.user.is_authenticated:
        return redirect('please_login')
    
    if request.method == 'POST':
        print(request)
        form = awsFiles(request.POST, request.FILES)
        print(request.POST.get("DNS"))
        if form.is_valid():
            print(form.cleaned_data)
            obj = form.save(commit = False)
            obj.user = request.user;
            obj.save()
            request.session['DNS'] = form.cleaned_data['DNS']
            request.session['tcpPort'] = str(form.cleaned_data['TCP_port'])
            # handle_uploaded_file(request.FILES['pemfile'])
            uploadedAWSPemFile = awsFile.objects.filter(user = request.user).latest('id')
            pemfile = uploadedAWSPemFile.pemfile

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            private_key_file = io.BytesIO()
            for line in pemfile:
                private_key_file.write(line)
            private_key_file.seek(0)

            byte_str = private_key_file.read()
            text_obj = byte_str.decode('UTF-8')
            private_key_file = io.StringIO(text_obj)
            
            privkey = paramiko.RSAKey.from_private_key(private_key_file)
            request.session['text_obj'] = text_obj
            client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)
            sftp = client.open_sftp()
            try:
                sftp.stat('docker_sims/FullMonteSW_setup.sh')
            except IOError:
                # cluster that's not setup
                client.close()
            
                print('before')
                current_process = psutil.Process()
                children = current_process.children(recursive=True)
                for child in children:
                    print('Child pid is {}'.format(child.pid))
                connections.close_all()
                p = Process(target=run_aws_setup, args=(request, ))
                # print(p)
                p.start()
                print('after')
                current_process = psutil.Process()
                children = current_process.children(recursive=True)

                form = processRunning()
                form.user=request.user
                
                for child in children:
                    form.pid = child.pid
                    form.running = True
                    print('Child pid is {}'.format(child.pid))
                
                conn = create_connection()
                conn.ensure_connection()
                form.save()
                conn.close()
                sys.stdout.flush()
                # client.close()
                
                return HttpResponseRedirect('/application/AWSsetup')
            
            client.close()
            return render(request, "aws_setup_complete.html")
    else:
        form = awsFiles()

    context = {
        'form': form,
    }
    return render(request, "aws.html", context)

# run AWS setup on the EC2 instance specified by user
def run_aws_setup(request):
    time.sleep(3)
    text_obj = request.session['text_obj']
    # uploadedAWSPemFile = awsFile.objects.filter(user = request.user).latest('id')
    private_key_file = io.StringIO(text_obj)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)

    dir_path = os.path.dirname(os.path.abspath(__file__))
    #tc file
    source_setup = dir_path + '/scripts/setup_aws.sh'
    source_setup = str(source_setup)

    source_fullmonte = dir_path + '/scripts/FullMonteSW_setup.sh'
    source_fullmonte = str(source_fullmonte)

    source_paraview = dir_path + '/scripts/ParaView_setup.sh'
    source_paraview = str(source_paraview)

    sftp = client.open_sftp()
    client.exec_command('mkdir -p docker_sims')
    sftp.put(source_setup, 'docker_sims/setup_aws.sh')
    sftp.put(source_fullmonte, 'docker_sims/FullMonteSW_setup.sh')
    sftp.put(source_paraview, 'docker_sims/ParaView_setup.sh')
    sftp.chmod('docker_sims/setup_aws.sh', 700)
    sftp.chmod('docker_sims/FullMonteSW_setup.sh', 700)
    sftp.chmod('docker_sims/ParaView_setup.sh', 700)

    # create dummy script to run
    sftp.chdir('docker_sims/')
    file=sftp.file('docker.sh', "w")
    file.write('#!/bin/bash\n')
    file.flush()
    sftp.chmod('docker.sh', 700)

    command = "sudo ~/docker_sims/setup_aws.sh"
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    for line in stdout_line:
        print (line)
    for line in stderr_line:
        print (line)

    command = "sudo ~/docker_sims/FullMonteSW_setup.sh"
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    for line in stdout_line:
        print (line)
    for line in stderr_line:
        print (line)

    command = "sudo ~/docker_sims/ParaView_setup.sh"
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    for line in stdout_line:
        print (line)
    for line in stderr_line:
        print (line)
    
    # alias = 'manual'
    conn = create_connection()
    conn.ensure_connection()
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    running_process.running = False
    running_process.save()
    conn.close()
    print('finished')
    client.close()
    sys.stdout.flush()

# AWS setup progress page
def AWSsetup(request):
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    pid = running_process.pid
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)
    if running_process.running:
        
        print("get current progress")
        sys.stdout.flush()
        stdin, stdout, stderr = client.exec_command('head -1 ~/setup.log')
        stdout_line = stdout.readlines()
        progress = ''
        if len(stdout_line) > 0:
            progress = stdout_line[0].split()[0]
        else:
            progress = '0.00'
        
        client.close()
        print("set up progress: " + progress)
        print("end current progress")
        sys.stdout.flush()
        progress = (float(progress) * 7.5)
        start_time = running_process.start_time
        current_time = datetime.now(timezone.utc)
        time_diff = current_time - start_time
        running_time = str(time_diff)
        running_time = running_time.split('.')[0]
        return render(request, "AWSsetup.html", {'progress':progress, 'time':running_time})
    else:
        stdin, stdout, stderr = client.exec_command('rm -rf ~/setup.log')
        client.close()
        return render(request, "aws_setup_complete.html")
    
# parse lines in file
def handle_uploaded_file(f):
    for line in f:
        print (line)

# execute FullMonte simulation
def exec_simulate(request, channel, command):
    
    print("start running " + command)
    sys.stdout.flush()
    channel.exec_command(command)
    while True:
        if channel.exit_status_ready():
            break
        rl, wl, xl = select.select([channel],[],[],0.0)
        if len(rl) > 0:
            print(channel.recv(1024))
            sys.stdout.flush()
    print("finish running")
    sys.stdout.flush()
    return  HttpResponseRedirect('/application/simulation_fail')

# simulation progress page
def running(request):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)

    stdin, stdout, stderr = client.exec_command('sudo sed -e "s/\\r/\\n/g" ~/sim_run.log > ~/cleaned.log')
    stdin, stdout, stderr = client.exec_command('sudo tail -1 ~/cleaned.log')
    stdout_word = stdout.readlines()
    progress = ''
    if len(stdout_word) > 0:
        # print(stdout_word[-1])
        # sys.stdout.flush()
        if stdout_word[-1].split()[0] == "Progress":
            progress = stdout_word[-1].split()[-1]
    if progress == '':
        if request.session['started'] == "false":
            progress = '0.00%'
        else:
            progress = '100.00%'

        print("got progres: "+progress)
        sys.stdout.flush()
    else:
        request.session['started'] = "true"
        print("got progres: "+progress)
        sys.stdout.flush()
    progress = progress[:-2]
    
    start_time = datetime.strptime(request.session['start_time'], '%Y-%m-%d %H:%M:%S.%f%z')
    current_time = datetime.now(timezone.utc)
    time_diff = current_time - start_time
    running_time = str(time_diff)
    running_time = running_time.split('.')[0]
    print("time is : ", running_time)
    sys.stdout.flush()

    stdin, stdout, stderr = client.exec_command('tail -1 ~/cleaned.log')
    stdout_line = stdout.readlines()
    status = ""
    if len(stdout_line) > 0:
        status = stdout_line[0]
        status = "".join(status.split())
    
    print("status:",status)
    sys.stdout.flush()
    client.close()
    if status == "[info]Simulationrunfinished":
        print("tclsh finish")
        sys.stdout.flush()
        return HttpResponseRedirect('/application/simulation_finish')
    else:
        print("tclsh not finished")
        sys.stdout.flush()
        return render(request, "running.html", {'time':running_time, 'progress':progress})

    # stdin, stdout, stderr = client.exec_command('ps -ef | grep tclsh |awk \'{print $2}\' | head -n1')
    # stdout_line = stdout.readlines()
    # pid = ''
    # pid = stdout_line[0]
    # # for line in stdout_line:
    # #     print (line)
    # #     pid = line
    # print("pid of tclsh is " + pid)
    # sys.stdout.flush()
    # if not pid:
    #     return render(request, "simulation_fail.html")
    # # request.session['pid'] = pid
    # stdin, stdout, stderr = client.exec_command('ps -p '+ pid)
    # stdout_line = stdout.readlines()
    # count =0
    # client.close()
    # for line in stdout_line:
    #     print (line)
    #     count+= 1
    #     sys.stdout.flush()
    
    # if count == 1:
    #     print("tclsh finish")
    #     sys.stdout.flush()
    #     return HttpResponseRedirect('/application/simulation_finish')
    
    # else:
    #     time = stdout_line[1].split()[2]
    #     print("tclsh not finished")
    #     sys.stdout.flush()
    #     return render(request, "running.html", {'time':time, 'progress':progress})


# page for failed simulation
def simulation_fail(request):
    return render(request, "simulation_fail.html")

# page for successfully finished simulation
def simulation_finish(request):
    # save output mesh file info
    outputMeshFile = tclInput.objects.filter(user = request.user).latest('id')
    outputMeshFileName = outputMeshFile.meshFile.name
    request.session['outputMesh'] = outputMeshFileName[:-4] + ".out.vtk"

    # display simulation outputs
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)

    ftp = client.open_sftp()
    # ftp.chdir('docker_sims/')
    file=ftp.file('sim_run.log', "r")
    output = file.read().decode()
    html_string=''
    # add <p> to output string since html does not support '\n'
    for e in output.splitlines():
        if len(e.split()) > 0  and  e.split()[0] != "Progress":
            html_string += e + '<br />'
    print(output)
    sys.stdout.flush()
    stdin, stdout, stderr = client.exec_command('sudo rm -f ~/cleaned.log')
    ftp.close()
    client.close()

    connections.close_all()
    p = Process(target=populate_simulation_history, args=(request, ))
    p.start()
    # populate_simulation_history(request)

    return render(request, "simulation_finish.html", {'output':html_string})

def populate_simulation_history(request):
    conn = create_connection()
    conn.ensure_connection()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)

    ftp = client.open_sftp()
    # store output files to S3, and populate simulation history
    history = simulationHistory()
    history.simulation_type = 'Fullmonte Simulation'
    history.user = request.user
    mesh = tclInput.objects.filter(user = request.user).latest('id')
    history.mesh_file_path = mesh.meshFile
    history.tcl_script_path = tclScript.objects.filter(user = request.user).latest('id').script

    mesh_vtk_name = mesh.meshFile.name
    mesh_name = mesh_vtk_name[:-4]
    tcl_name = mesh_name + '.tcl'
    output_vtk_name = mesh_name + '.out.vtk'
    output_txt_name = mesh_name + '.phi_v.txt'

    output_vtk_file = ftp.file('docker_sims/' + output_vtk_name)
    # default_storage.save(output_vtk_name, output_vtk_file)
    output_txt_file = ftp.file('docker_sims/' + output_txt_name)
    history.output_vtk_path.save(output_vtk_name, output_vtk_file)
    history.output_txt_path.save(output_txt_name, output_txt_file)
    # default_storage.save(output_txt_name, output_txt_file)
    
    ftp.close()
    client.close()

    '''
    history.tcl_script_path = tcl_name
    history.mesh_file_path = mesh_vtk_name
    history.output_vtk_path = output_vtk_name
    history.output_txt_path = output_txt_name
    '''
    # TODO: populate dvh path
    # history.output_dvh_path = ''
    history.save()

    conn.close()

def simulation_history(request):
    history = simulationHistory.objects.filter(user=request.user)
    return render(request, "simulation_history.html", {'history':history})
