from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url

from django.conf.urls import url

from . import views
from application.serverless import views as serverless_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    ####################### home #######################
    # /application
    path('', views.home, name='home'),

    ####################### tutorial #######################
    # /application/tutorial
    path('tutorial', views.fmTutorial, name='tutorial'),

    ####################### AWS #######################
    # /application/aws
    path('aws', views.aws, name='aws'),

    # /application/AWSsetup
    path('AWSsetup', views.AWSsetup, name='AWSsetup'),

    ####################### AWS simulator #######################
    # /application/simulator
    path('simulator', views.fmSimulator, name='simulator'),

    # /application/simulator_material
    path('simulator_material', views.fmSimulatorMaterial, name='simulator_material'),

    # /application/simulator_source
    path('simulator_source', views.fmSimulatorSource, name='simulator_source'),

    # /application/running
    path('running', views.running, name='running'),

    # /application/simulation_finish
    path('simulation_finish', views.simulation_finish, name='simulation_finish'),
    url(r'download_from_ec2/(?P<filepath>.*)$', views.ec2fileDownloadView, name='ec2_file_download'),

    # /application/preparing_download
    path('preparing_download', views.preparing_download, name='preparing_download'),

    # /application/simulation_confirmation
    path('simulation_confirmation', views.simulation_confirmation, name='simulation_confirmation'),

    # /application/kernel_info
    path('kernel_info', views.kernelInfo, name='kernel_info'),

    ####################### serverless simulator #######################
    # /application/serverless_simulator
    # path('serverless_simulator', serverless_views.fmServerlessSimulator, name='serverless_simulator'),
    path('serverless_simulator', views.fmServerlessSimulator, name='serverless_simulator'),

    # /application/simulator_material
    path('serverless_simulator_material', views.fmServerlessSimulatorMaterial, name='serverless_simulator_material'),

    # /application/simulator_source
    path('serverless_simulator_source', views.fmServerlessSimulatorSource, name='serverless_simulator_source'),

    # /application/serverless_running
    # path('serverless_running', serverless_views.serverless_running, name='serverless_running'),
    path('serverless_running', views.serverless_running, name='serverless_running'),

    # serverless files download
    url(r'cos_d/(?P<filename>[-\w_\\-\\.]+)&bucket=(?P<bucket>[-\w_\\-\\.]+)/$',
        serverless_views.cos_download_view, name='serverless_cos_download'),

    # /application/recommendation
    path('recommendation', views.instance_recommendation, name='recommendation'),

    ####################### visualization #######################
    # /application/visualization
    path('visualization', views.fmVisualization, name='visualization'),

    # /application/threshold_fluence_upload
    path('threshold_fluence_upload', views.visualization_threshold_fluence_upload, name='threshold_fluence_upload'),

    # /application/mesh_upload
    path('mesh_upload', views.visualization_mesh_upload, name='mesh_upload'),

    # /application/runningDVH
    path('runningDVH', views.runningDVH, name='runningDVH'),
    
    # /application/displayVisualization
    path('displayVisualization', views.displayVisualization, name='displayVisualization'),
    
    ####################### history #######################
    # /application/simulation_history
    path('simulation_history', views.simulation_history, name='simulation_history'),
    url(r'download/(?P<filename>[-\w_\\-\\.]+)(&output_name=(?P<originalfilename>[-\w_\\-\\.]+))?$', views.fileDownloadView.as_view(), name='file_download'),

    ####################### PDT-SPACE #######################
    path('pdt_space', views.pdt_space, name='pdt_space'),
    
    # /application/pdt_spcae_wait
    path('pdt_spcae_wait', views.pdt_spcae_wait, name='pdt_spcae_wait'),

    # /application/pdt_space_license
    path('pdt_space_license', views.pdt_space_license, name='pdt_space_license'),

    # /application/pdt_space_material
    path('pdt_space_material', views.pdt_space_material, name='pdt_space_material'),

    # /application/pdt_space_lightsource
    path('pdt_space_lightsource', views.pdt_space_lightsource, name='pdt_space_lightsource'),

    # /application/pdt_space_running
    path('pdt_space_running', views.pdt_space_running, name='pdt_space_running'),

    # /application/pdt_space_finish
    path('pdt_space_finish', views.pdt_space_finish, name='pdt_space_finish'),

    # /application/pdt_space_fail
    path('pdt_space_fail', views.pdt_space_fail, name='pdt_space_fail'),

    # /application/pdt_space_visualization
    path('pdt_space_visualization', views.pdt_space_visualization, name='pdt_space_visualization'),

    # /application/pdt_space_wait_visualization
    path('pdt_space_wait_visualization', views.pdt_space_wait_visualization, name='pdt_space_wait_visualization'),
    
    # /application/pdt_space_display_visualization
    path('pdt_space_display_visualization', views.pdt_space_display_visualization, name='pdt_space_display_visualization'),
    
    # /application/pdt_space_visualize
    path('pdt_space_visualize', views.pdt_space_visualize, name='pdt_space_visualize'),

    ####################### presets #######################
    # /application/create_preset_material
    path('create_preset_material', views.createPresetMaterial, name='create_preset_material'),

    ####################### account & registration #######################
    url(r'^password_reset/$', auth_views.PasswordResetView.as_view() , name='password_reset'),
    url(r'^password_reset/done/$', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    url(r'^reset/done/$', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('registration/accounts/signup', views.signup , name = 'signup'),

    path('login', views.LoginView.as_view(), name='login'),

    path('logout', views.LogoutView.as_view(), name='logout'),

    url(r'^ajax_requests/', views.ajaxrequests_view, name='ajax_requests'),

    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.activate, name='activate'),

    path('account', views.account, name='account'),

    url(r'^change_password/$', views.change_password, name='change_password'),

    path('please_login', views.please_login, name='please_login'),

    ####################### not in use (for now) #######################
    # /application/about
    path('about', views.about, name='about'),

    # /application/download_preset
    path('download_preset', views.downloadPreset, name='download_preset'),

    # /application/heroku_timeout    
    path('heroku_timeout', views.heroku_timeout, name='heroku_timeout'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
