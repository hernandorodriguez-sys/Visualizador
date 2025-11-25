#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_adc/adc_oneshot.h"
#include <math.h>
#include <string.h>

#define SAMPLE_RATE_HZ 2000  // 2000 Hz para mejor resolución
#define UART_PORT UART_NUM_0
#define BUF_SIZE 1024
#define ADC_CHANNEL ADC_CHANNEL_3  // GPIO39

// --- Pines del multiplexor CD4052 (2 bits de control) ---
#define MUX_PIN_A GPIO_NUM_25   // Pin A del multiplexor
#define MUX_PIN_B GPIO_NUM_26   // Pin B del multiplexor

// --- Derivaciones del ECG (4 derivaciones) ---
typedef enum {
    LEAD_DI = 0,    // A=0, B=0
    LEAD_DII = 1,   // A=0, B=1
    LEAD_DIII = 2,  // A=1, B=0
    LEAD_AVR = 3    // A=1, B=1
} ecg_lead_t;

// Configuración del multiplexor (A, B)
typedef struct {
    uint8_t pinA;
    uint8_t pinB;
} MuxConfig;

static const MuxConfig leadConfigs[4] = {
    {0, 0},  // DI:   A=0, B=0 → Y0
    {0, 1},  // DII:  A=0, B=1 → Y1
    {1, 0},  // DIII: A=1, B=0 → Y2
    {1, 1}   // aVR:  A=1, B=1 → Y3
};

static const char* leadNames[4] = {"DI", "DII", "DIII", "aVR"};

// --- Variables globales ---
static QueueHandle_t adc_queue;
static adc_oneshot_unit_handle_t adc_handle;
static ecg_lead_t current_lead = LEAD_DI;
static uint64_t last_lead_switch_time = 0;
static const uint32_t LEAD_SWITCH_INTERVAL_MS = 8000; // 8 segundos

// --- Inicializar pines del multiplexor CD4052 ---
void mux_init(void) {
    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_DISABLE,
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = (1ULL << MUX_PIN_A) | (1ULL << MUX_PIN_B),
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
    };
    gpio_config(&io_conf);
    
    // Inicializar en derivación DI (A=0, B=0)
    gpio_set_level(MUX_PIN_A, 0);
    gpio_set_level(MUX_PIN_B, 0);
    
    printf("Multiplexor CD4052 inicializado:\n");
    printf("  Pin A (GPIO25) = 0\n");
    printf("  Pin B (GPIO26) = 0\n");
    printf("  Derivacion inicial: DI\n");
}

// --- Seleccionar derivación del multiplexor CD4052 ---
void mux_select_lead(ecg_lead_t lead) {
    if (lead >= 4) return;  // Validación (4 derivaciones)
    
    MuxConfig config = leadConfigs[lead];
    gpio_set_level(MUX_PIN_A, config.pinA);
    gpio_set_level(MUX_PIN_B, config.pinB);
    
    // Pequeño delay para estabilización
    vTaskDelay(pdMS_TO_TICKS(2));
    
    // Verificar configuración
    int readA = gpio_get_level(MUX_PIN_A);
    int readB = gpio_get_level(MUX_PIN_B);
    
    printf("\n========================================\n");
    printf(">>> CAMBIO DE DERIVACION <<<\n");
    printf("Derivacion: %s\n", leadNames[lead]);
    printf("Configuracion: A=%d, B=%d\n", config.pinA, config.pinB);
    printf("Verificacion: GPIO25=%d, GPIO26=%d\n", readA, readB);
    printf("========================================\n\n");
    
    // Notificar a Python sobre el cambio
    char msg[64];
    snprintf(msg, sizeof(msg), "LEAD_CHANGE:%d,%s\n", lead, leadNames[lead]);
    uart_write_bytes(UART_PORT, msg, strlen(msg));
}

// --- Cambiar derivación automáticamente ---
void switch_lead_automatic(void) {
    uint64_t current_time = esp_timer_get_time() / 1000; // convertir a ms
    
    if (current_time - last_lead_switch_time >= LEAD_SWITCH_INTERVAL_MS) {
        // Cambiar a la siguiente derivación (ciclo de 4 derivaciones)
        current_lead = (ecg_lead_t)((current_lead + 1) % 4);
        mux_select_lead(current_lead);
        last_lead_switch_time = current_time;
    }
}

// --- Procesar comandos UART (opcional - para cambio manual desde Python) ---
void process_uart_command(void) {
    uint8_t data[BUF_SIZE];
    int length = uart_read_bytes(UART_PORT, data, BUF_SIZE, 0);
    
    if (length > 0) {
        data[length] = '\0'; // null terminate
        
        if (strstr((char*)data, "LEAD_DI")) {
            current_lead = LEAD_DI;
            mux_select_lead(current_lead);
            last_lead_switch_time = esp_timer_get_time() / 1000;
        }
        else if (strstr((char*)data, "LEAD_DII")) {
            current_lead = LEAD_DII;
            mux_select_lead(current_lead);
            last_lead_switch_time = esp_timer_get_time() / 1000;
        }
        else if (strstr((char*)data, "LEAD_DIII")) {
            current_lead = LEAD_DIII;
            mux_select_lead(current_lead);
            last_lead_switch_time = esp_timer_get_time() / 1000;
        }
        else if (strstr((char*)data, "LEAD_AVR")) {
            current_lead = LEAD_AVR;
            mux_select_lead(current_lead);
            last_lead_switch_time = esp_timer_get_time() / 1000;
        }
    }
}

// --- Timer callback para lectura ADC (SIN FILTROS - SEÑAL CRUDA) ---
static void IRAM_ATTR timer_callback(void* arg) {
    int raw = 0;
    adc_oneshot_read(adc_handle, ADC_CHANNEL, &raw);
    xQueueSendFromISR(adc_queue, &raw, NULL);
}

// --- Tarea UART (SIN FILTRADO - Transmite señal ADC directa) ---
void serial_task(void* pvParameters) {
    int val;
    uint8_t pkt[4];
    
    // Acumular 4 lecturas para promediar (reduce ruido sin filtrar)
    int samples[4];
    int sample_idx = 0;

    while (1) {
        if (xQueueReceive(adc_queue, &val, portMAX_DELAY)) {
            samples[sample_idx++] = val;
            
            // Cuando tengamos 4 muestras, promediar y enviar
            if (sample_idx >= 4) {
                int avg = (samples[0] + samples[1] + samples[2] + samples[3]) / 4;
                sample_idx = 0;
                
                // Empaquetar datos (valor ADC de 12 bits directo)
                pkt[0] = 0xAA;                  // start byte
                pkt[1] = avg & 0xFF;            // LSB
                pkt[2] = (avg >> 8) & 0xFF;     // MSB
                pkt[3] = pkt[0] ^ pkt[1] ^ pkt[2];  // checksum

                uart_write_bytes(UART_PORT, (const char*)pkt, 4);
            }
        }
    }
}

// --- Tarea para manejo del multiplexor ---
void mux_task(void* pvParameters) {
    while (1) {
        // Cambio automático de derivaciones cada 8 segundos
        switch_lead_automatic();
        
        // Procesar comandos UART (opcional para control manual)
        process_uart_command();
        
        // Esperar 100ms antes de la siguiente verificación
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void app_main(void) {
    printf("\n==========================================\n");
    printf("ESP32 - SISTEMA ECG 4 DERIVACIONES (SEÑAL CRUDA)\n");
    printf("==========================================\n");
    
    // --- Inicializar multiplexor CD4052 ---
    mux_init();
    
    // --- Inicializar ADC OneShot ---
    adc_oneshot_unit_init_cfg_t init_config = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    adc_oneshot_new_unit(&init_config, &adc_handle);

    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_12,
        .atten = ADC_ATTEN_DB_12,  // 0-3.3V
    };
    adc_oneshot_config_channel(adc_handle, ADC_CHANNEL, &config);

    // --- Inicializar UART ---
    const uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_driver_install(UART_PORT, BUF_SIZE, 0, 0, NULL, 0);
    uart_param_config(UART_PORT, &uart_config);

    // --- Crear Queue ---
    adc_queue = xQueueCreate(200, sizeof(int));

    // --- Inicializar tiempo para cambio de derivaciones ---
    last_lead_switch_time = esp_timer_get_time() / 1000;

    // --- Crear Timer para muestreo ADC a 2000 Hz ---
    const esp_timer_create_args_t periodic_timer_args = {
        .callback = &timer_callback,
        .name = "adc_timer"
    };
    esp_timer_handle_t periodic_timer;
    esp_timer_create(&periodic_timer_args, &periodic_timer);
    esp_timer_start_periodic(periodic_timer, 1000000 / SAMPLE_RATE_HZ); // µs

    // --- Crear tareas ---
    xTaskCreatePinnedToCore(serial_task, "serial_task", 4096, NULL, 5, NULL, 1);
    xTaskCreatePinnedToCore(mux_task, "mux_task", 2048, NULL, 4, NULL, 0);
    
    printf("\nSistema iniciado correctamente\n");
    printf("Frecuencia de muestreo: %d Hz\n", SAMPLE_RATE_HZ);
    printf("Derivaciones: %s, %s, %s, %s\n", 
           leadNames[0], leadNames[1], leadNames[2], leadNames[3]);
    printf("Intervalo de cambio: %lu segundos\n", LEAD_SWITCH_INTERVAL_MS/1000);
    printf("NOTA: Transmitiendo señal ADC CRUDA (sin filtros)\n");
    printf("==========================================\n\n");
}


