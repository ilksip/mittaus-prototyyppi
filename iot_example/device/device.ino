#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

//Wifitiedot
const char* ssid = "wifi name";
const char* password = "wifi password example";
//Palvelintiedot
const char* host_address = "192.168.0.100"; 
const int port = 5000;
const char* bootstrap_url = "/api/registerDevice";
const char* telemetry_url = "/api/telemetry";

//Komponenttien pinnit:
const int trigPin = D1;
const int echoPin = D2;

//Laitetiedot
String UUID = "";
const unsigned long delaytime = 30000; //30s; testaukseen

//
typedef float (*MeasurementFunction)();

void setup() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  Serial.begin(115200);

  //Wifi-yhteys
  Serial.print("Yhdistetään...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  //Bootstrap/Alustus
  while (UUID == "") {
    UUID = registerDevice();
    if (UUID == "") {
      Serial.println("Rekisteröinti epäonnistui? Yritetään uudelleen...");
      delay(5000);
    }
  Serial.println("Laitteen UUID: " + UUID);
  }
  Serial.println("Odotetaan 30s ennen toiminnan aloittamista...");
  delay(30000);
}

String registerDevice() {
  WiFiClient client;
  HTTPClient http;
  String registrationUrl = "http://" + String(host_address) + ":" + String(port) + bootstrap_url;
  
  if (http.begin(client, registrationUrl)) {
    http.addHeader("Content-Type", "application/json");

    JsonDocument doc;
    doc["mac_address"] = WiFi.macAddress();
    String requestBody;
    serializeJson(doc, requestBody);

    int httpCode = http.POST(requestBody);

    if (httpCode == httpCode == 200 || httpCode == 201) {
      String payload = http.getString();
      JsonDocument responseDoc;
      deserializeJson(responseDoc, payload);
      
      String receivedUUID = responseDoc["uuid"] | "";
      http.end();
      return receivedUUID;
    } else {
      Serial.printf("[BOOTSTRAP] Virhe: %d\n", httpCode);
      http.end();
      return "";
    }
  }
  return "";
}


// keskiarvon otto mittauksista = vakaampi tulos
float getAverageMeasurement(MeasurementFunction measureFn, int readingsCount) {
  float total = 0.0;
  int validReadings = 0;

  for (int i = 0; i < readingsCount; i++) {

    float value = measureFn();

    // Negative value means invalid reading
    if (value >= 0) {
      Serial.print(value);
      Serial.print(", ");

      total += value;
      validReadings++;
    }

    // Wait before next reading
    if (i < readingsCount - 1) {
      delay(500);
    }
  }

  if (validReadings > 0) {
    Serial.println("**");
    float measurement = total / validReadings;
      // Pyöristys kahteen desimaaliin
    measurement = round(measurement * 100.0f) / 100.0f;
    return measurement;
  }

  return -1.0;
}


// Ultrasonic sensor measurement
float measureUltrasonic() {

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);

  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH);
  // Calculate distance in cm
  float distance = (duration * 0.0343f) / 2.0f;
  // Validat
  if (distance >= 1.0f && distance <= 400.0f) {
    return distance;
  }
  return -1.0f;
}

String buildJson(const String& uuid, JsonObject sensorValues) {
  JsonDocument doc;

  doc["device_id"] = uuid;

  JsonObject values = doc["sensor_values"].to<JsonObject>();

  for (JsonPair kv : sensorValues) {
    values[kv.key()] = kv.value();
  }
  String output;
  serializeJson(doc, output);

  return output;
}
void loop() {
if (WiFi.status() == WL_CONNECTED) {
    JsonDocument mittaukset;
    mittaukset["fill_level"] = getAverageMeasurement(measureUltrasonic, 5);
    mittaukset["battery"] = 100;
    // Lisää tähän muut sensorit

    String jsonPayload = buildJson(UUID, mittaukset.as<JsonObject>());

    WiFiClient client;
    HTTPClient http;
    String telemetryUrl = "http://" + String(host_address) + ":" + String(port) + telemetry_url;
    Serial.println(telemetryUrl);
    if (http.begin(client, telemetryUrl)) {
      http.addHeader("Content-Type", "application/json");
      int httpCode = http.POST(jsonPayload);
      
      if (httpCode > 0) {
        Serial.printf("[HTTP] POST... code: %d\n", httpCode);
      } else {
        Serial.printf("[HTTP] POST... failed, error: %s\n", http.errorToString(httpCode).c_str());
      }
      http.end();
    }
  } else {
    Serial.println("WiFi Disconnected. Reconnecting...");
    WiFi.begin(ssid, password);
  }

  Serial.println("Going to sleep...");
  delay(delaytime); 
}
