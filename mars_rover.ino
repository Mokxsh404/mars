#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <DHT.h>
#include <SPI.h>
#include <SoftwareSerial.h>

// Custom ST7735 16-bit RGB565 Color Definitions
#ifndef ST7735_DARKGREEN
#define ST7735_DARKGREEN 0x03E0
#endif
#ifndef ST7735_DARKGREY
#define ST7735_DARKGREY  0x7BEF
#endif

// ================================================================
// PIN DEFINITIONS & MODULE SETUP
// ================================================================

// HC-05 Bluetooth Module (SoftwareSerial)
// D4 = Arduino RX (connect to HC-05 TX)
// D10 = Arduino TX (connect to HC-05 RX)
SoftwareSerial BT(4, 10);

// L298N Motor Driver Pins
#define ENA 5
#define ENB 3
#define IN1 7
#define IN2 6
#define IN3 8
#define IN4 9

// Environmental & Water Sensors Pins
#define DHTPIN 2
#define DHTTYPE DHT11
#define MQ135_PIN A0
#define TURBIDITY_PIN A1
#define TDS_PIN A2

// ST7735 1.8" Color TFT Display Pins
#define TFT_CS A4
#define TFT_DC 12
#define TFT_RST A5
// SCK is fixed to D13 (Hardware SPI)
// SDA/MOSI is fixed to D11 (Hardware SPI)

DHT dht(DHTPIN, DHTTYPE);
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

// ================================================================
// GLOBAL VARIABLES
// ================================================================
char currentCommand = 'S';
String roverStateStr = "STOPPED";

// Sensor Data Cache
float humidity = 0.0;
float temperature = 0.0;
int mq135Value = 0;
int turbidityValue = 0;
int tdsValue = 0;
bool dhtError = false;

// Non-blocking Timer Constants & State Variables
unsigned long lastPageChangeTime = 0;
const unsigned long PAGE_INTERVAL =
    2000; // Screen updates/switches every 2000 ms (2 seconds)
uint8_t currentPage = 0;
const uint8_t TOTAL_PAGES = 3;

unsigned long lastSensorReadTime = 0;
const unsigned long SENSOR_INTERVAL = 1000; // Read sensors every 1 second

// Function Declarations
void forward();
void backward();
void left();
void right();
void stopMotor();
void readSensors();
void updateDisplay();
void drawPageOverview();
void drawPageEnvironment();
void drawPageWaterQuality();

// ================================================================
// SETUP
// ================================================================
void setup() {
  Serial.begin(9600);
  BT.begin(9600);

  // Motor Driver Control Pins Initialization
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  analogWrite(ENA, 255); // Full Speed Enable (PWM)
  analogWrite(ENB, 255);
  stopMotor();

  // Sensor Initialization
  dht.begin();

  // ST7735 TFT Initialization
  tft.initR(INITR_BLACKTAB); // ST7735 screen init
  tft.setRotation(1);        // Landscape orientation (160x128)
  tft.fillScreen(ST7735_BLACK);

  // Startup Screen
  tft.setTextColor(ST7735_CYAN);
  tft.setTextSize(2);
  tft.setCursor(10, 30);
  tft.println("MARS ROVER");
  tft.setTextColor(ST7735_WHITE);
  tft.setTextSize(1);
  tft.setCursor(15, 65);
  tft.println("Initializing System...");
  delay(1500);

  tft.fillScreen(ST7735_BLACK);
  updateDisplay(); // Draw initial page immediately

  Serial.println("=== Mars Environmental Rover Initialized ===");
}

// ================================================================
// MAIN LOOP (NON-BLOCKING)
// ================================================================
void loop() {
  // 1. Bluetooth Mobility Control
  if (BT.available()) {
    currentCommand = BT.read();

    Serial.print("Command: ");
    Serial.println(currentCommand);

    switch (currentCommand) {
      case 'F':
        forward();
        roverStateStr = "FORWARD";
        break;

      case 'B':
        backward();
        roverStateStr = "BACKWARD";
        break;

      case 'L':
        left();
        roverStateStr = "TURN LEFT";
        break;

      case 'R':
        right();
        roverStateStr = "TURN RIGHT";
        break;

      case 'S':
        stopMotor();
        roverStateStr = "STOPPED";
        break;
    }
  }

  // 2. Periodic Sensor Telemetry Read (Every 1 Second)
  if (millis() - lastSensorReadTime >= SENSOR_INTERVAL) {
    lastSensorReadTime = millis();
    readSensors();
  }

  // 3. Screen Auto-Switching Carousel (Every 2 Seconds)
  if (millis() - lastPageChangeTime >= PAGE_INTERVAL) {
    lastPageChangeTime = millis();
    currentPage = (currentPage + 1) % TOTAL_PAGES;
    updateDisplay();
  }
}

// ================================================================
// TELEMETRY / SENSOR READING
// ================================================================
void readSensors() {
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  mq135Value = analogRead(MQ135_PIN);
  turbidityValue = analogRead(TURBIDITY_PIN);
  tdsValue = analogRead(TDS_PIN);

  dhtError = (isnan(humidity) || isnan(temperature));

  // Print to USB Serial Monitor
  Serial.println("--------------------------------");
  if (dhtError) {
    Serial.println("DHT11 Error!");
  } else {
    Serial.print("Temperature : ");
    Serial.print(temperature);
    Serial.println(" C");

    Serial.print("Humidity    : ");
    Serial.print(humidity);
    Serial.println(" %");
  }

  Serial.print("MQ135       : ");
  Serial.println(mq135Value);

  Serial.print("Turbidity   : ");
  Serial.println(turbidityValue);

  Serial.print("TDS         : ");
  Serial.println(tdsValue);

  // Transmit wirelessly over Bluetooth (HC-05) to Laptop Python GUI
  BT.println("--------------------------------");
  if (dhtError) {
    BT.println("DHT11 Error!");
  } else {
    BT.print("Temperature : ");
    BT.print(temperature);
    BT.println(" C");

    BT.print("Humidity    : ");
    BT.print(humidity);
    BT.println(" %");
  }

  BT.print("MQ135       : ");
  BT.println(mq135Value);

  BT.print("Turbidity   : ");
  BT.println(turbidityValue);

  BT.print("TDS         : ");
  BT.println(tdsValue);
}

// ================================================================
// ST7735 TFT DISPLAY PAGES (CAROUSEL)
// ================================================================
void updateDisplay() {
  tft.fillScreen(ST7735_BLACK);

  switch (currentPage) {
  case 0:
    drawPageOverview();
    break;
  case 1:
    drawPageEnvironment();
    break;
  case 2:
    drawPageWaterQuality();
    break;
  }
}

// Page 1: Rover Status & Quick Telemetry
void drawPageOverview() {
  // Title Banner
  tft.fillRect(0, 0, 160, 18, ST7735_BLUE);
  tft.setTextColor(ST7735_WHITE);
  tft.setTextSize(1);
  tft.setCursor(12, 5);
  tft.print("PAGE 1/3: ROVER STATUS");

  // Rover Motion Status
  tft.setCursor(5, 26);
  tft.setTextColor(ST7735_YELLOW);
  tft.print("State   : ");
  tft.setTextColor(ST7735_GREEN);
  tft.println(roverStateStr);

  tft.setCursor(5, 40);
  tft.setTextColor(ST7735_YELLOW);
  tft.print("BT Cmd  : ");
  tft.setTextColor(ST7735_WHITE);
  tft.println(currentCommand);

  // Horizontal Divider Line
  tft.drawFastHLine(5, 55, 150, ST7735_WHITE);

  // Telemetry Snapshot
  tft.setCursor(5, 64);
  tft.setTextColor(ST7735_CYAN);
  tft.print("Temp    : ");
  if (dhtError)
    tft.print("ERR");
  else {
    tft.print(temperature, 1);
    tft.print(" C");
  }

  tft.setCursor(5, 78);
  tft.setTextColor(ST7735_CYAN);
  tft.print("Humidity: ");
  if (dhtError)
    tft.print("ERR");
  else {
    tft.print(humidity, 1);
    tft.print(" %");
  }

  tft.setCursor(5, 92);
  tft.setTextColor(ST7735_MAGENTA);
  tft.print("Air Qual: ");
  tft.print(mq135Value);
}

// Page 2: Air Quality & Climate Details
void drawPageEnvironment() {
  // Title Banner
  tft.fillRect(0, 0, 160, 18, ST7735_DARKGREEN);
  tft.setTextColor(ST7735_WHITE);
  tft.setTextSize(1);
  tft.setCursor(10, 5);
  tft.print("PAGE 2/3: ENVIRONMENT");

  // Temperature
  tft.setCursor(5, 26);
  tft.setTextColor(ST7735_YELLOW);
  tft.print("Temperature : ");
  tft.setTextColor(ST7735_WHITE);
  if (dhtError)
    tft.println("DHT Error");
  else {
    tft.print(temperature);
    tft.println(" C");
  }

  // Humidity
  tft.setCursor(5, 45);
  tft.setTextColor(ST7735_YELLOW);
  tft.print("Humidity    : ");
  tft.setTextColor(ST7735_WHITE);
  if (dhtError)
    tft.println("DHT Error");
  else {
    tft.print(humidity);
    tft.println(" %");
  }

  // MQ135 Air Quality Sensor
  tft.setCursor(5, 64);
  tft.setTextColor(ST7735_YELLOW);
  tft.print("MQ135 Air Q : ");
  tft.setTextColor(ST7735_GREEN);
  tft.println(mq135Value);

  // Air Quality Rating
  tft.setCursor(5, 88);
  tft.setTextColor(ST7735_CYAN);
  tft.print("Air Rating  : ");
  if (mq135Value < 300) {
    tft.setTextColor(ST7735_GREEN);
    tft.print("GOOD");
  } else if (mq135Value < 600) {
    tft.setTextColor(ST7735_YELLOW);
    tft.print("MODERATE");
  } else {
    tft.setTextColor(ST7735_RED);
    tft.print("POOR");
  }
}

// Page 3: Water Quality Details
void drawPageWaterQuality() {
  // Title Banner
  tft.fillRect(0, 0, 160, 18, ST7735_MAGENTA);
  tft.setTextColor(ST7735_WHITE);
  tft.setTextSize(1);
  tft.setCursor(10, 5);
  tft.print("PAGE 3/3: WATER QUALITY");

  // Turbidity Sensor Reading
  tft.setCursor(5, 30);
  tft.setTextColor(ST7735_YELLOW);
  tft.print("Turbidity Raw : ");
  tft.setTextColor(ST7735_WHITE);
  tft.println(turbidityValue);

  // TDS Sensor Reading
  tft.setCursor(5, 55);
  tft.setTextColor(ST7735_YELLOW);
  tft.print("TDS Raw Value : ");
  tft.setTextColor(ST7735_WHITE);
  tft.println(tdsValue);

  tft.drawFastHLine(5, 80, 150, ST7735_WHITE);

  tft.setCursor(5, 92);
  tft.setTextColor(ST7735_GREEN);
  tft.print("Sensors Online & Active");
}

// ================================================================
// MOTOR MOBILITY CONTROL FUNCTIONS
// ================================================================
void forward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void backward() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void left() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void right() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void stopMotor() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}
