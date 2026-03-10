import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
import uuid

class UmrahMobileApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=30, spacing=20, **kwargs)

        # إعدادات الاتصال بالسيرفر اللي سويته أنت
        self.server_url = "http://127.0.0.1:8000/api/umrah"
        self.session_id = str(uuid.uuid4())

        # إحداثيات وهمية لمحاكاة المشي
        self.current_lat = 21.4225
        self.current_lon = 39.8262

        # الواجهة الرسومية
        self.info_label = Label(text="مستعد للعمرة؟", font_size=24)
        self.add_widget(self.info_label)

        self.tawaf_btn = Button(text="بدء الطواف (تحديد نقطة البداية)", font_size=20, background_color=(0, 0.7, 0, 1))
        self.tawaf_btn.bind(on_press=self.start_tawaf)
        self.add_widget(self.tawaf_btn)

        self.saee_btn = Button(text="بدء السعي", font_size=20, disabled=True)
        self.saee_btn.bind(on_press=self.start_saee)
        self.add_widget(self.saee_btn)

    def start_tawaf(self, instance):
        self.tawaf_btn.disabled = True
        self.info_label.text = "جاري الاتصال بالسيرفر لبدء الطواف..."

        # إرسال طلب البدء للـ API
        data = {"session_id": self.session_id, "lat": self.current_lat, "lon": self.current_lon}
        try:
            response = requests.post(f"{self.server_url}/start_tawaf", json=data).json()
            self.info_label.text = f"تم البدء!\nالأشواط: {response.get('tawaf_rounds', 0)}"

            # تشغيل تتبع الموقع كل 3 ثواني
            Clock.schedule_interval(self.track_location, 3)
        except Exception as e:
            self.info_label.text = "تأكد أن السيرفر (main.py) شغال!"
            self.tawaf_btn.disabled = False

    def track_location(self, dt):
        # محاكاة حركة المعتمر (تغيير الإحداثيات قليلاً لتجاوز 30 متر ثم العودة)
        self.current_lat += 0.0004 # يبتعد
        if self.current_lat > 21.4235:
            self.current_lat = 21.4225 # يرجع لنقطة البداية

        data = {"session_id": self.session_id, "lat": self.current_lat, "lon": self.current_lon}
        try:
            response = requests.post(f"{self.server_url}/track_tawaf", json=data).json()

            if "tawaf_rounds" in response:
                rounds = response['tawaf_rounds']
                timer = response.get('tawaf_timer_seconds', 0)
                self.info_label.text = f"الطواف شغال...\nالأشواط: {rounds} / 7\nالوقت: {timer} ثانية"

            # إذا أرسل السيرفر تنبيه (سواء الشوط الأخير أو الانتهاء)
            if "alert" in response:
                self.info_label.text = response["alert"]
                if "انتهى" in response["alert"]:
                    Clock.unschedule(self.track_location) # إيقاف التتبع
                    self.saee_btn.disabled = False # فتح زر السعي
                    self.saee_btn.background_color = (0, 0.7, 0, 1)
        except:
            pass

    def start_saee(self, instance):
        # هنا يتم استدعاء مسار /start_saee بنفس الطريقة
        self.saee_btn.disabled = True
        self.info_label.text = "تم بدء السعي... تقبل الله"

class MyApp(App):
    def build(self):
        return UmrahMobileApp()

if __name__ == '__main__':
    MyApp().run()