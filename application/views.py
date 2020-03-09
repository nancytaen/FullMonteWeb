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
            request.session['power'] = []

            for form in formset2:
                #print(form.cleaned_data)
                request.session['sourceType'].append(form.cleaned_data['sourceType'])
                request.session['xPos'].append(form.cleaned_data['xPos'])
                request.session['yPos'].append(form.cleaned_data['yPos'])
                request.session['zPos'].append(form.cleaned_data['zPos'])
                request.session['power'].append(form.cleaned_data['power'])

            mesh = tclInput.objects.latest('id')

            script_path = tclGenerator(request.session, mesh)

            request.session['script_path'] = script_path

            #print(tclInput.objects.all())
            #tclInput.objects.all().delete()
            #print(mesh.meshFile)
            #print(tclInput.objects.all())
            return HttpResponseRedirect('/application/tcl_viewer')

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
        tclScript.objects.all().delete()
        tclInput.objects.all().delete()

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
