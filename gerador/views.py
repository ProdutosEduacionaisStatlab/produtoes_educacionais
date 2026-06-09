import os
import json
import re
import PyPDF2
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
import google.generativeai as genai

from .models import Curso, Topico, EsqueletoQuestao

# ---------------------------------------------------------
# CONFIGURAÇÃO DE SEGURANÇA DA API (Do seu código!)
# ---------------------------------------------------------
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("AVISO: Chave da API do Google não encontrada nas variáveis de ambiente!")

modelo = genai.GenerativeModel('gemini-1.5-flash')


# ---------------------------------------------------------
# 1. PÁGINA INICIAL (O CONSTRUTOR LEGO)
# ---------------------------------------------------------
def index(request):
    cursos = Curso.objects.all()
    topicos = Topico.objects.all()
    return render(request, 'gerador/index.html', {'cursos': cursos, 'topicos': topicos})


# ---------------------------------------------------------
# 2. MOTOR DE GERAÇÃO DE PROVAS (RECEBE O MODO LEGO)
# ---------------------------------------------------------
def gerar_provas(request):
    if request.method == 'POST':
        # Captura os dados gerais
        curso_id = request.POST.get('curso')
        curso = Curso.objects.get(id=curso_id) if curso_id else None

        # Captura as LISTAS enviadas pelos blocos de Lego
        topicos_ids = request.POST.getlist('bloco_topico[]')
        qtd_itens_lista = request.POST.getlist('bloco_qtd_itens[]')
        formatos_lista = request.POST.getlist('bloco_formato[]')

        # Inicia a montagem do Super Prompt
        contexto_prova = f"Crie uma avaliação de Estatística. Público-alvo: {curso.nome}. Contexto: {curso.descricao_contexto}\n\n"
        instrucoes_questoes = ""

        # Loop passando por cada bloco de Lego que o professor adicionou
        for i in range(len(topicos_ids)):
            if not topicos_ids[i]: 
                continue # Pula se o bloco estiver vazio
            
            topico_base = Topico.objects.get(id=topicos_ids[i])
            # Sorteia um esqueleto qualquer dentro deste tópico no banco
            esqueleto = EsqueletoQuestao.objects.filter(topico=topico_base).order_by('?').first()
            
            qtd_itens = int(qtd_itens_lista[i])
            formato = formatos_lista[i]

            instrucoes_questoes += f"--- Questão {i+1} ---\n"
            instrucoes_questoes += f"Tópico: {topico_base.nome}\n"
            
            if esqueleto:
                instrucoes_questoes += f"Base Matemática: {esqueleto.enunciado_base}\n"
                instrucoes_questoes += f"Regras de Sorteio dos Números: {esqueleto.instrucoes_ia}\n"
            
            # Aplica as regras de formato que o professor escolheu na tela
            if qtd_itens > 0:
                instrucoes_questoes += f"Formato Exigido: Crie {qtd_itens} subitens (a, b, c...) do tipo {formato}.\n\n"
            else:
                instrucoes_questoes += f"Formato Exigido: Questão direta (sem subitens), do tipo {formato}.\n\n"

        prompt_final = f"""
        Você é um professor universitário de estatística experiente.
        Crie as questões usando EXATAMENTE as regras matemáticas e de formato abaixo.
        
        {contexto_prova}
        
        ESTRUTURA DAS QUESTÕES:
        {instrucoes_questoes}
        
        Escreva a prova inteira em código LaTeX limpo, pronto para compilar. 
        Não use markdown como ```latex, devolva apenas o texto puro do código.
        """

        try:
            resposta = modelo.generate_content(
    		prompt_final, # ou prompt_treinamento na outra função
    		generation_config=genai.types.GenerationConfig(temperature=0.3))
            
            # Por enquanto, retorna o LaTeX puro na tela para podermos copiar e testar no Overleaf
            return HttpResponse(f"<pre style='white-space: pre-wrap; padding: 20px;'>{resposta.text}</pre>")
            
        except Exception as e:
            return HttpResponse(f"<h3>Erro na IA:</h3> <p>{str(e)}</p>")

    return render(request, 'gerador/index.html')


# ---------------------------------------------------------
# 3. SALA DE TREINAMENTO (LEITOR DE PDF DO ADMIN)
# ---------------------------------------------------------
@staff_member_required
def treinar_ia(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        arquivo = request.FILES['arquivo']
        texto_extraido = ""

        # Lê o texto do PDF
        if arquivo.name.endswith('.pdf'):
            leitor = PyPDF2.PdfReader(arquivo)
            for pagina in leitor.pages:
                texto_extraido += pagina.extract_text()

        # O Super Prompt para o Gemini fazer a engenharia reversa
        prompt_treinamento = f"""
        Você é um Engenheiro de Dados Educacionais. Leia esta lista de exercícios de estatística e extraia a estrutura matemática das questões.
        Ignore cabeçalhos, números das questões e gabaritos.
        Para cada tipo de questão diferente, crie um molde generalista.
        
        Devolva APENAS um código JSON válido (sem formatação markdown) neste formato exato:
        [
            {{
                "topico": "Nome do Tópico (Ex: Probabilidade)",
                "subtopico": "Nome do Subtópico (Ex: Teorema de Bayes)",
                "enunciado_base": "O enunciado original com variáveis (X, Y, Z) no lugar dos números fixos",
                "instrucoes_ia": "Regras para sortear X, Y e Z e a fórmula genérica para resolver"
            }}
        ]

        Texto da lista de exercícios:
        {texto_extraido}
        """

        try:
            resposta = modelo.generate_content(prompt_treinamento)
            
            # Limpa o texto caso o Gemini coloque markdown
            json_limpo = re.sub(r'```json|```', '', resposta.text).strip()
            esqueletos = json.loads(json_limpo)

            # Salva no Banco de Dados
            novos_cadastros = 0
            for item in esqueletos:
                topico_obj, created = Topico.objects.get_or_create(nome=item['topico'])
                
                EsqueletoQuestao.objects.create(
                    topico=topico_obj,
                    subtopico=item['subtopico'],
                    enunciado_base=item['enunciado_base'],
                    instrucoes_ia=item['instrucoes_ia']
                )
                novos_cadastros += 1

            messages.success(request, f"Sucesso! A IA leu o PDF e cadastrou {novos_cadastros} novos esqueletos no banco.")
            
        except Exception as e:
            messages.error(request, f"Erro ao processar pela IA: {str(e)}")

    return render(request, 'gerador/treinar.html')