# NetProbe

UDP Tabanli Guvenilir Dosya Aktarimi, Trafik Izleme ve Ag Performans Analiz Platformu

Bursa Teknik Universitesi - Bilgisayar Aglari Dersi Donem Projesi

## GitHub

https://github.com/netprobe-btu/NetProbe

## Proje Yapisi

netprobe/

├── protocol.py          # Paket yapisi, pack/unpack, checksum

├── logger.py            # Olay kayit sistemi (CSV)

├── server.py            # UDP sunucu

├── client.py            # UDP istemci (stop-and-wait)

├── network_sim.py       # Yapay kayip/gecikme simulatoru

├── analyzer.py          # Performans metrikleri ve grafikler

├── run_experiments.py   # 4 deney senaryosu

## Kurulum

pip install matplotlib

## Calistirma

Terminal 1:
python server.py

Terminal 2:
python client.py dosya.txt

Deneyler:
python run_experiments.py

## Grup

- Ismihan Kirmizioglan - 23360859078
- Busra Yesin - 23360859076
- Melike Dal - 22360859017

## Danisman

Dr. Izzet Fatih Senturk
