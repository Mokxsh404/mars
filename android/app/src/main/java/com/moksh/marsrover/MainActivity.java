package com.moksh.marsrover;

import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.JavascriptInterface;
import androidx.appcompat.app.AppCompatActivity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.UUID;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

public class MainActivity extends AppCompatActivity {
    private BluetoothSocket socket;
    private OutputStream outStream;
    private InputStream inStream;
    private static final UUID MY_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);

        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBT");
        webView.loadUrl("file:///android_asset/index.html");
    }

    public class WebAppInterface {
        @JavascriptInterface
        public String getPairedDevices() {
            try {
                BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
                if (adapter == null) return "[]";
                Set<BluetoothDevice> devices = adapter.getBondedDevices();
                JSONArray arr = new JSONArray();
                for (BluetoothDevice dev : devices) {
                    JSONObject obj = new JSONObject();
                    obj.put("name", dev.getName());
                    obj.put("address", dev.getAddress());
                    arr.put(obj);
                }
                return arr.toString();
            } catch (Exception e) {
                return "[]";
            }
        }

        @JavascriptInterface
        public boolean connect(String address) {
            try {
                if (socket != null) {
                    try { socket.close(); } catch (Exception e) {}
                }
                BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
                BluetoothDevice dev = adapter.getRemoteDevice(address);
                socket = dev.createRfcommSocketToServiceRecord(MY_UUID);
                socket.connect();
                outStream = socket.getOutputStream();
                inStream = socket.getInputStream();
                
                startReadThread();
                return true;
            } catch (Exception e) {
                return false;
            }
        }

        @JavascriptInterface
        public void send(String cmd) {
            try {
                if (outStream != null) {
                    outStream.write(cmd.getBytes());
                }
            } catch (Exception e) {}
        }
    }

    private void startReadThread() {
        new Thread(() -> {
            byte[] buffer = new byte[1024];
            int bytes;
            StringBuilder sb = new StringBuilder();
            while (socket != null && socket.isConnected()) {
                try {
                    bytes = inStream.read(buffer);
                    if (bytes > 0) {
                        String data = new String(buffer, 0, bytes);
                        sb.append(data);
                        int lineEnd = sb.indexOf("\n");
                        if (lineEnd >= 0) {
                            String line = sb.substring(0, lineEnd).trim();
                            sb.delete(0, lineEnd + 1);
                            runOnUiThread(() -> {
                                if (webView != null) {
                                    webView.evaluateJavascript("handleIncomingLine(" + JSONObject.quote(line) + ")", null);
                                }
                            });
                        }
                    }
                } catch (Exception e) {
                    break;
                }
            }
        }).start();
    }
}
