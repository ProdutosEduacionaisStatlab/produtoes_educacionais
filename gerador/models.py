from django.db import models

class Disciplina(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da Disciplina")

    def __str__(self):
        return self.nome  # Retiramos o self.codigo daqui!
    
    
class Topico(models.Model):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="topicos")
    nome = models.CharField(max_length=100, verbose_name="Nome do Tópico")

    def __str__(self):
        return f"{self.disciplina.nome} > {self.nome}"

class Questao(models.Model):
    topico = models.ForeignKey(Topico, on_delete=models.CASCADE, related_name="questoes")
    
    enunciado = models.TextField(verbose_name="Enunciado (LaTeX)")
    
    # As 10 alternativas que virão das colunas do CSV
    alt_1 = models.CharField(max_length=500, verbose_name="Alternativa 1")
    alt_2 = models.CharField(max_length=500, verbose_name="Alternativa 2")
    alt_3 = models.CharField(max_length=500, verbose_name="Alternativa 3")
    alt_4 = models.CharField(max_length=500, verbose_name="Alternativa 4")
    alt_5 = models.CharField(max_length=500, verbose_name="Alternativa 5")
    alt_6 = models.CharField(max_length=500, verbose_name="Alternativa 6")
    alt_7 = models.CharField(max_length=500, verbose_name="Alternativa 7")
    alt_8 = models.CharField(max_length=500, verbose_name="Alternativa 8")
    alt_9 = models.CharField(max_length=500, verbose_name="Alternativa 9")
    alt_10 = models.CharField(max_length=500, verbose_name="Alternativa 10")
    
    # O sistema precisa saber qual dessas 10 é a correta (Ex: 3)
    correta = models.IntegerField(verbose_name="Qual a correta? (1 a 10)")
    
    resolucao = models.TextField(verbose_name="Resolução Comentada")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Questão {self.id} | {self.topico.nome}"