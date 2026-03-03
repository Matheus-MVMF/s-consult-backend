from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json # <--- ADICIONADO PARA LER A CHAVE EM STRING
import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, storage
import tempfile

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

# --- CONFIGURAÇÃO GOOGLE AI (ATUALIZADA) ---
# Tenta pegar GEMINI_API_KEY ou GOOGLE_API_KEY
api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- CONFIGURAÇÃO FIREBASE (ATUALIZADA PARA NUVEM + LOCAL) ---
if not firebase_admin._apps:
    try:
        # 1. Tenta primeiro pela Variável de Ambiente (Caminho 2 - Render)
        firebase_json = os.environ.get('FIREBASE_CONFIG')
        
        if firebase_json:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.environ.get('FIREBASE_BUCKET', 'teste-6f9b9.firebasestorage.app')
            })
            print("✅ Conectado ao Firebase via Variáveis de Ambiente!")
            
        # 2. Se não houver variável, tenta pelo arquivo local (Caminho 1 - PC)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'teste-6f9b9.firebasestorage.app' 
            })
            print("✅ Conectado ao Firebase via arquivo local!")
            
    except Exception as e:
        print(f"❌ Erro ao conectar no Firebase: {e}")

try:
    bucket = storage.bucket()
except:
    bucket = None

class ChatRequest(BaseModel):
    message: str 

# --- FUNÇÕES NOVAS (NUVEM) ---

def listar_pdfs_firebase(termo):
    """Procura arquivos PDF no Firebase Storage"""
    if not bucket: return []
    
    blobs = bucket.list_blobs()
    matches = []
    termo = termo.lower().strip()
    
    for blob in blobs:
        if blob.name.lower().endswith(".pdf") and termo in blob.name.lower():
            matches.append(blob.name)
            
    return list(set(matches))

def ler_pdf_firebase(nome_arquivo):
    """Baixa o PDF da nuvem temporariamente e lê o texto"""
    if not bucket: return None

    try:
        blob = bucket.blob(nome_arquivo)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            blob.download_to_filename(temp_pdf.name)
            temp_path = temp_pdf.name
            
        texto = ""
        with pdfplumber.open(temp_path) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() or ""
        
        os.remove(temp_path)
        return texto
    except Exception as e:
        print(f"Erro ao ler PDF da nuvem: {e}")
        return None

# --- ROTAS DA API ---

@app.get("/download")
async def download_pdf(filename: str):
    """Gera um link seguro para baixar o arquivo direto do Google"""
    try:
        blob = bucket.blob(filename)
        url = blob.generate_signed_url(version="v4", expiration=900, method="GET")
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no Firebase")

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    termo = request.message.strip()
    
    lista_arquivos = listar_pdfs_firebase(termo)
    
    if not lista_arquivos:
        return {"reply": f"⚠️ Não encontrei nenhum arquivo PDF no Banco de Dados (Firebase) com o termo '{termo}'. Verifique se você fez o upload."}
    
    if len(lista_arquivos) > 1:
        if termo in lista_arquivos:
            lista_arquivos = [termo]
        else:
            return {
                "reply": "🔍 Encontrei mais de um arquivo na nuvem. Qual deles é o correto?",
                "options": lista_arquivos
            }

    nome_arquivo_pdf = lista_arquivos[0]
    texto_pdf = ler_pdf_firebase(nome_arquivo_pdf)
    
    if not texto_pdf:
        return {"reply": "❌ Encontrei o arquivo no sistema, mas não consegui ler o conteúdo."}

    try:
        # Use o modelo gemini-1.5-flash (mais estável para produção)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt_sistema = f"""
        Aja como um Engenheiro Rodoviário Sênior. Analise o PDF: {nome_arquivo_pdf}.
        
        DADOS BRUTOS DO PDF:
        {texto_pdf[:80000]}

        REGRAS RÍGIDAS DE ENGENHARIA:
        1. **REGRA DE OURO - IMPLANTAÇÃO:** NUNCA coloque itens "Ruins" ou "Inexistentes" na lista "A Implantar".
           - "A Implantar" APENAS se houver uma tabela específica (ex: "Valetas para executar", "Novos Meios-fios").
           - Se não houver tabela de obra nova, "A Implantar" deve ser "0" ou "Não identificado".
        
        2. **RESTAURAÇÃO:** Só preencha se o PDF citar explicitamente "Restauração" ou "Reconstrução". Se for apenas "Tapa buraco" ou "Desgaste", a Restauração é 0.
        
        3. **FORMATAÇÃO:** Use Markdown (**, ###, >).

        --- TEMPLATE OBRIGATÓRIO (Preencha exatamente assim) ---

        [Breve introdução cordial e técnica sobre o trecho]

        Segue o resumo técnico:

        ### 📍 RESUMO TÉCNICO LVC
        + 🛣️ *Trecho:* {nome_arquivo_pdf.replace('.pdf', '')}

        - *Extensão:* **[X] km**
        - *Revestimento (Pista):* **[Tipo e KMs]**
        - *Acostamento:* **[Largura/Tipo]**

        > 🏗️ *Pórticos:*
        - [Situação]

        ---
        ### 1. PISTA DE ROLAMENTO

        > *Panelas Abertas (PA)*
        - Ocorrências: **[Total]**
        - Área Total: **[X] m²**
        - Locais Críticos: [Listar KMs]


        > *Rebaixamentos Laterais (RL)*
        - Ocorrências: **[Total]**
        - Área Total: **[X] m²**
        - Trechos: [Listar: KM X | Lado]


        > *Erosões*
        - Ocorrências: **[Total]**
        - Volume Total: **[X] m³**
        - Detalhes: [Descrição]


        > *Áreas para Restauração*
        - Ocorrências: **[Total]**
        - Extensão: **[X] m**
        - KMs: [Listar KMs ou "Não identificado"]


        > *Desgaste Superficial*
        - Ocorrências: **[Total]**
        - Área Total: **[X] m²**
        - Trechos: [Listar: KM Inicial ao Final | Lado]

        ---
        ### 2. DRENAGEM & OBRAS

        > *OAEs (Pontes/Viadutos)*
        - Total: **[X]** | Local: [Descrição]


        > *Passagens Molhadas*
        - Total: **[X]** | Situação: [Descrição]


        > *Bueiros*
        - Total: **[X]** unidades
        - Obs: [Descrição]


        > *Meios-fios (Existentes)*
        - Total Geral: **[X] m**
        - Estado: Bom (**[X]m**) | Regular (**[X]m**) | Ruim (**[X]m**)

        > *Sarjetas (Existentes)*
        - Total Geral: **[X] m**
        - Estado: Bom (**[X]m**) | Regular (**[X]m**) | Ruim (**[X]m**)

        > *Meios-fios (A Implantar)*
        - *Nota: Preencher APENAS se houver tabela de "Novos" ou "A Executar".*
        - Total a fazer: **[X] m**
        - Detalhes: [Lados e KMs]


        > *Sarjetas/Valas (A Implantar)*
        - *Nota: Preencher APENAS se houver tabela de "Novos" ou "A Executar".*
        - Total a fazer: **[X] m**
        - Detalhes: [Lados e KMs]

        ---
        ### 3. SINALIZAÇÃO

        > *Horizontal (Pintura)*
        - Situação: **[Descrição]**


        > *Vertical (Placas Existentes)*
        - Total: **[Qtd]**
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
        return {
            "reply": resposta.text,
            "pdf_name": nome_arquivo_pdf 
        }
        
    except Exception as e:
        return {"reply": f"Erro na IA: {str(e)}"}