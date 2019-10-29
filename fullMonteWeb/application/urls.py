from django.urls import path

from . import views

urlpatterns = [
    # /application
    path('', views.home, name='home'),
            
    # /application/tutorial
    path('tutorial', views.fmTutorial, name='tutorial'),
               
    # /application/simulator
    path('simulator', views.fmSimulator, name='simulator'),
               
    # /application/visualization
    path('visualization', views.fmVisualization, name='visualization'),
]
