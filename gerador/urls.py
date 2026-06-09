from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('gerar/', views.gerar_provas, name='gerar_provas'),
    
    # A nova rota secreta do admin
    path('admin-treinar/', views.treinar_ia, name='treinar_ia'),
]