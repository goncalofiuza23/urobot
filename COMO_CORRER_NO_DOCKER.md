# Como correr o uRobot no Docker Desktop

## Pre-requisito (UMA vez, fora do Docker)

A aplicacao usa o **Ollama** para o modelo de linguagem. O Ollama corre no PC
(nao dentro do container) e o container liga-se a ele.

1. Instalar o Ollama: https://ollama.com/download
2. Abrir o terminal e descarregar os modelos:
   ```
   ollama pull llama3
   ollama pull nomic-embed-text
   ```
3. Confirmar que o Ollama esta a correr (icone na barra de tarefas).

## Passos no Docker Desktop (para o video)

1. **Clonar o projeto** (se ainda nao tiver):
   ```
   git clone https://github.com/goncalofiuza23/urobot.git
   ```

2. Abrir a aplicacao **Docker Desktop**.

3. Ir ao separador **Images** -> botao **Build** (ou "Create" / "Build from
   Dockerfile") -> escolher a pasta do projeto (a que tem o ficheiro
   `Dockerfile`) -> dar um nome a imagem, por exemplo `urobot`.
   - Aguardar o build terminar (a primeira vez demora, instala as dependencias).

4. Quando a imagem aparecer na lista, clicar em **Run**.
   - Em **Optional settings**, no campo **Host port** escrever **7860**
     (mapeia para a porta 7860 do container).
   - Clicar em **Run**.

5. Ir ao separador **Containers** e confirmar que o container `urobot` esta
   a correr (verde).

6. Abrir o browser em **http://localhost:7860** e demonstrar a aplicacao:
   - Carregar um documento (PDF), fazer uma pergunta no chat, gerar um resumo,
     um questionario, etc.

## Notas

- A imagem do container so corre a aplicacao. O Ollama (modelo) fica no PC e o
  container fala com ele atraves de `host.docker.internal:11434` (ja configurado
  no `Dockerfile`).
- Porta da aplicacao: **7860**.
