# PDF Düzenleyici – Android APK

## Klasör yapısı
    pdf_duzenleyici/
      pyproject.toml              bağımlılıklar + Android izinleri
      src/main.py                 Flet arayüzü (13 araç)
      src/pdf_araclari.py         PDF işlemleri (PyMuPDF uyarlaması)
      src/assets/fonts/DejaVuSans.ttf   Türkçe karakter için yazı tipi
      .github/workflows/build-apk.yml   GitHub'da otomatik APK

## Yöntem A – Kendi bilgisayarında (Windows)
1. Python 3.12 kur (python.org, "Add to PATH" işaretli).
2. Windows'ta Geliştirici Modu'nu aç: Ayarlar > Gizlilik ve güvenlik > Geliştiriciler için > Geliştirici Modu.
3. Klasörde komut satırı aç:
       pip install "flet[all]==0.28.3"
       flet run                  (önce bilgisayarda dene)
       flet build apk
   İlk derlemede Flutter, JDK 17 ve Android SDK otomatik iner (birkaç GB, 15-30 dk).
4. APK: build/apk/app-release.apk

## Yöntem B – Hiçbir şey kurmadan (GitHub)
1. github.com'da yeni depo aç, bu klasörün tamamını yükle (.github klasörü dahil).
2. Actions > "APK Oluştur" > Run workflow.
3. Bitince sayfanın altındaki "pdf-duzenleyici-apk" dosyasını indir, içinden APK çıkar.

## Telefona kurma
APK'yı telefona at > aç > "Bilinmeyen kaynaklara izin ver" > Yükle.

## Kullanım
Sonuçlar: Dahili depolama / Download / PDF Duzenleyici
Birden fazla çıktı (ayır, PDF'ten görsel) ayrı alt klasöre kaydedilir.
