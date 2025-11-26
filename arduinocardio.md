#include <TimerOne.h>

// ===================== Protocolo Serial y Comandos =====================
#define CMD_TRIGGER         0x01
#define CMD_CHARGE          'C'
#define CMD_DISCHARGE_POS   'P'
#define CMD_DISCHARGE_NEG   'N'
#define CMD_MUX_0           '0'
#define CMD_MUX_1           '1'
#define CMD_MUX_2           '2'
#define CMD_MUX_3           '3'
#define CMD_MUX_START       'S'
#define CMD_MUX_STOP        'X'

// ===================== Pines Relés =====================
#define PIN_RELAY_CHARGE      2
#define PIN_RELAY_DISCHARGE   3
#define PIN_RELAY_POL_POS     4
#define PIN_RELAY_POL_NEG     5

// ===================== Pines ADC =====================
#define PIN_ADC_CHARGE        A0
#define PIN_ADC_DISCHARGE_POS A1
#define PIN_ADC_DISCHARGE_NEG A2

// ===================== Pines MUX =====================
#define PIN_MUX_S0            6
#define PIN_MUX_S1            7

// ===================== Parámetros Cardioversor =====================
static const float R_SHUNT = 0.1f;
static const float K_DIV_CHARGE = 0.122f;
static const float V_AREF = 5.0f;
static const uint16_t ADC_MAX = 1023;
static const float ADC_ATTENUATION = 5.0f;
static const float C_CAP = 470e-6f;

static float g_target_percent_pos = 50.0f;
static float g_target_percent_neg = 35.0f;
static const float MIN_RESERVE_PERCENT = 15.0f;

static float g_target_vcap_V = 20.0f;

static volatile float g_E_total_J = 0.0f;
static volatile float g_target_energy_pos_J = 0.0f;
static volatile float g_target_energy_neg_J = 0.0f;

static const uint32_t DISCH_POS_MS = 40;
static const uint32_t DISCH_NEG_MS = 40;
static const uint32_t SAFE_MS = 1;
static const uint32_t CHARGE_TIMEOUT_MS = 4000;
static const uint32_t REFRACT_MS = 200;

// ===================== FSM Estados =====================
enum DefibState {
  DEFIB_IDLE,
  DEFIB_CHARGING,
  DEFIB_ARMED,
  DEFIB_DISCHARGING_POS,
  DEFIB_DISCHARGING_NEG,
  DEFIB_SAFE,
  DEFIB_REFRACT
};

static volatile DefibState g_state = DEFIB_IDLE;
static volatile bool g_triggerBusy = false;
static volatile uint32_t g_phaseStartMs = 0;
static volatile uint32_t g_chargeStartMs = 0;
static volatile uint32_t g_refractStartMs = 0;

static volatile float g_energy_pos_J = 0.0f;
static volatile float g_energy_neg_J = 0.0f;

// ===================== ADC Timer =====================
static const unsigned long ADC_SAMPLE_PERIOD_US = 1000; // 1 kHz
static volatile bool g_adc_timer_active = false;
static volatile uint16_t g_last_vcap_counts = 0;
static uint32_t g_last_adc_us = 0;
static float g_P_prev = 0.0f;

// ===================== MUX Estado =====================
static volatile uint8_t g_mux_state = 0;
static volatile bool g_mux_auto = false;
static volatile uint32_t g_mux_auto_ms = 3000;
static volatile uint32_t g_mux_last_switch = 0;

// ===================== Utilidades ADC/Energía =====================
static inline float adc_to_volts(uint16_t counts) {
  return (counts / (float)ADC_MAX) * V_AREF * ADC_ATTENUATION;
}
static inline float adc_to_vcap(uint16_t counts) {
  float vadc = (counts / (float)ADC_MAX) * V_AREF;
  return vadc / K_DIV_CHARGE;
}
static inline float capacitor_energy(float vcap) {
  return 0.5f * C_CAP * vcap * vcap;
}

// ===================== ISR Timer ADC =====================
void adc_timer_isr() {
  if (!g_adc_timer_active) return;

  uint32_t now_us = micros();
  float dt = (g_last_adc_us == 0) ? 0.001f : (now_us - g_last_adc_us) * 1e-6f; // seconds
  g_last_adc_us = now_us;

  uint16_t adc_val = 0;
  float volts = 0.0f;

  if (g_state == DEFIB_DISCHARGING_POS) {
    adc_val = analogRead(PIN_ADC_DISCHARGE_POS);
    volts = adc_to_volts(adc_val);
    float I = volts / 10.0f;
    float P = volts * I;
    g_energy_pos_J += 0.5f * (g_P_prev + P) * dt;
    g_P_prev = P;

    Serial.print("T:");
    Serial.print(now_us);
    Serial.print(",POS:");
    Serial.print(volts, 4);
    Serial.print(",I:");
    Serial.print(I, 4);
    Serial.print(",E+:");
    Serial.println(g_energy_pos_J, 5);

  } else if (g_state == DEFIB_DISCHARGING_NEG) {
    adc_val = analogRead(PIN_ADC_DISCHARGE_NEG);
    volts = adc_to_volts(adc_val);
    float I = volts / 10.0f;
    float P = volts * I;
    g_energy_neg_J += 0.5f * (g_P_prev + P) * dt;
    g_P_prev = P;

    Serial.print("T:");
    Serial.print(now_us);
    Serial.print(",NEG:");
    Serial.print(volts, 4);
    Serial.print(",I:");
    Serial.print(I, 4);
    Serial.print(",E-:");
    Serial.println(g_energy_neg_J, 5);

  } else {
    adc_val = analogRead(PIN_ADC_CHARGE);
    volts = adc_to_vcap(adc_val);
    Serial.print("T:");
    Serial.print(now_us);
    Serial.print(",VCAP:");
    Serial.println(volts, 4);
  }
}

// ===================== Control Relés =====================
static inline void set_all_relays_low() {
  digitalWrite(PIN_RELAY_CHARGE, LOW);
  digitalWrite(PIN_RELAY_DISCHARGE, LOW);
  digitalWrite(PIN_RELAY_POL_POS, LOW);
  digitalWrite(PIN_RELAY_POL_NEG, LOW);
}

// ===================== MUX Apply =====================
static inline void mux_apply(uint8_t state) {
  digitalWrite(PIN_MUX_S0, (state & 0x01) ? HIGH : LOW);
  digitalWrite(PIN_MUX_S1, (state & 0x02) ? HIGH : LOW);
  Serial.print("MUX=");
  switch(state) {
    case 0: Serial.println("I"); break;
    case 1: Serial.println("II"); break;
    case 2: Serial.println("III"); break;
    case 3: Serial.println("aVR"); break;
    default: Serial.println("?"); break;
  }
}

// ===================== FSM Cardioversor =====================
void fsm_step() {
  uint32_t now = millis();

  switch (g_state) {
    case DEFIB_IDLE:
      break;

    case DEFIB_CHARGING:
      digitalWrite(PIN_RELAY_CHARGE, HIGH);
      {
        uint16_t c = analogRead(PIN_ADC_CHARGE);
        g_last_vcap_counts = c;
        float vcap = adc_to_vcap(c);

        if (vcap >= g_target_vcap_V) {
          digitalWrite(PIN_RELAY_CHARGE, LOW);
          g_E_total_J = capacitor_energy(vcap);

          float total_percent = g_target_percent_pos + g_target_percent_neg;
          if (total_percent > (100.0f - MIN_RESERVE_PERCENT)) {
            Serial.println("[FSM] ERROR: Porcentajes exceden límite (deben sumar <85%)");
            set_all_relays_low();
            g_state = DEFIB_REFRACT;
            g_refractStartMs = now;
            g_triggerBusy = false;
            break;
          }

          g_target_energy_pos_J = g_E_total_J * (g_target_percent_pos / 100.0f);
          g_target_energy_neg_J = g_E_total_J * (g_target_percent_neg / 100.0f);

          Serial.print("[FSM] ARMED Vcap=");
          Serial.print(vcap, 2);
          Serial.print("V E_total=");
          Serial.print(g_E_total_J, 4);
          Serial.print("J E+_target=");
          Serial.print(g_target_energy_pos_J, 4);
          Serial.print("J (");
          Serial.print(g_target_percent_pos, 1);
          Serial.print("%) E-_target=");
          Serial.print(g_target_energy_neg_J, 4);
          Serial.print("J (");
          Serial.print(g_target_percent_neg, 1);
          Serial.println("%)");

          g_state = DEFIB_ARMED;
        } else if ((now - g_chargeStartMs) >= CHARGE_TIMEOUT_MS) {
          digitalWrite(PIN_RELAY_CHARGE, LOW);
          set_all_relays_low();
          g_state = DEFIB_REFRACT;
          g_refractStartMs = now;
          g_triggerBusy = false;
          Serial.println("[FSM] FAIL:CHARGE_TIMEOUT");
        }
      }
      break;

    case DEFIB_ARMED:
      // Wait for TRIGGER or direct serial commands to control discharge states
      break;

    case DEFIB_DISCHARGING_POS:
      if (g_energy_pos_J >= g_target_energy_pos_J || (now - g_phaseStartMs) >= DISCH_POS_MS) {
        digitalWrite(PIN_RELAY_DISCHARGE, LOW);
        float percent_delivered = (g_E_total_J > 0) ? (g_energy_pos_J / g_E_total_J * 100.0f) : 0.0f;
        Serial.print("[FSM] DISCH_POS end E=");
        Serial.print(g_energy_pos_J, 4);
        Serial.print("J (");
        Serial.print(percent_delivered, 1);
        Serial.println("% del total)");

        g_state = DEFIB_DISCHARGING_NEG;
        g_phaseStartMs = now;
        g_energy_neg_J = 0.0f;
        g_P_prev = 0.0f;
        g_last_adc_us = 0;

        digitalWrite(PIN_RELAY_POL_POS, LOW);
        delay(5);
        digitalWrite(PIN_RELAY_POL_NEG, HIGH);
        delay(5);
        digitalWrite(PIN_RELAY_DISCHARGE, HIGH);
        Serial.println("[FSM] DISCH_NEG start");
      }
      break;

    case DEFIB_DISCHARGING_NEG:
      if (g_energy_neg_J >= g_target_energy_neg_J || (now - g_phaseStartMs) >= DISCH_NEG_MS) {
        digitalWrite(PIN_RELAY_DISCHARGE, LOW);
        digitalWrite(PIN_RELAY_POL_NEG, LOW);
        g_adc_timer_active = false;

        float percent_delivered = (g_E_total_J > 0) ? (g_energy_neg_J / g_E_total_J * 100.0f) : 0.0f;
        float total_delivered = g_energy_pos_J + g_energy_neg_J;
        float total_percent = (g_E_total_J > 0) ? (total_delivered / g_E_total_J * 100.0f) : 0.0f;

        Serial.print("[FSM] DISCH_NEG end E=");
        Serial.print(g_energy_neg_J, 4);
        Serial.print("J (");
        Serial.print(percent_delivered, 1);
        Serial.println("% del total)");
        Serial.print("[FSM] Total entregado: ");
        Serial.print(total_delivered, 4);
        Serial.print("J (");
        Serial.print(total_percent, 1);
        Serial.print("% de ");
        Serial.print(g_E_total_J, 4);
        Serial.println("J)");

        g_state = DEFIB_SAFE;
        g_phaseStartMs = now;
        Serial.println("[FSM] SAFE");
      }
      break;

    case DEFIB_SAFE:
      if ((now - g_phaseStartMs) >= SAFE_MS) {
        set_all_relays_low();
        g_state = DEFIB_REFRACT;
        g_refractStartMs = now;
        g_triggerBusy = false;
        Serial.println("[FSM] SUCCESS -> REFRACT");
      }
      break;

    case DEFIB_REFRACT:
      if ((now - g_refractStartMs) >= REFRACT_MS) {
        g_state = DEFIB_IDLE;
        Serial.println("[FSM] IDLE");
      }
      break;
  }
}

// ===================== Parser Serial =====================
void handle_serial() {
  while (Serial.available() > 0) {
    uint8_t b = Serial.read();
    if (b == CMD_CHARGE) {
      if (g_state == DEFIB_IDLE) {
        g_triggerBusy = false;
        g_state = DEFIB_CHARGING;
        g_chargeStartMs = millis();
        g_energy_pos_J = 0.0f;
        g_energy_neg_J = 0.0f;
        set_all_relays_low();
        Serial.println("[CMD] CHARGE Direct");
      } else {
        Serial.println("[CMD] CHARGE rejected (not IDLE)");
      }
    }
    else if (b == CMD_DISCHARGE_POS) {
      if (g_state == DEFIB_ARMED) {
        g_state = DEFIB_DISCHARGING_POS;
        g_phaseStartMs = millis();
        g_energy_pos_J = 0.0f;
        g_P_prev = 0.0f;
        g_last_adc_us = 0;
        g_adc_timer_active = true;
        digitalWrite(PIN_RELAY_DISCHARGE, LOW);
        digitalWrite(PIN_RELAY_POL_POS, HIGH);
        digitalWrite(PIN_RELAY_POL_NEG, LOW);
        delay(5);
        digitalWrite(PIN_RELAY_DISCHARGE, HIGH);
        Serial.println("[CMD] DISCHARGE_POS Direct");
      }
    }
    else if (b == CMD_DISCHARGE_NEG) {
      if (g_state == DEFIB_ARMED || g_state == DEFIB_DISCHARGING_POS) {
        g_state = DEFIB_DISCHARGING_NEG;
        g_phaseStartMs = millis();
        g_energy_neg_J = 0.0f;
        g_P_prev = 0.0f;
        g_last_adc_us = 0;
        g_adc_timer_active = true;
        digitalWrite(PIN_RELAY_DISCHARGE, LOW);
        digitalWrite(PIN_RELAY_POL_POS, LOW);
        delay(5);
        digitalWrite(PIN_RELAY_POL_NEG, HIGH);
        delay(5);
        digitalWrite(PIN_RELAY_DISCHARGE, HIGH);
        Serial.println("[CMD] DISCHARGE_NEG Direct");
      }
    }
    else if (b == CMD_TRIGGER) {
      // Now trigger ONLY starts discharge if ARMED
      if (g_state == DEFIB_ARMED && !g_triggerBusy) {
        g_triggerBusy = true;
        g_state = DEFIB_DISCHARGING_POS;
        g_phaseStartMs = millis();
        g_energy_pos_J = 0.0f;
        g_P_prev = 0.0f;
        g_last_adc_us = 0;
        g_adc_timer_active = true;
        digitalWrite(PIN_RELAY_DISCHARGE, LOW);
        digitalWrite(PIN_RELAY_POL_POS, HIGH);
        digitalWrite(PIN_RELAY_POL_NEG, LOW);
        delay(5);
        digitalWrite(PIN_RELAY_DISCHARGE, HIGH);
        Serial.println("[CMD] TRIGGER->DISCHARGE");
      } else {
        Serial.println("[CMD] TRIGGER rejected (not ARMED)");
      }
    }
    else if (b == CMD_MUX_0) {
      g_mux_state = 0; g_mux_auto = false; mux_apply(g_mux_state);
    }
    else if (b == CMD_MUX_1) {
      g_mux_state = 1; g_mux_auto = false; mux_apply(g_mux_state);
    }
    else if (b == CMD_MUX_2) {
      g_mux_state = 2; g_mux_auto = false; mux_apply(g_mux_state);
    }
    else if (b == CMD_MUX_3) {
      g_mux_state = 3; g_mux_auto = false; mux_apply(g_mux_state);
    }
    else if (b == CMD_MUX_START) {
      g_mux_auto = true; g_mux_last_switch = millis(); Serial.println("[CMD] MUX AUTO ON");
    }
    else if (b == CMD_MUX_STOP) {
      g_mux_auto = false; Serial.println("[CMD] MUX AUTO OFF");
    }
  }
}

// ===================== MUX Auto =====================
void mux_auto_step() {
  if (!g_mux_auto) return;
  uint32_t now = millis();
  if ((now - g_mux_last_switch) >= g_mux_auto_ms) {
    g_mux_last_switch = now;
    g_mux_state = (g_mux_state + 1) % 4;
    mux_apply(g_mux_state);
  }
}

// ===================== Setup =====================
void setup() {
  Serial.begin(9600);
  analogReference(DEFAULT);

  pinMode(PIN_RELAY_CHARGE, OUTPUT);
  pinMode(PIN_RELAY_DISCHARGE, OUTPUT);
  pinMode(PIN_RELAY_POL_POS, OUTPUT);
  pinMode(PIN_RELAY_POL_NEG, OUTPUT);
  set_all_relays_low();

  pinMode(PIN_ADC_CHARGE, INPUT);
  pinMode(PIN_ADC_DISCHARGE_POS, INPUT);
  pinMode(PIN_ADC_DISCHARGE_NEG, INPUT);

  pinMode(PIN_MUX_S0, OUTPUT);
  pinMode(PIN_MUX_S1, OUTPUT);
  mux_apply(g_mux_state);

  Timer1.initialize(ADC_SAMPLE_PERIOD_US);
  Timer1.attachInterrupt(adc_timer_isr);

  Serial.println("READY");
  Serial.print("Config: Vcap_target=");
  Serial.print(g_target_vcap_V, 1);
  Serial.print("V E+%=");
  Serial.print(g_target_percent_pos, 1);
  Serial.print(" E-%=");
  Serial.println(g_target_percent_neg, 1);
}

// ===================== Loop =====================
void loop() {
  handle_serial();
  fsm_step();
  mux_auto_step();
  delay(1); // yield CPU, avoid lockup
}
