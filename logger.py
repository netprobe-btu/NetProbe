# Bu dosya aktarim sirasinda olan her olayi kayit altina aliyor
# Hangi paket gonderildi, ACK geldi mi, timeout mu oldu hepsini CSV'ye yaziyoruz
# Sonunda ozet istatistik de cikartiyoruz

import csv
import time
import os
from datetime import datetime

# --- Olay tipleri ---
# Bunlari string olarak tanimliyoruz, CSV'de okunmasi kolay olsun
SEND = "SEND"  # paket gonderildi
ACK_ALINDI = "ACK_ALINDI"  # ACK geldi
TIMEOUT = "TIMEOUT"  # ACK gelmedi, sure doldu
RETRANSMIT = "RETRANSMIT"  # paket yeniden gonderiliyor
BASARISIZ = "BASARISIZ"  # max deneme asildi, paket gonderilemedi
DUPLICATE = "DUPLICATE"  # ayni paket tekrar geldi
FIN_SEND = "FIN_SEND"  # aktarim bitti sinyali gonderildi
FIN_ALINDI = "FIN_ALINDI"  # aktarim bitti sinyali alindi


class Logger:
    def __init__(self, log_dosyasi: str = None):
        # log dosyasi verilmediyse otomatik isim uret
        if log_dosyasi is None:
            zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dosyasi = f"logs/netprobe_{zaman}.csv"

        # logs klasoru yoksa olustur
        os.makedirs("logs", exist_ok=True)
        self.log_dosyasi = log_dosyasi
        self.baslangic = None
        self.toplam_sure = 0

        # her olay turunu sayiyoruz, sonunda ozette kullanacagiz
        self.gonderilen = 0
        self.ack_alinan = 0
        self.timeout_sayisi = 0
        self.retransmit = 0
        self.basarisiz = 0
        self.duplicate = 0

        # CSV dosyasini ac ve baslik satirini yaz
        self._f = open(self.log_dosyasi, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._f)
        self._writer.writerow(
            [
                "zaman_damgasi",  # saat:dakika:saniye
                "gecen_sure_ms",  # aktarim basladigindan beri gecen sure
                "olay",  # ne oldu (SEND, ACK, TIMEOUT vs)
                "seq_no",  # hangi paket
                "deneme",  # kacinci deneme
                "aciklama",  # varsa ek bilgi
            ]
        )

    def baslat(self):
        # aktarim baslangic zamanini kaydediyoruz
        # gecen_sure_ms hesabi buradan yapiliyor
        self.baslangic = time.time()

    def kaydet(self, olay: str, seq_no: int = -1, deneme: int = 0, aciklama: str = ""):
        # her olay icin bir satir CSV'ye yaziyoruz
        su_an = time.time()
        gecen = round((su_an - self.baslangic) * 1000, 3) if self.baslangic else 0
        zaman = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        self._writer.writerow([zaman, gecen, olay, seq_no, deneme, aciklama])
        self._f.flush()  # hemen diske yazsin, program cokerse kaybolmasin

        # olay tipine gore sayaci artir
        if olay == SEND:
            self.gonderilen += 1
        elif olay == ACK_ALINDI:
            self.ack_alinan += 1
        elif olay == TIMEOUT:
            self.timeout_sayisi += 1
        elif olay == RETRANSMIT:
            self.retransmit += 1
        elif olay == BASARISIZ:
            self.basarisiz += 1
        elif olay == DUPLICATE:
            self.duplicate += 1

    def bitis(self):
        # aktarim bitti, toplam sureyi hesapla
        self.toplam_sure = time.time() - self.baslangic if self.baslangic else 0

    def ozet_yazdir(self):
        # terminale guzel formatli ozet yazdir
        print("\n" + "=" * 50)
        print("         AKTARIM OZETI")
        print("=" * 50)
        print(f"  Gonderilen paket     : {self.gonderilen}")
        print(f"  Alinan ACK           : {self.ack_alinan}")
        print(f"  Timeout sayisi       : {self.timeout_sayisi}")
        print(f"  Yeniden gonderim     : {self.retransmit}")
        print(f"  Basarisiz paket      : {self.basarisiz}")
        print(f"  Duplicate paket      : {self.duplicate}")

        # retransmission rate hesabi - gonderilen 0 ise bolme hatasi vermemesi icin kontrol
        if self.gonderilen > 0:
            oran = round(self.retransmit / self.gonderilen * 100, 2)
            print(f"  Retransmission rate  : %{oran}")
            print(f"  Toplam sure          : {round(self.toplam_sure, 3)} sn")
        print("=" * 50 + "\n")

    def ozet_al(self) -> dict:
        # analyzer.py grafik cizmek icin bu sozlugu kullaniyor
        retrans_rate = self.retransmit / self.gonderilen if self.gonderilen > 0 else 0
        return {
            "gonderilen": self.gonderilen,
            "ack_alinan": self.ack_alinan,
            "timeout_sayisi": self.timeout_sayisi,
            "retransmit": self.retransmit,
            "basarisiz": self.basarisiz,
            "duplicate": self.duplicate,
            "retransmit_rate": retrans_rate,  # 0.0 ile 1.0 arasi oran
            "toplam_sure": self.toplam_sure,
            "log_dosyasi": self.log_dosyasi,
        }

    def kapat(self):
        # isimiz bitti, dosyayi kapat
        self._f.close()
