from android.runnable import run_on_ui_thread
from jnius import autoclass
from kivy.app import App
from kivy.uix.widget import Widget
from threading import Thread

def start_flask():
    from app import app
    app.run(host='127.0.0.1', port=5000, debug=False)

class WebViewWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_webview()

    @run_on_ui_thread
    def start_webview(self):
        Activity = autoclass('org.kivy.android.PythonActivity').mActivity
        WebView = autoclass('android.webkit.WebView')
        WebViewClient = autoclass('android.webkit.WebViewClient')
        
        webview = WebView(Activity)
        webview.getSettings().setJavaScriptEnabled(True)
        webview.getSettings().setDomStorageEnabled(True)
        webview.setWebViewClient(WebViewClient())
        
        webview.loadUrl('http://127.0.0.1:5000')
        Activity.setContentView(webview)

class WhotApp(App):
    def build(self):
        flask_thread = Thread(target=start_flask)
        flask_thread.daemon = True
        flask_thread.start()
        return WebViewWidget()

if __name__ == '__main__':
    WhotApp().run()
