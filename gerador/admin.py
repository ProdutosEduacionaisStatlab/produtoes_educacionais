from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Curso, Topico, EsqueletoQuestao

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'nivel')

@admin.register(Topico)
class TopicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'curso')

@admin.register(EsqueletoQuestao)
class EsqueletoQuestaoAdmin(ImportExportModelAdmin):
    list_display = ('id', 'topico', 'nivel') # Mostra essas colunas na tela