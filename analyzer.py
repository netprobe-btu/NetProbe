# Bu dosya deney sonuclarini analiz edip grafik uretiyor
# Log CSV dosyalarindan verileri okuyoruz
# matplotlib ile throughput, goodput, retransmission rate grafiklerini ciziyoruz

import csv
import os
import json
import matplotlib.pyplot as plt


def log_oku(log_dosyasi: str) -> list:
    # CSV log dosyasini okuyup her satiri sozluk olarak donduruyoruz
    satirlar = []
    with open(log_dosyasi, "r", encoding="utf-8") as f:
        for satir in csv.DictReader(f):
            satirlar.append(satir)
    return satirlar


def karsilastirmali_grafik(sonuclar: list, cikis_dizini: str = "results"):
    # birden fazla deney sonucunu yan yana gosteren 4 grafik ciziyoruz
    # throughput, goodput, retransmission rate, tamamlanma suresi

    os.makedirs(cikis_dizini, exist_ok=True)

    if not sonuclar:
        print("[ANALIZ] Karsilastirilacak sonuc yok.")
        return

    # grafik icin verileri listele
    etiketler = [s.get("etiket", f"Deney {i+1}") for i, s in enumerate(sonuclar)]
    throughputlar = [s.get("throughput", 0) / 1024 for s in sonuclar]  # byte/s -> KB/s
    goodputlar = [s.get("goodput", 0) / 1024 for s in sonuclar]  # byte/s -> KB/s
    retrans_rate = [
        s.get("retransmit_rate", 0) * 100 for s in sonuclar
    ]  # oran -> yuzde
    sureler = [s.get("toplam_sure", 0) for s in sonuclar]  # saniye

    # 2x2 grafik duzeni olustur
    fig, eksenler = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("NetProbe - Performans Analizi", fontsize=14, fontweight="bold")

    # her deney icin farkli renk kullanalim
    renkler = ["steelblue", "tomato", "mediumseagreen", "mediumpurple", "sandybrown"]

    def bar_ciz(ax, degerler, baslik, ylabel):
        # bar grafik ciz ve cubuk uzerine deger yaz
        cubuklar = ax.bar(
            etiketler, degerler, color=renkler[: len(degerler)], edgecolor="gray"
        )
        ax.set_title(baslik)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=15)
        ax.grid(axis="y", alpha=0.3)

        # her cubugun ustune degerini yaz, okumasi kolay olsun
        for c, d in zip(cubuklar, degerler):
            ax.text(
                c.get_x() + c.get_width() / 2,
                c.get_height() + max(degerler) * 0.01,
                f"{d:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # 4 grafigi ayri ayri ciz
    bar_ciz(eksenler[0, 0], throughputlar, "Throughput (KB/s)", "KB/s")
    bar_ciz(eksenler[0, 1], goodputlar, "Goodput (KB/s)", "KB/s")
    bar_ciz(eksenler[1, 0], retrans_rate, "Retransmission Rate (%)", "%")
    bar_ciz(eksenler[1, 1], sureler, "Tamamlanma Suresi (sn)", "sn")

    plt.tight_layout()
    cikis = os.path.join(cikis_dizini, "karsilastirma.png")
    plt.savefig(cikis, dpi=150)
    plt.close()
    print(f"[ANALIZ] Grafik kaydedildi: {cikis}")


def throughput_goodput_grafik(
    sonuclar: list, x_degiskeni: str, x_etiketi: str, cikis_dizini: str = "results"
):
    os.makedirs(cikis_dizini, exist_ok=True)

    x = [s.get(x_degiskeni, 0) for s in sonuclar]
    tp = [s.get("throughput", 0) / 1024 for s in sonuclar]
    gp = [s.get("goodput", 0) / 1024 for s in sonuclar]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x, tp, "o-", color="steelblue", label="Throughput (KB/s)", linewidth=2)
    ax.plot(x, gp, "s--", color="mediumseagreen", label="Goodput (KB/s)", linewidth=2)
    ax.fill_between(x, gp, tp, alpha=0.1, color="gray", label="Overhead")
    ax.set_xlabel(x_etiketi)
    ax.set_ylabel("Hiz (KB/s)")
    ax.set_title("Throughput vs Goodput")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    cikis = os.path.join(cikis_dizini, "tp_gp.png")
    plt.savefig(cikis, dpi=150)
    plt.close()
    print(f"[ANALIZ] Grafik kaydedildi: {cikis}")


def sonuclari_kaydet(sonuclar: list, dosya: str = "results/sonuclar.json"):
    # tum deney sonuclarini JSON olarak kaydediyoruz
    # rapor yazarken bu dosyaya bakabiliriz
    os.makedirs(os.path.dirname(dosya), exist_ok=True)
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, indent=2, ensure_ascii=False)
    print(f"[ANALIZ] Sonuclar kaydedildi: {dosya}")
