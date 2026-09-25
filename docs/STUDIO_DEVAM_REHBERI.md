# Studio'da kaldığımız yerden devam

Studio: http://127.0.0.1:5173/#studio-video

Kaydedilmiş proje: **Why AI Data Centers Are Running Out of Power**.
Ekrandaki 28,4 saniyelik video, açılıştan sonra gelen bir çalışma bölümüdür.
46,5 saniyelik açılış da korunmuştur. Tam video henüz hazır değildir.

## Şimdiki tek çalışma

Bu kısa bölüm üzerinde manuel AI → Studio → sahne değerlendirmesi döngüsünü
tamamlayacağız. Senin görevin konu ve yaratıcı yön konusunda karar vermek;
çekim kimlikleri, JSON düzenleme veya zaman kodlarını elle hazırlamak değil.

1. **Son AI görevini ZIP olarak indir** düğmesine bas. Paket, güncel videoyu,
   görüntüleri, kaynakları ve önceki değerlendirmeyi içerir.
2. ZIP'i dosya/video okuyabilen, abone olduğun AI aracına kendin yükle.
   Araç ZIP okuyamıyorsa içeriğini çıkarıp `task.json`, `review/current-cut.mp4`,
   önizlemeler ve kaynakları birlikte ekle. Aşağıdaki metni gönder.
3. AI'nın verdiği JSON dosyasını Studio'da **AI sonuç dosyasını içe al** ile aç.
   Dosya reddedilirse Studio'nun hata metnini aynı AI'ya ver; JSON'u elle düzeltme.
4. Eksik görsel bildirilirse önce onu karşıla. **Çalışma kurgusu üretilebilir**
   durumu geldiğinde **Kaydedilmiş planı üret** düğmesine bas.
5. Videoyu izle. Sorun varsa ilgili **Sahne** düğmesini seçip **Bu videoya
   değerlendirme ekle** alanına yaz. Sonraki düzeltme görevi bu kayda bağlı ilerler.

AI'ya gönderilecek metin:

> Ekli Studio görev paketini incele. Bu video açılış değil, 28,4 saniyelik bir
> devam bölümüdür. task.json içindeki instructions ve response_schema sözleşmesine
> uy. review/current-cut.mp4 dosyasını, görüntüleri ve kaynakları gerçekten
> inceleyerek anlatım–görüntü uyumunu, ritmi, tekrarları ve belge okunabilirliğini
> değerlendir. Görmediğin veya eksik olan malzemeyi açıkça belirt. Önceki geri
> bildirimi ve kaynakların sınırlarını koru. Studio'ya yükleyebileceğim tek bir
> JSON sonuç dosyası üret; açıklama metnini JSON dosyasına ekleme. task_id,
> task_hash ve mevcut medya/kaynak kimliklerini değiştirme.

AI görüntüleri/video içeriğini okuyamıyorsa o cevabı görsel inceleme geçmiş gibi
kullanma. Studio'nun dosyayı kabul etmesi yaratıcı kalite onayı değildir.

## Sonraki hedef

Bu döngü doğrulandıktan sonra bütün videonun hikâye planını ve bölüm başına
malzeme ihtiyaçlarını tamamlayacağız. Konu, yaklaşım ve yayın onayı sende kalacak.
İlk hedef business-tech; diğer kanal türleri daha sonra ayrı domain paketleriyle
eklenecek. Ücretli API otomasyonu sonraki aşamadır.

## Yeniden açma ve saklama

Studio kapalı olduğunda, proje klasöründe PowerShell ile:

```powershell
.\scripts\start_local_studio.ps1 -ApiPort 8007
```

Aktif veritabanları proje içindeki `.studio-data` klasöründedir. Bu klasör yerel
çalışma verisidir ve Git'e eklenmez. Kurtarma kopyaları
`output/phase17-project-state-recovery-20260925` altında tutulur. Bu klasörleri
proje yedeğine dahil et. 5 Eylül yedeği ve daha yeni kayıtları içeren çıktılar
korunmuştur; dışa aktarılmamış eski geçmişin tamamı geri getirildi sayılmaz.
