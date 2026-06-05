# Bu dosya gercek ag kosullarini simule etmek icin yazildi
# UDP soketinin uzerine bir sarmalayici (wrapper) gibi dusunebiliriz
# Paket kaybi ve gecikme ayarlanabilir, deney senaryolarinda kullaniyoruz

import random
import time
import socket


class AgSimulatoru:
    def __init__(
        self, soket: socket.socket, kayip_orani: float = 0.0, gecikme_ms: float = 0.0
    ):
        # asil UDP soketini aliyoruz, uzerine kayip/gecikme ekliyoruz
        self.soket = soket
        self.kayip_orani = kayip_orani  # 0.0 = kayip yok, 0.1 = %10 kayip
        self.gecikme_ms = gecikme_ms  # her pakete eklenecek yapay gecikme
        self._dusurme = 0  # kac paket dusuruldugunu sayiyoruz

    def gonder(self, veri: bytes, adres: tuple) -> bool:
        # once yapay gecikme uygula
        if self.gecikme_ms > 0:
            time.sleep(self.gecikme_ms / 1000.0)

        # rastgele sayi kayip oranindan kucukse paketi dusur
        # ornegin kayip_orani=0.1 ise yaklasik her 10 paketten 1i dusurulur
        if self.kayip_orani > 0 and random.random() < self.kayip_orani:
            self._dusurme += 1
            # paketi gondermiyoruz ama istemci bunu bilmiyor
            # timeout olunca anlayacak
            return False

        # normal kosullarda paketi gonder
        self.soket.sendto(veri, adres)
        return True

    def al(self, buffer: int = 65535):
        # alma tarafinda simulasyon yok, soketin kendi timeout'u calisiyor
        return self.soket.recvfrom(buffer)

    def settimeout(self, sure):
        # timeout'u alttaki sokete iletiyoruz
        self.soket.settimeout(sure)

    def kapat(self):
        # isimiz bitince soketi kapat
        self.soket.close()

    @property
    def dusurme_sayisi(self):
        # kac paket dusuruldugunu disaridan okuyabilmek icin
        return self._dusurme
