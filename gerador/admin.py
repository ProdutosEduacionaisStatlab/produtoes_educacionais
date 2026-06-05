from django.contrib import admin
from .models import Disciplina, Topico, Questao

# Isso avisa o painel do Django para mostrar nossas tabelas
admin.site.register(Disciplina)
admin.site.register(Topico)
admin.site.register(Questao)