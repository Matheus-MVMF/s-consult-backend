from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Configuração Inicial
load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

class ChatRequest(BaseModel):
    message: str 

# --- FUNÇÕES ---

def encontrar_pdfs_lista(termo, raiz):
    matches = []
    for root, dirs, files in os.walk(raiz):
        for file in files:
            if file.lower().endswith(".pdf") and termo.lower() in file.lower():
                matches.append(os.path.join(root, file))
    
    if len(matches) == 0:
        raiz_pai = os.path.dirname(raiz)
        for root, dirs, files in os.walk(raiz_pai):
            for file in files:
                if file.lower().endswith(".pdf") and termo.lower() in file.lower():
                    matches.append(os.path.join(root, file))
    return list(set(matches))

def ler_pdf(caminho):
    try:
        texto = ""
        with pdfplumber.open(caminho) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() or ""
        return texto
    except:
        return None

# --- ROTAS DA API ---

# Rota para baixar o PDF
@app.get("/download")
async def download_pdf(filename: str):
    pasta_atual = os.getcwd()
    # Reutiliza a busca para achar o caminho completo do arquivo pelo nome
    caminhos = encontrar_pdfs_lista(filename, pasta_atual)
    
    if not caminhos:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    # Pega o primeiro que encontrar com esse nome exato
    caminho_final = caminhos[0]
    return FileResponse(caminho_final, media_type='application/pdf', filename=filename)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    termo = request.message.strip()
    pasta_atual = os.getcwd()
    
    lista_arquivos = encontrar_pdfs_lista(termo, pasta_atual)
    
    if not lista_arquivos:
        return {"reply": f"⚠️ Não encontrei nenhum arquivo PDF com o termo '{termo}'."}
    
    # Tratamento de duplicidade
    if len(lista_arquivos) > 1:
        for caminho in lista_arquivos:
            if os.path.basename(caminho).lower() == termo.lower():
                lista_arquivos = [caminho]
                break
        else:
            nomes_arquivos = [os.path.basename(c) for c in lista_arquivos]
            return {
                "reply": "🔍 Encontrei mais de um arquivo com esse nome. Qual deles você quer analisar?",
                "options": nomes_arquivos
            }

    caminho_pdf = lista_arquivos[0]
    nome_arquivo_pdf = os.path.basename(caminho_pdf) # Salva o nome para o botão de download
    texto_pdf = ler_pdf(caminho_pdf)
    
    if not texto_pdf:
        return {"reply": "❌ Encontrei o arquivo, mas não consegui ler o texto."}

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        prompt_sistema = f"""
        Aja como um Engenheiro Rodoviário Sênior. Analise o PDF: {nome_arquivo_pdf}.
        
        DADOS:
        {texto_pdf[:70000]}

        REGRAS DE LÓGICA:
        1. **Desgaste vs Restauração:** Tabela de Desgaste vai em "Desgaste". Restauração é apenas se houver reconstrução profunda (se não, é 0).
        2. **Desgaste é para colocar algum dado somente se tiver a tabela, caso não tenha é 0.
        3. **Intro:** Comece com "Olá! Como Engenheiro Rodoviário Sênior..." e comente brevemente sobre a identificação da rodovia/trecho.
        4. **Formatação:** Use Markdown (**, ###, >) para o site.
        5. **OAEs não tem nada haver com Pórticos.

        --- TEMPLATE OBRIGATÓRIO (Mantenha os espaços em branco) ---

        [Introdução cordial e técnica]

        Segue o resumo técnico:

        ### 📍 RESUMO TÉCNICO LVC
        🛣️ *Trecho:* {nome_arquivo_pdf.replace('.pdf', '')}

        - *Extensão:* **[X] km**
        - *Revestimento (Pista):* **[Tipo e KMs]**
        - *Acostamento:* **[Largura/Tipo]**

        > 🏗️ *Pórticos:*
        - [Situação dos pórticos]

        ---
        ### 1. PISTA DE ROLAMENTO

        > *Panelas Abertas (PA)*
        - Ocorrências: **[Total]**
        - Área Total: **[X] m²**
        - Locais Críticos: [Listar]


        > *Rebaixamentos Laterais (RL)*
        - Ocorrências: **[Total]**
        - Área Total: **[X] m²**
        - Trechos: [Descrição]


        > *Erosões*
        - Ocorrências: **[Total]**
        - Volume Total: **[X] m³**
        - Detalhes: [Descrição]


        > *Áreas para Restauração*
        - Ocorrências: **[Total]**
        - Extensão: **[X] m**
        - Obs: [Descrição]


        > *Desgaste*
        - Ocorrências: **[Total]**
        - Área Total: **[X] m²**
        - Trechos: [Descrição]

        ---
        ### 2. DRENAGEM & OBRAS

        > *OAEs (Pontes/Viadutos)*
        - Total: **[X]** | Local: [Descrição]


        > *Passagens Molhadas*
        - Total: **[X]** | Situação: [Descrição]


        > *Bueiros*
        - Total: **[X]** unidades
        - Obs: [Descrição]


        > *Meios-fios e Sarjetas (Existentes)*
        - Total Geral: **[X] m**
        - Situação: Bom (**[X]m**) | Regular (**[X]m**) | Ruim (**[X]m**)

        > *Sarjetas (Existentes)*
        - Total Geral: **[X] m**
        - Situação: Bom (**[X]m**) | Regular (**[X]m**) | Ruim (**[X]m**)

        > *Meios-fios (A Implantar)*
        - Total a fazer: **[X] m**
        - Lado Esquerdo: [Descrição]
        - Lado Direito: [Descrição]


        > *Sarjetas/Valas (A Implantar)*
        - Total a fazer: **[X] m**
        - Lado Esquerdo: [Descrição]
        - Lado Direito: [Descrição]

        ---
        ### 3. SINALIZAÇÃO

        > *Horizontal (Pintura)*
        - Situação: **[Descrição]**


        > *Vertical (Placas Existentes)*
        - Total: ***[Qtd]**
        - Situação: [Descrição]


        > *A Implantar (Placas)*
        - Regulamentação: **[Qtd]** ([Obs])
        - Advertência: **[Qtd]** ([Obs])

        ---
        ### 4. SERVIÇOS GERAIS
        - *Roço Lateral:* **[X] ha** ([Obs])
        - *Conclusão:* [Parecer final técnico]
        """
        
        resposta = model.generate_content(prompt_sistema)
        # RETORNA TAMBÉM O NOME DO PDF PARA O BOTÃO DE DOWNLOAD
        return {
            "reply": resposta.text,
            "pdf_name": nome_arquivo_pdf 
        }
        
    except Exception as e:
        return {"reply": f"Erro na IA: {str(e)}"}