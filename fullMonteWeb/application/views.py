from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from .forms import tclInput

# Create your views here.

# homepage
def home(request):
    return render(request, "home.html")

# FullMonte Tutorial page
def fmTutorial(request):
    return render(request, "tutorial.html")

# FullMonte Simulator page
def fmSimulator(request):
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        form = tclInput(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            material = request.POST.get('material')
            scatteringCoeff = request.POST.get('scatteringCoeff')
            absorptionCoeff = request.POST.get('absorptionCoeff')
            refractiveIndex = request.POST.get('refractiveIndex')
            anisotropy = request.POST.get('anisotropy')
            
            sourceType = request.POST.get('sourceType')
            xPos = request.POST.get('xPos')
            yPos = request.POST.get('yPos')
            zPos = request.POST.get('zPos')
            power = request.POST.get('power')
            
            #debugging
            
            # redirect to a new URL:
            return HttpResponseRedirect('/application/visualization')

    # If this is a GET (or any other method) create the default form.
    else:
        form = tclInput()
        if request.method == 'GET':
            if request.GET.get('addMatSet'):
                form.materialSetSet.append(tclInput.materialSet())
            if request.GET.get('removeMatSet'):
                if len(form.materialSetSet) is not 0:
                    form.materialSetSet.pop()
            if request.GET.get('addLightSource'):
                form.lightSourceSet.append(tclInput.lightSource())
            if request.GET.get('removeLightSource'):
                if len(form.lightSourceSet) is not 0:
                    form.lightSourceSet.pop()

    context = {
        'form': form,
    }

    return render(request, "simulator.html", context)

# FullMonte Output page
def fmVisualization(request):
    return render(request, "visualization.html")
