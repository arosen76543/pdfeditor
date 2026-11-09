"""
PDF Düzenleyici - Android / masaüstü uygulaması (Flet 0.28)
Çalıştırma (bilgisayarda deneme):  flet run
APK üretme:                        flet build apk
"""
from __future__ import annotations

import base64
import os
import tempfile
from datetime import datetime

import flet as ft

import pdf_araclari as pa

KIRMIZI = "#DC2626"
GRI = "#64748B"

ARACLAR = [
    ("birlestir", ft.Icons.MERGE_TYPE, "PDF Birleştir", "Birden fazla PDF'i istediğiniz sırayla tek dosyada toplayın."),
    ("ayir", ft.Icons.CONTENT_CUT, "PDF Ayır", "Her sayfayı ayrı, aralıklara göre ya da her N sayfada bir bölün."),
    ("cikar", ft.Icons.FILTER_NONE, "Sayfa Çıkar", "Seçtiğiniz sayfalardan yeni bir PDF oluşturun."),
    ("sil", ft.Icons.DELETE_OUTLINE, "Sayfa Sil", "İstemediğiniz sayfaları kaldırın."),
    ("sirala", ft.Icons.SWAP_VERT, "Sayfa Sırala", "Sayfaların sırasını değiştirin."),
    ("dondur", ft.Icons.ROTATE_RIGHT, "Döndür", "Tüm ya da seçili sayfaları 90°, 180°, 270° döndürün."),
    ("sikistir", ft.Icons.COMPRESS, "Sıkıştır", "Görselleri küçülterek dosya boyutunu azaltın."),
    ("jpg2pdf", ft.Icons.IMAGE_OUTLINED, "Görselden PDF", "JPG / PNG görselleri tek PDF'e dönüştürün."),
    ("pdf2jpg", ft.Icons.PHOTO_LIBRARY_OUTLINED, "PDF'ten Görsel", "Her sayfayı JPG ya da PNG olarak kaydedin."),
    ("numara", ft.Icons.FORMAT_LIST_NUMBERED, "Sayfa Numarası", "Sayfalara numara ekleyin."),
    ("filigran", ft.Icons.WATER_DROP_OUTLINED, "Filigran", "Sayfalara yazı filigranı ekleyin."),
    ("sifrele", ft.Icons.LOCK_OUTLINE, "Şifrele", "PDF'i şifreyle koruyun."),
    ("sifrekaldir", ft.Icons.LOCK_OPEN, "Şifre Kaldır", "Şifresini bildiğiniz PDF'in korumasını kaldırın."),
]
ARAC = {a[0]: a for a in ARACLAR}
GORSEL_UZ = ["jpg", "jpeg", "png", "bmp", "webp", "tif", "tiff"]


# ------------------------------------------------------------------ kayıt klasörü
def cikti_klasoru() -> str:
    """Telefonda İndirilenler/PDF Duzenleyici; olmazsa uygulama klasörü."""
    adaylar = [
        "/storage/emulated/0/Download/PDF Duzenleyici",
        os.path.join(os.path.expanduser("~"), "Downloads", "PDF Duzenleyici"),
        os.path.join(os.environ.get("FLET_APP_STORAGE_DATA", ""), "ciktilar")
        if os.environ.get("FLET_APP_STORAGE_DATA") else "",
        os.path.join(tempfile.gettempdir(), "PDF Duzenleyici"),
    ]
    for yol in adaylar:
        if not yol:
            continue
        try:
            os.makedirs(yol, exist_ok=True)
            deneme = os.path.join(yol, ".yazma_testi")
            with open(deneme, "wb") as f:
                f.write(b"1")
            os.remove(deneme)
            return yol
        except Exception:
            continue
    return tempfile.gettempdir()


def benzersiz(yol: str) -> str:
    if not os.path.exists(yol):
        return yol
    kok, uz = os.path.splitext(yol)
    i = 2
    while os.path.exists(f"{kok}_{i}{uz}"):
        i += 1
    return f"{kok}_{i}{uz}"


def kaydet(dosyalar: list[tuple[str, bytes]], klasor_adi: str | None = None) -> list[str]:
    hedef = cikti_klasoru()
    if klasor_adi and len(dosyalar) > 1:
        hedef = benzersiz(os.path.join(hedef, klasor_adi))
        os.makedirs(hedef, exist_ok=True)
    yollar = []
    for ad, veri in dosyalar:
        yol = benzersiz(os.path.join(hedef, ad))
        with open(yol, "wb") as f:
            f.write(veri)
        yollar.append(yol)
    return yollar


# ------------------------------------------------------------------ uygulama
def main(page: ft.Page):
    page.title = "PDF Düzenleyici"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=KIRMIZI)
    page.padding = 0

    durum = {"arac": None, "dosyalar": [], "hedef": None}  # dosyalar: [(ad, bytes)]

    # ---------- dosya seçici
    def secim_bitti(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        yeni = []
        for f in e.files:
            try:
                if f.path:
                    with open(f.path, "rb") as fh:
                        yeni.append((f.name, fh.read()))
            except Exception as ex:
                bildir(f"{f.name} okunamadı: {ex}", hata=True)
        if durum["hedef"]:
            durum["hedef"](yeni)

    secici = ft.FilePicker(on_result=secim_bitti)
    page.overlay.append(secici)

    def dosya_sec(geri_cagir, coklu=False, gorsel=False):
        durum["hedef"] = geri_cagir
        secici.pick_files(
            dialog_title="Dosya seç",
            allow_multiple=coklu,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=GORSEL_UZ if gorsel else ["pdf"],
        )

    def bildir(metin, hata=False):
        page.open(ft.SnackBar(ft.Text(metin), bgcolor=ft.Colors.RED_700 if hata else None))

    # ---------- ana ekran
    def arac_karti(k, ikon, ad, _):
        return ft.Container(
            content=ft.Column(
                [ft.Icon(ikon, size=30, color=KIRMIZI),
                 ft.Text(ad, size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER, spacing=6),
            bgcolor=ft.Colors.WHITE, border_radius=14, padding=10,
            border=ft.border.all(1, "#FECACA"),
            ink=True, on_click=lambda e, k=k: arac_ac(k),
        )

    def ana_gorunum():
        return ft.View(
            "/",
            [
                ft.AppBar(title=ft.Text("PDF Düzenleyici", weight=ft.FontWeight.BOLD),
                          bgcolor=KIRMIZI, color=ft.Colors.WHITE,
                          leading=ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.WHITE)),
                ft.Container(
                    ft.Text("Birleştir, ayır, sıkıştır, dönüştür. Tüm işlemler telefonda yapılır.",
                            size=12, color=GRI), padding=ft.padding.only(16, 12, 16, 0)),
                ft.GridView(
                    [arac_karti(*a) for a in ARACLAR],
                    expand=True, max_extent=150, child_aspect_ratio=1.0,
                    spacing=10, run_spacing=10, padding=16),
            ],
            bgcolor="#FEF2F2", padding=0,
        )

    # ---------- araç ekranı
    def arac_ac(k):
        durum["arac"] = k
        durum["dosyalar"] = []
        page.views.append(arac_gorunum(k))
        page.update()

    def arac_gorunum(k):
        _, ikon, ad, aciklama = ARAC[k]
        govde = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        dosya_bilgi = ft.Column(spacing=4)
        onizleme_alani = ft.Row(wrap=True, spacing=8, run_spacing=8)
        ayarlar = ft.Column(spacing=10, visible=False)
        sonuc_alani = ft.Container(visible=False)
        ilerleme = ft.ProgressBar(visible=False, color=KIRMIZI)
        calistir_btn = ft.FilledButton("Çalıştır", icon=ikon, visible=False,
                                       style=ft.ButtonStyle(bgcolor=KIRMIZI), height=48)
        ctl = {}  # ayar kontrolleri

        coklu = k in ("birlestir", "jpg2pdf")
        gorsel = k == "jpg2pdf"

        # ----- dosya listesi
        def dosya_listesini_ciz():
            dosya_bilgi.controls.clear()
            onizleme_alani.controls.clear()
            d = durum["dosyalar"]
            for i, (ad_, veri) in enumerate(d):
                bilgi = pa.boyut_yazi(len(veri))
                if not gorsel:
                    n = pa.sayfa_sayisi(veri)
                    bilgi += f" · {n} sayfa" if n else " · okunamadı / şifreli"
                satir = [ft.Icon(ft.Icons.IMAGE if gorsel else ft.Icons.PICTURE_AS_PDF, color=KIRMIZI, size=20),
                         ft.Column([ft.Text(ad_, size=13, weight=ft.FontWeight.W_600, max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(bilgi, size=11, color=GRI)], spacing=0, expand=True)]
                if coklu:
                    satir += [
                        ft.IconButton(ft.Icons.ARROW_UPWARD, icon_size=18, disabled=i == 0,
                                      on_click=lambda e, i=i: tasi(i, -1)),
                        ft.IconButton(ft.Icons.ARROW_DOWNWARD, icon_size=18, disabled=i == len(d) - 1,
                                      on_click=lambda e, i=i: tasi(i, 1)),
                        ft.IconButton(ft.Icons.CLOSE, icon_size=18, on_click=lambda e, i=i: kaldir(i)),
                    ]
                dosya_bilgi.controls.append(
                    ft.Container(ft.Row(satir, spacing=8), bgcolor=ft.Colors.WHITE, border_radius=10,
                                 padding=8, border=ft.border.all(1, "#E2E8F0")))
            if d and k in ("cikar", "sil", "sirala") and pa.RENDER_VAR:
                for i, r in enumerate(pa.onizleme(d[0][1], en_fazla=40, genislik=110)):
                    onizleme_alani.controls.append(ft.Column(
                        [ft.Image(src_base64=base64.b64encode(r).decode(), width=72,
                                  border_radius=4, fit=ft.ImageFit.CONTAIN),
                         ft.Text(str(i + 1), size=10, color=GRI)],
                        spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
            hazir = bool(d) and (len(d) >= 2 if k == "birlestir" else True)
            ayarlar.visible = bool(d)
            calistir_btn.visible = hazir
            sonuc_alani.visible = False
            page.update()

        def tasi(i, yon):
            d = durum["dosyalar"]
            j = i + yon
            d[i], d[j] = d[j], d[i]
            dosya_listesini_ciz()

        def kaldir(i):
            durum["dosyalar"].pop(i)
            dosya_listesini_ciz()

        def dosya_eklendi(yeni):
            if coklu:
                durum["dosyalar"].extend(yeni)
            else:
                durum["dosyalar"] = yeni[:1]
            dosya_listesini_ciz()

        sec_btn = ft.OutlinedButton(
            ("Görsel ekle" if gorsel else "PDF ekle") if coklu else "PDF seç",
            icon=ft.Icons.UPLOAD_FILE, height=46,
            on_click=lambda e: dosya_sec(dosya_eklendi, coklu=coklu, gorsel=gorsel))

        # ----- araç ayarları
        def tf(anahtar, etiket, ipucu="", deger="", sifre=False, sayi=False):
            ctl[anahtar] = ft.TextField(label=etiket, hint_text=ipucu, value=deger, password=sifre,
                                        can_reveal_password=sifre, dense=True,
                                        keyboard_type=ft.KeyboardType.NUMBER if sayi else None)
            return ctl[anahtar]

        def secenek(anahtar, etiket, secenekler, deger):
            ctl[anahtar] = ft.Dropdown(label=etiket, value=deger, dense=True,
                                       options=[ft.dropdown.Option(key=a, text=b) for a, b in secenekler])
            return ctl[anahtar]

        def kaydirici(anahtar, etiket, mn, mx, deger, bolum, ondalik=False):
            yazi = ft.Text(f"{etiket}: {deger}", size=13)

            def degisti(e):
                v = e.control.value
                yazi.value = f"{etiket}: {v:.2f}" if ondalik else f"{etiket}: {int(v)}"
                page.update()
            ctl[anahtar] = ft.Slider(min=mn, max=mx, value=deger, divisions=bolum, on_change=degisti,
                                     active_color=KIRMIZI)
            return ft.Column([yazi, ctl[anahtar]], spacing=0)

        def gorunur_yap(anahtar_listesi, kosul):
            for a in anahtar_listesi:
                ctl[a].visible = kosul
            page.update()

        if k == "ayir":
            ctl["mod"] = ft.RadioGroup(value="her", content=ft.Column([
                ft.Radio(value="her", label="Her sayfa ayrı dosya"),
                ft.Radio(value="aralik", label="Aralıklara göre"),
                ft.Radio(value="n", label="Her N sayfada bir")], spacing=0),
                on_change=lambda e: (gorunur_yap(["aralik"], e.control.value == "aralik"),
                                     gorunur_yap(["adim"], e.control.value == "n")))
            ayarlar.controls += [ctl["mod"], tf("aralik", "Aralıklar (her biri ayrı dosya)", "1-3, 4-10, 11-"),
                                 tf("adim", "Her dosyada kaç sayfa?", deger="5", sayi=True)]
            ctl["aralik"].visible = ctl["adim"].visible = False
        elif k in ("cikar", "sil"):
            ayarlar.controls += [tf("sayfalar", "Sayfalar", "Örn: 1-3, 5, 8-")]
        elif k == "sirala":
            ctl["mod"] = ft.RadioGroup(value="elle", content=ft.Row([
                ft.Radio(value="elle", label="Elle sıra yaz"), ft.Radio(value="ters", label="Ters çevir")]),
                on_change=lambda e: gorunur_yap(["sira"], e.control.value == "elle"))
            ayarlar.controls += [ctl["mod"], tf("sira", "Yeni sıra", "Örn: 3, 1, 2, 4-")]
        elif k == "dondur":
            ayarlar.controls += [
                secenek("derece", "Açı", [("90", "90° saat yönünde"), ("180", "180°"),
                                          ("270", "270° saat yönünde")], "90"),
                secenek("hedef", "Sayfalar", [("tum", "Tümü"), ("secili", "Seçili sayfalar")], "tum"),
                tf("sayfalar", "Döndürülecek sayfalar", "Örn: 2, 5-7")]
            ctl["sayfalar"].visible = False
            ctl["hedef"].on_change = lambda e: gorunur_yap(["sayfalar"], e.control.value == "secili")
        elif k == "sikistir":
            ayarlar.controls += [secenek("kalite", "Sıkıştırma", [("80", "Az (yüksek kalite)"),
                                                                  ("60", "Önerilen"),
                                                                  ("35", "Yüksek (düşük kalite)")], "60")]
        elif k == "jpg2pdf":
            ctl["a4"] = ft.Switch(label="A4 sayfaya yerleştir", value=True, active_color=KIRMIZI)
            ayarlar.controls += [ctl["a4"], kaydirici("kenar", "Kenar boşluğu (px)", 0, 120, 40, 12)]
        elif k == "pdf2jpg":
            ayarlar.controls += [
                secenek("bicim", "Biçim", [("JPEG", "JPEG"), ("PNG", "PNG")], "JPEG"),
                secenek("dpi", "Çözünürlük (DPI)", [(str(x), str(x)) for x in (72, 100, 150, 200, 300)], "150"),
                tf("sayfalar", "Sayfalar (boş = tümü)", "Örn: 1-3")]
        elif k == "numara":
            ayarlar.controls += [
                secenek("konum", "Konum", [("alt-orta", "Alt orta"), ("alt-sag", "Alt sağ"),
                                           ("alt-sol", "Alt sol"), ("ust-orta", "Üst orta"),
                                           ("ust-sag", "Üst sağ"), ("ust-sol", "Üst sol")], "alt-orta"),
                secenek("bicim", "Biçim", [("{n} / {t}", "3 / 10"), ("{n}", "3"), ("Sayfa {n}", "Sayfa 3"),
                                           ("Sayfa {n} / {t}", "Sayfa 3 / 10")], "{n} / {t}"),
                tf("bas", "Başlangıç numarası", deger="1", sayi=True)]
        elif k == "filigran":
            ayarlar.controls += [tf("metin", "Filigran metni", deger="GİZLİDİR"),
                                 kaydirici("opak", "Saydamlık", 0.05, 0.6, 0.15, 11, ondalik=True),
                                 kaydirici("boyut", "Yazı boyutu", 20, 140, 60, 24),
                                 kaydirici("aci", "Açı", 0, 90, 45, 18)]
        elif k == "sifrele":
            ayarlar.controls += [tf("s1", "Şifre", sifre=True), tf("s2", "Şifre (tekrar)", sifre=True)]
        elif k == "sifrekaldir":
            ayarlar.controls += [tf("sifre", "PDF'in şifresi", sifre=True)]

        # ----- işlem
        def v(a):
            return ctl[a].value

        def islem():
            d = durum["dosyalar"]
            zaman = datetime.now().strftime("%Y%m%d_%H%M")
            if k == "birlestir":
                return [(f"birlesik_{zaman}.pdf", pa.birlestir([x[1] for x in d]))], None, \
                    f"{len(d)} dosya birleştirildi"
            if k == "jpg2pdf":
                kenar = int(ctl["kenar"].value)
                return [(f"gorseller_{zaman}.pdf",
                         pa.gorselden_pdf([x[1] for x in d], kenar_bosluk=kenar, a4=ctl["a4"].value))], None, \
                    f"{len(d)} sayfa"
            ad, veri = d[0]
            kok = pa._ad(ad)
            n = pa.sayfa_sayisi(veri)
            if k == "ayir":
                mod = v("mod")
                if mod == "her":
                    p = pa.ayir_her_sayfa(veri, ad)
                elif mod == "aralik":
                    p = pa.ayir_araliklar(veri, ad, v("aralik"))
                else:
                    try:
                        adim = int(v("adim"))
                    except ValueError:
                        raise pa.PdfHatasi("Sayfa sayısı rakam olmalı.")
                    p = pa.ayir_her_n(veri, ad, adim)
                return p, f"{kok}_ayrilmis", f"{len(p)} PDF oluşturuldu"
            if k == "cikar":
                ind = pa.aralik_coz(v("sayfalar"), n)
                return [(f"{kok}_secili.pdf", pa.sayfalari_al(veri, ind))], None, f"{len(ind)} sayfa"
            if k == "sil":
                ind = pa.aralik_coz(v("sayfalar"), n)
                return [(f"{kok}_duzenli.pdf", pa.sayfa_sil(veri, ind))], None, \
                    f"{len(set(ind))} sayfa silindi, {n - len(set(ind))} sayfa kaldı"
            if k == "sirala":
                sira = list(range(n - 1, -1, -1)) if v("mod") == "ters" else pa.aralik_coz(v("sira"), n)
                return [(f"{kok}_sirali.pdf", pa.sirala(veri, sira))], None, f"{len(sira)} sayfa"
            if k == "dondur":
                ind = None if v("hedef") == "tum" else pa.aralik_coz(v("sayfalar"), n)
                return [(f"{kok}_dondurulmus.pdf", pa.dondur(veri, int(v("derece")), ind))], None, ""
            if k == "sikistir":
                cikti = pa.sikistir(veri, kalite=int(v("kalite")))
                oran = (1 - len(cikti) / max(len(veri), 1)) * 100
                bilgi = f"{pa.boyut_yazi(len(veri))} → {pa.boyut_yazi(len(cikti))}"
                bilgi += f" (%{oran:.0f} küçüldü)" if oran > 0 else " (dosya zaten sıkıştırılmış)"
                return [(f"{kok}_sikistirilmis.pdf", cikti)], None, bilgi
            if k == "pdf2jpg":
                metin = (v("sayfalar") or "").strip()
                ind = pa.aralik_coz(metin, n) if metin else None
                p = pa.pdften_gorsel(veri, ad, dpi=int(v("dpi")), bicim=v("bicim"), indeksler=ind)
                return p, f"{kok}_gorseller", f"{len(p)} görsel"
            if k == "numara":
                try:
                    bas = int(v("bas"))
                except ValueError:
                    raise pa.PdfHatasi("Başlangıç numarası rakam olmalı.")
                return [(f"{kok}_numarali.pdf",
                         pa.sayfa_numarasi(veri, konum=v("konum"), bicim=v("bicim"), baslangic=bas))], None, ""
            if k == "filigran":
                return [(f"{kok}_filigranli.pdf",
                         pa.filigran(veri, v("metin"), opaklik=float(ctl["opak"].value),
                                     boyut=int(ctl["boyut"].value), aci=int(ctl["aci"].value)))], None, ""
            if k == "sifrele":
                if v("s1") != v("s2"):
                    raise pa.PdfHatasi("Şifreler aynı değil.")
                return [(f"{kok}_sifreli.pdf", pa.sifrele(veri, v("s1")))], None, "AES-256 ile şifrelendi"
            if k == "sifrekaldir":
                return [(f"{kok}_sifresiz.pdf", pa.sifre_kaldir(veri, v("sifre") or ""))], None, ""
            raise pa.PdfHatasi("Bilinmeyen işlem.")

        def calistir(e):
            calistir_btn.disabled = True
            ilerleme.visible = True
            sonuc_alani.visible = False
            page.update()
            try:
                dosyalar, klasor, bilgi = islem()
                yollar = kaydet(dosyalar, klasor)
                toplam = sum(len(x[1]) for x in dosyalar)
                konum = os.path.dirname(yollar[0]) if len(yollar) > 1 else yollar[0]
                sonuc_alani.content = ft.Column([
                    ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color="#059669"),
                            ft.Text("Hazır", weight=ft.FontWeight.BOLD, color="#065F46")]),
                    ft.Text(f"{len(yollar)} dosya · {pa.boyut_yazi(toplam)}" + (f" · {bilgi}" if bilgi else ""),
                            size=13, color="#065F46"),
                    ft.Text("Kaydedildi:", size=12, color=GRI),
                    ft.Text(konum, size=12, selectable=True),
                    ft.OutlinedButton("Yeni işlem", icon=ft.Icons.REFRESH, on_click=yeni_islem),
                ], spacing=6)
                sonuc_alani.visible = True
            except pa.PdfHatasi as ex:
                bildir(str(ex), hata=True)
            except MemoryError:
                bildir("Bellek yetmedi. Dosyayı parçalara bölüp tekrar deneyin.", hata=True)
            except Exception as ex:
                bildir(f"Beklenmeyen hata: {ex}", hata=True)
            finally:
                calistir_btn.disabled = False
                ilerleme.visible = False
                page.update()

        def yeni_islem(e):
            durum["dosyalar"] = []
            for c in ctl.values():
                if isinstance(c, ft.TextField) and c.password:
                    c.value = ""
            dosya_listesini_ciz()

        calistir_btn.on_click = calistir
        if k == "birlestir":
            calistir_btn.text = "Birleştir"

        sonuc_alani.bgcolor = "#ECFDF5"
        sonuc_alani.border = ft.border.all(1, "#A7F3D0")
        sonuc_alani.border_radius = 12
        sonuc_alani.padding = 12

        govde.controls = [
            ft.Text(aciklama, size=13, color=GRI),
            sec_btn,
            dosya_bilgi,
            onizleme_alani,
            ayarlar,
            calistir_btn,
            ilerleme,
            sonuc_alani,
            ft.Container(height=30),
        ]
        return ft.View(
            f"/{k}",
            [ft.AppBar(title=ft.Text(ad), bgcolor=KIRMIZI, color=ft.Colors.WHITE),
             ft.Container(govde, padding=16, expand=True)],
            bgcolor="#FAFAFA", padding=0,
        )

    # ---------- geri tuşu
    def geri(e):
        if len(page.views) > 1:
            page.views.pop()
            durum["dosyalar"] = []
            page.update()

    page.on_view_pop = geri
    page.views.clear()
    page.views.append(ana_gorunum())
    page.update()


ft.app(target=main)
