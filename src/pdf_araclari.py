"""
PDF Düzenleyici - işlem fonksiyonları (arayüzden bağımsız, Android uyumlu)

Gerekli: pypdf, reportlab, pillow, pymupdf, cryptography
Tüm fonksiyonlar girdi olarak bytes / BytesIO alır, çıktı olarak bytes döndürür.
"""
from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile

from pypdf import PdfReader, PdfWriter

try:
    import fitz  # PyMuPDF  (Android'de pypdfium2 yerine)
    RENDER_VAR = True
except Exception:  # pragma: no cover
    RENDER_VAR = False

PDFIUM_VAR = RENDER_VAR  # eski adla uyumluluk

BURASI = os.path.dirname(os.path.abspath(__file__))


class PdfHatasi(Exception):
    """Kullanıcıya gösterilecek anlaşılır hata."""


# ------------------------------------------------------------------ yardımcılar
def _akim(kaynak):
    if isinstance(kaynak, (bytes, bytearray)):
        return io.BytesIO(kaynak)
    if hasattr(kaynak, "seek"):
        kaynak.seek(0)
    return kaynak


def _bytes(kaynak) -> bytes:
    if isinstance(kaynak, (bytes, bytearray)):
        return bytes(kaynak)
    return _akim(kaynak).read()


def oku(kaynak, sifre: str | None = None) -> PdfReader:
    try:
        r = PdfReader(_akim(kaynak), strict=False)
    except Exception as e:
        raise PdfHatasi(f"PDF okunamadı: {e}") from e
    if r.is_encrypted:
        if not sifre:
            try:
                if r.decrypt("") == 0:
                    raise PdfHatasi("Bu PDF şifreli. Önce 'Şifre Kaldır' aracını kullanın.")
            except PdfHatasi:
                raise
            except Exception as e:
                raise PdfHatasi("Bu PDF şifreli. Önce 'Şifre Kaldır' aracını kullanın.") from e
        elif r.decrypt(sifre) == 0:
            raise PdfHatasi("Şifre yanlış.")
    return r


def sayfa_sayisi(kaynak) -> int:
    try:
        return len(oku(kaynak).pages)
    except PdfHatasi:
        return 0


def _yaz(writer: PdfWriter) -> bytes:
    with tempfile.TemporaryFile() as f:
        writer.write(f)
        f.seek(0)
        return f.read()


def aralik_coz(metin: str, toplam: int) -> list[int]:
    """'1-3, 5, 8-' -> [0,1,2,4,7,8,...] (0 tabanlı, sırası korunur)."""
    metin = (metin or "").replace(" ", "").replace(";", ",")
    if not metin:
        raise PdfHatasi("Sayfa aralığı boş.")
    sonuc = []
    for parca in metin.split(","):
        if not parca:
            continue
        m = re.fullmatch(r"(\d*)-(\d*)", parca)
        if m:
            bas = int(m.group(1)) if m.group(1) else 1
            bit = int(m.group(2)) if m.group(2) else toplam
        elif parca.isdigit():
            bas = bit = int(parca)
        else:
            raise PdfHatasi(f"'{parca}' anlaşılamadı. Örnek: 1-3, 5, 8-10")
        if bas < 1 or bit > toplam or bas > bit:
            raise PdfHatasi(f"'{parca}' geçersiz. PDF {toplam} sayfa.")
        sonuc.extend(range(bas - 1, bit))
    if not sonuc:
        raise PdfHatasi("Sayfa seçilmedi.")
    return sonuc


def aralik_gruplari(metin: str, toplam: int) -> list[tuple[str, list[int]]]:
    gruplar = []
    for parca in (metin or "").replace(" ", "").replace(";", ",").split(","):
        if parca:
            gruplar.append((parca, aralik_coz(parca, toplam)))
    if not gruplar:
        raise PdfHatasi("Sayfa aralığı boş.")
    return gruplar


def zip_yap(dosyalar: list[tuple[str, bytes]]) -> bytes:
    with tempfile.TemporaryFile() as f:
        with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
            for ad, veri in dosyalar:
                z.writestr(ad, veri)
        f.seek(0)
        return f.read()


def _ad(dosya_adi: str) -> str:
    return os.path.splitext(os.path.basename(dosya_adi or "belge"))[0] or "belge"


# ------------------------------------------------------------------ araçlar
def birlestir(kaynaklar: list) -> bytes:
    w = PdfWriter()
    for k in kaynaklar:
        for p in oku(k).pages:
            w.add_page(p)
    return _yaz(w)


def sayfalari_al(kaynak, indeksler: list[int]) -> bytes:
    r = oku(kaynak)
    w = PdfWriter()
    for i in indeksler:
        w.add_page(r.pages[i])
    return _yaz(w)


def ayir_her_sayfa(kaynak, ad: str) -> list[tuple[str, bytes]]:
    r = oku(kaynak)
    n = len(r.pages)
    hane = len(str(n))
    cikti = []
    for i in range(n):
        w = PdfWriter()
        w.add_page(r.pages[i])
        cikti.append((f"{_ad(ad)}_s{str(i + 1).zfill(hane)}.pdf", _yaz(w)))
    return cikti


def ayir_araliklar(kaynak, ad: str, metin: str) -> list[tuple[str, bytes]]:
    n = sayfa_sayisi(kaynak)
    return [(f"{_ad(ad)}_{etiket}.pdf", sayfalari_al(kaynak, ind)) for etiket, ind in aralik_gruplari(metin, n)]


def ayir_her_n(kaynak, ad: str, adim: int) -> list[tuple[str, bytes]]:
    n = sayfa_sayisi(kaynak)
    if adim < 1:
        raise PdfHatasi("Sayfa sayısı en az 1 olmalı.")
    cikti = []
    for bas in range(0, n, adim):
        bit = min(bas + adim, n)
        cikti.append((f"{_ad(ad)}_{bas + 1}-{bit}.pdf", sayfalari_al(kaynak, list(range(bas, bit)))))
    return cikti


def sayfa_sil(kaynak, silinecek: list[int]) -> bytes:
    r = oku(kaynak)
    sil = set(silinecek)
    kalan = [i for i in range(len(r.pages)) if i not in sil]
    if not kalan:
        raise PdfHatasi("Tüm sayfalar silinemez.")
    return sayfalari_al(kaynak, kalan)


def dondur(kaynak, derece: int, indeksler: list[int] | None = None) -> bytes:
    r = oku(kaynak)
    w = PdfWriter()
    hedef = set(indeksler) if indeksler is not None else None
    for i, p in enumerate(r.pages):
        if hedef is None or i in hedef:
            p.rotate(derece)
        w.add_page(p)
    return _yaz(w)


def sirala(kaynak, yeni_sira: list[int]) -> bytes:
    return sayfalari_al(kaynak, yeni_sira)


def sikistir(kaynak, kalite: int = 60, gorsel_kucult: bool = True) -> bytes:
    r = oku(kaynak)
    w = PdfWriter(clone_from=r)
    for p in w.pages:
        if gorsel_kucult:
            for img in p.images:
                try:
                    im = img.image
                    if im is None or im.mode in ("RGBA", "P", "LA"):
                        continue
                    if max(im.size) > 2000:
                        im = im.copy()
                        im.thumbnail((2000, 2000))
                    img.replace(im, quality=int(kalite))
                except Exception:
                    continue
        try:
            p.compress_content_streams(level=9)
        except Exception:
            pass
    try:
        w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    except Exception:
        pass
    return _yaz(w)


def gorselden_pdf(gorseller: list, kenar_bosluk: int = 0, a4: bool = False) -> bytes:
    from PIL import Image, ImageOps
    sayfalar = []
    for g in gorseller:
        im = ImageOps.exif_transpose(Image.open(_akim(g)))
        if im.mode != "RGB":
            arka = Image.new("RGB", im.size, "white")
            if im.mode in ("RGBA", "LA"):
                arka.paste(im, mask=im.split()[-1])
            else:
                arka.paste(im.convert("RGB"))
            im = arka
        if a4 or kenar_bosluk:
            W, H = (1240, 1754) if a4 else (im.width + 2 * kenar_bosluk, im.height + 2 * kenar_bosluk)
            if a4 and im.width > im.height:
                W, H = H, W
            tuval = Image.new("RGB", (W, H), "white")
            kopya = im.copy()
            kopya.thumbnail((W - 2 * kenar_bosluk, H - 2 * kenar_bosluk))
            tuval.paste(kopya, ((W - kopya.width) // 2, (H - kopya.height) // 2))
            im = tuval
        sayfalar.append(im)
    if not sayfalar:
        raise PdfHatasi("Görsel seçilmedi.")
    buf = io.BytesIO()
    sayfalar[0].save(buf, "PDF", save_all=True, append_images=sayfalar[1:], resolution=150)
    return buf.getvalue()


def _fitz_ac(kaynak):
    try:
        return fitz.open(stream=_bytes(kaynak), filetype="pdf")
    except Exception as e:
        raise PdfHatasi(f"PDF açılamadı: {e}") from e


def pdften_gorsel(kaynak, ad: str, dpi: int = 150, bicim: str = "JPEG",
                  indeksler: list[int] | None = None) -> list[tuple[str, bytes]]:
    if not RENDER_VAR:
        raise PdfHatasi("Bu özellik için PyMuPDF gerekli.")
    from PIL import Image
    doc = _fitz_ac(kaynak)
    n = len(doc)
    hedef = indeksler if indeksler is not None else list(range(n))
    uz = "jpg" if bicim == "JPEG" else "png"
    hane = len(str(n))
    cikti = []
    try:
        for i in hedef:
            pix = doc[i].get_pixmap(dpi=int(dpi), alpha=False)
            if bicim == "PNG":
                veri = pix.tobytes("png")
            else:
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                b = io.BytesIO()
                im.save(b, "JPEG", quality=90)
                veri = b.getvalue()
            cikti.append((f"{_ad(ad)}_s{str(i + 1).zfill(hane)}.{uz}", veri))
    finally:
        doc.close()
    return cikti


def onizleme(kaynak, en_fazla: int = 40, genislik: int = 160) -> list[bytes]:
    """İlk sayfaların küçük JPEG önizlemeleri."""
    if not RENDER_VAR:
        return []
    from PIL import Image
    try:
        doc = _fitz_ac(kaynak)
    except PdfHatasi:
        return []
    cikti = []
    try:
        for i in range(min(len(doc), en_fazla)):
            sayfa = doc[i]
            olcek = genislik / max(sayfa.rect.width, 1)
            pix = sayfa.get_pixmap(matrix=fitz.Matrix(olcek, olcek), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            b = io.BytesIO()
            im.save(b, "JPEG", quality=70)
            cikti.append(b.getvalue())
    finally:
        doc.close()
    return cikti


def sifrele(kaynak, sifre: str) -> bytes:
    if not sifre:
        raise PdfHatasi("Şifre boş olamaz.")
    r = oku(kaynak)
    w = PdfWriter(clone_from=r)
    w.encrypt(user_password=sifre, owner_password=sifre, algorithm="AES-256")
    return _yaz(w)


def sifre_kaldir(kaynak, sifre: str) -> bytes:
    r = oku(kaynak, sifre=sifre)
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)
    return _yaz(w)


def _kaplama(genislik, yukseklik, ciz):
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    c = canvas.Canvas(b, pagesize=(genislik, yukseklik))
    ciz(c, genislik, yukseklik)
    c.save()
    b.seek(0)
    return PdfReader(b).pages[0]


def _font():
    """Türkçe karakterler için TTF yazı tipi. Önce uygulamayla gelen DejaVuSans."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "TRFont" in pdfmetrics.getRegisteredFontNames():
        return "TRFont"
    for yol in (os.path.join(BURASI, "assets", "fonts", "DejaVuSans.ttf"),
                "/system/fonts/DroidSans.ttf",
                "/system/fonts/NotoSans-Regular.ttf",
                r"C:\Windows\Fonts\arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(yol):
            try:
                pdfmetrics.registerFont(TTFont("TRFont", yol))
                return "TRFont"
            except Exception:
                continue
    return "Helvetica"


def _metin_uygun(metin: str, font: str) -> str:
    if font != "Helvetica":
        return metin
    return metin.translate(str.maketrans("İıŞşĞğ", "IiSsGg"))


def sayfa_numarasi(kaynak, konum: str = "alt-orta", bicim: str = "{n} / {t}",
                   baslangic: int = 1, boyut: int = 10) -> bytes:
    r = oku(kaynak)
    w = PdfWriter()
    toplam = len(r.pages)
    font = _font()
    for i, p in enumerate(r.pages):
        gw, gy = float(p.mediabox.width), float(p.mediabox.height)
        metin = _metin_uygun(bicim.replace("{n}", str(i + baslangic))
                             .replace("{t}", str(toplam + baslangic - 1)), font)

        def ciz(c, W, H, metin=metin):
            c.setFont(font, boyut)
            c.setFillGray(0.25)
            y = 18 if konum.startswith("alt") else H - 24
            if konum.endswith("orta"):
                c.drawCentredString(W / 2, y, metin)
            elif konum.endswith("sag"):
                c.drawRightString(W - 28, y, metin)
            else:
                c.drawString(28, y, metin)
        p.merge_page(_kaplama(gw, gy, ciz))
        w.add_page(p)
    return _yaz(w)


def filigran(kaynak, metin: str, opaklik: float = 0.15, boyut: int = 60, aci: int = 45) -> bytes:
    if not metin:
        raise PdfHatasi("Filigran metni boş.")
    r = oku(kaynak)
    w = PdfWriter()
    font = _font()
    onbellek = {}
    for p in r.pages:
        gw, gy = float(p.mediabox.width), float(p.mediabox.height)
        anahtar = (round(gw), round(gy))
        if anahtar not in onbellek:
            def ciz(c, W, H):
                c.saveState()
                c.setFillColorRGB(0.6, 0.1, 0.1, alpha=opaklik)
                c.setFont(font, boyut)
                c.translate(W / 2, H / 2)
                c.rotate(aci)
                c.drawCentredString(0, -boyut / 3, _metin_uygun(metin, font))
                c.restoreState()
            onbellek[anahtar] = _kaplama(gw, gy, ciz)
        p.merge_page(onbellek[anahtar])
        w.add_page(p)
    return _yaz(w)


def boyut_yazi(b: int) -> str:
    for birim in ("B", "KB", "MB", "GB"):
        if b < 1024 or birim == "GB":
            return f"{b:.0f} {birim}" if birim == "B" else f"{b:.1f} {birim}"
        b /= 1024
