import csv
import random
import os
import subprocess
import tempfile
import zipfile
import io
import re
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse

from .models import Disciplina, Topico, Questao


@login_required(login_url='/admin/login/')
def index(request):
    disciplinas = Disciplina.objects.all()
    return render(request, 'gerador/index.html', {'disciplinas': disciplinas})


@login_required(login_url='/admin/login/')
def importar_csv(request):
    if request.method == 'POST':
        if 'arquivo_csv' not in request.FILES:
            messages.error(request, 'Nenhum arquivo selecionado.')
            return redirect('importar_csv')
        
        arquivo = request.FILES['arquivo_csv']
        
        if not arquivo.name.endswith('.csv'):
            messages.error(request, 'Por favor, envie um arquivo com extensão .csv')
            return redirect('importar_csv')
        
        try:
            linhas = arquivo.read().decode('utf-8').splitlines()
            leitor = csv.reader(linhas, delimiter=';')
            
            next(leitor) # Pula o cabeçalho
            
            contador = 0
            for linha in leitor:
                if len(linha) < 15:
                    continue
                    
                disciplina, _ = Disciplina.objects.get_or_create(
                    nome=linha[0].strip()
                )
                topico, _ = Topico.objects.get_or_create(
                    disciplina=disciplina, nome=linha[1].strip()
                )

                Questao.objects.create(
                    topico=topico,
                    enunciado=linha[2].strip(),
                    alt_1=linha[3].strip(), alt_2=linha[4].strip(), alt_3=linha[5].strip(), 
                    alt_4=linha[6].strip(), alt_5=linha[7].strip(), alt_6=linha[8].strip(), 
                    alt_7=linha[9].strip(), alt_8=linha[10].strip(), alt_9=linha[11].strip(), 
                    alt_10=linha[12].strip(),
                    correta=int(linha[13].strip()),
                    resolucao=linha[14].strip()
                )
                contador += 1
            
            messages.success(request, f'Sucesso! {contador} questões foram importadas para o banco de dados.')
        except Exception as e:
            messages.error(request, f'Erro ao processar o arquivo. Verifique as colunas: {str(e)}')
        
        return redirect('importar_csv')

    return render(request, 'gerador/importar.html')


@login_required(login_url='/admin/login/')
def carregar_dados_disciplina(request):
    disciplina_ids = request.GET.getlist('disciplina_id[]')
    
    if not disciplina_ids:
        return JsonResponse({'topicos': [], 'questoes': [], 'total_questoes': 0})
    
    topicos_db = Topico.objects.filter(disciplina_id__in=disciplina_ids)
    topicos = []
    for t in topicos_db:
        qtd_questoes = Questao.objects.filter(topico=t).count()
        if qtd_questoes > 0:
            topicos.append({
                'id': t.id, 
                'nome': f"{t.disciplina.nome} - {t.nome}",
                'qtd_questoes': qtd_questoes
            })
    
    questoes_db = Questao.objects.filter(topico__disciplina_id__in=disciplina_ids)
    questoes = []
    for q in questoes_db:
        previa = q.enunciado[:300] + "..." if len(q.enunciado) > 300 else q.enunciado
        questoes.append({
            'id': q.id,
            'topico_id': q.topico_id,
            'previa': previa
        })
        
    return JsonResponse({
        'topicos': topicos, 
        'questoes': questoes,
        'total_questoes': len(questoes)
    })


@login_required(login_url='/admin/login/')
def previa_prova(request):
    if request.method == 'POST':
        professor = request.POST.get('professor')
        periodo = request.POST.get('periodo')
        
        data_prova_str = request.POST.get('data_prova')
        data_prova = None
        if data_prova_str:
            data_prova = datetime.strptime(data_prova_str, '%Y-%m-%d')
            
        disciplina_ids = request.POST.getlist('disciplina')
        tipo_selecao = request.POST.get('tipo_selecao')
        num_versoes = request.POST.get('num_versoes', 1)
        topicos_selecionados = request.POST.getlist('topicos')

        disciplinas_selecionadas = Disciplina.objects.filter(id__in=disciplina_ids)
        nomes_disciplinas = " + ".join([d.nome for d in disciplinas_selecionadas])
        disciplina_fake = {'nome': nomes_disciplinas}

        if tipo_selecao == 'manual':
            questoes_ids = request.POST.getlist('questoes_selecionadas')
            questoes_db = Questao.objects.filter(id__in=questoes_ids)
        else:
            num_questoes = int(request.POST.get('num_questoes', 5))
            if topicos_selecionados:
                questoes_db = list(Questao.objects.filter(topico_id__in=topicos_selecionados).order_by('?')[:num_questoes])
            else:
                questoes_db = list(Questao.objects.filter(topico__disciplina_id__in=disciplina_ids).order_by('?')[:num_questoes])

        def preparar_latex_web(texto):
            texto = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texto)
            texto = texto.replace(r'\begin{tabular}', r'$$\begin{array}')
            texto = texto.replace(r'\end{tabular}', r'\end{array}$$')
            texto = re.sub(r'\\begin\{tikzpicture\}[\s\S]*?\\end\{tikzpicture\}', '<br><span class="badge bg-info text-dark border"><i class="bi bi-bar-chart"></i> 📊 Gráfico visível no PDF gerado</span><br>', texto)
            
            # Limpa a barra invertida do % apenas para ficar bonito na tela da Web
            texto = texto.replace(r'\%', '%')
            return texto

        prova_questoes = []
        for idx, q in enumerate(questoes_db, 1):
            todas_alts = [q.alt_1, q.alt_2, q.alt_3, q.alt_4, q.alt_5, q.alt_6, q.alt_7, q.alt_8, q.alt_9, q.alt_10]
            
            correta_texto = todas_alts[q.correta - 1]
            erradas = [alt for i, alt in enumerate(todas_alts) if i != (q.correta - 1) and alt.strip() != '']
            
            erradas_selecionadas = random.sample(erradas, min(4, len(erradas)))
            opcoes_finais = erradas_selecionadas + [correta_texto]
            random.shuffle(opcoes_finais)
            
            letras = ['a', 'b', 'c', 'd', 'e']
            letra_correta = letras[opcoes_finais.index(correta_texto)]

            opcoes_formatadas = [(letra, preparar_latex_web(texto_op)) for letra, texto_op in zip(letras, opcoes_finais)]

            prova_questoes.append({
                'numero': idx,
                'enunciado': preparar_latex_web(q.enunciado),
                'opcoes': opcoes_formatadas,
                'letra_correta': letra_correta
            })

        context = {
            'professor': professor,
            'periodo': periodo,
            'data_prova': data_prova,
            'disciplina': disciplina_fake,
            'questoes': prova_questoes,
            'num_versoes': num_versoes,
            'tipo_selecao': tipo_selecao,
            'questoes_ids': [q.id for q in questoes_db],
            'num_questoes': request.POST.get('num_questoes', 5),
            'topicos_selecionados': topicos_selecionados
        }
        return render(request, 'gerador/previa.html', context)
    
    return redirect('index')


@login_required(login_url='/admin/login/')
def gerar_provas(request):
    if request.method != 'POST':
        return redirect('index')

    def limpar_texto_latex(texto):
        if not texto:
            return ""
        
        texto = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', texto)
        
        # MÁGICA: O (?<!\\) significa "apenas se não houver uma barra antes".
        # Assim evitamos a dupla proteção que estava quebrando o PDF!
        texto = re.sub(r'(?<!\\)%', r'\\%', texto)
        texto = re.sub(r'(?<!\\)#', r'\\#', texto)
        
        texto = texto.replace(' | ', ' $\\vert$ ')
        return texto
    
    professor = request.POST.get('professor', '')
    periodo = request.POST.get('periodo', '')
    data_prova_str = request.POST.get('data_prova', '')
    
    data_formatada = ""
    if data_prova_str:
        data_formatada = datetime.strptime(data_prova_str, '%Y-%m-%d').strftime('%d/%m/%Y')

    num_versoes = int(request.POST.get('num_versoes', 1))
    tipo_selecao = request.POST.get('tipo_selecao')

    if tipo_selecao == 'manual':
        questoes_ids = request.POST.getlist('questoes_selecionadas')
        questoes_db = list(Questao.objects.filter(id__in=questoes_ids))
    else:
        num_questoes = int(request.POST.get('num_questoes', 5))
        topicos_selecionados = request.POST.getlist('topicos')
        disciplina_ids = request.POST.getlist('disciplina')
        disciplina_ids = [d for d in disciplina_ids if d.strip()] 
        
        if topicos_selecionados:
            questoes_db = list(Questao.objects.filter(topico_id__in=topicos_selecionados).order_by('?')[:num_questoes])
        elif disciplina_ids:
            questoes_db = list(Questao.objects.filter(topico__disciplina_id__in=disciplina_ids).order_by('?')[:num_questoes])
        else:
            questoes_db = []

    if not questoes_db:
        messages.error(request, "Nenhuma questão foi encontrada para gerar a prova.")
        return redirect('index')

    disciplinas_envolvidas = list(set([q.topico.disciplina.nome for q in questoes_db]))
    if len(disciplinas_envolvidas) > 1:
        nome_arquivo_zip = "Estatistica_Mista"
    else:
        nome_arquivo_zip = disciplinas_envolvidas[0].replace(" ", "_")

    BASE_CONFIG = r"""
\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath, amssymb}
\usepackage{mathpazo} 
\linespread{1.15} 
\usepackage{geometry}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
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
   {\large \textbf{Avaliação Oficial de Estatística}}
\end{center}

\vspace{0.2cm}
\hrule
\vspace{0.4cm}

\noindent \textbf{Professor:} <<PROFESSOR>> \hfill \textbf{Semestre:} <<PERIODO>> \hfill \textbf{Data:} <<DATA>>

\vspace{0.4cm}
\noindent \textbf{Aluno(a):} \rule{8cm}{0.5pt} \hfill \textbf{Matrícula:} \rule{2.5cm}{0.5pt} \hfill \textbf{Versão:} <<VERSAO>>

\vspace{0.4cm}
\hrule
\vspace{0.6cm}

\begin{enumerate}[label=\textbf{\arabic*.}, leftmargin=*]
<<QUESTOES>>
\end{enumerate}

\end{document}
"""

    TEMPLATE_GABARITO = BASE_CONFIG + r"""
\begin{center}
    {\large \textbf{UNIVERSIDADE FEDERAL DO CEARÁ}} \\[0.1cm]
    {\large \textbf{DEPARTAMENTO DE ESTATÍSTICA E MATEMÁTICA APLICADA}} \\[0.3cm]
    {\large \textbf{Gabarito}}
\end{center}

\vspace{0.2cm}
\hrule
\vspace{0.4cm}

\noindent \textbf{Professor:} <<PROFESSOR>> \hfill \textbf{Semestre:} <<PERIODO>> \hfill \textbf{Data:} <<DATA>>

\vspace{0.4cm}
\hrule
\vspace{0.6cm}

\begin{enumerate}[label=\textbf{\arabic*.}, leftmargin=*]
<<QUESTOES>>
\end{enumerate}

\end{document}
"""

    buffer = io.BytesIO()

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

            for versao in range(1, num_versoes + 1):
                latex_questoes = ""
                
                questoes_embaralhadas = list(questoes_db)
                random.shuffle(questoes_embaralhadas)

                for q in questoes_embaralhadas:
                    todas_alts = [
                        q.alt_1, q.alt_2, q.alt_3, q.alt_4, q.alt_5,
                        q.alt_6, q.alt_7, q.alt_8, q.alt_9, q.alt_10
                    ]

                    correta_texto = todas_alts[q.correta - 1]

                    erradas = [
                        alt for i, alt in enumerate(todas_alts)
                        if i != (q.correta - 1) and alt.strip() != ''
                    ]

                    erradas_selecionadas = random.sample(erradas, min(4, len(erradas)))
                    opcoes_finais = erradas_selecionadas + [correta_texto]
                    random.shuffle(opcoes_finais)

                    latex_questoes += f"\\item {limpar_texto_latex(q.enunciado)}\n\n"
                    latex_questoes += "\\vspace{0.1cm}\n"
                    
                    latex_questoes += "\\begin{enumerate}[label=\\textbf{\\alph*)}, leftmargin=0.8cm]\n"
                    latex_questoes += "    \\setlength{\\itemsep}{0.2cm}\n"

                    for op in opcoes_finais:
                        latex_questoes += f"    \\item {limpar_texto_latex(op)}\n"

                    latex_questoes += "\\end{enumerate}\n\\vspace{0.6cm}\n\n"

                conteudo_tex = TEMPLATE_PROVA.replace("<<PROFESSOR>>", professor)
                conteudo_tex = conteudo_tex.replace("<<PERIODO>>", periodo)
                conteudo_tex = conteudo_tex.replace("<<DATA>>", data_formatada)
                conteudo_tex = conteudo_tex.replace("<<VERSAO>>", str(versao))
                conteudo_tex = conteudo_tex.replace("<<QUESTOES>>", latex_questoes)

                tex_file = f"prova_{versao}.tex"
                tex_path = os.path.join(temp_dir, tex_file)

                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(conteudo_tex)

                processo = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', tex_file],
                    cwd=temp_dir, capture_output=True, text=True, encoding='utf-8', errors='replace'
                )

                pdf_path = tex_path.replace(".tex", ".pdf")
                if os.path.exists(pdf_path):
                    zip_file.write(pdf_path, f"Avaliacao_{nome_arquivo_zip}_V{versao}.pdf")
                if os.path.exists(tex_path):
                    zip_file.write(tex_path, f"Avaliacao_{nome_arquivo_zip}_V{versao}.tex")

            # ---------------- GABARITO ----------------
            latex_gabarito = ""
            for idx, q in enumerate(questoes_db, 1):
                latex_gabarito += f"\\item \\textbf{{(Ref: banco \\#{q.id})}} {limpar_texto_latex(q.enunciado)}\n\n"
                latex_gabarito += f"{limpar_texto_latex(q.resolucao)}\n\\vspace{{0.8cm}}\n\n"

            conteudo_gab = TEMPLATE_GABARITO.replace("<<PROFESSOR>>", professor)
            conteudo_gab = conteudo_gab.replace("<<PERIODO>>", periodo)
            conteudo_gab = conteudo_gab.replace("<<DATA>>", data_formatada)
            conteudo_gab = conteudo_gab.replace("<<QUESTOES>>", latex_gabarito)

            gab_filename = "gabarito.tex"
            gab_path = os.path.join(temp_dir, gab_filename)
            with open(gab_path, 'w', encoding='utf-8') as f:
                f.write(conteudo_gab)

            processo_gab = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', gab_filename],
                cwd=temp_dir, capture_output=True, text=True, encoding='utf-8', errors='replace'
            )

            pdf_gab = gab_path.replace('.tex', '.pdf')
            
            if os.path.exists(pdf_gab):
                zip_file.write(pdf_gab, "Gabarito.pdf")
            else:
                # SISTEMA ANTI-APAGÃO: Salva o log do erro se o PDF falhar
                erro_path = os.path.join(temp_dir, "ERRO_GABARITO.txt")
                with open(erro_path, 'w', encoding='utf-8') as f_erro:
                    f_erro.write("ERRO FATAL AO GERAR O GABARITO EM PDF.\n\nLOG DO COMPILADOR LATEX:\n\n")
                    f_erro.write(processo_gab.stdout)
                zip_file.write(erro_path, "ERRO_GABARITO_LEIA_AQUI.txt")
                
            if os.path.exists(gab_path):
                zip_file.write(gab_path, "Gabarito.tex")

    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=Provas_{nome_arquivo_zip}.zip'
    return response