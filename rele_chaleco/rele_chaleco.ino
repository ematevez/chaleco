const int relayPins[] = {5, 6, 7}; // Pines de los relés
const int activatePin = 13;        // Pin para activar relés
const int deactivatePin = 12;      // Pin para desactivar relés

void setup() {
  for (int i = 0; i < 3; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW); // Asegurarse de que los relés estén apagados al inicio
  }
  
  pinMode(activatePin, INPUT_PULLUP);   // Configurar pin de activación
  pinMode(deactivatePin, INPUT_PULLUP); // Configurar pin de desactivación

  Serial.begin(9600);
}

void loop() {
  // Verificar si el pin de activación está a masa
  if (digitalRead(activatePin) == LOW) {
    for (int i = 0; i < 3; i++) {
      digitalWrite(relayPins[i], HIGH); // Activar todos los relés
    }
    Serial.println("Relés activados por pin 13");
    delay(200); // Pequeño retraso para evitar rebotes
  }

  // Verificar si el pin de desactivación está a masa
  if (digitalRead(deactivatePin) == LOW) {
    for (int i = 0; i < 3; i++) {
      digitalWrite(relayPins[i], LOW); // Desactivar todos los relés
    }
    Serial.println("Relés desactivados por pin 12");
    delay(200); // Pequeño retraso para evitar rebotes
  }

  // Comando desde Serial
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "ACTIVATE") {
      for (int i = 0; i < 3; i++) {
        digitalWrite(relayPins[i], HIGH); // Activar todos los relés
      }
      delay(20000); // Mantener activado por 20 segundos
      Serial.println("Activando relés");
    } else if (command == "STOP") {
      for (int i = 0; i < 3; i++) {
        digitalWrite(relayPins[i], LOW); // Desactivar todos los relés
      }
      Serial.println("Desactivando relés");
    }
  }
}


