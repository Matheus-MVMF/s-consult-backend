from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai
from dotenv import load_dotenv
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

# Configuração do Gemini
api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# =====================================================================
# PROMPT 1: INVENTÁRIO ANTIGO (MANTIDO INTACTO)
# =====================================================================
def get_prompt_inventario(nome_arquivo):
    return f"""
Aja como um Engenheiro Rodoviário Sênior. Analise o arquivo de inventário em anexo ({nome_arquivo}).

REGRAS ABSOLUTAS E INQUEBRÁVEIS DE ENGENHARIA (NÃO DESOBEDEÇA NENHUMA):
1. SE NÃO EXISTIR NO PDF, APAGUE O TÓPICO. Apenas liste os que existem, e exclua os blocos vazios.
2. MENSAGEM DE BOM ESTADO: APENAS SE a "Pista de Rolamento" não tiver NENHUM defeito.
3. A IMPLANTAR (SINALIZAÇÃO E DRENAGEM): Se não houver uma tabela EXPLICANDO O QUE IMPLANTAR, APAGUE O TÓPICO INTEIRO.
4. ROÇO LATERAL (SEMPRE OBRIGATÓRIO): Se houver área para roço, informe o valor. Se for 0, escreva: "Não há necessidade de executar roço no levantamento atual."
5. UNIDADES OBRIGATÓRIAS: Restauração (m); Erosões (m³); Panelas, Desgaste, Rebaixamentos (m²).
6. DETALHAMENTO CIRÚRGICO: Você DEVE listar as medidas linha por linha. Exemplo obrigatório para cada defeito: "- KM X | Lado LD | Medida: X m²".
7. FORMATO OBRIGATÓRIO: Use '###' para títulos, '>' para blocos amarelos e '•' para listas.

--- TEMPLATE ESTRITO ---
### 📍 RESUMO TÉCNICO LVC
+ 🛣️ *Trecho:* Extraia do PDF

• Extensão: **[X] km**
• Revestimento (Pista): **[Tipo e KMs]**
• Acostamento: **[Descrição]**

[SE EXISTIR PÓRTICO, ESCREVA AQUI. SE NÃO, APAGUE]
> 🏗️ *Pórticos:*
- [Situação]

---
### 1. PISTA DE ROLAMENTO
> *[Nome do Defeito Existente]*
- Ocorrências: **[X]** | Total: **[X] [Unidade]**
- Relação Detalhada:
  - KM [X] | Lado [LE/LD/Eixo] | Medida: [X] [Unidade]

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

---
### 3. SINALIZAÇÃO
> *Horizontal (Pintura)*
• Situação: [Desc]

> *Vertical (Placas Existentes)*
• Situação: [Desc técnica geral]

[SE HOUVER PLACAS A IMPLANTAR NA TABELA, ESCREVA O BLOCO "A Implantar (Placas)" AQUI. SE NÃO, APAGUE]

---
### 4. SERVIÇOS GERAIS
- *Roço Lateral:* [Descreva a necessidade de roço]

---
### 5. OBSERVAÇÕES GERAIS (OBS)
• OBSERVAÇÕES:
[Transcreva as observações]

---
• Conclusão: [Parecer final]
"""

# =====================================================================
# PROMPT 2: NOVO RELATÓRIO (COM REGRAS DE INTERVALO DE KMS)
# =====================================================================
def get_prompt_relatorio(nome_arquivo):
    return f"""
Aja como um Engenheiro Rodoviário Sênior. Analise o NOVO RELATÓRIO INDIVIDUAL em anexo ({nome_arquivo}).
Busque nas tabelas deste relatório todo o conteúdo necessário e extraia as informações seguindo exatamente as mesmas regras e o mesmo TEMPLATE ESTRITO abaixo.

REGRAS ABSOLUTAS E INQUEBRÁVEIS DE ENGENHARIA (NÃO DESOBEDEÇA NENHUMA):
1. SE NÃO EXISTIR NO PDF, APAGUE O TÓPICO: Apenas liste os defeitos que existem (Panelas, Rebaixamentos, etc.), e exclua os blocos vazios.
2. MENSAGEM DE BOM ESTADO: APENAS SE a "Pista de Rolamento" não tiver NENHUM defeito.
3. A IMPLANTAR (SINALIZAÇÃO E DRENAGEM): Se não houver uma tabela EXPLICANDO O QUE IMPLANTAR, APAGUE O TÓPICO INTEIRO.
4. ROÇO LATERAL: NUNCA pode ser apagado.
5. UNIDADES OBRIGATÓRIAS: Restauração (m); Erosões (m³); Panelas, Rebaixamentos, Desgaste (m²).

6. REGRA CRÍTICA DE LADOS E INTERVALOS DE KM (LEIA ATENTAMENTE):
   - PANELAS: Extraia SEMPRE o KM Inicial e o KM Final, mesmo se forem iguais (Ex: KM 6.2 a 6.7 OU KM 5.98 a 5.98). NÃO INVENTE LADO! Coloque apenas KM e a Medida. NUNCA recuse o detalhamento.
   - DESGASTES: Extraia SEMPRE o KM Inicial e o KM Final, mesmo se forem iguais. Extraia o Lado conforme a tabela.
   - ÁREAS PARA RESTAURAÇÃO: Extraia SEMPRE o KM Inicial e o KM Final. O Lado DEVE ser SEMPRE escrito como "Ambos os Lados".
   - REBAIXAMENTOS E EROSÕES: Extraia apenas um KM. Extraia o lado EXATAMENTE como está na tabela (Ex: LE, LD). SE A PALAVRA "EIXO" NÃO ESTIVER ESCRITA NA TABELA, VOCÊ É PROIBIDO DE USÁ-LA.

7. REGRA DE PÓRTICOS E OBSERVAÇÕES:
   - PÓRTICOS: Devem ficar APENAS no topo do resumo. Busque na tabela de OBSERVAÇÕES. Extraia o KM e a descrição exata da tabela (Ex: "- KM X | Pórtico Novo"). NUNCA use "Situação: Existente".
   - OBSERVAÇÕES GERAIS (Tópico 5): Coloque AQUI APENAS as informações descritivas de texto que sobraram na tabela de OBSERVAÇÕES do relatório. NÃO coloque os pórticos aqui novamente.

--- TEMPLATE ESTRITO ---
### 📍 RESUMO TÉCNICO LVC
+ 🛣️ *Trecho:* Extraia do PDF

• Extensão: **[X] km**
• Revestimento (Pista): **[Tipo e KMs]**
• Acostamento: **[Descrição]**

[SE EXISTIR PÓRTICO, ESCREVA AQUI CONFORME A REGRA 7. SE NÃO, APAGUE]
> 🏗️ *Pórticos:*
- KM [X] | [Descrição exata da tabela]

---
### 1. PISTA DE ROLAMENTO
[SE ZERO DEFEITOS, USE A MENSAGEM DA REGRA 2. SE HOUVER, LISTE APENAS OS EXISTENTES]

> *[Nome do Defeito Existente]*
- Ocorrências: **[X]** | Total: **[X] [Unidade correta]**
- Relação Detalhada:
  - [Para Panelas: KM [Inicial] a [Final] | Medida: [X] m²]
  - [Para Restauração: KM [Inicial] a [Final] | Lado Ambos os Lados | Medida: [X] m]
  - [Para Desgastes: KM [Inicial] a [Final] | Lado [Extraído] | Medida: [X] m²]
  - [Para Rebaixamentos/Erosões: KM [X] | Lado [Extraído] | Medida: [X] [Unidade]]

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

[SE HOUVER IMPLANTAÇÃO EXATA, ESCREVA O BLOCO AQUI. SE NÃO, APAGUE]

---
### 3. SINALIZAÇÃO
> *Horizontal (Pintura)*
• Situação: [Desc]

> *Vertical (Placas Existentes)*
• Situação: [Desc técnica geral]
[Se houver tabela, liste a relação completa aqui]

[SE HOUVER PLACAS A IMPLANTAR NA TABELA, ESCREVA O BLOCO "A Implantar (Placas)" AQUI. SE NÃO, APAGUE]

---
### 4. SERVIÇOS GERAIS
- *Roço Lateral:* [Se houver valor, coloque "Há necessidade de roço em **X ha** LD / LE". Se for 0 ou não houver, escreva "Não há necessidade de executar roço no levantamento atual."]

---
### 5. OBSERVAÇÕES GERAIS (OBS)
• OBSERVAÇÕES:
[Transcreva apenas o conteúdo de texto da tabela de observações, excluindo os pórticos]

---
[SE HOUVER SERVIÇOS EXECUTADOS (RP OU TP), CRIE AQUI O TÓPICO "### 6. SERVIÇOS EXECUTADOS RECENTES" LISTANDO ÁREA E RELAÇÃO. SE NÃO, APAGUE O TÓPICO]

---
• Conclusão: [Parecer final]
"""

# =====================================================================
# ENDPOINT 1: UPLOAD DO INVENTÁRIO (TABELAS EXCEL)
# =====================================================================
@app.post("/upload-inventario")
async def upload_inventario_endpoint(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(await file.read())
        temp_path = temp_pdf.name
    
    try:
        arquivo_pdf = genai.upload_file(temp_path)
        model = genai.GenerativeModel("gemini-2.5-flash")
        resposta = model.generate_content([get_prompt_inventario(file.filename), arquivo_pdf], request_options={"timeout": 600.0})
        return {"reply": resposta.text, "pdf_name": file.filename}
    except Exception as e:
        return {"reply": f"❌ Erro: {str(e)}"}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

# =====================================================================
# ENDPOINT 2: UPLOAD DO NOVO RELATÓRIO
# =====================================================================
@app.post("/upload-relatorio")
async def upload_relatorio_endpoint(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(await file.read())
        temp_path = temp_pdf.name
    
    try:
        arquivo_pdf = genai.upload_file(temp_path)
        model = genai.GenerativeModel("gemini-2.5-flash")
        resposta = model.generate_content([get_prompt_relatorio(file.filename), arquivo_pdf], request_options={"timeout": 600.0})
        return {"reply": resposta.text, "pdf_name": file.filename}
    except Exception as e:
        return {"reply": f"❌ Erro: {str(e)}"}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)