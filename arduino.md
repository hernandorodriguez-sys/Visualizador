// Relés de carga
#define RL_STEPUP 4
#define RL_DIODE  5
#define RL_TO_H   8

// Relés bifásica (ADICIONALES)
#define RL_LEFT   10
#define RL_RIGHT  11

#define PWM_PIN 9

// Botones
#define BTN_CARGA     2
#define BTN_DESCARGA  3

// Sensado
#define DIV_FACTOR 11.0
#define V_TARGET_HIGH 25.0
#define V_RESTART      3.0

// Parámetros bifásica
#define T_ON_MS    50
#define DEAD_MS    10      // ← Reducido a 5ms
#define CYCLES_MAX  20
#define ADC_SAMPLES 2 

// Estados
bool cargando = false;
bool descargando = false;
bool esperandoDescarga = false;

// -----------------------------------------------
void enablePWM() {
  pinMode(PWM_PIN, OUTPUT);
  TCCR1A = (1 << COM1A1) | (1 << WGM11);
  TCCR1B = (1 << WGM13) | (1 << WGM12) | (1 << CS10);
  ICR1 = 511;
  OCR1A = 256;
}

void disablePWM() {
  TCCR1A &= ~(1 << COM1A1);
  digitalWrite(PWM_PIN, LOW);
}

// -----------------------------------------------
float readVcap() {
  uint32_t acc = 0;
  for (int i=0; i<ADC_SAMPLES; i++) {
    acc += analogRead(A0);
  }
  float avg = acc / (float)ADC_SAMPLES;
  float Va0 = avg * (5.0/1023.0);
  return Va0 * DIV_FACTOR;
}

// -----------------------------------------------
void iniciarCarga() {
  Serial.println("");
  Serial.println("====================================");
  Serial.println(">>> INICIANDO CARGA <<<");
  Serial.println("====================================");
  
  cargando = true;
  descargando = false;
  esperandoDescarga = false;
  
  digitalWrite(RL_STEPUP, HIGH);
  digitalWrite(RL_DIODE, HIGH);
  enablePWM();
  
  Serial.println("RL_STEPUP: HIGH");
  Serial.println("RL_DIODE: HIGH");
  Serial.println("PWM: ON");
}

// -----------------------------------------------
void detenerCarga() {
  Serial.println("");
  Serial.println(">>> DETENIENDO CARGA <<<");
  
  disablePWM();
  digitalWrite(RL_STEPUP, LOW);
  digitalWrite(RL_DIODE, LOW);
  
  cargando = false;
  esperandoDescarga = true;
  
  Serial.println("Sistema de carga: OFF");
  Serial.println("");
  Serial.println("*** ESPERANDO BOTON DESCARGA ***");
  Serial.println("Presiona boton pin 3 para descargar");
  Serial.println("");
}

// -----------------------------------------------
void descargaBifasica() {
  Serial.println("");
  Serial.println("====================================");
  Serial.println(">>> INICIANDO DESCARGA BIFÁSICA <<<");
  Serial.println("====================================");
  
  descargando = true;
  esperandoDescarga = false;
  
  digitalWrite(RL_LEFT, LOW);
  digitalWrite(RL_RIGHT, LOW);
  delay(20);
  
  Serial.println("Conectando RL_TO_H...");
  digitalWrite(RL_TO_H, HIGH);
  delay(20);
  
  float Vcap_inicial = readVcap();
  Serial.print("Vcap inicial: ");
  Serial.print(Vcap_inicial);
  Serial.println(" V");
  Serial.println("");
  
  for (unsigned int cycle = 0; cycle < CYCLES_MAX; cycle++) {
    
    float Vcap = readVcap();
    Serial.print("Ciclo ");
    Serial.print(cycle + 1);
    Serial.print("/");
    Serial.print(CYCLES_MAX);
    Serial.print(" - Vcap: ");
    Serial.print(Vcap);
    Serial.println(" V");
    
    if (Vcap <= V_RESTART) {
      Serial.println("*** Vcap <= 3V - Descarga completa ***");
      break;
    }
    
    // === FASE A ===
    Serial.println("  FASE A: LEFT ON");
    digitalWrite(RL_LEFT, HIGH);
    digitalWrite(RL_RIGHT, LOW);
    delay(T_ON_MS);
    digitalWrite(RL_LEFT, LOW);
    delay(DEAD_MS);
    
    Vcap = readVcap();
    Serial.print("    Después fase A: ");
    Serial.print(Vcap);
    Serial.println(" V");
    
    if (Vcap <= V_RESTART) {
      Serial.println("*** Vcap <= 3V - Descarga completa ***");
      break;
    }
    
    // === FASE B ===
    Serial.println("  FASE B: RIGHT ON");
    digitalWrite(RL_RIGHT, HIGH);
    digitalWrite(RL_LEFT, LOW);
    delay(T_ON_MS);
    digitalWrite(RL_RIGHT, LOW);
    delay(DEAD_MS);
    
    Vcap = readVcap();
    Serial.print("    Después fase B: ");
    Serial.print(Vcap);
    Serial.println(" V");
    Serial.println("");
  }
  
  float Vcap_final = readVcap();
  Serial.print("Vcap final después bifásica: ");
  Serial.print(Vcap_final);
  Serial.println(" V");
  
  if (Vcap_final > V_RESTART) {
    Serial.println(">>> Descarga adicional...");
    digitalWrite(RL_LEFT, HIGH);
    
    unsigned long tStart = millis();
    while ((millis() - tStart) < 3000 && Vcap_final > V_RESTART) {
      Vcap_final = readVcap();
      Serial.print("  Descargando: ");
      Serial.print(Vcap_final);
      Serial.println(" V");
      delay(100);
    }
    
    digitalWrite(RL_LEFT, LOW);
  }
  
  digitalWrite(RL_LEFT, LOW);
  digitalWrite(RL_RIGHT, LOW);
  delay(10);
  digitalWrite(RL_TO_H, LOW);
  
  descargando = false;
  
  Serial.println("");
  Serial.println("====================================");
  Serial.println(">>> DESCARGA COMPLETADA <<<");
  Serial.print("Voltaje final: ");
  Serial.print(Vcap_final);
  Serial.println(" V");
  Serial.println("====================================");
  Serial.println("");
  Serial.println("Presiona boton CARGA (pin 2) para nuevo ciclo");
  Serial.println("");
}

// -----------------------------------------------
void setup() {
  Serial.begin(9600);
  delay(500);
  
  Serial.println("====================================");
  Serial.println("=== SISTEMA CON DOS BOTONES ===");
  Serial.println("====================================");

  pinMode(RL_STEPUP, OUTPUT);
  pinMode(RL_DIODE, OUTPUT);
  pinMode(RL_TO_H, OUTPUT);
  pinMode(RL_LEFT, OUTPUT);
  pinMode(RL_RIGHT, OUTPUT);

  digitalWrite(RL_STEPUP, LOW);
  digitalWrite(RL_DIODE, LOW);
  digitalWrite(RL_TO_H, LOW);
  digitalWrite(RL_LEFT, LOW);
  digitalWrite(RL_RIGHT, LOW);
  
  pinMode(BTN_CARGA, INPUT_PULLUP);
  pinMode(BTN_DESCARGA, INPUT_PULLUP);
  
  Serial.println("Sistema listo");
  Serial.println("Boton CARGA: Pin 2 a GND");
  Serial.println("Boton DESCARGA: Pin 3 a GND");
  Serial.println("");
  Serial.println("Presiona boton CARGA para iniciar");
  Serial.println("====================================");
  Serial.println("");
}

// -----------------------------------------------
void loop() {
  
  // BOTÓN DE CARGA
  if (digitalRead(BTN_CARGA) == LOW && !cargando && !descargando && !esperandoDescarga) {
    delay(50);
    if (digitalRead(BTN_CARGA) == LOW) {
      Serial.println("*** BOTON CARGA PRESIONADO ***");
      while(digitalRead(BTN_CARGA) == LOW) delay(10);
      iniciarCarga();
    }
  }
  
  // MONITOREO DE CARGA
  if (cargando) {
    float Vcap = readVcap();
    Serial.print("Cargando: ");
    Serial.print(Vcap);
    Serial.println(" V");
    
    if (Vcap >= V_TARGET_HIGH) {
      delay(100);
      float Vcap2 = readVcap();
      delay(100);
      float Vcap3 = readVcap();
      
      if (Vcap2 >= V_TARGET_HIGH && Vcap3 >= V_TARGET_HIGH) {
        Serial.println("");
        Serial.println("*** 25V ALCANZADO (CONFIRMADO) ***");
        Serial.print("Voltaje final de carga: ");
        Serial.print(Vcap3);
        Serial.println(" V");
        
        detenerCarga();
      }
    }
    
    delay(200);
  }
  
  // BOTÓN DE DESCARGA
  if (digitalRead(BTN_DESCARGA) == LOW && esperandoDescarga && !descargando) {
    delay(50);
    if (digitalRead(BTN_DESCARGA) == LOW) {
      Serial.println("*** BOTON DESCARGA PRESIONADO ***");
      while(digitalRead(BTN_DESCARGA) == LOW) delay(10);
      
      float Vcap = readVcap();
      if (Vcap < 5.0) {
        Serial.println("ERROR: Voltaje muy bajo");
        Serial.print("Vcap: ");
        Serial.print(Vcap);
        Serial.println(" V");
        Serial.println("Presiona boton CARGA primero");
        esperandoDescarga = false;
      } else {
        descargaBifasica();
      }
    }
  }
  
  if (!cargando && !descargando) {
    delay(50);
  }
}