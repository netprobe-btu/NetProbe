# Bu dosya 4 farkli deney senaryosunu otomatik olarak calistiriyor
# Her senaryo farkli bir parametreyi degistirip sonuclari karsilastiriyor
# Grafikleri results/ klasorune, JSON sonuclari da ayni yere kaydediyor
#
# Kullanim:
#   Once sunucuyu baslat -> python server.py
#   Sonra bu dosyayi calistir -> python run_experiments.py

import os
import time
import sys
from client import dosya_gonder
from analyzer import karsilastirmali_grafik, throughput_goodput_grafik, sonuclari_kaydet
from protocol import DEFAULT_TIMEOUT, SERVER_PORT

# klasorleri bastan olustur, sonradan hata cikmasin
os.makedirs("test_files", exist_ok=True)
os.makedirs("results", exist_ok=True)
os.makedirs("logs", exist_ok=True)


def test_dosyasi_olustur(boyut: int, ad: str) -> str:
    # belirtilen boyutta test dosyasi olustur
    # dosya zaten varsa tekrar olusturma, zaman kaybetme
    yol = os.path.join("test_files", ad)
    if not os.path.exists(yol):
        with open(yol, "wb") as f:
            # tekrarlanabilir icerik kullaniyoruz
            # boylece her calistirmada ayni hash cikiyor
            icerik = b"NetProbe test verisi 1234567890 ABCDEFGHIJ\n"
            f.write((icerik * (boyut // len(icerik) + 1))[:boyut])
    return yol


# -----------------------------------------------------------
# SENARYO 1: Farkli Paket Boyutlari
# -----------------------------------------------------------
def senaryo1(ip, port):
    # chunk boyutunu degistirip throughput ve goodput'u olcuyoruz
    # kucuk chunk = cok paket = cok header overhead
    # buyuk chunk = az paket = daha verimli ama kayip olursa cok veri gider
    print("\n" + "=" * 55)
    print("SENARYO 1: Farkli Paket Boyutlari")
    print("=" * 55)

    dosya = test_dosyasi_olustur(500_000, "test_500kb.bin")
    sonuclar = []

    for chunk in [256, 512, 1024, 2048, 4096]:
        print(f"\n--- Chunk boyutu: {chunk} byte ---")
        time.sleep(0.5)  # sunucuya nefes aldirmak icin kisa bekleme

        ozet = dosya_gonder(
            dosya_yolu=dosya,
            sunucu_ip=ip,
            sunucu_port=port,
            chunk_boyut=chunk,
            kayip_orani=0.0,  # kayip yok, sadece chunk boyutu etkisine bakiyoruz
            log_adi=f"logs/s1_chunk_{chunk}.csv",
        )
        ozet["etiket"] = f"{chunk}B"
        ozet["chunk_boyut"] = chunk
        sonuclar.append(ozet)
        time.sleep(1)  # bir sonraki aktarim oncesi sunucunun hazirlanmasi icin bekle

    # grafikleri kaydet
    karsilastirmali_grafik(sonuclar, "results/senaryo1")
    throughput_goodput_grafik(
        sonuclar, "chunk_boyut", "Chunk Boyutu (byte)", "results/senaryo1"
    )
    sonuclari_kaydet(sonuclar, "results/senaryo1/sonuclar.json")


# -----------------------------------------------------------
# SENARYO 2: Farkli Timeout Degerleri
# -----------------------------------------------------------
def senaryo2(ip, port):
    # timeout degerini degistirip etkisini inceliyoruz
    # cok kucuk timeout -> gereksiz retransmission artar
    # cok buyuk timeout -> kayip olunca cok bekleriz, yavaslar
    print("\n" + "=" * 55)
    print("SENARYO 2: Farkli Timeout Degerleri")
    print("=" * 55)

    # biraz kayip ekledik, timeout etkisi daha belirgin gorunsun
    dosya = test_dosyasi_olustur(200_000, "test_200kb.bin")
    sonuclar = []

    for to in [0.5, 1.0, 2.0, 4.0]:
        print(f"\n--- Timeout: {to} sn ---")
        time.sleep(0.5)

        ozet = dosya_gonder(
            dosya_yolu=dosya,
            sunucu_ip=ip,
            sunucu_port=port,
            timeout_sure=to,
            kayip_orani=0.05,  # %5 kayip ile timeout farki daha net gorulur
            log_adi=f"logs/s2_timeout_{to}.csv",
        )
        ozet["etiket"] = f"{to}sn"
        ozet["timeout_sure"] = to
        sonuclar.append(ozet)
        time.sleep(1)

    karsilastirmali_grafik(sonuclar, "results/senaryo2")
    throughput_goodput_grafik(
        sonuclar, "timeout_sure", "Timeout Suresi (sn)", "results/senaryo2"
    )
    sonuclari_kaydet(sonuclar, "results/senaryo2/sonuclar.json")


# -----------------------------------------------------------
# SENARYO 3: Farkli Kayip Oranlari
# -----------------------------------------------------------
def senaryo3(ip, port):
    # kayip oranini artirip sistemin nasil davrandigini inceliyoruz
    # kayip artinca retransmission artar, goodput duser
    # belirli bir noktadan sonra sistem cok yavaslar
    print("\n" + "=" * 55)
    print("SENARYO 3: Farkli Kayip Oranlari")
    print("=" * 55)

    dosya = test_dosyasi_olustur(300_000, "test_300kb.bin")
    sonuclar = []

    for kayip in [0.0, 0.05, 0.10, 0.20, 0.30]:
        print(f"\n--- Kayip orani: %{int(kayip * 100)} ---")
        time.sleep(0.5)

        ozet = dosya_gonder(
            dosya_yolu=dosya,
            sunucu_ip=ip,
            sunucu_port=port,
            kayip_orani=kayip,
            timeout_sure=1.5,
            log_adi=f"logs/s3_kayip_{int(kayip * 100)}.csv",
        )
        ozet["etiket"] = f"%{int(kayip * 100)}"
        ozet["kayip_orani"] = kayip
        sonuclar.append(ozet)
        time.sleep(1)

    karsilastirmali_grafik(sonuclar, "results/senaryo3")
    throughput_goodput_grafik(
        sonuclar, "kayip_orani", "Kayip Orani", "results/senaryo3"
    )
    sonuclari_kaydet(sonuclar, "results/senaryo3/sonuclar.json")


# -----------------------------------------------------------
# SENARYO 4: Farkli Dosya Boyutlari
# -----------------------------------------------------------
def senaryo4(ip, port):
    # kucuk ve buyuk dosyalarda sistem verimliligi karsilastiriyoruz
    # kucuk dosyalarda baslangic/bitis overhead orani daha yuksek
    # buyuk dosyalarda sistem daha verimli calisir
    print("\n" + "=" * 55)
    print("SENARYO 4: Farkli Dosya Boyutlari")
    print("=" * 55)

    sonuclar = []

    for boyut, ad, etiket in [
        (50_000, "test_50kb.bin", "50KB"),
        (200_000, "test_200kb.bin", "200KB"),
        (500_000, "test_500kb.bin", "500KB"),
        (1_000_000, "test_1mb.bin", "1MB"),
    ]:
        dosya = test_dosyasi_olustur(boyut, ad)
        print(f"\n--- Dosya boyutu: {etiket} ---")
        time.sleep(0.5)

        ozet = dosya_gonder(
            dosya_yolu=dosya,
            sunucu_ip=ip,
            sunucu_port=port,
            kayip_orani=0.0,  # kayip yok, sadece dosya boyutu etkisine bakiyoruz
            log_adi=f"logs/s4_{ad}.csv",
        )
        ozet["etiket"] = etiket
        ozet["dosya_boyutu"] = boyut
        sonuclar.append(ozet)
        time.sleep(1)

    karsilastirmali_grafik(sonuclar, "results/senaryo4")
    throughput_goodput_grafik(
        sonuclar, "dosya_boyutu", "Dosya Boyutu (byte)", "results/senaryo4"
    )
    sonuclari_kaydet(sonuclar, "results/senaryo4/sonuclar.json")


# -----------------------------------------------------------
# Ana calistirici
# -----------------------------------------------------------
if __name__ == "__main__":
    # komut satirindan ip ve port verilebilir
    # python run_experiments.py 127.0.0.1 9090
    ip = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else SERVER_PORT

    print("\nNetProbe - Deney Senaryolari")
    print(f"Hedef: {ip}:{port}")
    print("Sunucunun calistigina emin ol: python server.py")
    input("\nHazir misin? ENTER'a bas...")

    senaryo1(ip, port)
    senaryo2(ip, port)
    senaryo3(ip, port)
    senaryo4(ip, port)

    print("\n" + "=" * 55)
    print("Tum senaryolar tamamlandi.")
    print("Grafikler results/ klasorunde.")
    print("=" * 55)
