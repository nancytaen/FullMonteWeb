import sys
import time

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse, HttpResponseRedirect
from django.db import IntegrityError
from django.db.models import Model
from django.shortcuts import redirect, render

from application.forms import materialSetSet, tclInputForm, lightSourceSet
from application.models import tclScript, tclInput, meshFiles
from application.serverless.cos_storage import cos_presigned_url, cos_upload_file, cos_search_prefix, \
    handle_uploaded_file
from application.serverless.models import ServerlessRequest, ServerlessOutput
from application.serverless.parameters import ServerlessParameters
from application.tclGenerator import emptyTclTemplateGeneratorServerless, tclGeneratorWriter

MESH_BUCKET = 'mesh_bucket'
TCL_BUCKET = 'tcl_bucket'
GENERATED_TCL_BUCKET = 'generated_tcl_bucket'
OUTPUT_BUCKET = 'output_bucket'
BUCKET_MAPPING = {
    MESH_BUCKET: settings.IBM_COS_MESH_BUCKET_NAME,
    GENERATED_TCL_BUCKET: settings.IBM_COS_GENERATED_TCL_BUCKET_NAME,
    TCL_BUCKET: settings.IBM_COS_TCL_BUCKET_NAME,
    OUTPUT_BUCKET: settings.IBM_COS_OUTPUT_BUCKET_NAME,
}

# def query_serverless_status(request):
#     if request.method != 'POST':
#         return HttpResponse(status=405)
#     try:
#         r = ServerlessRequest.objects.get(request_id=request.get('id'), user=request.user)
#     except Model.DoesNotExist:
#         return HttpResponse(status=404)
#     if r.completed:
#         return redirect('simulation_finish')
#     return HttpResponse(status=200)


def _initiate_serverless_simulation(source, serverless_request, user):
    """
    Upload tcl to bucket and insert an entry to ServerlessRequest db
    @param source: source file of tcl script
    @param serverless_request: dictionary of ServerlessParameter object
    @return:
    """
    cos_upload_file(settings.IBM_COS_TCL_BUCKET_NAME, serverless_request[ServerlessParameters.TCL], source)
    ServerlessRequest.objects.create(
        request_id=serverless_request[ServerlessParameters.ID],
        mesh_name=serverless_request[ServerlessParameters.MESH],
        tcl_name=serverless_request[ServerlessParameters.TCL],
        user=user
    )


def _record_completed_serverless_simulation(request_id, output_files):
    """
    insert output filenames to ServerlessOutput
    TODO email user
    @param request_id:
    @param output_files: dictionary of {[file extension] filename}
    @return:
    """
    r = ServerlessRequest.objects.get(request_id=request_id)
    ServerlessOutput.objects.create(
        request=r,
        output_vtk_name=output_files.get('out', ''),
        output_txt_name=output_files.get('txt', ''),
        log_name=output_files.get('log', ''),
    )
    r.completed = True
    r.save()
    # TODO email user
    print(r.user.email)


def cos_download_view(request, filename, bucket):
    """
        return presigned url to objects in IBM COS
        TODO authentication - do we want to grant access to
            * users who are not logged in
            * users who did not request the associated simulation
    """
    if request.method != 'GET':
        return HttpResponse(status=405)
    if filename is None:
        raise ValueError("Found empty filename")
    try:
        response = cos_presigned_url(
            bucket_name=BUCKET_MAPPING[bucket],
            key_name=filename
        )
    except:
        return HttpResponse("The file you are requesting does not exist on the server.")

    return HttpResponseRedirect(response)


def serverless_running(request):

    serverless_request = request.session.get(ServerlessParameters.SERVERLESS_REQUEST, {})
    if not serverless_request:
        return HttpResponse(status=404)

    try:
        prefix = serverless_request[ServerlessParameters.BASE]
        matches = cos_search_prefix(settings.IBM_COS_OUTPUT_BUCKET_NAME, prefix)
        print(f"output found: {', '.join(matches)}")
        output_files = {match[len(prefix):]: match for match in matches}
        if not output_files.get('log', ''):
            print("waiting for serverless simulation to complete")
            context = {}
            return render(request, 'serverless/serverless_running.html', context)
        _record_completed_serverless_simulation(serverless_request[ServerlessParameters.ID], output_files)

    except Model.DoesNotExist or IntegrityError:
        del request.session[ServerlessParameters.SERVERLESS_REQUEST]
        return HttpResponse(status=404)

    del request.session[ServerlessParameters.SERVERLESS_REQUEST]
    return HttpResponseRedirect('/application/serverless_simulation_finish')


def fmServerlessSimulatorSource(request):
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    # visualize input mesh
    # inputMeshFileName = tclInput.objects.filter(user = request.user).latest('id').meshFile.name
    # text_obj = request.session['text_obj']

    # # generate ParaView Visualization URL
    # # e.g. http://ec2-35-183-12-167.ca-central-1.compute.amazonaws.com:8080/
    # dns = request.session['DNS']
    # tcpPort = request.session['tcpPort']
    # visURL = "http://" + dns + ":" + tcpPort + "/"
    # # render 3D visualizer
    # p = Process(target=visualizer, args=(inputMeshFileName, True, dns, tcpPort, text_obj, ))
    # p.start()

    # # if this is a POST request we need to process the form data
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

            return HttpResponseRedirect('/application/serverless_confirmation')

    # If this is a GET (or any other method) create the default form.
    else:
        formset2 = lightSourceSet(request.GET or None)

    context = {
        'formset2': formset2,
        'unit': request.session['meshUnit'],
        # 'visURL': visURL,
    }

    return render(request, "simulator_source.html", context)


def serverless_simulation_confirmation(request):
    # TO DO: migrate to serverless
    # # Info about the generated TCL and mesh file
    # generated_tcl = tclScript.objects.filter(user = request.user).latest('id')
    # meshFilePath = tclInput.objects.filter(user = request.user).latest('id').meshFile.name
    serverless_request = request.session[ServerlessParameters.SERVERLESS_REQUEST]

    # Form for user-uploaded TCL
    class Optional_Tcl(forms.Form):
        tcl_file = forms.FileField(required=False)

    if request.method == 'POST':
        # Check if user uploaded their own TCL script
        # form = Optional_Tcl(request.POST, request.FILES)
        # if not request.POST.__contains__('tcl_file'):
        #     # there is a file uploaded
        #     default_storage.delete(request.FILES['tcl_file'].name)
        #     default_storage.save(request.FILES['tcl_file'].name, request.FILES['tcl_file']) # replace the TCL file in S3

        # text_obj = request.session['text_obj']
        # private_key_file = io.StringIO(text_obj)
        # privkey = paramiko.RSAKey.from_private_key(private_key_file)
        # try:
        #     client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='simulation_confirmation')
        # except:
        #     sys.stdout.flush()
        #     messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        #     return HttpResponseRedirect('/application/aws')
        # client.exec_command('> ~/sim_run.log')
        # sys.stdout.flush()
        # client.close()
        # connections.close_all()

        # Transfer all neccessary files for simulation
        # p = Process(target=transfer_files_and_run_simulation, args=(request, ))
        # p.start()

        mesh_name = serverless_request[ServerlessParameters.MESH]
        base_name = serverless_request[ServerlessParameters.BASE]
        energy = request.session['totalEnergy']
        meshUnit = request.session['meshUnit']
        energyUnit = request.session['energyUnit']
        source = tclGeneratorWriter(request.session, mesh_name, meshUnit, energy, energyUnit, base_name)
        _initiate_serverless_simulation(source, serverless_request, request.user)

        # redirect to run simulation
        # request.session['start_time'] = str(datetime.now(timezone.utc))
        # request.session['started'] = "false"
        # request.session['peak_mem_usage'] = 0
        # request.session['peak_mem_usage_unit'] = 'GB'
        return HttpResponseRedirect('/application/serverless_running')

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
        'mesh_name': serverless_request[ServerlessParameters.MESH],
        'materials': materials,
        'light_sources': light_sources,
        'tcl_script_name': serverless_request[ServerlessParameters.TCL],
        'tcl_form': tcl_form,
        'unit': request.session['meshUnit'],
    }

    return render(request, 'simulation_confirmation.html', context)


def fmServerlessSimulatorMaterial(request):
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')

    # Info about the generated TCL
    # generated_tcl = tclScript.objects.filter(user = request.user).latest('id')
    serverless_request = request.session[ServerlessParameters.SERVERLESS_REQUEST]

    # Form for user-uploaded TCL
    class Optional_Tcl(forms.Form):
        tcl_file = forms.FileField(required=True)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # conn = DbConnection()
        # text_obj = request.session['text_obj']
        # private_key_file = io.StringIO(text_obj)
        # privkey = paramiko.RSAKey.from_private_key(private_key_file)
        # # try:
        #     client = SshConnection(hostname=request.session['DNS'], privkey=privkey, id='fmSimulatorMaterial')
        # except:
        #     sys.stdout.flush()
        #     messages.error(request, 'Error - looks like your AWS remote server is down, please check your instance in the AWS console and connect again')
        #     return HttpResponseRedirect('/application/aws')

        # Skip rest of setup if user uploaded their own TCL script
        if '_skip' in request.POST:
            request.session['material'] = []
            request.session['region_name'] = [] # for visualization legend
            request.session['scatteringCoeff'] = []
            request.session['absorptionCoeff'] = []
            request.session['refractiveIndex'] = []
            request.session['anisotropy'] = []

            form = Optional_Tcl(request.POST, request.FILES)
            if form.is_valid():

                # get power
                indicator = b' energyPowerValue '
                tcl_file = request.FILES['tcl_file']
                for line in tcl_file:
                    if indicator in line:
                        request.session['totalEnergy'] = float(line.split()[2])
                        break

                # file uploaded and "Submit and Run" button clicked
                # form = Optional_Tcl(request.POST, request.FILES)
                # default_storage.delete(request.FILES['tcl_file'].name)
                # default_storage.save(request.FILES['tcl_file'].name, request.FILES['tcl_file']) # save new TCL script to S3
                # print("uploading tcl", default_storage.path(request.FILES['tcl_file'].name))
                # print("uploading tcl2", request.FILES['tcl_file'].temporary_file_path())
                # print("uploading tcl2", request.FILES['tcl_file'].file_path)
                # print("uploading tcl2", request.FILES['tcl_file'].file.name)

                # tcl_file = default_storage.open(generated_tcl.script.name)
                # print(tcl_file)
                # to do error if tcl file does not only contain letters, numbers, hyphens and underscores
                #  Reading file from storage
                # file = default_storage.open(request.FILES['tcl_file'].name)
                # TODO
                temp_dest = "/tmp/uploaded_tcl_script.tcl"
                handle_uploaded_file(request.FILES['tcl_file'], temp_dest)
                # with open("uploaded_tcl_script.tcl", "w") as f:
                #     for line in file:
                #         f.write(str(line, encoding='utf-8'))
                # f.close()

                _initiate_serverless_simulation(temp_dest, serverless_request, request.user)
                # client.exec_command('> ~/sim_run.log')
                # sys.stdout.flush()
                # client.close()
                # connections.close_all()

                # transfer all necessary files to run simulation
                # p = Process(target=transfer_files_and_run_simulation, args=(request, ))
                # p.start()

                # # redirect to run simulation
                # request.session['start_time'] = str(datetime.now(timezone.utc))
                # request.session['started'] = "false"
                # request.session['peak_mem_usage'] = 0
                # request.session['peak_mem_usage_unit'] = 'GB'
                return HttpResponseRedirect('/application/serverless_running')

        # # Get all entries from materials formset and check whether it's valid
        else:
        #     client.close()
        #     connections.close_all()
        #     # transfer all necessary files to run simulation
        #     p = Process(target=transfer_files_for_input_mesh_visualization, args=(request, ))
        #     p.start()
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
                    request.session['material'].append(form.cleaned_data['material'])
                    request.session['region_name'].append(form.cleaned_data['material'])  # for visualization legend
                    request.session['scatteringCoeff'].append(form.cleaned_data['scatteringCoeff'])
                    request.session['absorptionCoeff'].append(form.cleaned_data['absorptionCoeff'])
                    request.session['refractiveIndex'].append(form.cleaned_data['refractiveIndex'])
                    request.session['anisotropy'].append(form.cleaned_data['anisotropy'])

                return HttpResponseRedirect('/application/serverless_simulator_source')
            return HttpResponseRedirect('/application/serverless_running')


    # If this is a GET (or any other method) create the default form.
    else:
        formset1 = materialSetSet(request.GET or None)
        tcl_form = Optional_Tcl()

        context = {
            'formset1': formset1,
            # 'unit': request.session['meshUnit'],
            'tcl_script_name': serverless_request[ServerlessParameters.TCL],
            'tcl_form': tcl_form,
        }

        return render(request, "serverless/serverless_simulator_material.html", context)


def fmServerlessSimulator(request):
    # First check if user is logged-in
    if not request.user.is_authenticated:
        return redirect('please_login')
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        print(request.POST)
        print(request.FILES)
        sys.stdout.flush()
        form = tclInputForm(data=request.POST, files=request.FILES)
        # formset3 = regionIDSet(request.POST)
        # check whether it's valid:
        if form.is_valid():
            print(form.cleaned_data)
            sys.stdout.flush()
            request.session['ec2_file_paths'] = []
            request.session['scoredVolumeRegionID'] = []
            # if request.POST['selected_existing_meshes'] != "":
            #     # to do trigger run of fullmonte vsi by uploading a file to a cos
            #     print("This is 1")
            #     # selected a mesh from database
            #     mesh_from_database = meshFiles.objects.filter(id=request.POST['selected_existing_meshes'])[0]

            #     obj = form.save(commit = False)
            #     obj.meshFile = mesh_from_database.meshFile
            #     obj.originalMeshFileName = mesh_from_database.originalMeshFileName
            #     obj.meshFileID = mesh_from_database
            #     obj.user = request.user
            #     obj.save()
            # else:
            print("This is 2")
            # uploaded a new mesh
            # process cleaned data from formsets
            obj = form.save(commit = False)
            obj.user = request.user
            obj.originalMeshFileName = obj.meshFile.name
            print(obj.originalMeshFileName )
            obj.save()
            print(obj)
            sys.stdout.flush()

            # no need to save
            # # create entry for the newly uploaded meshfile
            # new_mesh_entry = meshFiles()
            # new_mesh_entry.meshFile = obj.meshFile
            # new_mesh_entry.originalMeshFileName = obj.originalMeshFileName
            # new_mesh_entry.user = request.user
            # new_mesh_entry.save()

            # update meshfile id
            # obj.meshFileID = new_mesh_entry
            # obj.save()
            # meshname = tclInput.objects.filter(user = request.user).latest('id').meshFile.file.name
            # print("default_storage.path(meshname)", meshname)

            # print(request.FILES['meshFile'].file.name)
            # upload random mesh
            # print(request.FILES['meshFile'].file.name)

            print(form.cleaned_data['kernelType'])

            selected_abosrbed = 'Absorbed' in form.cleaned_data['kernelType']
            selected_leaving = 'Leaving' in form.cleaned_data['kernelType']
            selected_internal = 'Internal' in form.cleaned_data['kernelType']

            # using_gpu = request.session['GPU_instance'] # set up cudo on instances
            using_gpu = False
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
            # for regionID in formset3:
            #     print(regionID.cleaned_data)
            #     request.session['scoredVolumeRegionID'].append(regionID.cleaned_data['scoredVolumeRegionID'])
            sys.stdout.flush()
            request.session['packetCount'] = form.cleaned_data['packetCount']
            request.session['totalEnergy'] = form.cleaned_data['totalEnergy']
            request.session['energyUnit'] = form.cleaned_data['energyUnit']

            # if request.POST.get("overwrite_on_ec2") == "True":
            #     request.session['overwrite_on_ec2'] = True
            # else:
            #     request.session['overwrite_on_ec2'] = False

            # generate empty TCL template TO DO EDIT:
            # mesh = tclInput.objects.filter(user = request.user).latest('id')
            # class meshFile:
            #     def __init__(self, name):
            #         self.name = name
            # class mesh_serverless:
            #     def __init__(self, name):
            #         self.originalMeshFileName = name
            #         self.meshFile = meshFile(name)
            #
            # mesh_serverless = mesh_serverless(obj.originalMeshFileName)

            serverless_request = ServerlessParameters(obj.originalMeshFileName)
            request.session[ServerlessParameters.SERVERLESS_REQUEST] = serverless_request.__dict__
            print(request.session[ServerlessParameters.SERVERLESS_REQUEST])
            energy = request.session['totalEnergy']
            meshUnit = request.session['meshUnit']
            energyUnit = request.session['energyUnit']
            source_path = emptyTclTemplateGeneratorServerless(
                request.session, serverless_request.mesh_name, meshUnit, energy, energyUnit, request.user
            )
            # save to ibm cloud storage object
            cos_upload_file(settings.IBM_COS_GENERATED_TCL_BUCKET_NAME, serverless_request.tcl_name, source_path)
            # TODO consider moving upload mesh to just before tcl upload to reduce setup latency
            cos_upload_file(
                settings.IBM_COS_MESH_BUCKET_NAME, serverless_request.mesh_name, request.FILES['meshFile'].file.name
            )
            return HttpResponseRedirect('/application/serverless_simulator_material')

    # If this is a GET (or any other method) create the default form.
    else:
        form = tclInputForm()
        # formset3 = regionIDSet(request.GET or None)

    uploaded_meshes = meshFiles.objects.filter(user=request.user)
    context = {
        'form': form,
        # 'formset3': formset3,
        'uploaded_meshes': uploaded_meshes,
    }

    return render(request, "serverless/serverless_simulator.html", context)


def serverless_simulation_finish(request):
    # create mesh output name
    meshName = tclInput.objects.filter(user = request.user).latest('id').meshFile.name[:tclInput.objects.filter(user = request.user).latest('id').meshFile.name.index(".")]
    unique_tclName = str(meshName + '.tcl-') # TO DO: NANCY WILL APPEND UNIQUE USER ID
    meshFileOutputName = str(unique_tclName + meshName +'.mesh.out.vtk')
    context = {
        'output_files': meshFileOutputName
    }
    return render(request, 'serverless/serverless_simulation_finish.html', context)
