#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>

// Configuración de Wi-Fi
const char* ssid = "INFORMATICA";
const char* password = "INFO2024";

// Pines
const int pinPulsador1 = D6;
const int pinPulsador2 = D7;
const int pinesRele[] = {D2,D3,D4,D5,D8};
const int pinLedPlaca = D0;
const int pinLedReles = D1;

// Configuración de Telegram
const String telegramToken = "992737156:AAHJH8m9uf8RmjWp3Sv8hkFAtN6buoMiS1s";
const String chatId = "1252733785";
const String serverTelegram = "https://api.telegram.org";

// Variables de control
unsigned long lastMillis = 0;
const unsigned long interval = 2000; // Intervalo para verificar Telegram
int lastUpdateId = 0;

WiFiClientSecure client;
HTTPClient http;

void setup() {
  Serial.begin(115200);

  // Configuración de pines
  pinMode(pinPulsador1, INPUT_PULLUP); // Pulsadores con lógica inversa
  pinMode(pinPulsador2, INPUT_PULLUP);
  pinMode(pinLedPlaca, OUTPUT);
  pinMode(pinLedReles, OUTPUT);
  digitalWrite(pinLedPlaca, HIGH);  // Indicar alimentación de la placa
  digitalWrite(pinLedReles, LOW);   // Indicar relés apagados

  for (int i = 0; i < 6; i++) {
    pinMode(pinesRele[i], OUTPUT);
    digitalWrite(pinesRele[i], HIGH); // Apagar relés inicialmente (lógica inversa)
  }

  Serial.println("\nPines configurados...");
  conectarWiFi();

  client.setInsecure();  // Evitar validación de certificados (solo para pruebas)
  enviarMensajeTelegram("Sistema de alarmas iniciado.");
}

void loop() {
  // Verificar el estado de los pulsadores
  verificarPulsadores();

  // Verificar Telegram periódicamente
  if (millis() - lastMillis > interval) {
    lastMillis = millis();
    verificarComandosTelegram();
  }
}

void verificarPulsadores() {
  // Activar/Desactivar relés según los pulsadores
  if (digitalRead(pinPulsador1) == LOW) {
    activarTodas();
  } else {
    desactivarTodas();
  }

  if (digitalRead(pinPulsador2) == LOW) {
    activarParcial(); // Activar D0 y D1
  } else {
    desactivarParcial(); // Desactivar D0 y D1
  }
}

void conectarWiFi() {
  Serial.println("Conectando a Wi-Fi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConectado a Wi-Fi");
  Serial.print("IP del dispositivo: ");
  Serial.println(WiFi.localIP());
}

void activarAlarma(int id) {
  if (id >= 0 && id < 6) {
    digitalWrite(pinesRele[id], LOW); // Lógica inversa: activar relé con LOW
    Serial.println("Relé " + String(id + 1) + " activado");
    actualizarIndicadorReles();
  }
}

void desactivarAlarma(int id) {
  if (id >= 0 && id < 6) {
    digitalWrite(pinesRele[id], HIGH); // Lógica inversa: desactivar relé con HIGH
    Serial.println("Relé " + String(id + 1) + " desactivado");
    actualizarIndicadorReles();
  }
}

void activarTodas() {
  for (int i = 0; i < 6; i++) {
    activarAlarma(i);
  }
}

void desactivarTodas() {
  for (int i = 0; i < 6; i++) {
    desactivarAlarma(i);
  }
}

void activarParcial() {
  activarAlarma(0); // Activar relé D0
  activarAlarma(1); // Activar relé D1
}

void desactivarParcial() {
  desactivarAlarma(0); // Desactivar relé D0
  desactivarAlarma(1); // Desactivar relé D1
}

void actualizarIndicadorReles() {
  bool algunaActiva = false;
  for (int i = 0; i < 6; i++) {
    if (digitalRead(pinesRele[i]) == LOW) {
      algunaActiva = true;
      break;
    }
  }
  digitalWrite(pinLedReles, algunaActiva ? HIGH : LOW);
}

void enviarMensajeTelegram(String mensaje) {
  String url = serverTelegram + "/bot" + telegramToken + "/sendMessage?chat_id=" + chatId + "&text=" + mensaje;

  Serial.println("Enviando mensaje a Telegram: " + mensaje);
  http.begin(client, url);
  int httpCode = http.GET();

  if (httpCode > 0) {
    String payload = http.getString();
    Serial.println("Respuesta de Telegram: " + payload);
  } else {
    Serial.println("Error al enviar mensaje, código: " + String(httpCode));
  }
  http.end();
}

void verificarComandosTelegram() {
  String url = serverTelegram + "/bot" + telegramToken + "/getUpdates?offset=" + String(lastUpdateId + 1);

  http.begin(client, url);
  int httpCode = http.GET();

  if (httpCode > 0) {
    String payload = http.getString();
    DynamicJsonDocument doc(2048);
    deserializeJson(doc, payload);

    if (doc["ok"]) {
      for (JsonObject result : doc["result"].as<JsonArray>()) {
        lastUpdateId = result["update_id"].as<int>();

        if (result.containsKey("message")) {
          String text = result["message"]["text"].as<String>();
          Serial.println("Comando recibido: " + text);

          if (text == "/activar todas") {
            activarTodas();
          } else if (text == "/desactivar todas") {
            desactivarTodas();
          } else if (text.startsWith("/activar ")) {
            int id = text.substring(9).toInt() - 1; // Extraer ID del comando
            activarAlarma(id);
          } else if (text.startsWith("/desactivar ")) {
            int id = text.substring(12).toInt() - 1; // Extraer ID del comando
            desactivarAlarma(id);
          }
        }
      }
    }
  } else {
    Serial.println("Error al verificar comandos, código: " + String(httpCode));
  }
  http.end();
}
