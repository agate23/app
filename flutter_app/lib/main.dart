import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webview_flutter/webview_flutter.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AgateRemoteApp());
}

class AgateRemoteApp extends StatelessWidget {
  const AgateRemoteApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Agate Remote',
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF8B5CF6),
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: const Color(0xFF100D17),
        useMaterial3: true,
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          filled: true,
        ),
      ),
      home: const ConnectionPage(),
    );
  }
}

bool isValidServerUrl(String value) {
  final uri = Uri.tryParse(value);
  return uri != null &&
      (uri.scheme == 'http' || uri.scheme == 'https') &&
      uri.host.isNotEmpty;
}

String normalizeUrl(String value) {
  var url = value.trim();
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = 'http://$url';
  }
  return url.endsWith('/') ? url.substring(0, url.length - 1) : url;
}

class PairingData {
  const PairingData({
    required this.url,
    required this.pin,
    this.name = 'PC',
    this.urls = const [],
  });

  final String url;
  final String pin;
  final String name;
  final List<String> urls;

  List<String> get candidates {
    final result = <String>[];
    for (final value in <String>[url, ...urls]) {
      final normalized = normalizeUrl(value);
      if (isValidServerUrl(normalized) && !result.contains(normalized)) {
        result.add(normalized);
      }
    }
    return result;
  }

  factory PairingData.fromQr(String raw) {
    final dynamic decoded = jsonDecode(raw);
    if (decoded is! Map) {
      throw const FormatException('QR Code inválido.');
    }

    final map = Map<String, dynamic>.from(decoded);
    final mainUrl = normalizeUrl((map['url'] ?? '').toString());
    final pin = (map['pin'] ?? '').toString().trim();
    final name = (map['name'] ?? 'PC').toString();
    final urls = <String>[];

    final dynamic rawUrls = map['urls'];
    if (rawUrls is List) {
      for (final item in rawUrls) {
        final candidate = normalizeUrl(item.toString());
        if (isValidServerUrl(candidate) && !urls.contains(candidate)) {
          urls.add(candidate);
        }
      }
    }
    if (isValidServerUrl(mainUrl) && !urls.contains(mainUrl)) {
      urls.insert(0, mainUrl);
    }
    if (urls.isEmpty) {
      throw const FormatException('Endereço inválido no QR Code.');
    }
    if (pin.length != 6) {
      throw const FormatException('PIN inválido no QR Code.');
    }

    return PairingData(url: urls.first, pin: pin, name: name, urls: urls);
  }
}

class ConnectionPage extends StatefulWidget {
  const ConnectionPage({super.key});

  @override
  State<ConnectionPage> createState() => _ConnectionPageState();
}

class _ConnectionPageState extends State<ConnectionPage> {
  final _url = TextEditingController();
  final _pin = TextEditingController();
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  @override
  void dispose() {
    _url.dispose();
    _pin.dispose();
    super.dispose();
  }

  Future<void> _restore() async {
    final prefs = SharedPreferencesAsync();
    _url.text = await prefs.getString('serverUrl') ?? '';
    _pin.text = await prefs.getString('serverPin') ?? '';
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _openRemote(PairingData data) async {
    final prefs = SharedPreferencesAsync();
    await prefs.setString('serverUrl', data.url);
    await prefs.setString('serverPin', data.pin);
    if (!mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => RemotePage(pairing: data)),
    );
  }

  Future<void> _scan() async {
    final result = await Navigator.of(context).push<PairingData>(
      MaterialPageRoute<PairingData>(builder: (_) => const ScannerPage()),
    );
    if (result == null) return;
    _url.text = result.url;
    _pin.text = result.pin;
    await _openRemote(result);
  }

  void _connect() {
    final url = normalizeUrl(_url.text);
    final pin = _pin.text.trim();
    if (!isValidServerUrl(url) || pin.length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Informe o endereço do PC e um PIN de 6 dígitos.'),
        ),
      );
      return;
    }
    _openRemote(PairingData(url: url, pin: pin, urls: [url]));
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const CircleAvatar(
                        radius: 38,
                        backgroundColor: Color(0xFF7C3AED),
                        child: Text(
                          'AR',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Agate Remote',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Controle seu PC pela rede local ou pelo Tailscale.',
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                      TextField(
                        controller: _url,
                        keyboardType: TextInputType.url,
                        autocorrect: false,
                        decoration: const InputDecoration(
                          labelText: 'Endereço',
                          hintText: 'http://192.168.0.10:8765',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _pin,
                        keyboardType: TextInputType.number,
                        maxLength: 6,
                        obscureText: true,
                        decoration: const InputDecoration(labelText: 'PIN'),
                      ),
                      FilledButton.icon(
                        onPressed: _connect,
                        icon: const Icon(Icons.link),
                        label: const Text('Conectar'),
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton.icon(
                        onPressed: _scan,
                        icon: const Icon(Icons.qr_code_scanner),
                        label: const Text('Ler QR Code'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  bool _handled = false;

  void _detected(BarcodeCapture capture) {
    if (_handled) return;
    final raw = capture.barcodes.firstOrNull?.rawValue;
    if (raw == null) return;
    try {
      final data = PairingData.fromQr(raw);
      _handled = true;
      Navigator.of(context).pop(data);
    } on FormatException catch (error) {
      _handled = true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
      Future<void>.delayed(const Duration(seconds: 2), () {
        if (mounted) _handled = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ler QR Code')),
      body: Stack(
        fit: StackFit.expand,
        children: [
          MobileScanner(onDetect: _detected),
          Center(
            child: Container(
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                border: Border.all(
                  color: const Color(0xFFD8B4FE),
                  width: 3,
                ),
                borderRadius: BorderRadius.circular(24),
              ),
            ),
          ),
          const Align(
            alignment: Alignment.bottomCenter,
            child: SafeArea(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'Aponte para o QR Code exibido pelo agente no Windows.',
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class RemotePage extends StatefulWidget {
  const RemotePage({super.key, required this.pairing});

  final PairingData pairing;

  @override
  State<RemotePage> createState() => _RemotePageState();
}

class _RemotePageState extends State<RemotePage> {
  late final WebViewController _controller;
  late final List<String> _urls;
  int _urlIndex = 0;
  int _progress = 0;
  String? _error;
  bool _pinInjected = false;

  String get _currentUrl => _urls[_urlIndex];

  @override
  void initState() {
    super.initState();
    _urls = widget.pairing.candidates;
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF100D17))
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (value) {
            if (mounted) setState(() => _progress = value);
          },
          onPageStarted: (_) {
            _pinInjected = false;
            if (mounted) setState(() => _error = null);
          },
          onWebResourceError: _handleWebError,
          onPageFinished: (_) => _injectPin(),
        ),
      )
      ..loadRequest(Uri.parse(_currentUrl));
  }

  void _handleWebError(WebResourceError error) {
    if (error.isForMainFrame != true) return;
    if (_urlIndex + 1 < _urls.length) {
      _urlIndex += 1;
      _pinInjected = false;
      if (mounted) {
        setState(() {
          _error = null;
          _progress = 0;
        });
      }
      _controller.loadRequest(Uri.parse(_currentUrl));
      return;
    }
    if (mounted) {
      setState(() {
        _error = '${error.description}\n\nEndereços testados:\n${_urls.join('\n')}';
      });
    }
  }

  Future<void> _injectPin() async {
    if (_pinInjected) return;
    final encodedPin = jsonEncode(widget.pairing.pin);
    await _controller.runJavaScript('''
      (() => {
        const input = document.getElementById('pinInput');
        const button = document.getElementById('pairButton');
        if (input && button) {
          input.value = $encodedPin;
          button.click();
          return true;
        }
        return false;
      })();
    ''');
    _pinInjected = true;
  }

  Future<bool> _handleBack() async {
    if (await _controller.canGoBack()) {
      await _controller.goBack();
      return false;
    }
    return true;
  }

  void _retry() {
    _urlIndex = 0;
    _pinInjected = false;
    setState(() {
      _error = null;
      _progress = 0;
    });
    _controller.loadRequest(Uri.parse(_currentUrl));
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        if (await _handleBack() && context.mounted) {
          Navigator.of(context).pop();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(widget.pairing.name),
              Text(
                Uri.parse(_currentUrl).host,
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ],
          ),
          actions: [
            IconButton(
              tooltip: 'Recarregar',
              onPressed: _retry,
              icon: const Icon(Icons.refresh),
            ),
          ],
          bottom: _progress < 100
              ? PreferredSize(
                  preferredSize: const Size.fromHeight(3),
                  child: LinearProgressIndicator(value: _progress / 100),
                )
              : null,
        ),
        body: _error == null
            ? WebViewWidget(controller: _controller)
            : Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.wifi_off, size: 56),
                      const SizedBox(height: 12),
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      const Text(
                        'Confirme que o PC e o celular estão na mesma rede e que a porta 8765 foi liberada no Firewall do Windows.',
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: _retry,
                        child: const Text('Tentar novamente'),
                      ),
                    ],
                  ),
                ),
              ),
      ),
    );
  }
}

extension FirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
