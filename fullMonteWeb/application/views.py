from django.shortcuts import render
from django.http import HttpResponse
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
    form = tclInput(request.POST or None)
    if request.method == 'POST':
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            material = request.POST.get('material')
            scatteringCoeff = request.POST.get('scatteringCoeff')
            absorptionCoeff = request.POST.get('absorptionCoeff')
            refractiveIndex = request.POST.get('refractiveIndex')
            anisotropy = request.POST.get('anisotropy')
            
            type = request.POST.get('type')
            xPos = request.POST.get('xPos')
            yPos = request.POST.get('yPos')
            zPos = request.POST.get('zPos')
            power = request.POST.get('power')
            # redirect to a new URL:
            return HttpResponseRedirect('/application/')
    return render(request, "simulator.html", {'form': form})

# FullMonte Output page
def fmVisualization(request):
    return render(request, "visualization.html")
