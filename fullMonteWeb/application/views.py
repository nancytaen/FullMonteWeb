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

# FullMonte About page
def about(request):
    return render(request, "about.html")

# FullMonte Simulator page
def fmSimulator(request):
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        form = tclInput(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            materialSetSet = form.materialSetSet
            lightSourceSet = form.lightSourceSet
            
            #debugging
            
            # redirect to a new URL:
            return HttpResponseRedirect('/application/visualization')

    # If this is a GET (or any other method) create the default form.
    else:
        form = tclInput()
    
    context = {
        'form': form,
    }

    return render(request, "simulator.html", context)

# FullMonte Output page
def fmVisualization(request):
    return render(request, "visualization.html")
