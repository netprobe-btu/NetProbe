# Bu dosya UDP sunucusunu olusturuyor
# Istemciden gelen paketleri aliyor, ACK gonderiyor, dosyayi yeniden birlestiriyor
# Duplicate paket kontrolu ve butunluk dogrulamasi da burada yapiliyor

import socket
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
import time
from protocol import (
    veri_paketi_coz,
    ack_paketi_olustur,
    fin_paketi_coz,
    dosya_hash,
    PKT_DATA,
    PKT_FIN,
    SERVER_PORT,
    BUFFER_SIZE,
)
from logger import Logger, ACK_ALINDI, DUPLICATE, FIN_ALINDI


def sunucu_baslat(kayit_dizini: str = "received", port: int = SERVER_PORT):
    # klasor yoksa olustur, alinan dosyalar buraya kaydedilecek
    os.makedirs(kayit_dizini, exist_ok=True)

    # UDP soketi olustur ve porta bagla
    # SOCK_DGRAM = UDP demek, SOCK_STREAM olsaydi TCP olurdu
    soket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    soket.bind(("0.0.0.0", port))  # tum arayuzlerden gelen baglantilari kabul et
    print(f"[SUNUCU] Port {port} dinleniyor...")

    # sunucu surekli calissin, her aktarimi sirayla isle
    while True:
        _aktarim_isle(soket, kayit_dizini)


def _aktarim_isle(soket: socket.socket, kayit_dizini: str):
    # tek bir dosya aktarimini isliyoruz
    # bir sonraki aktarim gelince bu fonksiyon tekrar cagrilacak

    paketler = {}  # seq_no -> payload, sirasiz gelse de burada tutuyoruz
    beklenen_total = None  # kac paket gelecegini ilk paketten ogreniyoruz
    istemci_adresi = None  # istemcinin IP ve portu
    log = None  # logger nesnesi

    print("[SUNUCU] Yeni aktarim bekleniyor...\n")

    while True:
        try:
            raw, adres = soket.recvfrom(BUFFER_SIZE)
        except Exception as e:
            print(f"[SUNUCU] Alma hatasi: {e}")
            continue

        # ilk pakette istemciyi taniyoruz ve logu baslatiyruz
        if istemci_adresi is None:
            istemci_adresi = adres
            log = Logger(f"logs/server_{int(time.time())}.csv")
            log.baslat()
            print(f"[SUNUCU] Istemci baglandi: {adres[0]}:{adres[1]}")

        # paketin ilk bytei tip bilgisi
        tip = raw[0]

        # --- VERI PAKETI GELDIYSE ---
        if tip == PKT_DATA:
            sonuc = veri_paketi_coz(raw)

            # checksum hatasi veya bozuk paket
            if sonuc is None:
                print("[SUNUCU] Bozuk paket alindi, yoksayiliyor.")
                continue  # ACK gondermiyoruz, istemci timeout'ta tekrar gonderecek

            seq, total, payload = sonuc

            # kac paket gelecegini ilk paketten ogreniyoruz
            if beklenen_total is None:
                beklenen_total = total
                print(f"[SUNUCU] Toplam {total} paket bekleniyor.")

            # bu seq daha once geldiyse duplicate demek
            # ayni veriyi tekrar dosyaya yazmiyoruz ama ACK gonderiyoruz
            # cunku istemci ACK'i almamis olabilir, bu yuzden tekrar gondermis
            if seq in paketler:
                print(f"[SUNUCU] Duplicate paket: {seq}, ACK tekrar gonderildi.")
                log.kaydet(DUPLICATE, seq_no=seq)
                soket.sendto(ack_paketi_olustur(seq), adres)
                continue

            # yeni paket, sozluge ekle
            paketler[seq] = payload
            print(f"[SUNUCU] Paket alindi: {seq}/{total - 1}")

            # ACK gonder, istemci bekliyor
            soket.sendto(ack_paketi_olustur(seq), adres)
            log.kaydet(ACK_ALINDI, seq_no=seq)

        # --- FIN PAKETI GELDIYSE ---
        # istemci tum paketleri gonderdi, aktarim bitti sinyali atiyor
        elif tip == PKT_FIN:
            gelen_hash = fin_paketi_coz(raw)
            print("\n[SUNUCU] FIN alindi, dosya yaziliyor...")

            # paketleri seq numarasina gore sirala ve dosyaya yaz
            # dict'te sirasiz tutuyorduk, simdi dogru siraya koyuyoruz
            os.makedirs(kayit_dizini, exist_ok=True)
            cikis = os.path.join(kayit_dizini, "alinan_dosya")
            with open(cikis, "wb") as f:
                for i in sorted(paketler.keys()):
                    f.write(paketler[i])
            # SHA256 hash ile butunluk kontrolu
            # istemcinin gonderdigi hash ile bizim hesapladigimiz eslesiyorsa dosya tam demek
            alinan_hash = dosya_hash(cikis)
            if alinan_hash == gelen_hash:
                print(f"[SUNUCU] Butunluk kontrolu BASARILI ✓")
                print(f"[SUNUCU] Dosya kaydedildi: {cikis}")
            else:
                print(f"[SUNUCU] UYARI: Butunluk kontrolu BASARISIZ ✗")
                print(f"  Beklenen : {gelen_hash}")
                print(f"  Alinan   : {alinan_hash}")

            log.kaydet(FIN_ALINDI, aciklama=f"butunluk={alinan_hash == gelen_hash}")
            log.bitis()
            log.ozet_yazdir()
            log.kapat()

            # FIN-ACK gonder, istemci bunu alinca kapanacak
            soket.sendto(ack_paketi_olustur(9999), adres)

            # bu aktarim bitti, donguden cik
            # sunucu_baslat'taki while True tekrar _aktarim_isle'yi cagriracak
            break


if __name__ == "__main__":
    # komut satirindan port verilebilir: python server.py 9090
    port = int(sys.argv[1]) if len(sys.argv) > 1 else SERVER_PORT
    sunucu_baslat(port=port)
