from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

# homepage
def home(request):
    return render(request, "home.html")

# FullMonte Tutorial page
def fmTutorial(request):
    return render(request, "tutorial.html")

# FullMonte Simulator page
def fmSimulator(request):
    return render(request, "simulator.html")

# FullMonte Output page
def fmVisualization(request):
    return render(request, "visualization.html")
