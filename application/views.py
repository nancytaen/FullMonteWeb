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
from pytz import timezone as tz
# Extremely hacky fix for VTK not importing correctly on Heroku
try:
    from shutil import copyfile
    initSrc = "./application/scripts/__init__.py"
    initDst = ".heroku/python/lib/python3.7/site-packages/vtk/__init__.py"
    copyfile(initSrc, initDst)

except OSError:
    pass

from .visualizerDVH import dose_volume_histogram as dvh
from .visualizerDVH import pdt_dose_volume_histogram as pdvh
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
from multiprocessing import Process, Event
import threading
import select
import re
# import scipy.io as sio
import os
import boto3
# from django.template import loader
#send_mail('Subject here', 'Here is the message.', settings.EMAIL_HOST_USER,
 #        ['to@example.com'], fail_silently=False)

# Create your views here.
class BaseFileDownloadView(DetailView):
    def get(self, request, *args, **kwargs):
        filename=self.kwargs.get('filename', None)
        originalfilename=self.kwargs.get('originalfilename', None)
        if filename is None:
            raise ValueError("Found empty filename")
        
        try:
            session=boto3.session.Session(region_name='us-east-2')
            conn=session.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, \
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY, \
                config=boto3.session.Config(signature_version='s3v4'))
            response=conn.generate_presigned_url('get_object', Params= \
                {'Bucket':'fullmontesuite-storage', 'Key':'media/public/'+filename}, ExpiresIn=600)
            # print(response)
        except:
            return HttpResponse("The file you are requesting does not exist on the server.")

        return HttpResponseRedirect(response)

        # try:
        #     some_file = default_storage.open(filename)
        # except:
            
        # response = FileResponse(some_file)
        # # https://docs.djangoproject.com/en/1.11/howto/outputting-csv/#streaming-large-csv-files
        # if originalfilename is not None:
        #     response['Content-Disposition'] = 'attachment; filename="%s"'%originalfilename
        # else:
        #     response['Content-Disposition'] = 'attachment; filename="%s"'%filename
        # return response

class fileDownloadView(BaseFileDownloadView):
    pass

def transfer_output_file(request, filepath):
    print(">>>>>>>>>>> in transfer")
    filename = filepath.rsplit('/', 1)[-1]
    local_root = os.path.dirname(__file__) + "/temp/" + request.user.username
    local_path = local_root + "/" + filename

    print(">>>>>>>>>>> connecting to client")
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='simulation_finish')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')
    print(">>>>>>>>>>> connected to client")
    paramiko.sftp_file.SFTPFile.MAX_REQUEST_SIZE = pow(2, 22) # 4MB per chunk
    ftp = client.open_sftp()
    try:
        # add user's username as subir
        print(">>>>>>>>>>> creating local directory")
        if os.path.exists(local_root):
            for filename in os.listdir(local_root):
                file_path = os.path.join(local_root, filename)
                os.remove(file_path)
        else:
            os.makedirs(local_root)
        remote_path = 'docker_sims/'+filepath
        print(">>>>>>>>>>> transfering file in chunks")
        ftp.get(remote_path, local_path)
        print(">>>>>>>>>>> done transfering file in chunks")
        # update process status
        conn = DbConnection()
        running_process = processRunning.objects.filter(user = request.user).latest('id')
        running_process.running = False
        running_process.save()
    finally:
        ftp.close()
        client.close()
        conn.close()
        print ('>>> destroyed connection from remote server in dose_volume_histogram.')
    print("done preparing for download")
    sys.stdout.flush()

def ec2fileDownloadView(request, filepath):
    local_root = os.path.dirname(__file__) + "/temp/" + request.user.username
    if os.path.exists(local_root):
        for filename in os.listdir(local_root):
            file_path = os.path.join(local_root, filename)
            os.remove(file_path)

    if filepath is None:
        raise ValueError("Found empty filepath")

    # Upload file from EC2 to website server
    request.session['ec2_file_path'] = filepath

    print('Transfering output file from EC2')
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    for child in children:
        print('Child pid is {}'.format(child.pid))
    connections.close_all()
    p = Process(target=transfer_output_file, args=(request, filepath, ))
    p.start()
    current_process = psutil.Process()
    children = current_process.children(recursive=True)

    form = processRunning()
    form.user=request.user

    for child in children:
        form.pid = child.pid
        form.running = True
        print('Child pid is {}'.format(child.pid))

    conn = DbConnection()
    form.save()
    sys.stdout.flush()
    return HttpResponseRedirect('/application/preparing_download')

def preparing_download(request):
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    if running_process.running:
        start_time = running_process.start_time
        current_time = datetime.now(timezone.utc)
        time_diff = current_time - start_time
        running_time = str(time_diff)
        running_time = running_time.split('.')[0]
        return render(request, "preparing_download.html", {'time':running_time})
    else:
        filepath = request.session['ec2_file_path']
        filename = filepath.rsplit('/', 1)[-1]
        local_root = os.path.dirname(__file__) + "/temp/" + request.user.username
        local_path = local_root + "/" + filename

        # Open the file for reading content
        if os.path.exists(local_path):
            path = open(local_path, 'r')
            # Set the return value of the HttpResponse
            response = HttpResponse(path)
            # Set the HTTP header for sending to browser
            response['Content-Disposition'] = "attachment; filename=%s" % filename
            # Return the response value
            os.remove(local_path)
            os.rmdir(local_root)
            return response
        else:
            return HttpResponseRedirect('/application/simulation_finish')

# Object finalizer implementation for safe paramiko client connection & destruction
# https://extsoft.pro/safely-destroying-connections-in-python/
class SshConnection:
    """ The class is an adapter of a **paramiko.SSHClient**. """
    
    def __init__(self, hostname, privkey, id=''):
        self._id = id
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print ('>>> connecting to remote server in ' + self._id + '...')
        self._client.connect(hostname=hostname, username='ubuntu', pkey=privkey, timeout=10)
        print ('>>> connected to remote server in ' + self._id + '.')
    
    def __del__(self):
        """ Called when the instance is about to be destroyed. 
                
        The connection has to be closed here.
        """
        if self._client:
            self._client.close()
            print ('>>> destroyed connection from remote server in ' + self._id + '.')

    def close(self):
        """ volunteerily close the connection"""
        if self._client:
            self._client.close()
            print ('>>> disconnected from remote server in ' + self._id + '.')

    def open_sftp(self):
        return self._client.open_sftp()

    def exec_command(self, command):
        return self._client.exec_command(command)

# Object finalizer implementation for safe connection & destruction to database
# https://stackoverflow.com/questions/56733112/how-to-create-new-database-connection-in-django
class DbConnection:
    """ The class is an adapter of a **paramiko.SSHClient**. """
    
    def __init__(self, alias=DEFAULT_DB_ALIAS):
        connections.ensure_defaults(alias)
        connections.prepare_test_settings(alias)
        self._db = connections.databases[alias]
        self._backend = load_backend(self._db['ENGINE'])
        self._conn = self._backend.DatabaseWrapper(self._db, alias)
        self._conn.ensure_connection()
    
    def __del__(self):
        """ Called when the instance is about to be destroyed. 
                
        The connection has to be closed here.
        """
        if self._conn:
            self._conn.close()

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
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    # Check if EC2 instance is set up in the current session
    try:
        dns = request.session['DNS']
        text_obj = request.session['text_obj']
        tcpPort = request.session['tcpPort']
    except:
        messages.error(request, 'Error - please connect to an AWS remote server before trying to simulate')
        return HttpResponseRedirect('/application/aws')
    #print(22222)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        #print(11111)
        print(request.POST)
        #print(request.FILES)
        sys.stdout.flush()
        form = tclInputForm(data=request.POST, files=request.FILES)
        formset3 = regionIDSet(request.POST)

        # check whether it's valid:
        if form.is_valid() and formset3.is_valid():
            print(form.cleaned_data)
            sys.stdout.flush()
            request.session['ec2_file_paths'] = []
            request.session['scoredVolumeRegionID'] = []
            if request.POST['selected_existing_meshes'] != "":
                print("This is 1")
                # selected a mesh from database
                mesh_from_database = meshFiles.objects.filter(id=request.POST['selected_existing_meshes'])[0]

                obj = form.save(commit = False)
                obj.meshFile = mesh_from_database.meshFile
                obj.originalMeshFileName = mesh_from_database.originalMeshFileName
                obj.meshFileID = mesh_from_database
                obj.user = request.user
                obj.save()
            else:
                print("This is 2")
                # uploaded a new mesh
                # process cleaned data from formsets
                obj = form.save(commit = False)
                obj.user = request.user
                obj.originalMeshFileName = obj.meshFile.name
                obj.save()
                print(obj)
                sys.stdout.flush()

                # create entry for the newly uploaded meshfile
                new_mesh_entry = meshFiles()
                new_mesh_entry.meshFile = obj.meshFile
                new_mesh_entry.originalMeshFileName = obj.originalMeshFileName
                new_mesh_entry.user = request.user
                new_mesh_entry.save()

                # update meshfile id
                obj.meshFileID = new_mesh_entry
                obj.save()

            print(form.cleaned_data['kernelType'])
            selected_abosrbed = 'Absorbed' in form.cleaned_data['kernelType']
            selected_leaving = 'Leaving' in form.cleaned_data['kernelType']
            selected_internal = 'Internal' in form.cleaned_data['kernelType']

            using_gpu = request.session['GPU_instance']
            if selected_internal:
                if using_gpu:
                    request.session['kernelType'] = 'TetraCUDAInternalKernel'
                else:
                    request.session['kernelType'] = 'TetraInternalKernel'
            elif selected_leaving and selected_abosrbed:
                if using_gpu:
                    request.session['kernelType'] = 'TetraCUDASVKernel'
                else:
                    request.session['kernelType'] = 'TetraSVKernel'
            elif selected_leaving:
                if using_gpu:
                    request.session['kernelType'] = 'TetraCUDASurfaceKernel'
                else:
                    request.session['kernelType'] = 'TetraSurfaceKernel'
            elif selected_abosrbed:
                if using_gpu:
                    request.session['kernelType'] = 'TetraCUDAVolumeKernel'
                else:
                    request.session['kernelType'] = 'TetraVolumeKernel'
            else:
                # this should not happen, but just in case
                if using_gpu:
                    request.session['kernelType'] = 'TetraCUDAInternalKernel'
                else:
                    request.session['kernelType'] = 'TetraInternalKernel'

            sys.stdout.flush()
            request.session['meshUnit'] = form.cleaned_data['meshUnit']
            for regionID in formset3:
                print(regionID.cleaned_data)
                request.session['scoredVolumeRegionID'].append(regionID.cleaned_data['scoredVolumeRegionID'])
            sys.stdout.flush()
            request.session['packetCount'] = form.cleaned_data['packetCount']
            request.session['totalEnergy'] = form.cleaned_data['totalEnergy']
            request.session['energyUnit'] = form.cleaned_data['energyUnit']

            if request.POST.get("overwrite_on_ec2") == "True":
                request.session['overwrite_on_ec2'] = True
            else:
                request.session['overwrite_on_ec2'] = False

            # generate empty TCL template
            mesh = tclInput.objects.filter(user = request.user).latest('id')
            energy  = request.session['totalEnergy']
            meshUnit = request.session['meshUnit']
            energyUnit = request.session['energyUnit']
            script_path = emptyTclTemplateGenerator(request.session, mesh, meshUnit, energy, energyUnit, request.user)

            return HttpResponseRedirect('/application/simulator_material')

    # If this is a GET (or any other method) create the default form.
    else:
        form = tclInputForm(CUDA=request.session['GPU_instance'])
        formset3 = regionIDSet(request.GET or None)

    uploaded_meshes = meshFiles.objects.filter(user=request.user)

    context = {
        'form': form,
        'formset3': formset3,
        'aws_path': request.session['DNS'],
        'port': request.session['tcpPort'],
        'uploaded_meshes': uploaded_meshes,
    }

    return render(request, "simulator.html", context)

# FullMonte Simulator material page
def fmSimulatorMaterial(request):
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    # Info about the generated TCL
    generated_tcl = tclScript.objects.filter(user = request.user).latest('id')

    # Form for user-uploaded TCL
    class Optional_Tcl(forms.Form):
        tcl_file = forms.FileField(required=False)
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        conn = DbConnection()
        text_obj = request.session['text_obj']
        private_key_file = io.StringIO(text_obj)
        privkey = paramiko.RSAKey.from_private_key(private_key_file)
        try:
            client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='fmSimulatorMaterial')
        except:
            sys.stdout.flush()
            messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
            return HttpResponseRedirect('/application/aws')

        # Skip rest of setup if user uploaded their own TCL script
        if '_skip' in request.POST:
            request.session['material'] = []
            request.session['region_name'] = [] # for visualization legend
            request.session['scatteringCoeff'] = []
            request.session['absorptionCoeff'] = []
            request.session['refractiveIndex'] = []
            request.session['anisotropy'] = []

            # get power
            indicator = b' energyPowerValue '
            tcl_file = request.FILES['tcl_file']
            for line in tcl_file:
                if indicator in line:
                    request.session['totalEnergy'] = float(line.split()[2])
                    break

            # file uploaded and "Submit and Run" button clicked
            form = Optional_Tcl(request.POST, request.FILES)
            default_storage.delete(request.FILES['tcl_file'].name)
            default_storage.save(request.FILES['tcl_file'].name, request.FILES['tcl_file']) # save new TCL script to S3

            client.exec_command('> ~/sim_run.log')
            sys.stdout.flush()
            client.close()
            connections.close_all()

            # transfer all necessary files to run simulation
            p = Process(target=transfer_files_and_run_simulation, args=(request, ))
            p.start()
            
            # redirect to run simulation
            request.session['start_time'] = str(datetime.now(timezone.utc))
            request.session['started'] = "false"
            request.session['peak_mem_usage'] = 0
            request.session['peak_mem_usage_unit'] = 'GB'
            return HttpResponseRedirect('/application/running')

        # Get all entries from materials formset and check whether it's valid
        else:
            client.close()
            connections.close_all()
            # transfer all necessary files to run simulation
            p = Process(target=transfer_files_for_input_mesh_visualization, args=(request, ))
            p.start()
            formset1 = materialSetSet(request.POST)

            if formset1.is_valid():
                # process cleaned data from formsets

                request.session['material'] = []
                request.session['region_name'] = [] # for visualization legend
                request.session['scatteringCoeff'] = []
                request.session['absorptionCoeff'] = []
                request.session['refractiveIndex'] = []
                request.session['anisotropy'] = []

                for form in formset1:
                    #print(form.cleaned_data)
                    request.session['material'].append(form.cleaned_data['material'])
                    request.session['region_name'].append(form.cleaned_data['material'])  # for visualization legend
                    request.session['scatteringCoeff'].append(form.cleaned_data['scatteringCoeff'])
                    request.session['absorptionCoeff'].append(form.cleaned_data['absorptionCoeff'])
                    request.session['refractiveIndex'].append(form.cleaned_data['refractiveIndex'])
                    request.session['anisotropy'].append(form.cleaned_data['anisotropy'])

                return HttpResponseRedirect('/application/simulator_source')

    # If this is a GET (or any other method) create the default form.
    else:
        formset1 = materialSetSet(request.GET or None)
        tcl_form = Optional_Tcl()

    context = {
        'formset1': formset1,
        'unit': request.session['meshUnit'],
        'tcl_script_name': generated_tcl.script.name,
        'tcl_form': tcl_form,
    }

    return render(request, "simulator_material.html", context)

# ajax requests
def ajaxrequests_view(request):
    ind = request.POST.get('ind', None)
    if(ind):
        ind = int(ind)
        get_data = Material.objects.filter(id=ind)
        # do conversion if units do not match (temporory, do not save model after conversion)
        for data in get_data:
            if data.material_unit != request.session['meshUnit']:
                if request.session['meshUnit'] == 'cm': # convert mm to cm
                    data.scattering_coeff *= 10
                    data.absorption_coeff *= 10
                else: # convert cm to mm
                    data.scattering_coeff /= 10
                    data.absorption_coeff /= 10

        ser_data = serializers.serialize("json", get_data)
        return HttpResponse(ser_data, content_type="application/json")
    else:
        return HttpResponse(None, content_type="application/json")

# ajax requests to ransfer mesh file when button is clicked
def transfer_files_for_input_mesh_visualization(request):
    # transfer input mesh to Ec2 instance
    conn = DbConnection()
    meshFilePath = tclInput.objects.filter(user = request.user).latest('id').meshFile.name
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='transfer_files_for_input_mesh_visualization')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')
    
    ftp = client.open_sftp()
    try:
        ftp.chdir('docker_sims/')
        # transfer mesh in chunks to save memory
        need_transfer = True
        if not request.session['overwrite_on_ec2']:
            need_transfer = False
            try:
                ftp.stat(meshFilePath)
            except:
                need_transfer = True

        if not need_transfer:
            print("skipped mesh file transfer")
            sys.stdout.flush()
        
        if need_transfer:
            print("starting mesh file transfer")
            with ftp.open('./'+meshFilePath, 'wb') as ftp_file:
                with default_storage.open(meshFilePath) as mesh_file:
                    for piece in mesh_file.chunks(chunk_size=32*1024*1024):
                        ftp_file.write(piece)
            print("finished mesh file transfer")
            sys.stdout.flush()
    finally:
        ftp.close()
        client.close()

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
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    # visualize input mesh
    inputMeshFileName = tclInput.objects.filter(user = request.user).latest('id').meshFile.name
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)

    # generate ParaView Visualization URL
    # e.g. http://ec2-35-183-12-167.ca-central-1.compute.amazonaws.com:8080/
    dns = request.session['DNS']
    tcpPort = request.session['tcpPort']
    visURL = "http://" + dns + ":" + tcpPort + "/"
    # render 3D visualizer
    p = Process(target=visualizer, args=(inputMeshFileName, True, dns, tcpPort, text_obj, ))
    p.start()

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        formset2 = lightSourceSet(request.POST)
        print(request.POST)
        sys.stdout.flush()


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
            request.session['volumeRegion'] = []
            request.session['emitHemiSphere'] = []
            request.session['hemiSphereEmitDistribution'] = []
            request.session['numericalAperture'] = []
            request.session['checkDirection'] = []
            request.session['xDir1'] = []
            request.session['yDir1'] = []
            request.session['zDir1'] = []
            request.session['xPos0'] = []
            request.session['yPos0'] = []
            request.session['zPos0'] = []
            request.session['xPos1'] = []
            request.session['yPos1'] = []
            request.session['zPos1'] = []
            request.session['emitVolume'] = []

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
                request.session['volumeRegion'].append(form.cleaned_data['volumeRegion'])
                request.session['emitHemiSphere'].append(form.cleaned_data['emitHemiSphere'])
                request.session['hemiSphereEmitDistribution'].append(form.cleaned_data['hemiSphereEmitDistribution'])
                request.session['numericalAperture'].append(form.cleaned_data['numericalAperture'])
                request.session['checkDirection'].append(form.cleaned_data['checkDirection'])
                request.session['xDir1'].append(form.cleaned_data['xDir1'])
                request.session['yDir1'].append(form.cleaned_data['yDir1'])
                request.session['zDir1'].append(form.cleaned_data['zDir1'])
                request.session['xPos0'].append(form.cleaned_data['xPos0'])
                request.session['yPos0'].append(form.cleaned_data['yPos0'])
                request.session['zPos0'].append(form.cleaned_data['zPos0'])
                request.session['xPos1'].append(form.cleaned_data['xPos1'])
                request.session['yPos1'].append(form.cleaned_data['yPos1'])
                request.session['zPos1'].append(form.cleaned_data['zPos1'])
                request.session['emitVolume'].append(form.cleaned_data['emitVolume'])
            
            mesh = tclInput.objects.filter(user = request.user).latest('id')
            energy  = request.session['totalEnergy']
            meshUnit = request.session['meshUnit']
            energyUnit = request.session['energyUnit']

            script_path = tclGenerator(request.session, mesh, meshUnit, energy, energyUnit, request.user)
            return HttpResponseRedirect('/application/simulation_confirmation')

    # If this is a GET (or any other method) create the default form.
    else:
        formset2 = lightSourceSet(request.GET or None)

    context = {
        'formset2': formset2,
        'unit': request.session['meshUnit'],
        'visURL': visURL,
    }

    return render(request, "simulator_source.html", context)

# FullMonte Simulator input confirmation page
def simulation_confirmation(request):
    # Info about the generated TCL and mesh file
    generated_tcl = tclScript.objects.filter(user = request.user).latest('id')
    meshFilePath = tclInput.objects.filter(user = request.user).latest('id').meshFile.name

    # Form for user-uploaded TCL
    class Optional_Tcl(forms.Form):
        tcl_file = forms.FileField(required=False)
    
    if request.method == 'POST':
        # Check if user uploaded their own TCL script
        form = Optional_Tcl(request.POST, request.FILES)
        if not request.POST.__contains__('tcl_file'):
            # there is a file uploaded
            default_storage.delete(request.FILES['tcl_file'].name)
            default_storage.save(request.FILES['tcl_file'].name, request.FILES['tcl_file']) # replace the TCL file in S3

        text_obj = request.session['text_obj']
        private_key_file = io.StringIO(text_obj)
        privkey = paramiko.RSAKey.from_private_key(private_key_file)
        try:
            client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='simulation_confirmation')
        except:
            sys.stdout.flush()
            messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
            return HttpResponseRedirect('/application/aws')
        client.exec_command('> ~/sim_run.log')
        sys.stdout.flush()
        client.close()
        connections.close_all()

        # Transfer all neccessary files for simulation
        p = Process(target=transfer_files_and_run_simulation, args=(request, ))
        p.start()
        
        # redirect to run simulation
        request.session['start_time'] = str(datetime.now(timezone.utc))
        request.session['started'] = "false"
        request.session['peak_mem_usage'] = 0
        request.session['peak_mem_usage_unit'] = 'GB'
        return HttpResponseRedirect('/application/running')
    
    # Info to display on confirmation page
    class Material_Class:
        pass
    class Light_Source_Class:
        pass

    materials = []
    for i in range(len(request.session['material'])):
        temp = Material_Class()
        temp.layer = i
        temp.material = request.session['material'][i]
        temp.scatteringCoeff = request.session['scatteringCoeff'][i]
        temp.absorptionCoeff = request.session['absorptionCoeff'][i]
        temp.refractiveIndex = request.session['refractiveIndex'][i]
        temp.anisotropy = request.session['anisotropy'][i]
        materials.append(temp)

    light_sources = []
    for i in range(len(request.session['sourceType'])):
        temp = Light_Source_Class()
        temp.source = i + 1
        temp.sourceType = request.session['sourceType'][i]
        temp.xPos = request.session['xPos'][i]
        temp.yPos = request.session['yPos'][i]
        temp.zPos = request.session['zPos'][i]
        temp.xDir = request.session['xDir'][i]
        temp.yDir = request.session['yDir'][i]
        temp.zDir = request.session['zDir'][i]
        temp.vElement = request.session['vElement'][i]
        temp.rad = request.session['rad'][i]
        temp.power = request.session['power'][i]
        temp.volumeRegion = request.session['volumeRegion'][i]
        temp.emitHemiSphere = request.session['emitHemiSphere'][i]
        temp.hemiSphereEmitDistribution = request.session['hemiSphereEmitDistribution'][i]
        temp.numericalAperture = request.session['numericalAperture'][i]
        temp.checkDirection = request.session['checkDirection'][i]
        temp.xDir1 = request.session['xDir1'][i]
        temp.yDir1 = request.session['yDir1'][i]
        temp.zDir1 = request.session['zDir1'][i]
        temp.xPos0 = request.session['xPos0'][i]
        temp.yPos0 = request.session['yPos0'][i]
        temp.zPos0 = request.session['zPos0'][i]
        temp.xPos1 = request.session['xPos1'][i]
        temp.yPos1 = request.session['yPos1'][i]
        temp.zPos1 = request.session['zPos1'][i]
        temp.emitVolume = request.session['emitVolume'][i]
        light_sources.append(temp)
    
    tcl_form = Optional_Tcl()

    context = {
        'mesh_name': meshFilePath, 
        'materials': materials,
        'light_sources': light_sources,
        'tcl_script_name': generated_tcl.script.name,
        'tcl_form': tcl_form,
        'unit': request.session['meshUnit'],
    }

    return render(request, 'simulation_confirmation.html', context)

def transfer_files_and_run_simulation(request):
    conn = DbConnection()
    meshFilePath = tclInput.objects.filter(user = request.user).latest('id').meshFile.name
    generated_tcl = tclScript.objects.filter(user = request.user).latest('id')
    tcl_file = default_storage.open(generated_tcl.script.name)
    
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='transfer_files_and_run_simulation')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')
    
    # delete all old files
    stdin, stdout, stderr = client.exec_command('cd ~/docker_sims; find . ! -name "*.sh" -exec rm -r {} \;')
    sys.stdout.flush()

    # check if files need to be transfered
    ftp = client.open_sftp()
    try:
        ftp.chdir('docker_sims/')
        file=ftp.file('docker.sh', "w")
        file.write('#!/bin/bash\ncd sims/\ntclmonte.sh ./'+generated_tcl.script.name)
        file.flush()
        ftp.chmod('docker.sh', 700)

        # transfer mesh in chunks to save memory
        need_transfer = True
        if not request.session['overwrite_on_ec2']:
            need_transfer = False
            try:
                ftp.stat(meshFilePath)
            except:
                need_transfer = True

        if not need_transfer:
            print("skipped mesh file transfer")
            sys.stdout.flush()
        
        if need_transfer:
            print("starting mesh file transfer")
            session=boto3.session.Session(region_name='us-east-2')
            conn=session.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, \
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY, \
                config=boto3.session.Config(signature_version='s3v4'))
            response=conn.generate_presigned_url('get_object', Params= \
                {'Bucket':'fullmontesuite-storage', 'Key':'media/public/'+meshFilePath}, ExpiresIn=600)

            download_command = "wget \"" +response + "\" -O ~/docker_sims/" + meshFilePath
            stdin, stdout, stderr = client.exec_command(download_command)
            print("finished mesh file transfer")
            sys.stdout.flush()

        ftp.putfo(tcl_file, './'+generated_tcl.script.name)
    finally:
        ftp.close()

    # command to remove previously created temporary files, just in case
    cd_cmd = 'cd ~/docker_sims;'
    rm_cmd = 'rm -rf files_before.txt files_after.txt files_diff.txt single_vtk_file.txt single_txt_file.txt;'
    
    # command to identify files before simulation
    find_cmd = 'find * ! -name "files_before.txt" ! -name "files_after.txt" ! -name "*.sh" ! -name "*.tcl" ! -name "*.csv" ! -name "*.png" -type f >> files_before.txt;'
    
    # command to run simulation
    if request.session['GPU_instance']:
        # add an argument to add nvidia runtime for gpu
        run_cmd = "sudo ~/docker_sims/FullMonteSW_setup.sh 1 > ~/sim_run.log 2>&1" 
    else:
        run_cmd = "sudo ~/docker_sims/FullMonteSW_setup.sh > ~/sim_run.log 2>&1"
    
    # command to execute commands in order
    print("Commands executed:", cd_cmd + rm_cmd + find_cmd + run_cmd)
    stdin, stdout, stderr = client.exec_command(cd_cmd + rm_cmd + find_cmd + run_cmd)
    client.close()
    sys.stdout.flush()

# Output mesh upload page
def visualization_mesh_upload(request):
    if request.method == 'POST':
        print(request)
        form = visualizeMeshForm(request.POST, request.FILES)
        if form.is_valid():
            print(form.cleaned_data)
            # get mesh file from form
            obj = form.save(commit = False)
            obj.user = request.user
            obj.save()
            uploadedOutputMeshFile = visualizeMesh.objects.filter(user = request.user).latest('id')
            outputMeshFileName = uploadedOutputMeshFile.outputMeshFile.name
            outputMeshFile = default_storage.open(outputMeshFileName)
            print(outputMeshFileName)

            # copy mesh into remote server
            text_obj = request.session['text_obj']
            private_key_file = io.StringIO(text_obj)
            privkey = paramiko.RSAKey.from_private_key(private_key_file)
            try:
                client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='visualization_mesh_upload')
            except:
                sys.stdout.flush()
                messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
                return HttpResponseRedirect('/application/aws')

            sftp = client.open_sftp()
            try:
                sftp.chdir('docker_sims/')
                sftp.putfo(outputMeshFile, './'+outputMeshFileName)
                # parse out mesh and fluence energy units from mesh
                i = 0
                with sftp.open('./'+outputMeshFileName) as meshFile:
                    for line in meshFile:
                        if i == 1: # look for second line
                            data = line.split()
                            if data[0] == "MeshUnit:":
                                meshUnit = data[1]
                                energyUnit = data[3]
                            else:
                                meshUnit = ""
                                energyUnit = ""
                            break
                        i = i + 1
            finally:
                sftp.close()
            client.close()
            
            # save mesh file info for visualization
            info = meshFileInfo.objects.filter(user = request.user).latest('id')
            info.fileName = outputMeshFileName
            info.dvhFig = "<p>Dose Volume Histogram not yet generated</p>"
            info.powerAndScaling = ""
            info.thresholdFluence = "" # reset for uploaded mesh
            info.save()

            # save units
            if len(energyUnit) > 0 and len(meshUnit) > 0:
                request.session['fluenceEnergyUnit'] = energyUnit + "/" + meshUnit
            else:
                request.session['fluenceEnergyUnit'] = "(unit not provided in mesh file)"

            # set material list to empty because the list is only used for mesh visualizaition from simulation.
            # uploaded mesh files do not have material information provided, so they will not have material names in legend
            request.session['region_name'] = []
            request.session['uploaded_output_mesh'] = True
            return HttpResponseRedirect('/application/visualization')
    else:
        form = visualizeMeshForm(request.GET or None)
    context = {
        'form': form,
    }
    return render(request, "mesh_upload.html", context)

# Threshold fluence upload page
def visualization_threshold_fluence_upload(request):
    if request.method == 'POST':
        print(request)
        form = fmVisThresholdFluenceForm(request.POST, request.FILES)
        if form.is_valid():
            thresholdFluence = ""
            tissuePropertyFile = request.FILES['tissue_property']
            namesFromTissuePropertiesFile = []
            namesFromTissuePropertiesFile.append("Air")
            for line in tissuePropertyFile:
                line = line.decode('ascii')
                print(line)
                columns = line.split(",")
                if len(columns) != 3 or isinstance(columns[1], (float, int)):
                    messages.error(request, 'Error - file format is wrong. Please upload a valid tissue properties file.')
                    return HttpResponseRedirect('/application/threshold_fluence_upload')
                thresholdFluence = thresholdFluence + " " + columns[1]
                namesFromTissuePropertiesFile.append(columns[0])
            print(">>>>>>>>>>>>>>>>", thresholdFluence)
            normalizeOrNot = form.cleaned_data['normalization']
            if normalizeOrNot == 'normalize':
                request.session['normalization'] = True
            else:
                request.session['normalization'] = False
            request.session['cutoffPercentage'] = form.cleaned_data['cutoffPercentage']
            request.session['tumorRegion'] = form.cleaned_data['tumorRegion']
            request.session['v100'] = form.cleaned_data['v100']
            if(len(namesFromTissuePropertiesFile) > len(request.session['region_name'])):
                request.session['region_name'] = namesFromTissuePropertiesFile
            # save threshold fluence info for visualization
            info = meshFileInfo.objects.filter(user = request.user).latest('id')
            info.thresholdFluence = thresholdFluence
            info.save()
            return HttpResponseRedirect('/application/visualization')
    else:
        form = fmVisThresholdFluenceForm(request.GET or None)
    context = {
        'form': form,
    }
    return render(request, "threshold_fluence_upload.html", context)

# FullMonte output Visualization - generate DVH
def fmVisualization(request):
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    # Check if current session has simulation completed/mesh file uploaded
    info = meshFileInfo.objects.filter(user = request.user).latest('id')
    outputMeshFileName = info.fileName
    if len(outputMeshFileName) == 0:
        messages.error(request, 'Error - please run simulation or upload a mesh before trying to visualize')
        return HttpResponseRedirect('/application/mesh_upload')

    # check if current session has threshold fluence provided
    thresholdFluence = info.thresholdFluence
    if len(thresholdFluence) == 0:
        return HttpResponseRedirect('/application/threshold_fluence_upload')

    # check if user is connected to AWS
    try:
        dns = request.session['DNS']
        text_obj = request.session['text_obj']
        tcpPort = request.session['tcpPort']
    except:
        messages.error(request, 'Error - please connect to an AWS remote server before trying to visualize')
        return HttpResponseRedirect('/application/aws')

    # Try to connect to remote server
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='fmVisualization')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    # Check if mesh file and DVH file exist in the remote server
    sftp = client.open_sftp()
    try:
        sftp.stat('docker_sims/'+outputMeshFileName)
        info.remoteFileExists = True
    except:
        info.remoteFileExists = False
    finally:
        sftp.close()
    client.close()

    sys.stdout.flush()
    info.save()

    # file exists for DVH
    # if(dvhTxtFileExists):
    if(info.remoteFileExists):
        # generate DVH
        if info.dvhFig == "<p>Dose Volume Histogram not yet generated</p>":
            print('generating DVH')
            print('before')
            current_process = psutil.Process()
            children = current_process.children(recursive=True)
            for child in children:
                print('Child pid is {}'.format(child.pid))
            connections.close_all()
            meshUnit = request.session['meshUnit']
            energyUnit = request.session['energyUnit']
            materials = request.session['region_name']
            thresholdFluence = info.thresholdFluence
            power = request.session['totalEnergy']
            normalization = request.session['normalization']
            cutoffPercentage = request.session['cutoffPercentage']
            tumorRegion = request.session['tumorRegion']
            v100 = request.session['v100']
            uploaded = request.session['uploaded_output_mesh']
            p = Process(target=dvh, args=(request.user, dns, tcpPort, text_obj, meshUnit, energyUnit, materials, thresholdFluence, power, normalization, cutoffPercentage, tumorRegion, v100, uploaded, ))
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

            conn = DbConnection()
            form.save()
            sys.stdout.flush()
            return HttpResponseRedirect('/application/runningDVH')
        # load saved DVH
        else:
            print('using last saved DVH')
            return HttpResponseRedirect('/application/displayVisualization')
    
    # DVH cannot be generated
    else:
        # info.maxFluence = 0
        info.dvhFig = "<p>Could not generate Dose Volume Histogram</p>"
        info.powerAndScaling = ""
        info.save()
        return HttpResponseRedirect('/application/displayVisualization')


# Running DVH progress page
def runningDVH(request):
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    if running_process.running:
        start_time = running_process.start_time
        current_time = datetime.now(timezone.utc)
        time_diff = current_time - start_time
        running_time = str(time_diff)
        running_time = running_time.split('.')[0]
        return render(request, "waitingDVH.html", {'time':running_time})
    else:
        # save history for dvh data if output mesh comes from simulation
        if (len(request.session['region_name']) > 0):
            info = meshFileInfo.objects.filter(user = request.user).latest('id')
            outputMeshFileName = info.fileName
            history = simulationHistory.objects.filter(user=request.user).latest('id')
            conn = DbConnection()

            text_obj = request.session['text_obj']
            private_key_file = io.StringIO(text_obj)
            privkey = paramiko.RSAKey.from_private_key(private_key_file)
            try:
                client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='runningDVH')
            except:
                sys.stdout.flush()
                messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
                return HttpResponseRedirect('/application/aws')

            ftp = client.open_sftp()
            mesh_name = outputMeshFileName[:-8]
            output_csv_name = mesh_name + '.dvh.csv'
            output_png_name = mesh_name + '.dvh.png'

            try:
                output_csv_file = ftp.file('docker_sims/' + output_csv_name)
                output_png_file = ftp.file('docker_sims/' + output_png_name)
                history.output_dvh_csv_path.save(output_csv_name, output_csv_file)
                history.output_dvh_fig_path.save(output_png_name, output_png_file)
            except:
                print("Cannot save history for DVH data because file does not exist")
            finally:
                ftp.close()
            
            client.close()
            history.save()
        return HttpResponseRedirect('/application/displayVisualization')


# page that loads both the 3D visualization and DVH
def displayVisualization(request):
    info = meshFileInfo.objects.filter(user = request.user).latest('id')
    outputMeshFileName = info.fileName
    fileExists = info.remoteFileExists
    dvhFig = info.dvhFig
    powerAndScaling = info.powerAndScaling
    thresholdFluence = info.thresholdFluence
    # maxFluence = round(info.maxFluence, 2)

    # generate ParaView Visualization URL
    # e.g. http://ec2-35-183-12-167.ca-central-1.compute.amazonaws.com:8080/
    dns = request.session['DNS']
    tcpPort = request.session['tcpPort']
    visURL = "http://" + dns + ":" + tcpPort + "/"

    # render 3D visualizer
    text_obj = request.session['text_obj']
    p = Process(target=visualizer, args=(outputMeshFileName, fileExists, dns, tcpPort, text_obj, ))
    p.start()

    # get message
    if(fileExists):
        msg = "Using output mesh \"" + outputMeshFileName + "\" from the last simulation or upload."
    else:
        msg = "Mesh \"" + outputMeshFileName + "\" from the last simulation or upload was not found. Perhaps it was deleted. \
                Please also note that the DVH generator looks for a default mesh name from simulation, so if you modified the output file paths \
                in the TCL script, the generator would not find the output mesh. However, you can work around by downloading the mesh file(s) and uploading \
                them back to this page to view their DVH. You can also still use the 3D visualizer: if the default file name is not found, your AWS instance's \
                Root folder will be loaded to the ParaView application, and you can look for your desired mesh by browsing through the Root folder."
    
    # pass message, DVH figure, and 3D visualizer link to the HTML
    materials = request.session['region_name']
    thresholdFluenceArray = thresholdFluence.split()
    thresholdFluenceArray.insert(0, "0")
    materialToThreshold = {}
    for i in range(1, len(thresholdFluenceArray)):
        if len(materials) == len(thresholdFluenceArray):
            materialToThreshold[materials[i]] = thresholdFluenceArray[i]
        else:
            materialToThreshold["Region" + str(i)] = thresholdFluenceArray[i]
    context = {'message': msg, 'dvhFig': dvhFig, 'powerAndScaling':powerAndScaling, 'visURL': visURL, 'materialToThreshold': materialToThreshold, 'fluenceEnergyUnit': request.session['fluenceEnergyUnit']}
    return render(request, "visualization.html", context)

# page for diplaying info about kernel type
def kernelInfo(request):
    return render(request, "kernel_info.html")

# page for downloading preset values
def downloadPreset(request):    
    # First check if user is logged-in
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
            user.is_active = True
            user.save()
            #username = form.cleaned_data.get('username')
            #raw_password = form.cleaned_data.get('password1')
            #user = authenticate(username=username, password=raw_password)

            # disable activation email for now, until we find a better email server 
            """
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
            """
            login(request, user)
            return render(request, "activation_complete.html")

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
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')
    return render(request, "account.html")

# user account changing passwords page
def change_password(request):
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    # if this is a POST request we need to process the form data
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
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        print(request)
        form = awsFiles(request.POST, request.FILES)
        print(request.POST.get("DNS"))
        print(request.POST.get("GPU_instance"))
        sys.stdout.flush()
        if form.is_valid():
            info = meshFileInfo() # prepare new mesh entry
            info.user = request.user
            info.save()
            print(form.cleaned_data)
            obj = form.save(commit = False)
            obj.user = request.user
            obj.save()
            request.session['DNS'] = form.cleaned_data['DNS']
            request.session['tcpPort'] = str(form.cleaned_data['TCP_port'])
            if request.POST.get("GPU_instance") == "True":
                request.session['GPU_instance'] = True
            else:
                request.session['GPU_instance'] = False
            print(request.session['GPU_instance'])
            sys.stdout.flush()
            # handle_uploaded_file(request.FILES['pemfile'])
            uploadedAWSPemFile = awsFile.objects.filter(user = request.user).latest('id')
            pemfile = uploadedAWSPemFile.pemfile

            private_key_file = io.BytesIO()
            for line in pemfile:
                private_key_file.write(line)
            private_key_file.seek(0)

            byte_str = private_key_file.read()
            text_obj = byte_str.decode('UTF-8')
            private_key_file = io.StringIO(text_obj)
            privkey = paramiko.RSAKey.from_private_key(private_key_file)
            request.session['text_obj'] = text_obj
            try:
                client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='aws')
            except:
                sys.stdout.flush()
                messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
                return HttpResponseRedirect('/application/aws')
            
            sftp = client.open_sftp()
            try:
                need_setup = "false"

                try:
                    sftp.stat('docker_sims/FullMonteSW_setup.sh')
                except IOError:
                    need_setup = "true"

                if request.session['GPU_instance']:
                    try:
                        sftp.stat('docker_sims/CUDA_setup.sh')
                    except IOError:
                        need_setup = "true"
                
                try:
                    sftp.stat('docker_pdt/pdt_space_setup.sh')
                except IOError:
                    need_setup = "true"
            finally:
                sftp.close()
            client.close()
            
            if need_setup == "true":
                # cluster that's not setup            
                print('before')
                current_process = psutil.Process()
                children = current_process.children(recursive=True)
                for child in children:
                    print('Child pid is {}'.format(child.pid))
                connections.close_all()
                p = Process(target=run_aws_setup, args=(request, request.session['GPU_instance'], ))
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
                
                conn = DbConnection()
                form.save()
                sys.stdout.flush()
                
                return HttpResponseRedirect('/application/AWSsetup')
            
            return render(request, "aws_setup_complete.html")
    else:
        form = awsFiles()

    context = {
        'form': form,
    }
    return render(request, "aws.html", context)

# run AWS setup on the EC2 instance specified by user
def run_aws_setup(request, GPU_instance):
    time.sleep(3)
    text_obj = request.session['text_obj']
    # uploadedAWSPemFile = awsFile.objects.filter(user = request.user).latest('id')
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='run_aws_setup')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    dir_path = os.path.dirname(os.path.abspath(__file__))
    #tc file
    source_setup = dir_path + '/scripts/setup_aws.sh'
    source_setup = str(source_setup)

    source_fullmonte = dir_path + '/scripts/FullMonteSW_setup.sh'
    source_fullmonte = str(source_fullmonte)

    source_paraview = dir_path + '/scripts/ParaView_setup.sh'
    source_paraview = str(source_paraview)

    source_pdt_space = dir_path + '/scripts/pdt_space_setup.sh'
    source_pdt_space = str(source_pdt_space)

    source_CUDA = dir_path + '/scripts/CUDA_setup.sh'
    source_CUDA = str(source_CUDA)

    source_license = dir_path + '/license/mosek.lic'
    source_license = str(source_license)

    sftp = client.open_sftp()
    try:
        stdin, stdout, stderr = client.exec_command('mkdir -p docker_sims; mkdir -p docker_pdt')
        exit_status = stdout.channel.recv_exit_status()          # Blocking call
        if exit_status == 0:
            print ("Directories created")
        else:
            print("Error", exit_status)
        sftp.put(source_setup, 'docker_sims/setup_aws.sh')
        sftp.put(source_fullmonte, 'docker_sims/FullMonteSW_setup.sh')
        sftp.put(source_paraview, 'docker_sims/ParaView_setup.sh')
        sftp.put(source_pdt_space, 'docker_pdt/pdt_space_setup.sh')
        if GPU_instance:
            sftp.put(source_CUDA, 'docker_sims/CUDA_setup.sh')
        # sftp.put(source_license, 'docker_pdt/mosek.lic')
        sftp.chmod('docker_sims/setup_aws.sh', 700)
        sftp.chmod('docker_sims/FullMonteSW_setup.sh', 700)
        sftp.chmod('docker_sims/ParaView_setup.sh', 700)
        sftp.chmod('docker_pdt/pdt_space_setup.sh', 700)
        if GPU_instance:
            sftp.chmod('docker_sims/CUDA_setup.sh', 700)

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
        
        #pdt-space
        print('start setup pdt-space')
        file=sftp.file('../docker_pdt/docker.sh', "w")
        file.write('#!/bin/bash\n')
        file.write('echo dockertest')
        file.flush()
        sftp.chmod('../docker_pdt/docker.sh', 700)
    finally:
        sftp.close()

    command = "sudo sh ~/docker_pdt/pdt_space_setup.sh \"ls /usr/local/pdt-space/data\" 0"
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    for line in stdout_line:
        print (line)
    for line in stderr_line:
        print (line)
    print('end setup pdt-space')

    if GPU_instance:
        command = "sudo ~/docker_sims/CUDA_setup.sh > ~/CUDA_setup.log"
        stdin, stdout, stderr = client.exec_command(command)
        stdout_line = stdout.readlines()
        stderr_line = stderr.readlines()
        for line in stdout_line:
            print (line)
        for line in stderr_line:
            print (line)

    client.close()

    # alias = 'manual'
    conn = DbConnection()
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    running_process.running = False
    running_process.save()
    print('finished')
    sys.stdout.flush()

# AWS setup progress page
def AWSsetup(request):
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    pid = running_process.pid
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='AWSsetup')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

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
        
        print("set up progress: " + progress)
        print("end current progress")
        sys.stdout.flush()
        progress = (float(progress) * 6)
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
# def exec_simulate(request, channel, command):
    
#     print("start running " + command)
#     sys.stdout.flush()
#     channel.exec_command(command)
#     while True:
#         if channel.exit_status_ready():
#             break
#         rl, wl, xl = select.select([channel],[],[],0.0)
#         if len(rl) > 0:
#             print(channel.recv(1024))
#             sys.stdout.flush()
#     print("finish running")
#     sys.stdout.flush()
#     return  HttpResponseRedirect('/application/simulation_fail')

# simulation progress page
def running(request):
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='running')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    stdin, stdout, stderr = client.exec_command('sudo sed -e "s/\\r/\\n/g" ~/sim_run.log > ~/cleaned.log; sudo tail -1 ~/cleaned.log')
    stdout_word = stdout.readlines()
    progress = ''
    if len(stdout_word) > 0:
        # print(stdout_word[-1])
        # sys.stdout.flush()
        try:
            if stdout_word[-1].split()[0] == "Progress":
                progress = stdout_word[-1].split()[-1]
        except:
            pass
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
    
    stdin, stdout, stderr = client.exec_command('pgrep tclsh')
    stdout_pid = stdout.readlines()
    sys.stdout.flush()
    peak_mem_usage = 0
    mem_unit = 'GB'
    if len(stdout_pid) > 0:
        print("tclsh pid is:", stdout_pid[0])
        stdin, stdout, stderr = client.exec_command('grep ^VmPeak /proc/' + stdout_pid[0].strip() + '/status')
        stdout_mem = stdout.readlines()
        sys.stdout.flush()
        if len(stdout_mem):
            stdout_mem_list = stdout_mem[0].split()
            if stdout_mem_list[-1] == 'kB':
                peak_mem_usage = int(stdout_mem_list[1].strip()) / 1000000.0
                mem_unit = 'GB'
            else:
                peak_mem_usage = int(stdout_mem_list[1].strip())
                mem_unit = stdout_mem_list[-1].strip()
            print("peak memory usage is:", str(peak_mem_usage) + ' ' + mem_unit)

    request.session['peak_mem_usage'] = max(request.session['peak_mem_usage'], peak_mem_usage)

    # command to check remaining disk space
    stdin, stdout, stderr = client.exec_command('df -hT ~ | awk \'$NF == "/" { print $6 }\'')
    stdout_disk_space = stdout.readlines()
    sys.stdout.flush()
    stdin, stdout, stderr = client.exec_command('df -hT ~ | awk \'$NF == "/" { print $3 }\'')
    stdout_disk_size = stdout.readlines()
    sys.stdout.flush()
    disk_used = 0
    disk_size = 0
    if len(stdout_disk_space):
        disk_used = stdout_disk_space[0]
        print("disk space is:", disk_used)
    if len(stdout_disk_size):
        disk_size = stdout_disk_size[0]
        print("disk space is:", disk_size)
    
    print("status:",status)
    sys.stdout.flush()
    if status == "[info]Simulationrunfinished":
        print("tclsh finish")
        sys.stdout.flush()
        client.close()
        # save memory and disk usage
        request.session['peak_mem_usage_unit'] = mem_unit
        request.session['disk_space_usage'] = disk_used
        request.session['disk_size'] = disk_size
        return HttpResponseRedirect('/application/simulation_finish')
    else:
        print("tclsh not finished")
        sys.stdout.flush()
        peak_mem_usage_str = str(round(peak_mem_usage,2)) + ' ' + mem_unit
        return render(request, "running.html", {'time':running_time, 'progress':progress, 'disk_space':disk_used, 'disk_size':disk_size, 'peak_mem':peak_mem_usage_str})

# page for failed simulation
# def simulation_fail(request):
#     return render(request, "simulation_fail.html")

# Response for finished simulation
def simulation_finish(request):
    # display simulation outputs
    request.session['uploaded_output_mesh'] = False
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='simulation_finish')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    command = "echo \"Your FullMonteWeb simulation run has finished. \
        If you are not planning to run more simulations, please stop your AWS \
        instance to avoid excessive charges.\" | \
        sudo mail -s \"Your FullMonteWeb run has finished\" -r \'<fullmonteweb@outlook.com>\' " + str(request.user.email)
    stdin, stdout, stderr = client.exec_command(command)

    # identify local output files to display
    file_paths = request.session['ec2_file_paths']
    if not file_paths:
        # command to identify files after simulation
        cd_cmd = 'cd ~/docker_sims;'
        find_cmd = 'find * ! -name "files_before.txt" ! -name "files_after.txt" ! -name "*.sh" ! -name "*.tcl" ! -name "*.csv" ! -name "*.png" -type f >> files_after.txt;'
        # command to diff directory for newly created files and determine the number of new files created
        diff_cmd = 'comm -13 files_before.txt files_after.txt >> files_diff.txt'
        # execute commands in order
        stdin, stdout, stderr = client.exec_command(cd_cmd + find_cmd + diff_cmd)
        exit_status = stdout.channel.recv_exit_status()          # Blocking call
        if exit_status == 0:
            print ("Output files successfully diffed")
        else:
            print("Error", exit_status)
        sys.stdout.flush()

    ftp = client.open_sftp()
    try:
        # ftp.chdir('docker_sims/')
        file=ftp.file('sim_run.log', "r")
        output = file.read().decode()
        if '[error]' in output:
            simulation_failed = True
        else:
            simulation_failed = False
        html_string=''
        # add <p> to output string since html does not support '\n'
        for e in output.splitlines():
            if len(e.split()) > 0  and  e.split()[0] != "Progress":
                html_string += e + '<br />'
        print(output)
        sys.stdout.flush()
        stdin, stdout, stderr = client.exec_command('sudo rm -f ~/cleaned.log')
        # get files for view
        if not file_paths:
            with ftp.open('docker_sims/files_diff.txt') as output_vtk_files:
                for line in output_vtk_files:
                    output_vtk_path = line.rstrip()
                    file_paths.append(output_vtk_path)
            request.session['ec2_file_paths'] = file_paths
    finally:
        ftp.close()
    # remove temporary file
    stdin, stdout, stderr = client.exec_command('cd ~/docker_sims; rm -rf files_diff.txt')
    exit_status = stdout.channel.recv_exit_status()          # Blocking call
    if exit_status == 0:
        print ("Temporary file successfully deleted")
    else:
        print("Error", exit_status)
    sys.stdout.flush()
    client.close()
    if 'peak_mem_usage' in request.session:
        html_string += 'Physical peak memory (RAM) usage: ' + str(round(request.session['peak_mem_usage'],2)) + ' ' + request.session['peak_mem_usage_unit'] + '<br />'
    if 'disk_space_usage' in request.session:
        html_string += 'Disk space used: ' + request.session['disk_space_usage'] + ' out of ' + request.session['disk_size'] + 'B<br />'

    # save output mesh file info
    # using tcl script name to identify as meshes can be reused
    info = meshFileInfo.objects.filter(user = request.user).latest('id')

    # if there is error, clear output mesh file info so user cannot use visualizer; go simulation failed page
    if(simulation_failed):
        info.fileName = ""
        info.dvhFig = ""
        info.powerAndScaling = ""
        info.thresholdFluence = ""
        info.save()
        return render(request, "simulation_fail.html", {'output':html_string})
    
    # otherwise, simulation completed
    # save output mesh info
    outputMeshFile = tclScript.objects.filter(user = request.user).latest('id')
    outputMeshFileName = outputMeshFile.script.name
    info.fileName = outputMeshFileName[:-4] + ".out.vtk"
    info.dvhFig = "<p>Dose Volume Histogram not yet generated</p>"
    info.powerAndScaling = ""
    info.thresholdFluence = ""
    info.save()
    # save fluence energy unit
    meshUnit = request.session['meshUnit']
    energyUnit = request.session['energyUnit']
    request.session['fluenceEnergyUnit'] = energyUnit + "/" + meshUnit

    # populate history
    connections.close_all()
    p = Process(target=populate_simulation_history, args=(request, ))
    p.start()
    return render(request, "simulation_finish.html", {'output':html_string, 'output_file_paths':file_paths})

def populate_simulation_history(request):
    conn = DbConnection()

    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='populate_simulation_history')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    # store output files to S3, and populate simulation history
    history = simulationHistory()
    history.simulation_type = 'Fullmonte Simulation'
    history.user = request.user
    mesh = tclInput.objects.filter(user = request.user).latest('id')
    history.mesh_file_path = mesh.meshFile
    history.originalMeshFileName = mesh.originalMeshFileName
    history.meshFileID = mesh.meshFileID
    history.tcl_script_path = tclScript.objects.filter(user = request.user).latest('id').script

    mesh_vtk_name = mesh.meshFile.name
    mesh_name = mesh_vtk_name[:-4]
    tcl_name = history.tcl_script_path.name
    output_vtk_name = tcl_name[:-4]
    output_vtk_name = output_vtk_name.replace(".", "_") + '_out_vtk.zip'
    output_txt_name = tcl_name[:-4]
    output_txt_name = output_txt_name.replace(".", "_") + '_out_txt.zip'

    # command to identify files after simulation
    cd_cmd = 'cd ~/docker_sims;'
    find_cmd = 'find * ! -name "files_before.txt" ! -name "files_after.txt" ! -name "*.sh" ! -name "*.tcl" ! -name "*.csv" ! -name "*.png" -type f >> files_after.txt;'

    # command to diff directory for newly created files and determine the number of new files created
    diff_cmd = 'comm -13 files_before.txt files_after.txt >> files_diff.txt;'
    ct_vtk_cmd = 'if [[ $(grep -c ".vtk" files_diff.txt) -eq 1 ]]; then grep ".vtk" files_diff.txt > single_vtk_file.txt; fi;'
    ct_txt_cmd = 'if [[ $(grep -c ".txt" files_diff.txt) -eq 1 ]]; then grep ".txt" files_diff.txt > single_txt_file.txt; fi'

    # execute commands in order
    print("Command executed:", cd_cmd + find_cmd + diff_cmd + ct_vtk_cmd + ct_txt_cmd)
    stdin, stdout, stderr = client.exec_command(cd_cmd + find_cmd + diff_cmd + ct_vtk_cmd + ct_txt_cmd)
    exit_status = stdout.channel.recv_exit_status()          # Blocking call
    if exit_status == 0:
        print ("Output files successfully diffed")
    else:
        print("Error", exit_status)
    sys.stdout.flush()

    ftp = client.open_sftp()
    try:
        # if just one file, then overwrite the output vtk name with the sigle file's name and do not zip
        try:
            with ftp.open('docker_sims/single_vtk_file.txt') as single_vtk_file:
                for line in single_vtk_file:
                    output_vtk_name = line.rstrip() # overwrite
            zip_vtk_cmd = ''
        except:
            zip_vtk_cmd = 'grep ".vtk" files_diff.txt | zip ' + output_vtk_name + ' -@ > /dev/null 2>&1;'

        try:
            with ftp.open('docker_sims/single_txt_file.txt') as single_txt_file:
                for line in single_txt_file:
                    output_txt_name = line.rstrip() # overwrite
            zip_txt_cmd = ''
        except:
            zip_txt_cmd = 'grep ".txt" files_diff.txt | zip ' + output_txt_name + ' -@ > /dev/null 2>&1;'

        # command to remove temporary files
        rm_cmd = 'rm -rf files_before.txt files_after.txt files_diff.txt single_vtk_file.txt single_txt_file.txt'

        # execute commands in order
        print("Command executed:", cd_cmd + zip_vtk_cmd + zip_txt_cmd + rm_cmd)
        stdin, stdout, stderr = client.exec_command(cd_cmd + zip_vtk_cmd + zip_txt_cmd + rm_cmd)
        exit_status = stdout.channel.recv_exit_status()          # Blocking call
        if exit_status == 0:
            print ("Output files successfully prepared for download")
        else:
            print("Error", exit_status)
        sys.stdout.flush()

        try:
            output_vtk_file = ftp.file('docker_sims/' + output_vtk_name)
            history.output_vtk_path.save(output_vtk_name, output_vtk_file)
            output_txt_file = ftp.file('docker_sims/' + output_txt_name)
            history.output_txt_path.save(output_txt_name, output_txt_file)
        except:
            print("Cannot save history for simulation output because file does not exist")
    finally:
        ftp.close()
    client.close()
    history.save()

def simulation_history(request):
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    history = simulationHistory.objects.filter(user=request.user).order_by('-simulation_time') # order by time (most present at top)
    historySize = history.count()
    if historySize > 0:
        return render(request, "simulation_history.html", {'history':history, 'historySize':historySize})
    else:
        return render(request, "simulation_history_empty.html")
    return render(request, "simulation_history.html", {'history':history, 'historySize':historySize})

#               Current unsolved problem in PDT-SPACE
#       1.  When running the docker image for pdt-space, sometimes the image needs to be downloaded and reinstall again.
#           Sometimes it doesn't need to. As a result, the docker image will occupy more disk space.
#  
#       2.  When the the pdt-space run actually finished (the function launch_pdt_space() printed "finished"),
#           the program is stuck in function  pdt_space_running() and the web page is keep loading when auto refreshing the page(freezed).
#           This only happens once and is not able to reproduce.
#       
def pdt_space(request):
    print("in pdt_space")
    sys.stdout.flush()

    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    try:
        dns = request.session['DNS']
        text_obj = request.session['text_obj']
        tcpPort = request.session['tcpPort']
    except:
        messages.error(request, 'Error - please connect to an AWS remote server before trying to simulate')
        return HttpResponseRedirect('/application/aws')
    
    #lanuch job to search all preset mesh and optical files in the PDT-SPACE repo
    # print('before')
    # current_process = psutil.Process()
    # children = current_process.children(recursive=True)
    # for child in children:
    #     print('Child pid is {}'.format(child.pid))
    # connections.close_all()
    # p = Process(target=search_pdt_space, args=(request, ))
    # p.start()
    # print('after')
    # current_process = psutil.Process()
    # children = current_process.children(recursive=True)
    # form = processRunning()
    # form.user=request.user
    # for child in children:
    #     form.pid = child.pid
    #     form.running = True
    #     print('Child pid is {}'.format(child.pid))
    # conn = DbConnection()
    # form.save()
    # sys.stdout.flush()
    return HttpResponseRedirect('/application/pdt_spcae_wait')


def pdt_spcae_wait(request):
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    pid = running_process.pid
    # client = paramiko.SSHClient()
    # client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # text_obj = request.session['text_obj']
    # private_key_file = io.StringIO(text_obj)
    # privkey = paramiko.RSAKey.from_private_key(private_key_file)
    # client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)
    if running_process.running:
    # if False:
        print("get current progress")
        sys.stdout.flush()
        return render(request, "pdt_spcae_wait.html")

    else:
        # client.close()
        print("progress done")
        sys.stdout.flush()
        return HttpResponseRedirect('/application/pdt_space_license')


def search_pdt_space(request):
    time.sleep(3)
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='search_pdt_space')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    ####### check whether image cleanup is required
    need_cleanup = False
    command = "tail -1 ~/docker_pdt/daily_cleanup.txt"
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()

    timezone = tz('US/Eastern')
    current_date = str(datetime.now(timezone).date())
    if len(stdout_line) == 0:
        need_cleanup = True
        print("daily_cleanup.txt file is not exist.")
    
    elif stdout_line[-1].rstrip() != current_date:
        need_cleanup = True
        print("date in file: ",stdout_line[-1].rstrip())
        print("date current: ",current_date)
    
    else:
        print("date match.")

    if need_cleanup == True:
        print("cleanup instance.")
        command1 = "echo \"" + current_date + "\" > ~/docker_pdt/daily_cleanup.txt; "
        command2 = "sudo docker image prune --all -f"
        stdin, stdout, stderr = client.exec_command(command1 + command2)
        stdout_line = stdout.readlines()
        for line in stdout_line:
            print (line)

    sys.stdout.flush()
    #########################################
    foo_list = []
    addr_list = []
    command = "sudo sh ~/docker_pdt/pdt_space_setup.sh \"find /usr/local/pdt-space/data -name *.opt\" 0"
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    
    for line in stdout_line:
        if line.rstrip().endswith('.opt'):
            request.session[line.rstrip().split('/')[-1]] = line.rstrip()
            foo_list.append(line.rstrip().split('/')[-1])
            addr_list.append(line.rstrip())
            # print (line)
    opt_list = ",".join(foo_list)
    opt_addr = ",".join(addr_list)
    request.session['opt_list'] = opt_list
    print(request.session['opt_list'])
    print("This is all preset .opt files")
    sys.stdout.flush()
    
    foo_list = []
    addr_list = []
    command = "sudo sh ~/docker_pdt/pdt_space_setup.sh \"find /usr/local/pdt-space/data -name *.mesh\" 0"
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    
    for line in stdout_line:
        if line.rstrip().endswith('.mesh'):
            request.session[line.rstrip().split('/')[-1]] = line.rstrip()
            foo_list.append(line.rstrip().split('/')[-1])
            addr_list.append(line.rstrip())
            # print (line)
    mesh_list = ",".join(foo_list)
    mesh_addr = ",".join(addr_list)
    request.session['mesh_list'] = mesh_list
    print(request.session['mesh_list'])
    print("This is all preset .mesh files")
    client.close()

    conn = DbConnection()
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    running_process.running = False
    running_process.save()

    form = pdtPresetData()
    form.user=request.user
    form.opt_list = opt_list
    form.mesh_list = mesh_list

    form.opt_addr = opt_addr
    form.mesh_addr = mesh_addr
    form.save()
    print('finished')
    sys.stdout.flush()



def pdt_space_license(request):
    if request.method == 'POST':
        form = mosekLicense(request.POST, request.FILES)
        if form.is_valid():
            text_obj = request.session['text_obj']
            private_key_file = io.StringIO(text_obj)
            privkey = paramiko.RSAKey.from_private_key(private_key_file)
            try:
                client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='pdt_space_license')
            except:
                sys.stdout.flush()
                messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
                return HttpResponseRedirect('/application/aws')
            sftp = client.open_sftp()
            try:
                sftp.putfo(request.FILES['mosek_license'], 'docker_pdt/mosek.lic')
            finally:
                sftp.close()
            client.close()
        else:
            print("pdt_space_license not valid")
        return HttpResponseRedirect('/application/pdt_space_material') 
    else:
        text_obj = request.session['text_obj']
        private_key_file = io.StringIO(text_obj)
        privkey = paramiko.RSAKey.from_private_key(private_key_file)
        try:
            client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='pdt_space_license')
        except:
            sys.stdout.flush()
            messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
            return HttpResponseRedirect('/application/aws')
        sftp = client.open_sftp()
        try:
            sftp.stat('docker_pdt/mosek.lic')
        except IOError:
            form = mosekLicense()
            context = {
                'form': form,
            }
            sftp.close()
            return render(request, "pdt_space_license.html", context)
        finally:
            sftp.close()
        client.close()
        return HttpResponseRedirect('/application/pdt_space_material') 


def pdt_space_material(request):
    print("in pdt_space_material")
    sys.stdout.flush()

    conn = DbConnection()
    # pdt_info = pdtPresetData.objects.filter(user = request.user).latest('id')
    # opt_str = pdt_info.opt_list
    # mesh_str = pdt_info.mesh_list

    # opt_addr = pdt_info.opt_addr
    # mesh_addr = pdt_info.mesh_addr
    # opt_str = request.session['opt_list']
    # mesh_str = request.session['mesh_list']

    # print("the opt str is ",opt_str)
    # print("the mesh str is ",mesh_str)

    # print("the opt addr is ",opt_addr)
    # print("the mesh addr is ",mesh_addr)
    # sys.stdout.flush()
    # sys.stdout.flush()

    # _opt_list=[]
    # _mesh_list=[]
    # for sinlge in opt_str.split(','):
    #     _opt_list.append(sinlge)
    
    # for sinlge in mesh_str.split(','):
    #     _mesh_list.append(sinlge)
        
    if request.method == 'POST':
        
        form = pdtForm(request.POST, request.FILES)
        if form.is_valid():
            print(form.cleaned_data)
            op_file = opFileInput()
            op_file.user=request.user
            op_file.total_energy = form.cleaned_data['total_energy']
            op_file.num_packets = form.cleaned_data['num_packets']
            op_file.wave_length = form.cleaned_data['wave_length']
            request.session['wave_length'] = op_file.wave_length
            
            op_file.tumor_weight = form.cleaned_data['tumor_weight']
            
            mesh_name = request.FILES['mesh'].name
            opt_name = request.FILES['opt'].name
            op_file.data_name = mesh_name.split('.')[0]
            op_file.opt_file_storage = request.FILES['opt']
            op_file.mesh_file_storage = request.FILES['mesh']
            op_file.tissue_property_file_storage = request.FILES['tissue_property']
            op_file.tissue_types_file_storage = request.FILES['tissue_type']
            # op_file.placement_file = request.FILES['light_placement_file']
            # print("light file name is ", op_file.placement_file.name)
            # sys.stdout.flush()
            # for sub in mesh_addr.split(','):
            #     if sub.split('/')[-1] == mesh_name:
            #         op_file.data_dir = "/".join(sub.split('/')[:-1])

            # for sub in opt_addr.split(','):
            #     if sub.split('/')[-1] == opt_name:
            #         op_file.opt_file = sub
            op_file.opt_file = "/sims/"+op_file.opt_file_storage.name
            op_file.save()
        else:
            print(" pdt_space_material form not valid")
            print(form.errors)
        sys.stdout.flush()
        return HttpResponseRedirect('/application/pdt_space_lightsource')
    else:
        
        form = pdtForm()
    context = {
        'form': form,
    }
    return render(request, "pdt_space_material.html", context)


def pdt_space_lightsource(request):
    print("in pdt_space_lightsource")

    if request.method == 'POST':
        form = pdtPlaceFile(request.POST, request.FILES)
        if form.is_valid():
            conn = DbConnection()
            opfile = opFileInput.objects.filter(user = request.user).latest('id')
            opfile.placement_file = request.FILES['light_placement_file']
            # opfile.source_type = form.cleaned_data['source_type']
            opfile.placement_type = form.cleaned_data['placement_type']
            
            opfile.save()
            opfile.light_source_file = "/sims/" + str(opfile.placement_file.name)
            opfile.save()

            print("check data")
            print(opfile.total_energy)
            print(opfile.num_packets)
            print(opfile.wave_length)
            print(opfile.data_dir)
            print(opfile.data_name)
            # print(opfile.source_type)
            print(opfile.tumor_weight)
            print(opfile.placement_type)
            print(opfile.opt_file)
            print(opfile.light_source_file)
            print(opfile.placement_file.name)
            sys.stdout.flush()

            # lanuch pdt-space with a use process
            print('before')
            current_process = psutil.Process()
            children = current_process.children(recursive=True)
            for child in children:
                print('Child pid is {}'.format(child.pid))
            connections.close_all()
            # request.session['pdt_error_msg'] = []
            p = Process(target=launch_pdt_space, args=(request, ))
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
            conn = DbConnection()
            form.save()
            sys.stdout.flush()
            # channel = client.get_transport().open_session()
            # command = "sudo sh ~/docker_pdt/pdt_space_setup.sh \"sh /sims/docker.sh\" 1 "
            # stdin, stdout, stderr = client.exec_command(command)
            # client.exec_command(command)
            # stdout_line = stdout.readlines()
            # stderr_line = stderr.readlines()
            # for line in stdout_line:
            #     print (line)
            # for line in stderr_line:
            #     print (line)
            # sys.stdout.flush()  
            # time.sleep(3)
            request.session['started'] = "false"
            return HttpResponseRedirect('/application/pdt_space_running')
        else:
            print(" pdt_space_lightsource form error")
            print(form.errors)
            sys.stdout.flush()
            return HttpResponseRedirect('/application/pdt_space_running')
    else:
        form = pdtPlaceFile()
        context = {
            'form': form,
        }


    return render(request, "pdt_space_lightsource.html", context)

def pdt_space_running(request):
    # print("checking the pdt-space status")
    sys.stdout.flush()
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    pid = running_process.pid
    # print("got running process")
    sys.stdout.flush()
    if running_process.running:
        print("pdt-space running")
        sys.stdout.flush()

        text_obj = request.session['text_obj']
        private_key_file = io.StringIO(text_obj)
        privkey = paramiko.RSAKey.from_private_key(private_key_file)
        try:
            client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='pdt_space_running')
        except:
            sys.stdout.flush()
            messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
            return HttpResponseRedirect('/application/aws')
        
        ftp = client.open_sftp()
        try:
            stdin, stdout, stderr = client.exec_command('sudo sed -e "s/\\r/\\n/g" ~/eval_result.log > ~/copy_eval_result.log')
            exit_status = stdout.channel.recv_exit_status()          # Blocking call
            file=ftp.file('copy_eval_result.log', "r")
            output = file.read().decode()
            output_lines = output.splitlines()

            progress = ''
            status = ''
            index = -1
            
            for line in output_lines:
                if len(output_lines[index]) > 0:
                    if output_lines[index] == "Solving for objective":
                        progress = '99.00%'
                        status = 'Running optimization'
                        break

                    if len(output_lines[index].split()) == 5 and output_lines[index].split()[0] == "Currently":
                        request.session['started'] = "true"
                        if progress == '':
                            progress = '0.00%'
                        else:
                            progress = progress
                        status = "Running simulation for light source number: " + output_lines[index].split()[-1]
                        break

                    if output_lines[index].split()[0] == "Progress:" and progress == '':
                        progress = output_lines[index].split()[-1]

                index -= 1

            if status == '' or request.session['started'] == "false":
                status = "Preparing PDT-SPACE"
                progress ="0.00%"
            progress = progress[:-2]
            start_time = running_process.start_time
            current_time = datetime.now(timezone.utc)
            time_diff = current_time - start_time
            running_time = str(time_diff)
            running_time = running_time.split('.')[0]
            print(status)
            print(progress)
            print(running_time)
            # print(request.session['source_type'])
            print(request.session['started'])
            sys.stdout.flush()
        finally:
            ftp.close()
            client.close()
        return render(request, "pdt_space_running.html", {'status':status, 'progress':progress, 'time':running_time})

    else:
        # client.close()
        print("pdt-space done")
        sys.stdout.flush()
        return HttpResponseRedirect('/application/pdt_space_finish')
    # client = paramiko.SSHClient()
    # client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # text_obj = request.session['text_obj']
    # private_key_file = io.StringIO(text_obj)
    # privkey = paramiko.RSAKey.from_private_key(private_key_file)
    # client.connect(hostname=request.session['DNS'], username='ubuntu', pkey=privkey)

    # # stdin, stdout, stderr = client.exec_command('sudo sed -e "s/\\r/\\n/g" ~/pdt_run.log > ~/cleaned_pdt_run.log')
    # stdin, stdout, stderr = client.exec_command('tail -1 ~/eval_result.log')
    # stdout_line = stdout.readlines()
    # status = ""

    # if len(stdout_line) > 0:
    #     status = stdout_line[0]
    #     status = "".join(status.split())
    
    # print("status:",status)
    # sys.stdout.flush()
    # client.close()
    
    # # if status == "[info]PDT-SPACErunfinished":
    # if status == "===========================================================================":
    #     print("pdt space finish")
    #     sys.stdout.flush()
    #     return HttpResponseRedirect('/application/pdt_space_finish')
    # else:
    #     print("pdt space not finished")
    #     sys.stdout.flush()
    #     return render(request, "pdt_space_running.html")

def launch_pdt_space(request):
    time.sleep(3)
    conn = DbConnection()
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='launch_pdt_space')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    opfile = opFileInput.objects.filter(user = request.user).latest('id')

    #generate .op file
    dir_path = os.path.dirname(os.path.abspath(__file__))
    source = dir_path + '/pdtOp/pdt_space.op'

    #start by wiping script template
    with open(source, 'r') as f:
        lines = f.readlines()
    
    f = open(source, 'w')
    for line in lines[::-1]:
        del lines[-1]
    
    f = open(source, 'a')
    f.write('RUN_TESTS = false\n\n')
    f.write('PNF = ' + opfile.total_energy + '\n\n')
    f.write('NUM_PACKETS = ' + opfile.num_packets + '\n\n')
    f.write('WAVELENGTH = ' + opfile.wave_length + '\n\n')
    wavelength = opfile.wave_length
    f.write('DATA_DIR = /sims/\n\n')
    data_dir = "/sims"
    f.write('DATA_NAME = ' + opfile.mesh_file_storage.name.split('.')[0] + '\n\n')
    f.write('READ_VTK = false\n\n')
    if opfile.placement_type == 'fixed_point':
        f.write('source_type = ' + 'point' + '\n\n')
        f.write('tumor_weight = ' + opfile.tumor_weight + '\n\n')
        f.write('PLACEMENT_TYPE = ' + 'fixed' + '\n\n')
    if opfile.placement_type == 'fixed_line':
        f.write('source_type = ' + 'line' + '\n\n')
        f.write('tumor_weight = ' + opfile.tumor_weight + '\n\n')
        f.write('PLACEMENT_TYPE = ' + 'fixed' + '\n\n')
    if opfile.placement_type == 'virtual_point':
        f.write('source_type = ' + 'point' + '\n\n')
        f.write('tumor_weight = ' + opfile.tumor_weight + '\n\n')
        f.write('PLACEMENT_TYPE = ' + 'virtual' + '\n\n')

    # f.write('TAILORED = false\n\n')
    f.write('OPTICAL_FILE = ' + opfile.opt_file_storage.name + '\n\n')
    f.write('INIT_PLACEMENT_FILE = ' + opfile.light_source_file + '\n\n')
    f.close()
    f = open(source, 'r')

    ftp = client.open_sftp()
    try:
        ftp.chdir('docker_pdt/')
        file=ftp.file('docker.sh', "w")
        file.write('#!/bin/bash\nexport MOSEKLM_LICENSE_FILE=/sims/mosek.lic\ncd sims/\npdt_space pdt_space.op v100_dvh.m')
        file.flush()
        ftp.chmod('docker.sh', 700)
        ftp.putfo(f,'./pdt_space.op')
        ftp.putfo(opfile.placement_file, './'+opfile.placement_file.name)
        ftp.putfo(opfile.opt_file_storage, './'+opfile.opt_file_storage.name)
        ftp.putfo(opfile.mesh_file_storage, './'+opfile.mesh_file_storage.name)
        ftp.putfo(opfile.tissue_property_file_storage, './tissue_properties_' + wavelength + 'nm.txt')
        ftp.putfo(opfile.tissue_types_file_storage, './TissueTypes.txt')
    finally:
        ftp.close()
    f.close()

    command = "sudo sh ~/docker_pdt/pdt_space_setup.sh \"sh /sims/docker.sh\" 1 "
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    for line in stdout_line:
        print (line)
    for line in stderr_line:
        # if len(line) > 0:
        # request.session['pdt_error_msg'].append(line)
        # print ("error:  ",request.session['pdt_error_msg'])
        print (line)
    sys.stdout.flush() 
    client.close()

    #conn = DbConnection()
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    running_process.running = False
    running_process.save()
    print('finished')
    sys.stdout.flush()

def pdt_space_finish(request):
    # print("in fihish")
    # sys.stdout.flush()

    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='pdt_space_finish')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')
    
    # pdt-space output in ~/eval_result.log
    conn = DbConnection()
    opfile = opFileInput.objects.filter(user = request.user).latest('id')
    total_energy = opfile.total_energy
    total_pack = opfile.num_packets
    
    ftp = client.open_sftp()
    file=ftp.file('eval_result.log', "r")
    output = file.read().decode()
    output_lines = output.splitlines()
    try:
        check_success = output_lines[-3]
    except:
        print("pdt-space fail")
        ftp.close()
        client.close()
        return HttpResponseRedirect('/application/pdt_space_fail')
    # print(check_success)
    check_success = re.sub(r'[^\w]', ' ', check_success)
    check_success = "".join(check_success.split())
    print(check_success)
    if check_success != "ENDOFRUN":
        print("pdt-space fail")
        ftp.close()
        client.close()
        return HttpResponseRedirect('/application/pdt_space_fail')
        
    # get num_material and num_source by reading the log file
    # num_material: number of materials in input mesh (excluding air)
    # num_source: number of light source placement
    try:
        num_material = 0
        num_source = 0
        index = 0
        for line in output_lines:
            if output_lines[index].split()[0] == "Directory":
                num_material = output_lines[index + 1].split()[-1]
                break
            index += 1
        print(num_material)
        request.session['num_material'] = num_material

        index = -1
        for line in output_lines:
            found = re.findall(r'x\[(\d*)\] = \d*\.\d*', output_lines[index]) # find id in last line of the form "x[id] = #.#"
            if(found):
                num_source = found[0]
                break
            index -= 1
        print(num_source)    

        html_fluence_dist=''
        html_pow_alloc=''
        num_material = int(num_material)
        num_source = int(num_source) + 1    # index + 1

        output_info = output_lines[-21:-19]
        time_simu = output_info[0].split()[8]
        time_opt = output_info[1].split()[3]

        output_info = output_lines[-26 - num_source :-26]
        for e in output_info:
            html_pow_alloc += e + '<br />'
        
        request.session['material_name']= []
        output_info = output_lines[-26 - num_source - 2 - num_material :-26 - num_source - 2]
        for e in output_info:
            html_fluence_dist += e + '<br />'
            request.session['material_name'].append(e.split()[0])

        print(request.session['material_name'])

        ####### get log file
        pdt_log_file = pdtOuputLogFile()
        pdt_log_file.user=request.user
        f = ftp.file('eval_result.log')
        pdt_log_file.pdt_space_log.save('eval_result.log', f)
        
        pdt_log_file.save()



        sys.stdout.flush()
        ftp.close()
        client.close()
        return render(request, "pdt_space_finish.html", 
                    {'html_fluence_dist':html_fluence_dist, 
                    'html_pow_alloc':html_pow_alloc, 
                    'time_simu':time_simu, 
                    'time_opt':time_opt, 
                    'total_energy':total_energy, 
                    'total_pack':total_pack, 
                    'num_source':num_source, 
                    'pdt_log_file':pdt_log_file})
    except:
        print("pdt-space fail")
        ftp.close()
        client.close()
        return HttpResponseRedirect('/application/pdt_space_fail')

def pdt_space_fail(request):
    # print("in fail")
    # sys.stdout.flush()
    conn = DbConnection()
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='pdt_space_fail')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')
 
    ftp = client.open_sftp()
    try:
        pdt_log_file = pdtOuputLogFile()
        pdt_log_file.user=request.user
        f = ftp.file('eval_result.log')
        pdt_log_file.pdt_space_log.save('eval_result.log', f)
        
        pdt_log_file.save()
        # error_msg = ''
        # for line in request.session['pdt_error_msg']:
        #     print(line)
        #     error_msg = error_msg + line + '<br />'
        # print("catch: ", len(request.session['pdt_error_msg']), error_msg)
        # sys.stdout.flush()
        # ftp.chdir('docker_pdt/')
        # v100 = ftp.file('fp_v100.m')

        # output_lines = v100.read().decode().splitlines()

        # local_path = os.path.dirname(__file__) + "/temp/v100.m"
        # ft = open(local_path, "w+")
        # for line in output_lines:
        #     ft.write(line + "\n")
        # ft.close()
    finally:    
        ftp.close()
    client.close()
    return render(request, "pdt_space_fail.html", {'pdt_log_file':pdt_log_file})
    # return render(request, "pdt_space_fail.html", {'error_msg':error_msg ,'pdt_log_file':pdt_log_file})

def pdt_space_visualization(request):
    text_obj = request.session['text_obj']
    private_key_file = io.StringIO(text_obj)
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    try:
        client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='pdt_space_visualization')
    except:
        sys.stdout.flush()
        messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        return HttpResponseRedirect('/application/aws')

    ##get tissue type name
    command = "sudo sh ~/docker_pdt/pdt_space_setup.sh \"cat /sims/tissue_properties_" + str(request.session['wave_length']) + "nm.txt\" 0"
    print(command)
    stdin, stdout, stderr = client.exec_command(command)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    request.session['region_name']= []
    for line in stdout_line:
        print(line)

    for line in stdout_line:
        if len(line.split(',')) == 3:
            request.session['region_name'].append(line.split(',')[0])
    print(request.session['region_name'])
    sys.stdout.flush()
    
    ftp = client.open_sftp()
    try:
        ftp.chdir('docker_pdt/')
        v100 = ftp.file('v100_dvh.m')

        output_lines = v100.read().decode().splitlines()
        ##copy v100 file to local
        local_path = os.path.dirname(__file__) + "/temp/v100.m"
        ft = open(local_path, "w+")
        for line in output_lines:
            ft.write(line + "\n")
        ft.close()
    except:
        context = {'dvhFig': "Error: No DVH file."}
        return render(request, "pdt_space_display_visualization.html", context)
    finally:
        ftp.close()
    client.close()

    print('before')
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    for child in children:
        print('Child pid is {}'.format(child.pid))
    connections.close_all()
    p = Process(target=pdvh, args=(request.user, request.session['num_material'], request.session['region_name'], ))
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

    conn = DbConnection()
    form.save()
    sys.stdout.flush()
    return HttpResponseRedirect('/application/pdt_space_wait_visualization')


def pdt_space_wait_visualization(request):
    running_process = processRunning.objects.filter(user = request.user).latest('id')
    if running_process.running:
        start_time = running_process.start_time
        current_time = datetime.now(timezone.utc)
        time_diff = current_time - start_time
        running_time = str(time_diff)
        running_time = running_time.split('.')[0]
        return render(request, "pdt_space_wait_visualization.html", {'time':running_time})
    else:
        return HttpResponseRedirect('/application/pdt_space_display_visualization')

def pdt_space_display_visualization(request):
    info = meshFileInfo.objects.filter(user = request.user).latest('id')
    dvhFig = info.dvhFig
    context = {'dvhFig': dvhFig}
    return render(request, "pdt_space_display_visualization.html", context)

    

def pdt_space_visualize(request):
    """
    Todo:
    In pdt_space_finish, save mesh file info
        info = meshFileInfo.objects.filter(user = request.user).latest('id')
        info.fileName = <output mesh name>
        exists = <check if file actually exists on disk>
        if exists:
            info.remoteFileExists = true
        else
            info.remoteFileExists = false
        info.dvhFig = <dose volume histogram html string generated>
        info.maxFluence = <maximum fluence from simulation>
    In displayVisualization
        add a new parameter to check if visualization request comes from fullmonte or pdtspace.
        p = Process(target=visualizer, args=(outputMeshFileName, fileExists, dns, tcpPort, text_obj, caller))
            where caller = 'fullmonte' or 'pdtspace'
    In visualizer3D.py
        choose file path depending on caller
        if caller == 'fullmonte':
            cmd = "Visualizer --paraview /home/ubuntu/ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit/ --data /home/ubuntu/docker_sims/ --port " + tcpPort
        else:
            cmd = "Visualizer --paraview /home/ubuntu/ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit/ --data /home/ubuntu/docker_pdt/ --port " + tcpPort
    """
    return HttpResponseRedirect('/application/displayVisualization')
