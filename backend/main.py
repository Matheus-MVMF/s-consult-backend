from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
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

# --- CONFIGURAÇÃO GOOGLE AI ---
api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- CONFIGURAÇÃO FIREBASE ---
if not firebase_admin._apps:
    try:
        firebase_json = os.environ.get('FIREBASE_CONFIG')
        if firebase_json:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.environ.get('FIREBASE_BUCKET', 'teste-6f9b9.firebasestorage.app')
            })
            print("✅ Conectado ao Firebase via Variáveis!")
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'teste-6f9b9.firebasestorage.app' 
            })
            print("✅ Conectado ao Firebase localmente!")
    except Exception as e:
        print(f"❌ Erro ao conectar no Firebase: {e}")

try:
    bucket = storage.bucket()
except:
    bucket = None

class ChatRequest(BaseModel):
    message: str 

def listar_pdfs_firebase(termo):
    if not bucket: return []
    blobs = bucket.list_blobs()
    matches = []
    termo = termo.lower().strip()
    for blob in blobs:
        if blob.name.lower().endswith(".pdf") and termo in blob.name.lower():
            matches.append(blob.name)
    return list(set(matches))

def ler_pdf_firebase(nome_arquivo):
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
        return None

# =====================================================================
# SERVIÇO 1: DOWNLOAD
# =====================================================================
@app.get("/download")
async def download_pdf(filename: str):
    try:
        blob = bucket.blob(filename)
        url = blob.generate_signed_url(version="v4", expiration=900, method="GET")
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no Firebase")

# =====================================================================
# SERVIÇO 2: BUSCA NO BANCO DE DADOS (RELATÓRIOS PRONTOS)
# =====================================================================
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    termo = request.message.strip()
    lista_arquivos = listar_pdfs_firebase(termo)
    
    if not lista_arquivos:
        return {"reply": f"⚠️ Não encontrei nenhum arquivo PDF no Banco de Dados com o termo '{termo}'."}
    
    if len(lista_arquivos) > 1:
        if termo in lista_arquivos:
            lista_arquivos = [termo]
        else:
            return {"reply": "🔍 Encontrei mais de um arquivo na nuvem. Qual deles é o correto?", "options": lista_arquivos}

    nome_arquivo_pdf = lista_arquivos[0]
    texto_pdf = ler_pdf_firebase(nome_arquivo_pdf)
    
    if not texto_pdf:
        return {"reply": "❌ Encontrei o arquivo no sistema, mas não consegui ler o conteúdo."}

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt_sistema = f"""
Aja como um Engenheiro Rodoviário Sênior. Analise o PDF: {nome_arquivo_pdf}.
DADOS BRUTOS DO PDF:
{texto_pdf[:80000]}

 REGRAS RÍGIDAS DE ENGENHARIA:
        1. **REGRA DE OURO - IMPLANTAÇÃO:** NUNCA coloque itens "Ruins" ou "Inexistentes" na lista "A Implantar".
           - "A Implantar" APENAS se houver uma tabela específica (ex: "Valetas ou sarjetas para executar", "Meios-fios fios para executar").
           - Se não houver tabela de obra nova, "A Implantar" deve ser "0" ou "Não identificado".
        
        2. **RESTAURAÇÃO:** Só preencha se o PDF citar explicitamente "Restauração" ou "Reconstrução". Se for apenas "Tapa buraco" ou "Desgaste", a Restauração é 0.
        
        3. **FORMATAÇÃO:** Use Markdown (**, ###, >).

        --- TEMPLATE OBRIGATÓRIO (Preencha exatamente assim) ---

Siga o Template LVC rigorosamente com formatação Markdown. NUNCA use blocos de código (```).
        
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

> *Remendos Profundos Executados Recentes* (RP)
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Locais Críticos: [Listar KMs]

> *Tapa Buracos Executados Recentes* (TP)
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Locais Críticos: [Listar KMs]

> *Rebaixamentos Laterais (RL)*
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Relação Detalhada:
  - KM [X] | Lado: [LE/LD] | Área: [X] m²

> *Erosões*
- Ocorrências: **[Total]**
- Volume Total: **[X] m³**
- Relação Detalhada:
  - KM [X] | Lado: [LE/LD] | Volume: [X] m³

> *Áreas para Restauração*
- Ocorrências: **[Total]**
- Extensão: **[X] m**
- KMs: [Listar: KM Inicial ao Final]

> *Desgaste Superficial*
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Trechos: [Listar: KM Inicial ao Final | Lado]

---
### 2. DRENAGEM E OAEs

> *OAEs (Pontes/Viadutos)*
- Total: **[X]** | Local: [Descrição]

> *Passagens Molhadas*
- Total: **[X]** | Situação: [Descrição]

> *Bueiros*
- Total de Bueiros: **[X]**
- Relação Detalhada de Bueiros:
  (REGRA ABSOLUTA: É estritamente PROIBIDO resumir os bueiros. Você DEVE ler a tabela "BUEIROS" e listar TODOS eles, um por um, copiando a Localização, Tipo, Condição e Observação):
  - KM [Localização] | Tipo: [Tipo] | Condição: [Condição] | Obs: [Observação]

> *Meios-fios (Existentes)*
- Total Geral: **[X] m**
- Estado: Bom (**[X]m**) | Regular (**[X]m**) | Ruim (**[X]m**)

> *Sarjetas (Existentes)*
- Total Geral: **[X] m**
- Estado: Bom (**[X]m**) | Regular (**[X]m**) | Ruim (**[X]m**)

> *Meios-fios e Sarjetas (A Implantar)*
- Total Meios-fios a Implantar: **[X] m**
- Total Sarjetas a Implantar: **[X] m**
- Relação Detalhada a Implantar:
  (ATENÇÃO: É OBRIGATÓRIO LISTAR TODOS OS TRECHOS SEM EXCEÇÃO. NÃO RESUMA E NÃO USE "ETC". LISTE CADA TRECHO ENCONTRADO NO PDF, LINHA POR LINHA):
  - [Meio-fio ou Sarjeta] | KM [Inicial] ao KM [Final] | Lado [LE/LD/Ambos] | Extensão: [X] m
---
### 3. SINALIZAÇÃO E SERVIÇOS

> *Vertical (Placas Existentes)*
- Total: **[Qtd]**
- Situação: [Descrição]

> *A Implantar (Placas)*
- Total a Implantar: **[Qtd]**
- Relação de Placas A Implantar:
  (ATENÇÃO: É OBRIGATÓRIO LISTAR TODAS AS PLACAS SEM EXCEÇÃO. NÃO RESUMA, NÃO OMITA E NÃO USE "ETC". LISTE CADA UMA DAS PLACAS ENCONTRADAS NO PDF, LINHA POR LINHA):
  - KM [X] | Lado [LE/LD] | [Código da Placa, Ex: R-7]

---
### 4. CONSIDERAÇÕES FINAIS
- *Roço Lateral:* **[X] ha**

### 5. OBSERVAÇÕES GERAIS (OBS)
(REGRA ABSOLUTA: Procure pela seção "OBSERVAÇÕES" no final do PDF. Você DEVE transcrever todas as observações contidas lá na íntegra, linha por linha. Não omita NENHUMA observação. Se houver marcação de KM, inclua-a).
- KM [X] | [Texto completo da observação]
- [Texto de observação geral sem KM]

> *OBSERVAÇÕES GERAIS (OBS)*
(ATENÇÃO: Extraia e transcreva fielmente os textos contidos na seção "OBSERVAÇÕES" do documento. É OBRIGATÓRIO manter as referências de "Km" e as descrições técnicas exatas. Liste cada observação em tópicos, linha por linha):
- KM [X] | [Texto da Observação detalhada, Ex: Bueiro celular múltiplo... / Fissura longitudinal...]
- [Texto de observação geral sem KM, Ex: Verificou-se que diversas placas...]

- *Conclusão:* [Parecer final]
"""
        # ✅ NOVIDADE: Timeout de 10 minutos (600s) na busca de nuvem
        resposta = model.generate_content(prompt_sistema, request_options={"timeout": 600.0})
        return {"reply": resposta.text, "pdf_name": nome_arquivo_pdf}
    except Exception as e:
        return {"reply": f"Erro na IA: {str(e)}"}


# =====================================================================
# SERVIÇO 3: LER TABELAS (A LÓGICA DO GERAR_RESUMO.PY)
# =====================================================================
@app.post("/upload-pdf")
async def upload_pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        return {"reply": "❌ Por favor, envie um arquivo PDF."}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(await file.read())
        temp_path = temp_pdf.name

    try:
        # A IA LÊ O PDF INTEIRO (NATIVO DO GEMINI) IGUAL AO GERAR_RESUMO.PY
        arquivo_pdf = genai.upload_file(temp_path)
        
        prompt_sistema = f"""Aja como um Engenheiro Rodoviário Sênior. Analise o inventário em PDF anexado.
        
REGRAS RÍGIDAS DE ENGENHARIA E TABELAS:
1. **ATENÇÃO MÁXIMA A KMs E LADOS:** Leia as tabelas com precisão cirúrgica. NUNCA invente intervalos se a tabela listar KMs pontuais. 
2. Para Erosão, Rebaixamento, Desgaste e Panelas, você DEVE capturar o KM exato, o LADO (LE, LD, Eixo) e a dimensão/volume de cada linha da tabela.
3. **SINALIZAÇÃO DETALHADA:** Liste TODAS as placas lidas nas tabelas (tanto existentes quanto a implantar), linha por linha, informando KM, Lado e o Código da Placa.
4. NUNCA USE BLOCOS DE CÓDIGO (```). ESCREVA O TEXTO DIRETAMENTE.

--- TEMPLATE OBRIGATÓRIO ---

### 📍 RESUMO TÉCNICO LVC
+ 🛣️ *Trecho:* {file.filename.replace('.pdf', '').replace('_', ' ')}

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

> *Remendos Profundos Executados Recentes* (RP)
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Locais Críticos: [Listar KMs]

> *Tapa Buracos Executados Recentes* (TP)
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Locais Críticos: [Listar KMs]

> *Rebaixamentos Laterais (RL)*
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Relação Detalhada:
  - KM [X] | Lado: [LE/LD] | Área: [X] m²

> *Erosões*
- Ocorrências: **[Total]**
- Volume Total: **[X] m³**
- Relação Detalhada:
  - KM [X] | Lado: [LE/LD] | Volume: [X] m³

> *Áreas para Restauração*
- Ocorrências: **[Total]**
- Extensão Total: **[X] m**
- KMs: [Listar: KM Inicial ao Final]

> *Desgaste Superficial*
- Ocorrências: **[Total]**
- Área Total: **[X] m²**
- Trechos: [Listar: KM Inicial ao Final | Lado]

---
### 2. DRENAGEM E OAEs

> *OAEs e Bueiros*
- Pontes/Viadutos: **[X]** | Local: [Descrição]
- Passagens Molhadas: **[X]**
- Total de Bueiros: **[X]**
- Relação Detalhada de Bueiros:
  (REGRA ABSOLUTA: É estritamente PROIBIDO resumir os bueiros. Você DEVE ler a tabela "BUEIROS" e listar TODOS eles, um por um, copiando a Localização, Tipo, Condição e Observação):
  - KM [Localização] | Tipo: [Tipo] | Condição: [Condição] | Obs: [Observação]

> *Meios-fios e Sarjetas (Existentes)*
- Total Meios-fios: **[X] m** | Bom (**[X]m**) | Ruim (**[X]m**)
- Total Sarjetas: **[X] m** | Bom (**[X]m**) | Ruim (**[X]m**)

> *Meios-fios e Sarjetas (A Implantar)*
- Total Meios-fios a Implantar: **[X] m**
- Total Sarjetas a Implantar: **[X] m**
- Relação Detalhada a Implantar:
  (ATENÇÃO: É OBRIGATÓRIO LISTAR TODOS OS TRECHOS SEM EXCEÇÃO. NÃO RESUMA E NÃO USE "ETC". LISTE CADA TRECHO ENCONTRADO NO PDF, LINHA POR LINHA):
  - [Meio-fio ou Sarjeta] | KM [Inicial] ao KM [Final] | Lado [LE/LD/Ambos] | Extensão: [X] m
---
### 3. SINALIZAÇÃO

> *Horizontal (Pintura)*
- Situação: **[Descrição]**

> *Vertical (Placas Existentes)*
- Total Identificado: **[Qtd]**
- Relação de Placas Existentes:
  - KM [X] | Lado [LE/LD] | [Ex: R-19]

> *A Implantar (Placas)*
- Total a Implantar: **[Qtd]**
- Relação de Placas A Implantar:
  - KM [X] | Lado [LE/LD] | [Ex: R-7]

---
### 4. SERVIÇOS GERAIS
- *Roço Lateral:* **[X] ha**

---
### 5. OBSERVAÇÕES GERAIS (OBS)
- *OBSERVAÇÕES:*
- [Texto de observação geral sem KM]
- KM [X] | [Texto completo da observação]
(REGRA ABSOLUTA: Procure pela seção "OBSERVAÇÕES" no final do PDF. Você DEVE transcrever todas as observações contidas lá na íntegra, linha por linha. Não omita NENHUMA observação. Se houver marcação de KM, inclua-a).


- *Conclusão:* [Parecer final técnico]
"""
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # ✅ NOVIDADE: Timeout de 10 minutos (600s) no upload de arquivo
        resposta = model.generate_content([prompt_sistema, arquivo_pdf], request_options={"timeout": 600.0})
        
        try:
            arquivo_pdf.delete()
        except:
            pass

        return {"reply": resposta.text, "pdf_name": file.filename}

    except Exception as e:
        return {"reply": f"❌ Erro na IA ao ler tabelas: {str(e)}"}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)