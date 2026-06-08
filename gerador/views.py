import os
import subprocess
import tempfile
import zipfile
import io
import re
from datetime import datetime
import google.generativeai as genai

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from .models import Curso, Topico, EsqueletoQuestao

@login_required(login_url='/admin/login/')
def index(request):
    # Carrega os cursos e tópicos para o professor escolher na tela inicial
    cursos = Curso.objects.all()
    topicos = Topico.objects.all()
    return render(request, 'gerador/index.html', {'cursos': cursos, 'topicos': topicos})

@login_required(login_url='/admin/login/')
def gerar_provas(request):
    if request.method != 'POST':
        return redirect('index')

    professor = request.POST.get('professor', '')
    periodo = request.POST.get('periodo', '')
    data_prova_str = request.POST.get('data_prova', '')
    curso_id = request.POST.get('curso')
    topicos_selecionados = request.POST.getlist('topicos')
    num_questoes = int(request.POST.get('num_questoes', 3))
    num_versoes = int(request.POST.get('num_versoes', 1))

    data_formatada = ""
    if data_prova_str:
        data_formatada = datetime.strptime(data_prova_str, '%Y-%m-%d').strftime('%d/%m/%Y')

    try:
        curso_escolhido = Curso.objects.get(id=curso_id)
    except Curso.DoesNotExist:
        messages.error(request, "Por favor, selecione um curso válido.")
        return redirect('index')

    # Filtra os esqueletos baseados nos tópicos escolhidos
    esqueletos_db = list(EsqueletoQuestao.objects.filter(topico_id__in=topicos_selecionados).order_by('?')[:num_questoes])

    if not esqueletos_db:
        messages.error(request, "Nenhum esqueleto de questão encontrado para os tópicos selecionados.")
        return redirect('index')

    # Configura a IA
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    modelo = genai.GenerativeModel('gemini-1.5-flash')

    nome_arquivo_zip = curso_escolhido.nome.replace(" ", "_")

    # Seu Template LaTeX Original (Adaptado para questões abertas)
    BASE_CONFIG = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath, amssymb}
\usepackage{mathpazo} 
\linespread{1.15} 
\usepackage{geometry}
\usepackage{enumitem}
\geometry{margin=2cm}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.3em}
\begin{document}
"""

    TEMPLATE_PROVA = BASE_CONFIG + r"""
\begin{center}
    {\large \textbf{UNIVERSIDADE FEDERAL DO CEARÁ}} \\[0.1cm]
    {\large \textbf{DEPARTAMENTO DE ESTATÍSTICA E MATEMÁTICA APLICADA}} \\[0.3cm]
   {\large \textbf{Avaliação Oficial de Estatística - <<CURSO>>}}
\end{center}
\vspace{0.2cm}\hrule\vspace{0.4cm}
\noindent \textbf{Professor:} <<PROFESSOR>> \hfill \textbf{Semestre:} <<PERIODO>> \hfill \textbf{Data:} <<DATA>>
\vspace{0.4cm}
\noindent \textbf{Aluno(a):} \rule{8cm}{0.5pt} \hfill \textbf{Matrícula:} \rule{2.5cm}{0.5pt} \hfill \textbf{Versão:} <<VERSAO>>
\vspace{0.4cm}\hrule\vspace{0.6cm}
\begin{enumerate}[label=\textbf{\arabic*.}, leftmargin=*]
<<QUESTOES>>
\end{enumerate}
\end{document}
"""

    buffer = io.BytesIO()

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            latex_gabarito_global = ""

            for versao in range(1, num_versoes + 1):
                latex_questoes = ""
                latex_gabarito_global += f"\\subsection*{{Gabarito - Versão {versao}}}\n\\begin{{enumerate}}[label=\\textbf{{\\arabic*.}}, leftmargin=*]\n"
                
                # Para cada esqueleto, pedimos para a IA gerar uma variação única
                for q in esqueletos_db:
                    prompt = f"""
                    Você é um gerador de provas de estatística em LaTeX.
                    Gere UMA questão baseada na seguinte estrutura, mas contextualizada para alunos de {curso_escolhido.nome} ({curso_escolhido.descricao_contexto}).
                    
                    ESTRUTURA BASE: {q.enunciado_base}
                    INSTRUÇÕES: {q.instrucoes_ia}
                    
                    Formate a saída EXATAMENTE em dois blocos de texto puro, separados pela palavra "DIVISOR_GABARITO".
                    Não use blocos de código Markdown (```latex). Apenas o texto.
                    Use notação LaTeX para matemática ($ ou $$).
                    
                    Exemplo do formato esperado:
                    O enunciado da questão aqui com variáveis sorteadas.
                    DIVISOR_GABARITO
                    A resolução detalhada aqui com os cálculos.
                    """
                    
                    resposta = modelo.generate_content(prompt).text
                    
                    # Separa o enunciado da resolução
                    partes = resposta.split("DIVISOR_GABARITO")
                    enunciado_gerado = partes[0].strip()
                    resolucao_gerada = partes[1].strip() if len(partes) > 1 else "Resolução indisponível."

                    # Adiciona na Prova
                    latex_questoes += f"\\item {enunciado_gerado}\n\n\\vspace{{3cm}}\n\n"
                    
                    # Adiciona no Gabarito
                    latex_gabarito_global += f"\\item \\textbf{{Enunciado:}} {enunciado_gerado}\n\n\\textbf{{Resolução:}} {resolucao_gerada}\n\n\\vspace{{1cm}}\n"

                latex_gabarito_global += "\\end{enumerate}\n\\newpage\n"

                # Compila a prova PDF
                conteudo_tex = TEMPLATE_PROVA.replace("<<CURSO>>", curso_escolhido.nome)
                conteudo_tex = conteudo_tex.replace("<<PROFESSOR>>", professor)
                conteudo_tex = conteudo_tex.replace("<<PERIODO>>", periodo)
                conteudo_tex = conteudo_tex.replace("<<DATA>>", data_formatada)
                conteudo_tex = conteudo_tex.replace("<<VERSAO>>", str(versao))
                conteudo_tex = conteudo_tex.replace("<<QUESTOES>>", latex_questoes)

                tex_file = f"prova_versao_{versao}.tex"
                tex_path = os.path.join(temp_dir, tex_file)

                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(conteudo_tex)

                subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_file], cwd=temp_dir, capture_output=True)

                pdf_path = tex_path.replace(".tex", ".pdf")
                if os.path.exists(pdf_path):
                    zip_file.write(pdf_path, f"Prova_{nome_arquivo_zip}_V{versao}.pdf")

            # Compila o Gabarito Unificado
            conteudo_gab = BASE_CONFIG + r"""
\begin{center}
    {\large \textbf{UNIVERSIDADE FEDERAL DO CEARÁ}} \\[0.1cm]
    {\large \textbf{Gabarito Unificado - <<CURSO>>}}
\end{center}
\vspace{0.4cm}\hrule\vspace{0.6cm}
<<CONTEUDO_GABARITO>>
\end{document}
"""
            conteudo_gab = conteudo_gab.replace("<<CURSO>>", curso_escolhido.nome)
            conteudo_gab = conteudo_gab.replace("<<CONTEUDO_GABARITO>>", latex_gabarito_global)
            
            gab_path = os.path.join(temp_dir, "Gabaritos.tex")
            with open(gab_path, "w", encoding="utf-8") as f:
                f.write(conteudo_gab)
                
            subprocess.run(['pdflatex', '-interaction=nonstopmode', "Gabaritos.tex"], cwd=temp_dir, capture_output=True)
            if os.path.exists(os.path.join(temp_dir, "Gabaritos.pdf")):
                zip_file.write(os.path.join(temp_dir, "Gabaritos.pdf"), "Gabaritos_Todas_Versoes.pdf")

    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=Provas_Geradas_{nome_arquivo_zip}.zip'
    return response