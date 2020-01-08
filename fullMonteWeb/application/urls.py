from django.urls import path

from . import views

urlpatterns = [
    # /application
    path('', views.home, name='home'),
            
    # /application/tutorial
    path('tutorial', views.fmTutorial, name='tutorial'),
               
    # /application/simulator
    path('simulator', views.fmSimulator, name='simulator'),
               
    # /application/simulator_material
    path('simulator_material', views.fmSimulatorMaterial, name='simulator_material'),
               
    # /application/simulator_source
    path('simulator_source', views.fmSimulatorSource, name='simulator_source'),
               
    # /application/visualization
    path('visualization', views.fmVisualization, name='visualization'),

    # /application/about
    path('about', views.about, name='about'),
]
