#include <WiFi.h>

// Target Wi-Fi credentials
const char* ssid = "esp_wifi";
const char* password = "password123";

// TCP server
WiFiServer server(1234);

// Allowed pins
int allowedPins[] = {13, 12, 14, 27, 26, 25, 33, 32, 35, 34};
#define NUM_PINS (sizeof(allowedPins) / sizeof(allowedPins[0]))

void setupPins() {
  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(allowedPins[i], OUTPUT);
    digitalWrite(allowedPins[i], LOW);
  }
}

bool isValidPin(int pin) {
  for (int i = 0; i < NUM_PINS; i++) {
    if (allowedPins[i] == pin) return true;
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Scanning for available WiFi networks...");
  int n = WiFi.scanNetworks();

  bool ssidFound = false;
  for (int i = 0; i < n; ++i) {
    String foundSSID = WiFi.SSID(i);
    Serial.printf("Found SSID: %s\n", foundSSID.c_str());
    if (foundSSID == ssid) {
      ssidFound = true;
    }
  }

  if (!ssidFound) {
    Serial.printf("SSID \"%s\" not found. Halting...\n", ssid);
    while (true);  // Halt execution (crash out)
  }

  Serial.printf("Connecting to SSID \"%s\"...\n", ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED ) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nFailed to connect to WiFi. Halting...");
    while (true);  // Halt execution (crash out)
  }

  Serial.println("\nConnected to WiFi!");
  Serial.println(WiFi.localIP());

  setupPins();
  server.begin();
}


void loop() {
  WiFiClient client = server.available();
  if (client) {
    Serial.println("Client connected!");
    while (client.connected()) {
      Serial.println("Waiting for command...");
      if (client.available()) {

        String data = client.readStringUntil('\n');
        Serial.print("Recived data: ");
        Serial.println(data);
        data.trim();

        int pin, state;
        if (sscanf(data.c_str(), "%d %d", &pin, &state) == 2) {
          if (isValidPin(pin) && (state == 0 || state == 1)) {
            digitalWrite(pin, state);
            client.println("OK");
            Serial.printf("Set pin %d to %d\n", pin, state);
          } else {
            client.println("Invalid pin or state");
          }
        } else {
          client.println("Invalid format. Use: <pin> <state>");
        }
      }
    }
    client.stop();
    Serial.println("Client disconnected.");
  }
}
