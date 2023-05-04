
#include <DHT.h>
#include <string.h>
#include <stdlib.h>
#include <Preferences.h>


#define DHTPIN 2
#define REDLEDPIN 12
#define GREENLEDPIN 14
#define LIGHTPIN 15
#define SERIALBUFLEN 200
#define SERIALARGLEN 16
#define NVSNAME "POITsensor"

Preferences NVS;
DHT dhtstruct(DHTPIN, DHT11);

int cycle;
int cyclesForReadings;
int greenLightLevel;
int redLedOut;
int redLedRise;
int redLedStep;
float redLedTemp;
float redLedHumid;
float curTemp;
float curHumid;
int curLight;
char serialInBuf[SERIALBUFLEN + 1];
char serialOutBuf[SERIALBUFLEN + 1];
char serialArg1[SERIALARGLEN + 1];
char serialArg2[SERIALARGLEN + 1];



void setup() {
  Serial.begin(9600);
  Serial.println("");
  Serial.println("ESP32 Started");

  redLedRise = 1;
  redLedOut = 0;
  redLedStep = 8;
  redLedTemp = 0;
  redLedHumid = 0;
  curTemp = 0;
  curHumid = 0;
  curLight = 0;
  cycle = 0;
  cyclesForReadings = 100;
  greenLightLevel = 700;

  dhtstruct.begin();
  pinMode(GREENLEDPIN, OUTPUT);
  ledcSetup(0, 5000, 8);
  ledcAttachPin(REDLEDPIN, 0);

  digitalWrite(GREENLEDPIN, redLedOut);
  ledcWrite(0, 0);

  memset(serialInBuf, 0, SERIALBUFLEN + 1);
  memset(serialOutBuf, 0, SERIALBUFLEN + 1);
  memset(serialArg1, 0, SERIALARGLEN + 1);
  memset(serialArg2, 0, SERIALARGLEN + 1);

  NVS.begin(NVSNAME, false);
  redLedStep = NVS.getInt("RLS", 8);
  NVS.putInt("RLS", redLedStep);
  redLedTemp = NVS.getFloat("RLT", 0);
  NVS.putFloat("RLT", redLedTemp);
  redLedHumid = NVS.getFloat("RLH", 0);
  NVS.putFloat("RLH", redLedHumid);
  cyclesForReadings = NVS.getInt("CFR", 100);
  NVS.putInt("CFR", cyclesForReadings);
  greenLightLevel = NVS.getInt("GLL", 700);
  NVS.putInt("GLL", greenLightLevel);
  NVS.end();
}

void loop() {
  if (cycle >= cyclesForReadings) {
    cycle = 0;
    getEnviroReadings();
    readSerial();
  } else {
    cycle++;
  }
  redLed();
  delay(20);
}

void getEnviroReadings() {
  curTemp = dhtstruct.readTemperature();
  curHumid = dhtstruct.readHumidity();
  curLight = analogRead(LIGHTPIN);

  /*
  Serial.print("Temperature: ");
  Serial.println(curTemp);
  Serial.print("Humidity: ");
  Serial.println(curHumid);
  Serial.print("Light: ");
  Serial.println(curLight);
  Serial.println("");
  */

  memset(serialOutBuf, 0, SERIALBUFLEN + 1);
  sprintf(serialOutBuf, "++TMP:%f;HUM:%f;LIG:%d+", curTemp, curHumid, curLight);
  Serial.println(serialOutBuf);

  if (curLight < greenLightLevel) {
    digitalWrite(GREENLEDPIN, 1);
  } else {
    digitalWrite(GREENLEDPIN, 0);
  }
}

void redLed() {
  if (curTemp > redLedTemp || curHumid > redLedHumid) {
    if (redLedRise) {
      redLedOut += redLedStep;
    } else {
      redLedOut -= redLedStep;
    }
    if (redLedOut >= 255) {
      redLedOut = 255;
      redLedRise = 0;
    } else if (redLedOut <= 0) {
      redLedOut = 0;
      redLedRise = 1;
    }
    ledcWrite(0, redLedOut);
  } else {
    ledcWrite(0, 0);
  }
}

void readSerial() {
  int i;
  memset(serialInBuf, 0, SERIALBUFLEN);
  memset(serialArg1, 0, SERIALARGLEN);
  memset(serialArg2, 0, SERIALARGLEN);
  Serial.read(serialInBuf, SERIALBUFLEN);
  for (i = 0; i < SERIALBUFLEN - 1; i++) {
    if (serialInBuf[i] == '#' && serialInBuf[i + 1] == '#') {
      i += 2;
      int j = 0;
      while (serialInBuf[i] != '#') {
        serialArg1[j] = serialInBuf[i];
        j++;
        i++;
      }
      i++;
      j = 0;
      while (serialInBuf[i] != '#') {
        serialArg2[j] = serialInBuf[i];
        j++;
        i++;
      }
      i++;
      if (strcmp(serialArg1, "RLS") == 0) {
        redLedStep = atoi(serialArg2);
        NVS.begin(NVSNAME);
        NVS.putInt("RLS", redLedStep);
        NVS.end();
      }
      if (strcmp(serialArg1, "RLT") == 0) {
        redLedTemp = strtof(serialArg2, NULL);
        NVS.begin(NVSNAME);
        NVS.putFloat("RLT", redLedTemp);
        NVS.end();
      }
      if (strcmp(serialArg1, "RLH") == 0) {
        redLedHumid = strtof(serialArg2, NULL);
        NVS.begin(NVSNAME);
        NVS.putFloat("RLH", redLedHumid);
        NVS.end();
      }
      if (strcmp(serialArg1, "CFR") == 0) {
        cyclesForReadings = atoi(serialArg2);
        NVS.begin(NVSNAME);
        NVS.putInt("CFR", cyclesForReadings);
        NVS.end();
      }
      if (strcmp(serialArg1, "GLL") == 0) {
        greenLightLevel = atoi(serialArg2);
        NVS.begin(NVSNAME);
        NVS.putInt("GLL", greenLightLevel);
        NVS.end();
      }
      if (strcmp(serialArg1, "RESET") == 0) {
        NVS.begin(NVSNAME);
        NVS.clear();
        NVS.end();
      }
      if (strcmp(serialArg1, "GETVARF") == 0) {
        memset(serialOutBuf, 0, SERIALBUFLEN + 1);
        NVS.begin(NVSNAME, true);
        sprintf(serialOutBuf, "++VAR:%f+", NVS.getFloat(serialArg2, -1234));
        Serial.println(serialOutBuf);
        NVS.end();
      }
      if (strcmp(serialArg1, "GETVARI") == 0) {
        memset(serialOutBuf, 0, SERIALBUFLEN + 1);
        NVS.begin(NVSNAME, true);
        sprintf(serialOutBuf, "++VAR:%d+", NVS.getInt(serialArg2, -1234));
        Serial.println(serialOutBuf);
        NVS.end();
      }
      memset(serialArg1, 0, SERIALARGLEN);
      memset(serialArg2, 0, SERIALARGLEN);
    }
  }
}
