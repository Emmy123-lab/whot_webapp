import threading
import time
from flask import Flask
# Import your actual whot_webapp Flask app instance here
# (Assuming your Flask instance is named 'app' inside your project files)
from app import app 

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

# Hardcoded port for your local game server
PORT = 5000

def start_flask():
    """Runs the Flask server in a dedicated background thread."""
    # We force the server to host on localhost purely for internal mobile processing
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)

class WhotMobileApp(App):
    def build(self):
        self.title = "Whot Mobile Pro"
        layout = BoxLayout(orientation='vertical')
        
        # If running natively on Android, we inject the Android system WebView component
        if platform == 'android':
            from jnius import autoclass
            from android.runnable import run_on_ui_thread
            
            # Access native Android web layout classes via Pyjnius bridge
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            Activity = autoclass('org.kivy.android.PythonActivity').mActivity
            
            @run_on_ui_thread
            def create_webview():
                webview = WebView(Activity)
                # Enable critical local storage & JavaScript execution configurations
                webview.getSettings().setJavaScriptEnabled(True)
                webview.getSettings().setDomStorageEnabled(True)
                webview.setWebViewClient(WebViewClient())
                
                # Load your local offline Flask web app route directly
                webview.loadUrl(f"http://127.0.0.1:{PORT}")
                Activity.setContentView(webview)
                
            create_webview()
        else:
            # Fallback label configuration for testing on desktop environments
            from kivy.uix.label import Label
            layout.add(Label(text=f"Server running at http://127.0.0.1:{PORT}\nOpen in your browser!"))
            
        return layout

if __name__ == '__main__':
    # 1. Launch the Flask backend as an independent background daemon thread
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Give the background Flask system a brief moment to warm up before launching the UI view
    time.sleep(1)
    
    # 2. Run the native Kivy mobile rendering engine wrapper
    WhotMobileApp().run()

