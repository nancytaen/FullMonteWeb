from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url

from django.conf.urls import url

from . import views
from django.contrib.auth import views as auth_views

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

    # /application/download_output
    path('download_output', views.downloadOutput, name='download_output'),

    # /application/kernel_info
    path('kernel_info', views.kernelInfo, name='kernel_info'),

    # /application/download_preset
    path('download_preset', views.downloadPreset, name='download_preset'),

    # /application/create_preset_material
    path('create_preset_material', views.createPresetMaterial, name='create_preset_material'),

    # /application/aws
    path('aws', views.aws, name='aws'),

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

    path('running', views.running, name='running'),
    
    path('AWSsetup', views.AWSsetup, name='AWSsetup'),

    path('simulation_fail', views.simulation_fail, name='simulation_fail'),

    path('simulation_finish', views.simulation_finish, name='simulation_finish'),
               
    path('heroku_timeout', views.heroku_timeout, name='heroku_timeout'),

    path('mesh_upload', views.visualization_mesh_upload, name='mesh_upload'),
    
    path('displayVisualization', views.displayVisualization, name='displayVisualization'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
