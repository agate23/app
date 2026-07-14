from pathlib import Path

manifest = Path("android/app/src/main/AndroidManifest.xml")
text = manifest.read_text(encoding="utf-8")
permissions = (
    '<uses-permission android:name="android.permission.INTERNET" />\n'
    '<uses-permission android:name="android.permission.CAMERA" />\n'
)
if "android.permission.CAMERA" not in text:
    insert_at = text.find(">") + 1
    text = text[:insert_at] + "\n    " + permissions.replace("\n", "\n    ").rstrip() + text[insert_at:]
if "usesCleartextTraffic" not in text:
    text = text.replace("<application", '<application android:usesCleartextTraffic="true"', 1)
manifest.write_text(text, encoding="utf-8")

for candidate in (Path("android/app/build.gradle.kts"), Path("android/app/build.gradle")):
    if not candidate.exists():
        continue
    build = candidate.read_text(encoding="utf-8")
    build = build.replace("minSdk = flutter.minSdkVersion", "minSdk = 24")
    build = build.replace("minSdkVersion flutter.minSdkVersion", "minSdkVersion 24")
    candidate.write_text(build, encoding="utf-8")
