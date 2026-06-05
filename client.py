# Bu dosya UDP istemcisini olusturuyor
# Dosyayi parcalara bolup sunucuya gonderiyor
# Stop-and-wait protokolu kullaniyoruz: bir paket gonder, ACK bekle, sonra digerine gec
# ACK gelmezse timeout olunca tekrar gonderiyoruz, maksimum 5 kez deniyoruz

import socket
import os
import sys
import time
from protocol import (
    veri_paketi_olustur,
    ack_paketi_coz,
    fin_paketi_olustur,
    dosya_hash,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRY,
    SERVER_PORT,
    BUFFER_SIZE,
)
from logger import Logger, SEND, ACK_ALINDI, TIMEOUT, RETRANSMIT, BASARISIZ, FIN_SEND
from network_sim import AgSimulatoru


def dosya_gonder(
    dosya_yolu: str,
    sunucu_ip: str = "127.0.0.1",
    sunucu_port: int = SERVER_PORT,
    chunk_boyut: int = DEFAULT_CHUNK_SIZE,  # kac byte'lik parcalara bolecegiz
    timeout_sure: float = DEFAULT_TIMEOUT,  # ACK icin kac saniye bekleyecegiz
    max_deneme: int = DEFAULT_MAX_RETRY,  # maksimum kac kez tekrar gonderecegiz
    kayip_orani: float = 0.0,  # deney icin yapay kayip orani
    gecikme_ms: float = 0.0,  # deney icin yapay gecikme
    log_adi: str = None,  # log dosyasinin adi
) -> dict:

    # dosya var mi kontrol et
    if not os.path.exists(dosya_yolu):
        print(f"[ISTEMCI] Dosya bulunamadi: {dosya_yolu}")
        return {}

    # --- 1. DOSYAYI PARCALARA BOL ---
    # dosyayi chunk_boyut kadar parcalara ayiriyoruz
    # son parca daha kucuk olabilir, o da dahil ediliyor
    parcalar = []
    with open(dosya_yolu, "rb") as f:
        while True:
            veri = f.read(chunk_boyut)
            if not veri:
                break  # dosya bitti
            parcalar.append(veri)

    toplam_pkt = len(parcalar)
    toplam_byte = os.path.getsize(dosya_yolu)
    kaynak_hash = dosya_hash(dosya_yolu)  # aktarim bittikten sonra butunluk icin

    print(
        f"\n[ISTEMCI] Dosya: {os.path.basename(dosya_yolu)} | {toplam_byte} byte | {toplam_pkt} paket"
    )
    print(
        f"[ISTEMCI] Chunk={chunk_boyut}B | Timeout={timeout_sure}sn | Kayip=%{int(kayip_orani*100)}\n"
    )

    # --- 2. SOKET VE LOGGER HAZIRLA ---
    ham_soket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # AgSimulatoru gercek soketi sariyor, kayip/gecikme ekliyor
    sim = AgSimulatoru(ham_soket, kayip_orani=kayip_orani, gecikme_ms=gecikme_ms)
    sim.settimeout(timeout_sure)

    log = Logger(log_adi or f"logs/client_{int(time.time())}.csv")
    log.baslat()

    sunucu_adres = (sunucu_ip, sunucu_port)
    gonderilen_byte = 0  # retransmissionlar dahil toplam gonderilen byte
    yararli_byte = 0  # sadece basarili paketlerin verisi (goodput icin)

    # --- 3. STOP-AND-WAIT GONDERIM DONGUSU ---
    # her paket icin ACK gelene kadar bekliyoruz
    # ACK gelmezse tekrar gonderiyoruz
    for seq, parca in enumerate(parcalar):
        paket = veri_paketi_olustur(seq, toplam_pkt, parca)
        basarili = False

        for deneme in range(1, max_deneme + 1):
            # ilk deneme normal gonderim, sonrakiler retransmission
            if deneme == 1:
                log.kaydet(SEND, seq_no=seq, deneme=deneme)
                print(f"  [TX] seq={seq:4d}  deneme={deneme}")
            else:
                log.kaydet(RETRANSMIT, seq_no=seq, deneme=deneme)
                print(f"  [RE] seq={seq:4d}  deneme={deneme}")

            # paketi gonder (simulatorden gecebilir, dusurebilir)
            sim.gonder(paket, sunucu_adres)
            gonderilen_byte += len(paket)

            # ACK bekle
            try:
                raw, _ = sim.al(BUFFER_SIZE)
                ack_no = ack_paketi_coz(raw)

                # gelen ACK bizim bekledigimiz mi?
                if ack_no == seq:
                    log.kaydet(ACK_ALINDI, seq_no=seq, deneme=deneme)
                    yararli_byte += len(parca)  # bu parca basariyla iletildi
                    basarili = True
                    break  # bir sonraki pakete gec
                else:
                    # yanlis ACK, tekrar bekle
                    print(f"  [??] Beklenmeyen ACK: {ack_no}, beklenen: {seq}")

            except socket.timeout:
                # ACK suresi doldu, tekrar gonderecegiz
                log.kaydet(TIMEOUT, seq_no=seq, deneme=deneme)
                print(f"  [TO] seq={seq:4d}  timeout! ({deneme}/{max_deneme})")

        # max deneme asildi ve hala ACK gelmedi
        if not basarili:
            log.kaydet(BASARISIZ, seq_no=seq, aciklama="max deneme asildi")
            print(f"  [!!] seq={seq:4d}  BASARISIZ - max deneme asildi")

    # --- 4. FIN PAKETI GONDER ---
    # tum paketler gonderildi, sunucuya bitti sinyali ver
    # icinde dosyanin SHA256 hashi var, sunucu butunluk kontrolu yapacak
    fin = fin_paketi_olustur(kaynak_hash)
    print(f"\n[ISTEMCI] FIN gonderiliyor...")
    log.kaydet(FIN_SEND)

    # FIN icin de birka kez dene, kaybolabilir
    for _ in range(5):
        sim.gonder(fin, sunucu_adres)
        try:
            raw, _ = sim.al(BUFFER_SIZE)
            if raw:
                print("[ISTEMCI] FIN-ACK alindi, aktarim tamamlandi.")
                break
        except socket.timeout:
            print("[ISTEMCI] FIN-ACK gelmedi, tekrar gonderiliyor...")

    # --- 5. METRIKLERI HESAPLA ---
    log.bitis()
    sure = log.toplam_sure if log.toplam_sure > 0 else 0.001  # sifira bolme hatasi

    # throughput: retransmissionlar dahil tum gonderilen veri / sure
    # goodput: sadece basarili iletilen yararli veri / sure
    throughput = gonderilen_byte / sure
    goodput = yararli_byte / sure

    ozet = log.ozet_al()
    ozet.update(
        {
            "dosya_boyutu": toplam_byte,
            "toplam_pkt": toplam_pkt,
            "chunk_boyut": chunk_boyut,
            "timeout_sure": timeout_sure,
            "kayip_orani": kayip_orani,
            "throughput": throughput,
            "goodput": goodput,
            "gonderilen_byte": gonderilen_byte,
            "yararli_byte": yararli_byte,
        }
    )

    log.ozet_yazdir()
    print(f"  Throughput : {throughput/1024:.2f} KB/s")
    print(f"  Goodput    : {goodput/1024:.2f} KB/s")
    # verimlilik: goodput / throughput, ne kadar overhead var gorebiliriz
    print(
        f"  Verimlilik : %{round(goodput/throughput*100,1) if throughput > 0 else 0}\n"
    )

    log.kapat()
    sim.kapat()
    return ozet


if __name__ == "__main__":
    # komut satirindan kullanim:
    # python client.py dosya.txt
    # python client.py dosya.txt 127.0.0.1 9090 2048 2.0 0.1
    if len(sys.argv) < 2:
        print(
            "Kullanim: python client.py <dosya> [ip] [port] [chunk] [timeout] [kayip]"
        )
        sys.exit(1)

    dosya = sys.argv[1]
    ip = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else SERVER_PORT
    chunk = int(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_CHUNK_SIZE
    timeout = float(sys.argv[5]) if len(sys.argv) > 5 else DEFAULT_TIMEOUT
    kayip = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0

    dosya_gonder(dosya, ip, port, chunk, timeout, kayip_orani=kayip)
