from django.urls import path
from . import views

urlpatterns = [
    # A página inicial com o formulário da IA
    path('', views.index, name='index'),
    
    # A rota invisível que recebe os dados e chama o Gemini para gerar a prova
    path('gerar/', views.gerar_provas, name='gerar_provas'),
]