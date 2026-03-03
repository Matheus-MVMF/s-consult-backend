import os
import shutil

# --- CONFIGURAÇÃO ---
# Cole aqui o caminho da pasta "TD 01" que aparece na sua imagem
# DICA: No Windows, clique com botão direito na pasta TD 01 e escolha "Copiar como caminho"
pasta_origem = r"C:\Users\engen\OneDrive\Documentos\Matheus\PESSOAL\S CONSULT V2\TDS\TD 12"

# Nome da nova pasta onde tudo será salvo
pasta_destino = os.path.join(pasta_origem, "00_TODOS_PDFS_PARA_UPLOAD")

def organizar_arquivos():
    # 1. Cria a pasta de destino se não existir
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
        print(f"📂 Pasta criada: {pasta_destino}")
    
    contador = 0
    erros = 0

    print("🚀 Começando a varredura...")

    # 2. Percorre todas as subpastas
    for raiz, pastas, arquivos in os.walk(pasta_origem):
        
        # Pula a própria pasta de destino para não entrar em loop
        if "00_TODOS_PDFS_PARA_UPLOAD" in raiz:
            continue

        for arquivo in arquivos:
            # 3. Verifica se é PDF (maiúsculo ou minúsculo)
            if arquivo.lower().endswith(".pdf"):
                caminho_completo_original = os.path.join(raiz, arquivo)
                
                # Pega o nome da pasta onde o arquivo estava (ex: "PI - 301...")
                nome_da_pasta_pai = os.path.basename(raiz)
                
                # 4. Cria um nome novo para evitar duplicatas e identificar a origem
                # Ex: "PI - 301... -- relatorio.pdf"
                novo_nome = f"{nome_da_pasta_pai} -- {arquivo}"
                caminho_destino = os.path.join(pasta_destino, novo_nome)

                try:
                    # 5. Faz a cópia
                    shutil.copy2(caminho_completo_original, caminho_destino)
                    print(f"✅ Copiado: {novo_nome}")
                    contador += 1
                except Exception as e:
                    print(f"❌ Erro ao copiar {arquivo}: {e}")
                    erros += 1

    print("-" * 30)
    print("✨ CONCLUÍDO!")
    print(f"📂 Total de PDFs copiados: {contador}")
    if erros > 0:
        print(f"⚠️ Erros encontrados: {erros}")
    print(f"📍 Seus arquivos estão em: {pasta_destino}")

if __name__ == "__main__":
    organizar_arquivos()