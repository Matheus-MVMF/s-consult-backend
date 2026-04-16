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

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

if not firebase_admin._apps:
    try:
        firebase_json = os.environ.get('FIREBASE_CONFIG')
        if firebase_json:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.environ.get('FIREBASE_BUCKET', 'teste-6f9b9.firebasestorage.app')
            })
    except Exception as e:
        print(f"Erro Firebase: {e}")

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

# PROMPT COM REGRAS INQUEBRÁVEIS E EXCEÇÃO DO ROÇO
def get_prompt(nome_trecho, texto_extraido):
    return f"""
Aja como um Engenheiro Rodoviário Sênior. Analise o Inventário: {nome_trecho}.
DADOS: {texto_extraido[:80000]}

REGRAS ABSOLUTAS E INQUEBRÁVEIS DE ENGENHARIA (NÃO DESOBEDEÇA NENHUMA):
1. SE NÃO EXISTIR NO PDF, APAGUE O TÓPICO: Se não houver Panelas, Rebaixamentos, Erosões, Desgaste ou Áreas para Restauração no inventário, VOCÊ É PROIBIDO DE ESCREVER O NOME DESSES DEFEITOS. Apenas liste os que existem, e exclua os blocos vazios.
2. MENSAGEM DE BOM ESTADO: APENAS SE a "Pista de Rolamento" não tiver NENHUM defeito (zero Panelas, zero Erosões, etc.), escreva a frase: "Não foram identificados defeitos na rodovia devido o trecho estar em bom estado de conservação."
3. A IMPLANTAR (SINALIZAÇÃO E DRENAGEM): Se não houver uma tabela EXPLICANDO O QUE IMPLANTAR (Placas, Meio-fio, Sarjeta), VOCÊ É PROIBIDO de colocar o tópico "A Implantar". APAGUE O TÓPICO INTEIRO.
4. ROÇO LATERAL (SEMPRE OBRIGATÓRIO): O tópico "4. SERVIÇOS GERAIS" NUNCA pode ser apagado. Se houver área para roço, informe o valor. Se for 0 ou não houver, escreva EXATAMENTE: "Não há necessidade de executar roço no levantamento atual."
5. UNIDADES OBRIGATÓRIAS (EXTREMA IMPORTÂNCIA):
   - Restauração: Extensão (m)
   - Erosões: Volume (m³)
   - Rebaixamentos, Panelas, Desgaste, Remendos (RP) e Tapa Buracos (TP): Área (m²)
6. DETALHAMENTO CIRÚRGICO: Você DEVE listar as medidas linha por linha. Exemplo obrigatório para cada defeito: "- KM X | Lado LD | Medida: X m²". NUNCA omita a medida individual. ATENÇÃO EXCLUSIVA: Para o defeito "Áreas para Restauração", o campo Lado deve ser SEMPRE preenchido obrigatoriamente como "Ambos os Lados" (nunca use "Não Especificado").
7. FORMATO OBRIGATÓRIO: Use '###' para títulos, '>' para blocos amarelos e '•' para listas.

--- TEMPLATE ESTRITO ---
### 📍 RESUMO TÉCNICO LVC
+ 🛣️ *Trecho:* {nome_trecho}

• Extensão: **[X] km**
• Revestimento (Pista): **[Tipo e KMs]**
• Acostamento: **[Descrição]**

[SE EXISTIR PÓRTICO, ESCREVA AQUI. SE NÃO, APAGUE]
> 🏗️ *Pórticos:*
- [Situação]

---
### 1. PISTA DE ROLAMENTO
[SE ZERO DEFEITOS, USE A FRASE DA REGRA 2. SE HOUVER, LISTE APENAS OS QUE EXISTEM COM O SEGUINTE MODELO E APAGUE OS VAZIOS:]

> *[Nome do Defeito Existente]*
- Ocorrências: **[X]** | Total: **[X] [Unidade correta]**
- Relação Detalhada:
  - KM [X] | Lado [LE/LD/Eixo] | Medida: [X] [Unidade correta]

---
### 2. DRENAGEM E OAEs
> *OAEs e Bueiros*
• Pontes/Viadutos: [Qtd] | Local: [Desc]
• Passagens Molhadas: [Qtd]
• Total de Bueiros: [X]
• Relação de Bueiros: [KM | Tipo | Condição | Obs]

> *Meios-fios e Sarjetas (Existentes)*
• Total Meios-fios: [X] m | Bom ([X]m) | Ruim ([X]m)
• Total Sarjetas: [X] m | Bom ([X]m) | Ruim ([X]m)

[SE HOUVER IMPLANTAÇÃO EXATA, ESCREVA O BLOCO DE IMPLANTAÇÃO AQUI. SE NÃO HOUVER, APAGUE]

---
### 3. SINALIZAÇÃO
> *Horizontal (Pintura)*
• Situação: [Desc]

> *Vertical (Placas Existentes)*
• Situação: [Desc técnica geral]
[Se houver tabela, liste a relação completa aqui]

[SE HOUVER PLACAS A IMPLANTAR NA TABELA, ESCREVA O BLOCO "A Implantar (Placas)" AQUI. SE NÃO HOUVER, APAGUE ABSOLUTAMENTE O BLOCO]

---
### 4. SERVIÇOS GERAIS
- *Roço Lateral:* [Se houver valor, coloque "Há necessidade de roço em **X ha** LD / LE". Se for 0 ou não houver, escreva EXATAMENTE "Não há necessidade de executar roço no levantamento atual."]

---
### 5. OBSERVAÇÕES GERAIS (OBS)
• OBSERVAÇÕES:
[Transcreva as observações]

---
[SE HOUVER SERVIÇOS EXECUTADOS (RP OU TP), CRIE AQUI O TÓPICO "### 6. SERVIÇOS EXECUTADOS RECENTES" LISTANDO ÁREA E RELAÇÃO. SE NÃO, APAGUE O TÓPICO]

---
• Conclusão: [Parecer final]
"""

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    termo = request.message.strip()
    lista_arquivos = listar_pdfs_firebase(termo)
    if not lista_arquivos: return {"reply": "Não encontrado."}
    nome = lista_arquivos[0]
    texto = ler_pdf_firebase(nome)
    model = genai.GenerativeModel("gemini-2.5-flash")
    resposta = model.generate_content(get_prompt(nome, texto), request_options={"timeout": 600.0})
    return {"reply": resposta.text, "pdf_name": nome}

@app.post("/upload-pdf")
async def upload_pdf_endpoint(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(await file.read())
        temp_path = temp_pdf.name
    arquivo_pdf = genai.upload_file(temp_path)
    model = genai.GenerativeModel("gemini-2.5-flash")
    resposta = model.generate_content([get_prompt(file.filename, ""), arquivo_pdf], request_options={"timeout": 600.0})
    return {"reply": resposta.text, "pdf_name": file.filename}