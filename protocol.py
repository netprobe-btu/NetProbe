# Bu dosya paketin nasil olusturulacagini ve cozumlenecegin tanimlar
# Veri paketi, ACK paketi ve FIN paketi burada yapildi
# struct kutuphanesi ile byte dizisine donusturuyoruz (pack/unpack)

import struct
import hashlib

# --- Paket tipleri ---
# Hangi paketin ne oldugunu anlamak icin ilk byte'a bakiyoruz
PKT_DATA = 0x01  # veri paketi
PKT_ACK = 0x02  # onay paketi
PKT_FIN = 0x03  # aktarim bitti sinyali

# --- Varsayilan degerler ---
# Bunlar client.py'de de kullaniliyor, tek yerden degistirmek kolaylik sagliyor
DEFAULT_CHUNK_SIZE = 1024  # her paketin tasiyacagi veri miktari (byte)
DEFAULT_TIMEOUT = 2.0  # ACK gelmezse kac saniye bekleyecegiz
DEFAULT_MAX_RETRY = 5  # maksimum kac kez tekrar gonderecegiz (foyden zorunlu)
SERVER_PORT = 9090  # sunucunun dinleyecegi port
BUFFER_SIZE = 65535  # soketten okuyacagimiz maksimum veri

# Veri paketi baslik formati
# ! = big-endian (ag standardi)
# B = 1 byte (paket tipi)
# I = 4 byte unsigned int (seq numarasi)
# I = 4 byte unsigned int (toplam paket sayisi)
# H = 2 byte unsigned short (payload uzunlugu)
# 16s = 16 byte (MD5 checksum)
DATA_HEADER_FORMAT = "!B I I H 16s"
DATA_HEADER_SIZE = struct.calcsize(DATA_HEADER_FORMAT)

# ACK paketi baslik formati
# B = tip, I = ack numarasi, 16s = checksum
ACK_FORMAT = "!B I 16s"
ACK_SIZE = struct.calcsize(ACK_FORMAT)

# FIN paketi formati
# B = tip, 64s = SHA256 hash (64 karakter hex string)
FIN_FORMAT = "!B 64s"
FIN_SIZE = struct.calcsize(FIN_FORMAT)


def hesapla_checksum(veri: bytes) -> bytes:
    # MD5 ile 16 byteli checksum uretiyoruz
    # payload bozulduysa bunu karsilastirarak anlayabiliriz
    return hashlib.md5(veri).digest()


def dosya_hash(dosya_yolu: str) -> str:
    # SHA256 ile dosyanin parmak izini cikartiyoruz
    # aktarim bittikten sonra sunucudaki dosya ile karsilastirilacak
    sha = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        while True:
            blok = f.read(8192)
            if not blok:
                break
            sha.update(blok)
    return sha.hexdigest()


def veri_paketi_olustur(seq: int, total: int, payload: bytes) -> bytes:
    # once payloadun checksumini hesapliyoruz
    # sonra header'i pack edip payload ile birlestiriyoruz
    chk = hesapla_checksum(payload)
    header = struct.pack(DATA_HEADER_FORMAT, PKT_DATA, seq, total, len(payload), chk)
    return header + payload  # header + asil veri


def veri_paketi_coz(raw: bytes):
    # gelen ham bytelari ayristiriyoruz
    # once boyut kontrolu, sonra tip kontrolu, sonra checksum kontrolu
    if len(raw) < DATA_HEADER_SIZE:
        return None  # paket cok kucuk, bir sorun var

    tip, seq, total, length, chk = struct.unpack(
        DATA_HEADER_FORMAT, raw[:DATA_HEADER_SIZE]
    )

    if tip != PKT_DATA:
        return None  # bu bir veri paketi degil

    # header'dan sonraki kisim payload
    payload = raw[DATA_HEADER_SIZE : DATA_HEADER_SIZE + length]

    # checksum eslesmiyor mu? veri yolda bozulmus demek
    if hesapla_checksum(payload) != chk:
        print(f"[UYARI] Paket {seq} checksum hatasi!")
        return None

    return seq, total, payload


def ack_paketi_olustur(ack_num: int) -> bytes:
    # sunucu bu fonksiyonla ACK paketi olusturuyor
    # hangi paketi aldigini ack_num ile bildiriyor
    chk = hesapla_checksum(ack_num.to_bytes(4, "big"))
    return struct.pack(ACK_FORMAT, PKT_ACK, ack_num, chk)


def ack_paketi_coz(raw: bytes):
    # istemci gelen ACK'i bu fonksiyonla cozuyor
    # ack numarasini donduruyoruz
    if len(raw) < ACK_SIZE:
        return None

    tip, ack_num, chk = struct.unpack(ACK_FORMAT, raw[:ACK_SIZE])

    if tip != PKT_ACK:
        return None

    # ACK paketi de bozulabilir, checksumunu dogrula
    if chk != hesapla_checksum(ack_num.to_bytes(4, "big")):
        return None

    return ack_num


def fin_paketi_olustur(file_hash: str) -> bytes:
    # aktarim bitti, dosyanin hashini sunucuya gonderiyoruz
    # sunucu kendi hesapladigiyla karsilastiracak
    hash_bytes = file_hash.encode()[:64].ljust(64, b"\x00")
    return struct.pack(FIN_FORMAT, PKT_FIN, hash_bytes)


def fin_paketi_coz(raw: bytes):
    # sunucu FIN paketini bu fonksiyonla cozuyor
    # icerisindeki hash stringi donduruyoruz
    if len(raw) < FIN_SIZE:
        return None
    tip, hash_bytes = struct.unpack(FIN_FORMAT, raw[:FIN_SIZE])
    if tip != PKT_FIN:
        return None
    return hash_bytes.decode().strip("\x00")
