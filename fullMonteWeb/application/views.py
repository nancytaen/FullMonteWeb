from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from .forms import *

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
        form = tclInput(request.POST, request.FILES)
        
        # check whether it's valid:
        print(form.data)
        
        return HttpResponseRedirect('/application/simulator_material')

    # If this is a GET (or any other method) create the default form.
    else:
        form = tclInput(request.GET or None)
        
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
            # print(formset1.data)
            
            for form in formset1:
                print(form.cleaned_data)
            
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
            # print(formset2.data)
            
            for form in formset2:
                print(form.cleaned_data)
            
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
    return render(request, "visualization.html")
