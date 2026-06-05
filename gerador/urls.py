from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('importar/', views.importar_csv, name='importar_csv'),
    path('api/carregar-dados/', views.carregar_dados_disciplina, name='carregar_dados'),
    path('previa/', views.previa_prova, name='previa'),
    path('gerar/', views.gerar_provas, name='gerar_provas'), # A ROTA DA MÁQUINA
]