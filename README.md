# Arquivo Oculto — automação inicial

Este projeto cria um Short vertical a partir de um roteiro gerado por Gemini:
1. Gemini cria roteiro e cinco cartões de cena.
2. Edge-TTS gera a narração em português.
3. Pillow cria fundos visuais originais com movimento de zoom via FFmpeg.
4. FFmpeg monta um vídeo 9:16.
5. Opcionalmente, a API oficial do YouTube envia o vídeo como **privado**.

## Limitações importantes
- O visual desta primeira versão é motion design original (cartões e fundos animados), não cenas cinematográficas geradas por IA.
- `edge-tts` usa um serviço online não oficial; pode mudar ou parar de funcionar.
- A cota gratuita do Gemini pode mudar e não é garantia de produção ilimitada.
- O envio automático ao YouTube exige OAuth e aprovação/condições da API. Projetos de API não verificados podem ter restrições de visibilidade; por segurança, este projeto envia como privado.
- O agendamento do GitHub Actions pode ser desativado em repositórios públicos sem atividade por 60 dias. O workflow também pode ser iniciado manualmente.
- Não coloque chaves ou tokens nos arquivos do repositório. Use GitHub Secrets.

## Configuração pelo celular
1. Crie um repositório GitHub. Para usar runners padrão sem cobrança, um repositório público pode ser uma opção; o código ficará visível. Nunca publique segredos.
2. Envie todos os arquivos desta pasta para o repositório pelo site do GitHub.
3. Em Settings → Secrets and variables → Actions → New repository secret, crie:
   - `GEMINI_API_KEY`: chave criada no Google AI Studio.
4. Abra Actions e habilite workflows, se o GitHub pedir.
5. Execute `Daily Short` → Run workflow para testar.
6. O vídeo será salvo como artefato `arquivo-oculto-short` na execução. Baixe para conferir.

## Ativar upload automático (opcional)
O upload automático não fica ativo por padrão. Para ativá-lo, será necessário:
- Criar um projeto no Google Cloud e ativar YouTube Data API v3.
- Criar credenciais OAuth adequadas para YouTube upload.
- Obter um token OAuth com refresh token e escopo `https://www.googleapis.com/auth/youtube.upload`.
- Guardar o JSON de credenciais autorizado, codificado em Base64, no segredo `YT_TOKEN_JSON_B64`.
- Criar a variável de repositório `YOUTUBE_AUTO_UPLOAD` com valor `true`.

O script usa `privacyStatus=private` intencionalmente. Não altere para público sem compreender as restrições de API e conferir o vídeo. O fluxo pode exigir revisão/auditoria do projeto do YouTube para publicar publicamente.

## Executar localmente
Requer Python 3.11, FFmpeg e fontes DejaVu:
```bash
pip install -r requirements.txt
export GEMINI_API_KEY="SUA_CHAVE"
python pipeline.py
```

## Transparência e direitos
O roteiro é gerado por IA e precisa ser factual. A versão inicial pede fontes no roteiro, mas não valida automaticamente cada afirmação. Não use nomes, imagens, vozes ou material protegido de terceiros sem autorização. Evite apresentar lendas como fatos.
