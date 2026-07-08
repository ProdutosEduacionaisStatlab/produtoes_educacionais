from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Curso, Topico, EsqueletoQuestao

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    pass  # O modo mais seguro possível. O Django decide o que mostrar.

@admin.register(Topico)
class TopicoAdmin(admin.ModelAdmin):
    pass  # Nada de tentar chamar colunas que podem não existir.

@admin.register(EsqueletoQuestao)
class EsqueletoQuestaoAdmin(ImportExportModelAdmin):
    list_display = ('id', 'topico', 'subtopico')