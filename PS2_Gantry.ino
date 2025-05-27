#include <AccelStepper.h>

// Define pins for X, Y, Z axes on CNC Shield
#define X_STEP_PIN 2
#define X_DIR_PIN 5
#define Y_STEP_PIN 3
#define Y_DIR_PIN 6
#define Z_STEP_PIN 4
#define Z_DIR_PIN 7
#define ENABLE_PIN 8

// Steps per mm for T8 lead screw (8 mm pitch, 1/16 microstepping)
const float STEPS_PER_MM = 400.0; // 3200 steps/rev / 8 mm/rev = 400 steps/mm
const float MAX_POSITION_MM = 400.0; // 400 mm travel distance

// Initialize steppers (1 = driver type, STEP pin, DIR pin)
AccelStepper stepperX(1, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(1, Y_STEP_PIN, Y_DIR_PIN);
AccelStepper stepperZ(1, Z_STEP_PIN, Z_DIR_PIN);

float currentXPos = 0.0; // Current X/Z position in mm
float currentYPos = 0.0; // Current Y position in mm

void setup() {
  Serial.begin(9600);
  
  // Set up the enable pin (active LOW)
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);
  
  // Configure steppers
  stepperX.setMaxSpeed(1000); // Steps per second
  stepperX.setAcceleration(500); // Steps per second^2
  stepperY.setMaxSpeed(1000);
  stepperY.setAcceleration(500);
  stepperZ.setMaxSpeed(1000);
  stepperZ.setAcceleration(500);
  
  // Initial positions (0 mm)
  stepperX.setCurrentPosition(0);
  stepperY.setCurrentPosition(0);
  stepperZ.setCurrentPosition(0);
  
  Serial.println("CNC Gantry Initialized");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.startsWith("X,")) {
      // Parse X and Y positions (e.g., "X,200,Y,150")
      int xIndex = input.indexOf("X,") + 2;
      int yIndex = input.indexOf(",Y,");
      if (yIndex == -1) return; // Invalid format
      
      String xPosStr = input.substring(xIndex, yIndex);
      String yPosStr = input.substring(yIndex + 3);
      
      float targetXPos = xPosStr.toFloat();
      float targetYPos = yPosStr.toFloat();
      
      // Constrain positions to 0-400 mm
      targetXPos = constrain(targetXPos, 0, MAX_POSITION_MM);
      targetYPos = constrain(targetYPos, 0, MAX_POSITION_MM);
      
      // Convert positions to steps
      long xSteps = targetXPos * STEPS_PER_MM;
      long ySteps = targetYPos * STEPS_PER_MM;
      
      // Move X and Z together, Y independently
      stepperX.moveTo(xSteps);
      stepperZ.moveTo(xSteps); // Synchronize Z with X
      stepperY.moveTo(ySteps);
      
      // Update current positions
      currentXPos = targetXPos;
      currentYPos = targetYPos;
      
      // Run until all steppers reach their targets
      while (stepperX.distanceToGo() != 0 || stepperY.distanceToGo() != 0 || stepperZ.distanceToGo() != 0) {
        stepperX.run();
        stepperY.run();
        stepperZ.run();
      }
      
      // Send confirmation back to GUI
      Serial.print("POS,X,");
      Serial.print(currentXPos);
      Serial.print(",Y,");
      Serial.print(currentYPos);
      Serial.println();
    }
  }
}