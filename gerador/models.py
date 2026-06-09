from django.db import models

class Curso(models.Model):
    nome = models.CharField(max_length=200)
    descricao_contexto = models.TextField(help_text="Ex: Focado em biologia marinha, aquicultura e clima.")

    def __str__(self):
        return self.nome

class Topico(models.Model):
    nome = models.CharField(max_length=200)

    def __str__(self):
        return self.nome

class EsqueletoQuestao(models.Model):
    topico = models.ForeignKey(Topico, on_delete=models.CASCADE)
    subtopico = models.CharField(max_length=200, blank=True, null=True, help_text="Ex: Eventos Independentes")
    enunciado_base = models.TextField(help_text="A estrutura matemática rígida da questão.")
    instrucoes_ia = models.TextField(help_text="Regras de sorteio e contexto para o Gemini.")

    def __str__(self):
        if self.subtopico:
            return f"{self.topico.nome} - {self.subtopico}"
        return self.topico.nome