import os
import shutil

# Define onde estão os arquivos (pode ser a pasta atual '.')
pasta_alvo = "TDS/TD 04" 

# Varre todos os arquivos da pasta
for arquivo in os.listdir(pasta_alvo):
    # Se for um PDF (e não for o script nem pastas)
    if arquivo.lower().endswith(".pdf"):
        nome_sem_extensao = os.path.splitext(arquivo)[0]
        
        # Cria a pasta com o nome do trecho (se não existir)
        caminho_nova_pasta = os.path.join(pasta_alvo, nome_sem_extensao)
        if not os.path.exists(caminho_nova_pasta):
            os.makedirs(caminho_nova_pasta)
            print(f"📂 Pasta criada: {nome_sem_extensao}")
        
        # Move o PDF para dentro dela
        caminho_antigo = os.path.join(pasta_alvo, arquivo)
        caminho_novo = os.path.join(caminho_nova_pasta, arquivo)
        shutil.move(caminho_antigo, caminho_novo)
        print(f"➡️ PDF movido para: {caminho_novo}")

print("✅ Organização concluída! Agora arraste as fotos para dentro de cada pasta.")