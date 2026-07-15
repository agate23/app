# Agate Remote para Android

Aplicativo Flutter que adiciona leitura do QR Code, conexão salva e uma WebView dedicada para a interface completa do Agate Remote.

## Executar localmente

```bash
flutter create --platforms=android --org com.agate.remote --project-name agate_remote .
python tool/prepare_android.py
flutter pub get
flutter run
```

O Android precisa estar na mesma rede do PC ou conectado à mesma rede Tailscale.
