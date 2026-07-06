from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('gerar/', views.gerar_provas, name='gerar_provas'),
    path('admin-treinar/', views.treinar_ia, name='treinar_ia'),
    path('baixar-latex/', views.baixar_latex, name='baixar_latex'),
    path('baixar-pacote/', views.baixar_pacote_prova, name='baixar_pacote'),
]