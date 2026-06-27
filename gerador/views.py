import os
import json
import re
import PyPDF2
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from openai import OpenAI
from .models import Curso, Topico, EsqueletoQuestao

# ---------------------------------------------------------
# CONFIGURAÇÃO DA IA (NVIDIA NIM - DeepSeek R1)
# ---------------------------------------------------------
# Cole a sua chave gerada no site build.nvidia.com aqui dentro das aspas:
api_key =os.environ.get("NVIDIA_API_KEY")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key
)


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
                continue  # Pula se o bloco estiver vazio

            topico_base = Topico.objects.get(id=topicos_ids[i])
            # Sorteia um esqueleto qualquer dentro deste tópico no banco
            esqueleto = EsqueletoQuestao.objects.filter(topico=topico_base).order_by('?').first()

            qtd_itens = int(qtd_itens_lista[i])
            formato = formatos_lista[i]

            instrucoes_questoes += f"--- Questão {i + 1} ---\n"
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
            # NOVA CHAMADA PARA A NVIDIA (DeepSeek R1)
            resposta_completa = client.chat.completions.create(
                model="deepseek-ai/deepseek-v4-pro",
                messages=[{"role": "user", "content": prompt_final}],
                temperature=0.3,
                max_tokens=4096
            )

            texto_bruto = resposta_completa.choices[0].message.content
            # Remove a tag <think> gerada pelo DeepSeek para exibir apenas o LaTeX
            resposta_final = re.sub(r'<think>.*?</think>', '', texto_bruto, flags=re.DOTALL).strip()

            # Retorna o LaTeX puro na tela
            return HttpResponse(f"<pre style='white-space: pre-wrap; padding: 20px;'>{resposta_final}</pre>")

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

        # O Super Prompt para a engenharia reversa
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
            # NOVA CHAMADA PARA A NVIDIA (DeepSeek R1)
            resposta_completa = client.chat.completions.create(
                model="deepseek-ai/deepseek-r1",
                messages=[{"role": "user", "content": prompt_treinamento}],
                temperature=0.3,
                max_tokens=4096
            )

            texto_bruto = resposta_completa.choices[0].message.content
            # Remove a tag <think>
            texto_sem_think = re.sub(r'<think>.*?</think>', '', texto_bruto, flags=re.DOTALL).strip()

            # Limpa o texto caso a IA coloque markdown de JSON
            json_limpo = re.sub(r'```json|```', '', texto_sem_think).strip()
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

            messages.success(request,
                             f"Sucesso! A IA leu o PDF e cadastrou {novos_cadastros} novos esqueletos no banco.")

        except Exception as e:
            messages.error(request, f"Erro ao processar pela IA: {str(e)}")

    return render(request, 'gerador/treinar.html')