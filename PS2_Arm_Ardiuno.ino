#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN  150 // Min pulse length
#define SERVOMAX  600 // Max pulse length

int currentAngles[6] = {0, 0, 0, 0, 0, 0}; // Store current angles in GUI range (-45 to 45)

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(60);
  // Do not set any initial positions; servos remain at their current physical positions
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "READ_POS") {
      // Send current angles as a comma-separated string
      String posString = "";
      for (int i = 0; i < 6; i++) {
        posString += String(currentAngles[i]);
        if (i < 5) posString += ",";
      }
      posString += "\n";
      Serial.print(posString);
    } else {
      // Parse incoming angles (e.g., "-10,20,30,40,50,60")
      int angles[6];
      int index = 0;

      while (input.length() && index < 6) {
        int commaIndex = input.indexOf(',');
        String part = (commaIndex == -1) ? input : input.substring(0, commaIndex);
        angles[index++] = part.toInt();
        input = (commaIndex == -1) ? "" : input.substring(commaIndex + 1);
      }

      if (index == 6) {
        // Update servos and store current angles
        for (int i = 0; i < 6; i++) {
          // Map GUI range (-45 to 45) to servo range (0 to 180)
          int servoAngle = map(angles[i], -45, 45, 0, 180);
          int pulse = map(servoAngle, 0, 180, SERVOMIN, SERVOMAX);
          pwm.setPWM(i, 0, pulse);
          currentAngles[i] = angles[i]; // Store the GUI angle (-45 to 45)
        }
      }
    }
  }
}