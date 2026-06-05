from django.contrib import admin
from django.urls import path, include
from gerador import views # Verifique se isso já está aí

urlpatterns = [
    path('admin/', admin.site.urls),
    # Essa linha diz: "Qualquer acesso na página inicial, mande para o aplicativo gerador"
    path('', include('gerador.urls')), 
]