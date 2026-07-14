# Agate Remote V2

Controle um computador Windows pelo celular na mesma rede Wi-Fi ou por uma rede privada Tailscale. O projeto inclui agente Windows, interface PWA e aplicativo Flutter para Android.

## Recursos implementados

- Agente Windows com ícone na bandeja, PIN e QR Code.
- Mouse, clique, rolagem, teclado, texto, clipboard, mídia e bloqueio da sessão.
- Transmissão da tela por WebRTC com 5–30 FPS e ajuste de qualidade.
- Transferência de arquivos nos dois sentidos pela pasta `Downloads/AgateRemote`.
- Limite configurável de upload, nomes sanitizados e cálculo SHA-256 no recebimento.
- Perfis editáveis para mídia, apresentação, estoque e jogos.
- Acesso por rede local ou Tailscale, sem abrir portas no roteador.
- PWA instalável e aplicativo Flutter Android com leitura do QR Code.
- Builds automáticos do `.exe` e do APK pelo GitHub Actions.

## Segurança

O aplicativo não oferece terminal remoto, PowerShell remoto ou execução arbitrária de programas. O agente aceita por padrão apenas loopback, redes privadas, link-local e a faixa `100.64.0.0/10` usada pelo Tailscale. O pareamento usa PIN, bloqueio de tentativas e token temporário vinculado ao endereço do celular.

Use somente em computadores e redes sob sua autorização. Não encaminhe a porta `8765` no roteador.

## Rodar pelo código no Windows

1. Instale Python 3.11 ou superior e marque **Add Python to PATH**.
2. Baixe a branch e execute `instalar_windows.bat`.
3. Use o ícone **Agate Remote** perto do relógio para mostrar o QR Code.
4. No celular, abra o endereço exibido ou use o aplicativo Android.

Nas próximas vezes, execute `iniciar_windows.bat`.

## Usar o executável

Abra **Actions**, selecione **Build Windows EXE** e baixe o artefato `AgateRemote-Windows`. Extraia e execute `AgateRemote.exe`.

## Aplicativo Android

Abra **Actions**, selecione **Build Android APK** e baixe `AgateRemote-Android`. O projeto-fonte está em `flutter_app/`.

## Tailscale

1. Instale e entre na mesma conta do Tailscale no PC e no celular.
2. Inicie o Agate Remote.
3. No menu da bandeja, copie o endereço. Quando o Tailscale estiver ativo, será mostrado um endereço `http://100.x.x.x:8765`.
4. Use esse endereço no aplicativo Android.

Nenhuma porta pública precisa ser aberta.

## Configuração opcional

```powershell
$env:AGATE_REMOTE_PORT="8765"
$env:AGATE_REMOTE_PIN="123456"
$env:AGATE_REMOTE_MAX_UPLOAD_MB="100"
$env:AGATE_REMOTE_SHARED_DIR="D:\Compartilhado"
python server.py
```

Definir `AGATE_REMOTE_PRIVATE_ONLY=0` libera endereços públicos e não é recomendado.

## Estrutura

```text
server.py                    API, WebSocket e inicialização
agent/                       segurança, controle, WebRTC, arquivos e bandeja
web/                         PWA responsiva
flutter_app/                 aplicativo Android
profiles.json                perfis iniciais
AgateRemote.spec             empacotamento PyInstaller
.github/workflows/           builds do EXE e APK
```
