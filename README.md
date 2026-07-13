# Agate Remote

Controle um computador Windows pelo celular usando o navegador, na mesma rede Wi‑Fi. O projeto combina um agente leve em Python no PC com uma interface móvel instalável como PWA.

## O que já funciona no MVP

- Mouse estilo trackpad com clique, clique duplo, botão direito, botão do meio, rolagem e modo arrastar.
- Teclado remoto, envio de textos com acentos, setas e combinações como `Ctrl + Shift + Esc`.
- Controle de mídia e volume.
- Prévia leve da tela do computador, atualizada aproximadamente uma vez por segundo.
- Área de transferência entre celular e PC.
- Painel de atalhos editável pelo celular.
- Atalhos seguros para teclas, mídia, texto e abertura de sites.
- Métricas de CPU, memória e bateria.
- Bloqueio remoto da sessão do Windows.
- Pareamento por PIN, sessão temporária e bloqueio contra tentativas repetidas.
- Restrição padrão para endereços de rede local.

## Segurança adotada

O celular não pode enviar comandos de terminal, PowerShell ou caminhos de programas arbitrários. O painel personalizado aceita somente tipos de ação validados. A porta não deve ser encaminhada no roteador nem publicada diretamente na internet.

> Use somente em computadores e redes sob sua autorização.

## Instalação no Windows

1. Instale o **Python 3.11 ou superior** e marque a opção **Add Python to PATH**.
2. Baixe este repositório e extraia a pasta.
3. Execute `instalar_windows.bat`.
4. O terminal mostrará um endereço como `http://192.168.0.10:8765` e um PIN de seis dígitos.
5. Abra o endereço no celular conectado à mesma rede Wi‑Fi e informe o PIN.
6. Nas próximas vezes, use `iniciar_windows.bat`.

Caso o Firewall do Windows pergunte, permita o Python somente em **redes privadas**.

## Instalar como aplicativo no celular

Depois de abrir no navegador, use **Adicionar à tela inicial** ou o botão **Instalar no celular** quando ele estiver disponível. Assim o controle abre em tela cheia como um aplicativo.

## Configuração opcional

As variáveis abaixo podem ser definidas antes de iniciar:

```powershell
$env:AGATE_REMOTE_PORT="8765"
$env:AGATE_REMOTE_PIN="123456"
python server.py
```

- `AGATE_REMOTE_PORT`: porta do servidor.
- `AGATE_REMOTE_PIN`: PIN fixo. Sem essa variável, um PIN novo é gerado a cada início.
- `AGATE_REMOTE_PRIVATE_ONLY=0`: libera endereços externos. **Não recomendado** sem VPN e HTTPS.

## Estrutura

```text
server.py                 agente do Windows, API e WebSocket
actions.json              painel de atalhos persistente
web/index.html            interface móvel
web/manifest.webmanifest  configuração PWA
web/sw.js                 cache básico da interface
```

## Próximas etapas planejadas

- Empacotar o agente como `.exe` com bandeja do sistema e QR Code.
- Transmissão de tela por WebRTC com maior taxa de quadros.
- Transferência segura de arquivos entre celular e PC.
- Perfis de painel para mídia, apresentação, estoque e jogos.
- Controle opcional pela internet através de Tailscale, sem abrir portas públicas.
- Aplicativo Flutter nativo para Android, mantendo a PWA como opção leve.

## Licença

MIT.
